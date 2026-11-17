"""Run remaining articles serially, with a fresh AI4Science process per article.

Curator-owned orchestration only: never generate scientific records, commit,
retry automatically, aggregate, or approve matching. See README.md.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (
    "Process only article {article}. Complete its article-level workflow. "
    "Stop after its checked comparison draft. "
    "Do not process another article or aggregate."
)
PREFLIGHT_SOURCES = (
    "METHOD.md",
    "requirements.txt",
    "tools/series.py",
    "tools/ablation_db.py",
    "tools/snapshot_scope.py",
    "data/ablation_snapshot.schema.json",
    "data/snapshot_manifest.json",
)


class BatchError(Exception):
    """A blocker requiring operator attention, not an automatic retry."""


def rows(path: Path) -> list[dict]:
    """Read an operational CSV without interpreting scientific evidence."""
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, strict=True))


def article_id(value: str) -> int:
    """Reject malformed IDs before using them in paths or commands."""
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise BatchError(f"Invalid article ID: {value!r}")
    return int(value)


def plan(root: Path) -> tuple[list[int], list[int]]:
    """Preserve corpus order; existing complete checkpoints still need validation."""
    ids = [article_id(row["article_id"]) for row in rows(root / "data/corpus.csv")]
    if not ids or len(ids) != len(set(ids)):
        raise BatchError("Corpus must contain unique positive article IDs")
    ledger = root / "results/extraction_status.csv"
    statuses = {}
    for row in rows(ledger) if ledger.exists() else []:
        aid = article_id(row["article_id"])
        if aid not in ids or aid in statuses:
            raise BatchError(f"Unknown or duplicate ledger article: {aid}")
        if row["status"] not in {"complete", "pending", "unreadable"}:
            raise BatchError(f"Invalid reading status for article {aid}")
        statuses[aid] = row["status"]
    remaining, completed = [], []
    for aid in ids:
        checkpoint = root / f"results/articles/{aid}/summary.json"
        target = (
            completed
            if statuses.get(aid) == "complete" and checkpoint.exists()
            else remaining
        )
        target.append(aid)
    return remaining, completed


def git(root: Path, *args: str) -> str:
    """Read Git state; never stage or commit on behalf of the agent."""
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise BatchError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def require_clean(root: Path) -> None:
    """Leave dirty scientific or curator changes for explicit human review."""
    changed = git(root, "status", "--porcelain")
    if changed:
        raise BatchError(
            "Working tree is dirty. Review/commit changes before running; "
            f"the runner never stages them:\n{changed}"
        )


def digest(path: Path) -> str:
    """Hash exact bytes, without importing or running numerical code."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_preflight(root: Path, aid: int) -> None:
    """Require an article dry pass bound to the current snapshot and source set."""
    path = root / f"results/verifier/articles/{aid}/dry.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        report.get("step") != "dry"
        or report.get("status") != "pass"
        or report.get("scope") != {"article_id": aid}
        or report.get("violations") != []
    ):
        raise BatchError(f"Article {aid}: missing/failed/wrong-scope dry preflight")
    expected = {p: digest(root / p) for p in PREFLIGHT_SOURCES}
    expected.update(
        {
            str(p.relative_to(root)): digest(p)
            for p in sorted((root / "checks/verifier").glob("*.py"))
        }
    )
    if (
        report.get("snapshot_sha256") != digest(root / "data/ablation_snapshot.json")
        or report.get("schema_sha256")
        != digest(root / "data/ablation_snapshot.schema.json")
        or report.get("provenance", {}).get("source_sha256") != expected
    ):
        raise BatchError(f"Article {aid}: stale dry preflight; curator review required")


