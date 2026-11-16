"""Mechanical candidates and context, without scientific decisions or scores."""

import re

from tools.ablation_db import SnapshotTools

from .inputs import (
    MEDIA,
    MODELS,
    SHAPES,
    PipelineError,
    json_object,
    require,
    scope_marker,
)


def load_series(data, tools=None):
    """Use one fixed snapshot view; never recalculate size/error/shape here."""
    result = {}
    try:
        if tools is None:
            snapshot = (
                data.snapshot
                if data.article is not None
                else json_object(
                    data.sources.read("data/ablation_snapshot.json"), "snapshot"
                )
            )
            tools = SnapshotTools.from_data(snapshot)
        for aid in data.ids:
            for row in tools.list_series(aid):
                sid = row["series_id"]
                require(
                    type(row["article_id"]) is int and row["article_id"] == aid,
                    f"series belongs to another article: {sid}",
                )
                require(
                    isinstance(sid, str) and re.fullmatch(rf"{aid}-s[1-9][0-9]*", sid),
                    f"invalid series ID: {sid}",
                )
                require(sid not in result, f"duplicate series: {sid}")
                require(row["medium_class"] in MEDIA, f"invalid series medium: {sid}")
                require(
                    all(row[f"shape_{model}"] in SHAPES for model in MODELS),
                    f"invalid series shape: {sid}",
                )
                result[sid] = row
    except PipelineError:
        raise
    except Exception as error:
        raise PipelineError(f"series tools failed: {error}") from error
    return result


def candidate_pairs(data, series):
    """Return every same-article/medium pair, including no-candidate entries."""
    pairs = []
    for claim in sorted(data.own_claims, key=lambda row: row["claim_id"]):
        matches = sorted(
            sid
            for sid, row in series.items()
            if row["article_id"] == int(claim["article_id"])
            and (
                claim["medium_class"] == "unspecified"
                or claim["medium_class"] == row["medium_class"]
            )
        )
        pairs.extend((claim["claim_id"], sid) for sid in matches or [""])
    return pairs


def workspace(data, series):
    """Derived context only: no suggested judgments or agreement labels."""
    claims = {row["claim_id"]: row for row in data.own_claims}
    hidden = {"shape_primary", "shape_lenient", "spearman_rho"}
    return {
        "format": 1,
        "inputs": data.hashes,
        **({"scope": scope_marker(data.article)} if data.article is not None else {}),
        "candidates": [
            {
                "claim": claims[cid],
                "series": {k: v for k, v in series[sid].items() if k not in hidden}
                if sid
                else None,
            }
            for cid, sid in candidate_pairs(data, series)
        ],
    }
