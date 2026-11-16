"""Validate agent-authored decisions and apply the concordance specification."""

from .candidates import candidate_pairs
from .inputs import ASSESSMENTS, MODELS, require


def validate_audit(data, series, audit):
    remaining = set(candidate_pairs(data, series))
    for row in audit:
        pair = (row["claim_id"], row["series_id"])
        require(pair in remaining, f"audit: unexpected or duplicate pair {pair}")
        remaining.remove(pair)
        decision, assessment = row["decision"], row["assessment"]
        require(
            decision in ("include", "exclude", "no_candidates"),
            f"audit {pair}: invalid decision",
        )
        require(
            (not pair[1]) == (decision == "no_candidates"),
            f"audit {pair}: invalid no_candidates decision",
        )
        require(
            row["reason"].strip() and row["caveats"].strip(),
            f"audit {pair}: reason and caveats required",
        )
        if decision == "include":
            require(assessment in ASSESSMENTS, f"audit {pair}: assessment required")
            if assessment != "direct":
                require(
                    row["caveats"].strip().casefold() != "none",
                    f"audit {pair}: substantive caveats required",
                )
        else:
            require(not assessment, f"audit {pair}: assessment must be empty")
    require(not remaining, f"audit: missing pairs {sorted(remaining)}")


def agrees(direction, shape):
    """Concordance under the recorded assumptions, not proof of the claim."""
    if direction == "affects":
        return shape != "flat"
    if direction == "non_monotonic":
        return shape in ("peak", "valley", "irregular")
    return (
        shape
        == {"increase": "increasing", "decrease": "decreasing", "no_effect": "flat"}[
            direction
        ]
    )


def compare(data, series, audit):
    validate_audit(data, series, audit)
    claims = {row["claim_id"]: row for row in data.own_claims}
    result = []
    for decision in sorted(audit, key=lambda row: (row["claim_id"], row["series_id"])):
        if decision["decision"] != "include":
            continue
        cid, sid = decision["claim_id"], decision["series_id"]
        row = {
            "claim_id": cid,
            "series_id": sid,
            "direction": claims[cid]["direction"],
            "assessment": decision["assessment"],
            "note": f"Audit {cid}/{sid}: {decision['reason']}; caveats: {decision['caveats']}",
        }
        for model in MODELS:
            shape = series[sid][f"shape_{model}"]
            row[f"shape_{model}"] = shape
            row[f"agree_{model}"] = (
                ""
                if row["assessment"] == "unassessable"
                else str(agrees(row["direction"], shape)).lower()
            )
        result.append(row)
    return result