def stop_group(process: subprocess.Popen) -> None:
    """Stop launcher, Goose and proxy together, including unresponsive children."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def command(args: list[str], root: Path, log: Path, timeout: float, env: dict) -> None:
    """Capture real exit codes; no terminal input or inherited conversation."""
    with log.open("a", encoding="utf-8") as output:
        output.write(f"\n$ {shlex.join(args)}\n")
        output.flush()
        process = subprocess.Popen(
            args,
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            stop_group(process)
            raise BatchError(f"Timed out after {timeout:g}s; see {log}") from error
        except BaseException:
            stop_group(process)
            raise
        # A launcher can exit while a proxy/tool child remains in its group.
        # Drain that group before validation or the next fresh invocation.
        stop_group(process)
        output.write(f"\n[runner] exit={code}\n")
    if code:
        raise BatchError(f"Command exited {code}; see {log}")


def validate(root: Path, aid: int, log: Path, env: dict) -> None:
    """Delegate scientific validation to the supplied independent checker."""
    command(
        [
            str(root / ".venv/bin/python"),
            "checks/check.py",
            "--article",
            str(aid),
            "--analysis",
            "draft",
        ],
        root,
        log,
        120,
        env,
    )
    validate_preflight(root, aid)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def positive_seconds(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def interrupted(signum, frame) -> None:
    """Convert SIGTERM into the same child-cleanup path as Ctrl-C."""
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("smart_approve", "auto", "approve"),
        default="smart_approve",
        help="Goose permission mode (default: smart_approve)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the queue only; no agent, checker, locks or log writes",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        help="process at most this many remaining articles",
    )
    parser.add_argument(
        "--timeout",
        type=positive_seconds,
        default=1800,
        help="seconds allowed per agent process (default: 1800)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.home() / "ai4science-batch",
        help="log directory outside the project",
    )
    parser.add_argument(
        "--agent", default="ai4science", help="AI4Science executable name or path"
    )
    parser.add_argument("--project", type=Path, default=ROOT, help="project root")
    args = parser.parse_args(argv)
    root = args.project.resolve()
    previous_handler = signal.signal(signal.SIGTERM, interrupted)
    old_umask = os.umask(0o077)
    try:
        remaining, completed = plan(root)
        selected = remaining[: args.limit]
        print(
            f"Mode: {args.mode}; remaining: {len(remaining)}; selected: {len(selected)}",
            flush=True,
        )
        print(
            f"Existing checkpoints to validate before skipping: {completed}", flush=True
        )
        print(f"Queue (corpus order): {selected}", flush=True)
        if args.dry_run:
            print(
                "Preview only: checkpoint validity and Git cleanliness have not been checked."
            )
            return 0
        log_dir = args.log_dir.expanduser().resolve()
        if log_dir.is_relative_to(root):
            raise BatchError(
                "Logs must be outside the project to avoid readiness failures"
            )
        lock_path = Path(git(root, "rev-parse", "--git-path", "ai4science-batch.lock"))
        if not lock_path.is_absolute():
            lock_path = root / lock_path
        with lock_path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise BatchError(
                    "Another article runner holds this checkout's lock"
                ) from error
            # Re-read only after acquiring the lock; a previous runner may have finished.
            require_clean(root)
            remaining, completed = plan(root)
            selected = remaining[: args.limit]
            agent = shutil.which(args.agent)
            if selected and agent is None:
                raise BatchError(f"AI4Science executable not found: {args.agent}")
            if agent is not None:
                agent = str(Path(agent).resolve())
            python = root / ".venv/bin/python"
            if not os.access(python, os.X_OK):
                raise BatchError(f"Project Python is not executable: {python}")
            log_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            run_dir = Path(tempfile.mkdtemp(prefix=stamp, dir=log_dir))
            print(f"Logs: {run_dir}", flush=True)
            (run_dir / "queue.json").write_text(
                json.dumps(
                    {
                        "project": str(root),
                        "mode": args.mode,
                        "queue": remaining,
                        "selected": selected,
                        "existing_checkpoints": completed,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "AI4SCIENCE_WEB_DISABLED": "1",
                "AI4SCIENCE_LEAN_DISABLED": "1",
            }
            for aid in completed:
                print(f"Validate existing article {aid}", flush=True)
                validate(root, aid, run_dir / f"{aid}-existing.log", env)
            for index, aid in enumerate(selected, 1):
                require_clean(root)
                log = run_dir / f"{aid}.log"
                print(f"[{index}/{len(selected)}] Article {aid}: {log}", flush=True)
                command(
                    [
                        agent,
                        "run",
                        "--no-lean",
                        "--mode",
                        args.mode,
                        "--",
                        PROMPT.format(article=aid),
                    ],
                    root,
                    log,
                    args.timeout,
                    env,
                )
                validate(root, aid, log, env)
                require_clean(root)
                print(f"Article {aid}: checked draft complete", flush=True)
            print(
                f"Finished {len(selected)} article(s); {len(remaining) - len(selected)} still queued. "
                "No aggregation or curator approval performed.",
                flush=True,
            )
        return 0
    except KeyboardInterrupt:
        print(
            "Stopped: interrupted. Review the current article before restarting.",
            file=sys.stderr,
        )
        return 130
    except (
        BatchError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        csv.Error,
        subprocess.SubprocessError,
    ) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    finally:
        os.umask(old_umask)
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
