"""Stable serialization, approval validation, and staged publication."""

import csv
import io
import json
import os
import tempfile
from datetime import date
from pathlib import Path

from .inputs import COMPARISON, REVIEW, SUMMARY, PipelineError, json_object, require


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def validate_final(sources, summary, comparison_bytes):
    """Require an unchanged existing draft and a separately authored approval."""
    require(
        sources.read(COMPARISON) == comparison_bytes,
        "final requires the current comparison from a generated draft; build/check a new draft first",
    )
    previous = json_object(sources.read(SUMMARY), SUMMARY)
    require(
        previous.get("stage") in ("draft", "final"),
        "final requires an existing draft summary",
    )
    previous["stage"] = "final"
    require(
        json_bytes(previous) == json_bytes(summary),
        "draft inputs or results changed; regenerate/check the draft and obtain new curator approval",
    )
    review = json_object(sources.read(REVIEW), REVIEW)
    require(
        set(review) == {"decision", "reviewer", "date", "inputs"},
        "invalid matching approval keys",
    )
    require(
        review["decision"] == "accepted"
        and isinstance(review["reviewer"], str)
        and review["reviewer"].strip(),
        "matching approval requires curator acceptance and reviewer",
    )
    try:
        require(
            isinstance(review["date"], str)
            and date.fromisoformat(review["date"]).isoformat() == review["date"],
            "invalid matching approval date",
        )
    except ValueError as error:
        raise PipelineError("invalid matching approval date") from error
    require(
        json_bytes(review["inputs"]) == json_bytes(summary["inputs"]),
        "matching approval is stale: its inputs differ from the current draft",
    )


def publish(root, artifacts):
    """Stage all bytes before replacing anything; restore originals on errors.

    Each rename is atomic. Summary is published last by the caller; a crash
    between renames is detectable by its comparison fingerprint, not certified
    as a coherent result. This is not a multi-file filesystem transaction.
    """
    root = Path(root).resolve()
    temporary, backups, installed = {}, {}, []

    def stage(target, raw, mode):
        fd, name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        temporary_paths.add(Path(name))
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return Path(name)

    temporary_paths = set()
    try:
        for relative, raw in artifacts.items():
            target = root / relative
            require(
                target.resolve().is_relative_to(root)
                and not any(
                    path.is_symlink()
                    for path in (target, *target.parents)
                    if path.is_relative_to(root) and path != root
                ),
                f"refusing output outside project or through symlink: {relative}",
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            old = target.read_bytes() if target.exists() else None
            if old == raw:
                continue
            mode = target.stat().st_mode & 0o777 if old is not None else 0o660
            temporary[target] = stage(target, raw, mode)
            backups[target] = stage(target, old, mode) if old is not None else None
        for target, name in temporary.items():
            os.replace(name, target)
            installed.append(target)
    except BaseException as failure:
        recovery = []
        for target in reversed(installed):
            backup = backups[target]
            try:
                if backup is None:
                    target.unlink()
                else:
                    os.replace(backup, target)
            except OSError as error:
                # Never discard the only recovery copy if the filesystem also
                # prevents rollback. Report its path for manual recovery.
                if backup is not None:
                    temporary_paths.discard(backup)
                recovery.append(f"{target}: {error}; original backup: {backup}")
        if recovery:
            raise PipelineError(
                "publication failed; manual recovery needed: " + "; ".join(recovery)
            ) from failure
        raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
