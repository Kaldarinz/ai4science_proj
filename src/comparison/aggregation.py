"""Resume-friendly corpus assembly from independently bound article checkpoints."""

from tools.ablation_db import SnapshotTools

from .candidates import load_series, workspace
from .comparison import compare
from .inputs import (
    AUDIT,
    AUDIT_COLUMNS,
    COMPARISON,
    COMPARISON_COLUMNS,
    SUMMARY,
    WORKSPACE,
    digest,
    json_object,
    load_inputs,
    require,
)
from .outputs import csv_bytes, json_bytes, publish
from .summary import summarize


def validated_checkpoints(data, tools=None):
    """Verify every completed article, returning merged decisions and raw bindings."""
    from . import _render

    rows, bindings = [], {}
    for aid in data.ids:
        if data.statuses[str(aid)] != "complete":
            continue
        part = load_inputs(data.sources.root, aid)
        series = load_series(part, tools)
        audit, comparison, summary = _render(part, series, "draft", tools)
        require(
            part.sources.read(part.path(COMPARISON)) == comparison,
            f"article {aid}: comparison checkpoint is stale or edited; rebuild/check it",
        )
        stored = json_object(part.sources.read(part.path(SUMMARY)), part.path(SUMMARY))
        require(
            json_bytes(stored) == json_bytes(summary),
            f"article {aid}: summary checkpoint is stale or edited; rebuild/check it",
        )
        for relative in (WORKSPACE, AUDIT, COMPARISON, SUMMARY):
            path = part.path(relative)
            bindings[path] = digest(part.sources.read(path))
        # Merge captured bytes so the outer operation detects concurrent edits.
        for path, raw in part.sources.raw.items():
            require(
                path not in data.sources.raw or data.sources.raw[path] == raw,
                f"input changed during aggregation: {path}",
            )
            data.sources.raw[path] = raw
        rows.extend(audit)
    rows.sort(key=lambda row: (row["claim_id"], row["series_id"]))
    return rows, bindings


def aggregate_locked(root, tools=None):
    data = load_inputs(root)
    if tools is None:
        tools = SnapshotTools.from_data(
            json_object(data.sources.read("data/ablation_snapshot.json"), "snapshot")
        )
    audit, bindings = validated_checkpoints(data, tools)
    series = load_series(data, tools)
    comparison = compare(data, series, audit)
    audit_raw = csv_bytes(audit, AUDIT_COLUMNS)
    raw = csv_bytes(comparison, COMPARISON_COLUMNS)
    fingerprints = {**data.hashes, AUDIT: digest(audit_raw), COMPARISON: digest(raw)}
    summary = summarize(data, series, audit, comparison, fingerprints, "draft")
    context = {**workspace(data, series), "checkpoints": bindings}
    data.sources.verify_unchanged()
    # Global files are derived. Article audits/checkpoints are never replaced.
    publish(
        data.sources.root,
        {
            WORKSPACE: json_bytes(context),
            AUDIT: audit_raw,
            COMPARISON: raw,
            SUMMARY: json_bytes(summary),
        },
    )
    return summary
