"""Article-set accounting and conservative outcomes, independently implemented."""

from scipy.stats import binomtest

from .inputs import (
    ASSESSMENTS,
    BASES,
    DIRECTIONS,
    MODELS,
    OUTCOMES,
    SHAPES,
    STATUSES,
    VARIABLES,
)


def claim_outcome(records, model):
    positive = negative = unknown = 0
    for row in records:
        value = row[f"agree_{model}"]
        positive += value == "true"
        negative += value == "false"
        unknown += value == ""
    if positive and negative:
        return "mixed"
    if unknown or not records:
        return "unassessable"
    return "all_agree" if positive else "all_disagree"


def pair_counts(records, model):
    result = {
        "n_included": 0,
        "n_assessable": 0,
        "agree": 0,
        "disagree": 0,
        "unassessable": 0,
    }
    for row in records:
        result["n_included"] += 1
        value = row[f"agree_{model}"]
        if value:
            result["n_assessable"] += 1
            result["agree" if value == "true" else "disagree"] += 1
        else:
            result["unassessable"] += 1
    return result


def summarize(data, series, audit, comparison, fingerprints, stage):
    complete = {aid for aid, status in data.statuses.items() if status == "complete"}
    prevalence, unspecified = set(), set()
    by_basis = {basis: set() for basis in BASES}
    by_direction = {direction: set() for direction in DIRECTIONS}
    cross = {basis: {direction: set() for direction in DIRECTIONS} for basis in BASES}
    for claim in data.claims:
        aid = claim["article_id"]
        if aid not in complete:
            continue
        if claim["variable"] == "unspecified":
            unspecified.add(aid)
        if claim["variable"] in VARIABLES:
            prevalence.add(aid)
            by_basis[claim["basis"]].add(aid)
            by_direction[claim["direction"]].add(aid)
            cross[claim["basis"]][claim["direction"]].add(aid)
    articles = {
        "n_corpus": len(data.ids),
        **{
            f"n_{status}": list(data.statuses.values()).count(status)
            for status in STATUSES
        },
        "prevalence": {
            "numerator": len(prevalence),
            "denominator": len(complete),
            "fraction": len(prevalence) / len(complete) if complete else None,
        },
        "n_with_unspecified_claim": len(unspecified),
        "by_basis": {key: len(value) for key, value in by_basis.items()},
        "by_direction": {key: len(value) for key, value in by_direction.items()},
        "by_basis_and_direction": {
            basis: {key: len(value) for key, value in cells.items()}
            for basis, cells in cross.items()
        },
    }
    groups = {row["claim_id"]: [] for row in data.own_claims}
    for row in comparison:
        groups[row["claim_id"]].append(row)
    outcomes = {}
    for cid, rows in sorted(groups.items()):
        outcomes[cid] = {
            **{model: claim_outcome(rows, model) for model in MODELS},
            "n_included": len(rows),
            "n_qualified": sum(row["assessment"] == "qualified" for row in rows),
            "n_unassessable": sum(row["assessment"] == "unassessable" for row in rows),
        }
    unmatched = {row["claim_id"] for row in audit if row["decision"] == "no_candidates"}
    included = {cid for cid, rows in groups.items() if rows}
    comparison_summary = {
        "n_own_data_claims": len(groups),
        "n_with_candidates": len(groups) - len(unmatched),
        "n_without_candidates": len(unmatched),
        "n_with_included_series": len(included),
        "n_all_candidates_excluded": len(set(groups) - unmatched - included),
        "n_candidate_pairs": sum(row["series_id"] != "" for row in audit),
        "n_included_pairs": len(comparison),
        "n_excluded_pairs": sum(row["decision"] == "exclude" for row in audit),
        "claim_outcomes": outcomes,
        "by_model": {},
    }
    for model in MODELS:
        counts = {outcome: 0 for outcome in OUTCOMES}
        for values in outcomes.values():
            counts[values[model]] += 1
        comparison_summary["by_model"][model] = {
            "claims": {"denominator": len(groups), **counts},
            "pairs": pair_counts(comparison, model),
            "pairs_by_assessment": {
                assessment: pair_counts(
                    [row for row in comparison if row["assessment"] == assessment],
                    model,
                )
                for assessment in ASSESSMENTS
            },
        }
    diagnostics = {}
    for model in MODELS:
        counts = dict.fromkeys(SHAPES, 0)
        for row in series.values():
            counts[row[f"shape_{model}"]] += 1
        n = counts["increasing"] + counts["decreasing"]
        diagnostics[model] = {
            "counts": counts,
            "n_test": n,
            "p_value": float(
                binomtest(counts["increasing"], n, 0.5, alternative="greater").pvalue
            )
            if n
            else None,
        }
    return {
        "contract_version": 1,
        "stage": stage,
        "inputs": fingerprints,
        "articles": articles,
        "comparison": comparison_summary,
        "series": diagnostics,
    }
