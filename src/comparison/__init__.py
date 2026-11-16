"""Supplied deterministic comparison pipeline; scientific judgments stay external."""

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

from .candidates import load_series, workspace
from .comparison import compare
from .inputs import (
    AUDIT,
    AUDIT_COLUMNS,
    COMPARISON,
    COMPARISON_COLUMNS,
    SUMMARY,
    WORKSPACE,
    PipelineError,
    artifact_path,
    digest,
    json_object,
    load_inputs,
    require,
    scope_marker,
)
from .outputs import csv_bytes, json_bytes, publish, validate_final
from .summary import summarize

DEFAULT_ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def operation_lock(root):
    """Serialize pipeline operations; never unlink a lock another process holds."""
    directory = Path(root).resolve() / "results"
    require(
        directory.resolve().is_relative_to(Path(root).resolve()),
        "results directory is outside project",
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".comparison.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o660)
    except FileExistsError:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    else:
        os.fchmod(fd, 0o660)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PipelineError("another comparison operation is running") from error
        yield
    finally:
        os.close(fd)


def prepare(root=DEFAULT_ROOT, *, article=None, tools=None):
    """Write one article's context (or the legacy corpus context), never decisions."""
    with operation_lock(root):
        data = load_inputs(root, article)
        series = load_series(data, tools)
        document = workspace(data, series)
        relative = data.path(WORKSPACE)
        path = data.sources.root / relative
        previous = (
            json_object(data.sources.read(relative), relative)
            if path.exists()
            else None
        )
        if previous != document:
            require(
                not (data.sources.root / data.path(AUDIT)).exists(),
                "preparation changed or is missing while an audit exists; archive the old audit, "
                "rerun prepare, then re-review this scope's matching decisions",
            )
        data.sources.verify_unchanged()
        publish(data.sources.root, {relative: json_bytes(document)})
        return document


def _render(data, series, stage, tools=None):
    """Validate/serialize without publishing; used by build and aggregation."""
    relative = data.path(WORKSPACE)
    prepared = json_object(data.sources.read(relative), relative)
    checkpoint_bindings = (
        prepared.pop("checkpoints", None) if data.article is None else None
    )
    require(
        json_bytes(prepared) == json_bytes(workspace(data, series)),
        "candidate preparation is stale or edited; rerun prepare and review the audit",
    )
    audit = data.sources.table(data.path(AUDIT), AUDIT_COLUMNS)
    if data.article is None:
        has_checkpoints = any(
            (data.sources.root / artifact_path(AUDIT, aid)).exists()
            for aid in data.ids
            if data.statuses[str(aid)] == "complete"
        )
        if checkpoint_bindings is not None or has_checkpoints:
            require(
                checkpoint_bindings is not None,
                "article checkpoints exist; run aggregate to generate the corpus draft",
            )
            from .aggregation import validated_checkpoints

            rows, bindings = validated_checkpoints(data, tools)
            require(
                checkpoint_bindings == bindings,
                "article checkpoints changed; rerun aggregate and obtain new approval",
            )
            require(
                csv_bytes(audit, AUDIT_COLUMNS) == csv_bytes(rows, AUDIT_COLUMNS),
                "corpus audit differs from article checkpoints; rerun aggregate",
            )
    comparison = compare(data, series, audit)
    raw = csv_bytes(comparison, COMPARISON_COLUMNS)
    fingerprints = {
        **data.hashes,
        data.path(AUDIT): digest(data.sources.read(data.path(AUDIT))),
        data.path(COMPARISON): digest(raw),
    }
    summary = summarize(data, series, audit, comparison, fingerprints, stage)
    if data.article is not None:
        summary["scope"] = scope_marker(data.article)
    if stage == "final":
        validate_final(data.sources, summary, raw)
    return audit, raw, summary


def build(root=DEFAULT_ROOT, *, stage, article=None, tools=None):
    """Publish one article checkpoint or a curator-gated corpus result."""
    require(stage in ("draft", "final"), "stage must be draft or final")
    require(
        article is None or stage == "draft",
        "article checkpoints use stage=draft; final approval is corpus-wide after aggregate",
    )
    with operation_lock(root):
        data = load_inputs(root, article)
        require(
            stage != "final" or "pending" not in data.statuses.values(),
            "final analysis cannot contain pending articles",
        )
        series = load_series(data, tools)
        _, raw, summary = _render(data, series, stage, tools)
        data.sources.verify_unchanged()
        publish(
            data.sources.root,
            {data.path(COMPARISON): raw, data.path(SUMMARY): json_bytes(summary)},
        )
        return summary


def aggregate(root=DEFAULT_ROOT, *, tools=None):
    """Merge validated article checkpoints into a corpus draft, never approval."""
    from .aggregation import aggregate_locked

    with operation_lock(root):
        return aggregate_locked(root, tools)
