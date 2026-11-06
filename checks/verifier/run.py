"""HW2 contract check and gated paired sensitivity experiment: dry → smoke → full."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checks.verifier.contract import (
    SNAPSHOT_PATH,
    SNAPSHOT_SHA256,
    Violation,
    check_series,
    check_snapshot,
    load_json,
)
from checks.verifier.resampling import (
    CONFIGS,
    RUN_FIELDS,
    collect_cases,
    summarize,
    sweep,
)

BASELINE_COMMIT = "e9fecd3"


def digest(path: Path) -> str:
    """Hash exact file bytes for the provenance record."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(path: Path = SNAPSHOT_PATH) -> dict:
    """Run the pinned-snapshot contract; return no scientific shape outputs."""
    started = time.monotonic()
    report = {"step": "dry", "status": "fail", "snapshot_sha256": digest(path),
              "baseline_commit": BASELINE_COMMIT, "series": [], "exclusions": [], "violations": []}
    errors = []
    if report["snapshot_sha256"] != SNAPSHOT_SHA256:
        errors.append(Violation("snapshot_hash_mismatch", str(path), "snapshot differs from METHOD §3"))
    try:
        raw = load_json(path)
        errors.extend(check_snapshot(raw))
    except (ValueError, OSError) as error:
        errors.append(Violation("invalid_json", str(path), str(error)))
    if not errors:
        # Import the system under verification only after independent raw checks.
        from tools.ablation_db import SnapshotTools

        try:
            db = SnapshotTools(path)
            for article in db.find_articles():
                aid = article["article_id"]
                for row in db.list_series(aid):
                    for model in ("primary", "lenient"):
                        errors.extend(check_series(raw, db.get_series(row["series_id"], model), model=model))
                    report["series"].append({k: row[k] for k in ("series_id", "article_id", "n_points", "x_quantity")})
                report["exclusions"].extend(db.list_exclusions(aid))
            reference = [r for r in report["series"] if r["article_id"] == 80094]
            if [(r["series_id"], r["n_points"], r["x_quantity"]) for r in reference] != [
                    ("80094-s1", 6, "pulse_energy"), ("80094-s2", 6, "pulse_energy")]:
                errors.append(Violation("reference_mismatch", "80094", "expected two six-point energy series"))
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            errors.append(Violation("build_failure", "SnapshotTools", f"{type(error).__name__}: {error}"))
    report["violations"] = [e.as_dict() for e in errors]
    report["status"] = "pass" if not errors else "fail"
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return report


def provenance() -> dict:
    """Record code hashes, actual checkout, and dependency versions, not results."""
    sources = [ROOT / p for p in ("METHOD.md", "requirements.txt", "tools/series.py", "tools/ablation_db.py",
                                  "data/ablation_snapshot.schema.json")]
    sources.extend(sorted((ROOT / "checks/verifier").glob("*.py")))
    return {
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
        "python": platform.python_version(),
        "packages": {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "pytest", "hypothesis", "jsonschema")},
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
    }


def write_csv(path: Path, rows: list[dict], fields: tuple | list) -> None:
    """Write UTF-8 CSV without platform-dependent newlines."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def require_smoke(directory: Path, report: dict) -> list[dict]:
    """Fail closed unless a complete smoke run matches the current source."""
    smoke_path = directory / "smoke.json"
    smoke = load_json(smoke_path)
    if (smoke.get("step") != "smoke" or smoke.get("status") != "pass"
            or smoke.get("snapshot_sha256") != report["snapshot_sha256"]
            or smoke.get("provenance", {}).get("source_sha256") != report["provenance"]["source_sha256"]):
        raise ValueError("run smoke with the current snapshot and source before full")
    csv_path = directory / "smoke_runs.csv"
    if smoke.get("artifacts", {}).get("smoke_runs.csv") != digest(csv_path):
        raise ValueError("smoke run CSV does not match its manifest")
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(r["series_id"], m) for r in report["series"] for m in ("primary", "lenient")}
    if (len(rows) != len(expected) or {(r["series_id"], r["model"]) for r in rows} != expected
            or any(r["step"] != "smoke" or r["seed"] != "0" or r["draws"] != "100" for r in rows)):
        raise ValueError("smoke must cover every series/model with seed 0 and 100 draws")
    report["prerequisite_smoke_sha256"] = digest(smoke_path)
    return rows


def experiment(step: str, directory: Path, report: dict) -> None:
    """Gate each sweep on contract/properties and full on a matching smoke run."""
    previous = require_smoke(directory, report) if step == "full" else []
    check = subprocess.run(
        [sys.executable, "-m", "pytest", "checks/verifier", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    check_path = directory / f"{step}_preflight.txt"
    check_path.write_text(check.stdout + check.stderr, encoding="utf-8")
    if check.returncode:
        raise ValueError(f"property/reference preflight failed; see {check_path.name}")
    from tools.ablation_db import SnapshotTools

    cases = collect_cases(SnapshotTools())
    if {c["series_id"] for c in cases} != {r["series_id"] for r in report["series"]}:
        raise ValueError("series changed after the contract preflight")
    rows = sweep(cases, step, report["provenance"]["git_head"])
    expected_rows = len(cases) * 2 * len(CONFIGS[step]["seeds"])
    if len(rows) != expected_rows or digest(SNAPSHOT_PATH) != report["snapshot_sha256"]:
        raise ValueError("incomplete sweep or snapshot changed during run")
    # Fail before publishing CSVs if inference cannot be completed.
    summary = summarize(rows) if step == "full" else []
    csv_path = directory / f"{step}_runs.csv"
    write_csv(csv_path, rows, RUN_FIELDS)
    write_csv(directory / "runs.csv", [*previous, *rows], RUN_FIELDS)
    if summary:
        write_csv(directory / "summary.csv", summary, list(summary[0]))
    report["config"] = {"seeds": list(CONFIGS[step]["seeds"]), "draws": CONFIGS[step]["draws"],
                        "models": ["primary", "lenient"], "fixed_errors": True,
                        "noise_sigma": "original primary error", "paired_z": True,
                        "truncate_negative_sizes": False, "baseline_weights": "inverse primary variance"}
    report["n_series"] = len(cases)
    report["n_rows"] = len(rows)
    report["summary"] = summary
    # The combined log is rewritten by full: do not give smoke a hash of
    # that mutable derivative. Its immutable stage-specific CSV is retained.
    artifacts = [csv_path, check_path]
    if summary:
        artifacts.extend([directory / "summary.csv", directory / "runs.csv"])
    report["artifacts"] = {p.name: digest(p) for p in artifacts}


def main(argv: list[str] | None = None) -> int:
    """Run only the requested stage and log failures without scientific exceptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["dry", "smoke", "full"])
    parser.add_argument("--output", type=Path, help="dry JSON only, within results/verifier/")
    args = parser.parse_args(argv)
    directory = ROOT / "results/verifier"
    if args.output is not None and args.step != "dry":
        parser.error("--output is only supported for dry")
    output = (args.output or directory / f"{args.step}.json").resolve()
    if not output.is_relative_to(directory.resolve()):
        parser.error("--output must be inside results/verifier/")
    started = time.monotonic()
    report = evaluate()
    report["step"] = args.step
    report["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["provenance"] = provenance()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.step != "dry" and report["status"] == "pass":
        try:
            experiment(args.step, directory, report)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, subprocess.TimeoutExpired) as error:
            report["status"] = "fail"
            report["violations"].append(Violation("experiment_failure", args.step, f"{type(error).__name__}: {error}").as_dict())
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
