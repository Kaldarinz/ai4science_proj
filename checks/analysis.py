"""Independent, read-only acceptance checks for results_spec §§5–6.

No imports from src/, no scientific matching decisions, no output generation.
Numerical tools are supplied by the caller only in explicit analysis mode.
"""

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

STATUS_COLUMNS = ("article_id", "status", "files_sha256", "reason")
AUDIT_COLUMNS = ("claim_id", "series_id", "decision", "assessment", "reason", "caveats")
COMPARISON_COLUMNS = (
    "claim_id", "series_id", "direction", "shape_primary", "shape_lenient",
    "agree_primary", "agree_lenient", "assessment", "note",
)
STATUSES = ("complete", "pending", "unreadable")
DECISIONS = ("include", "exclude", "no_candidates")
ASSESSMENTS = ("direct", "qualified", "unassessable")
OUTCOMES = ("all_agree", "all_disagree", "mixed", "unassessable")
MODELS = ("primary", "lenient")
BASES = ("own_data", "cited", "general")
DIRECTIONS = ("increase", "decrease", "no_effect", "non_monotonic", "affects")
SHAPES = ("flat", "increasing", "decreasing", "peak", "valley", "irregular")
VARIABLES = frozenset({"fluence", "energy", "power", "intensity"})
AGREES = {
    "increase": {"increasing"}, "decrease": {"decreasing"},
    "no_effect": {"flat"}, "non_monotonic": {"peak", "valley", "irregular"},
    "affects": set(SHAPES) - {"flat"},
}
# Exact raw-byte hashes bind a review and summary to these inputs, not to Git HEAD.
INPUT_PATHS = (
    "data/corpus.csv", "data/files.csv", "data/ablation_snapshot.json",
    "data/ablation_snapshot.schema.json", "results/claims.csv",
    "results/no_claims.csv", "results/extraction_status.csv",
    "results/matching_audit.csv", "results/comparison.csv",
    "checks/claims_spec.md", "checks/results_spec.md", "ontology.yaml",
    "checks/analysis.py", "checks/check.py", "tools/ablation_db.py", "tools/series.py",
)


def rows(root, relative, columns, report):
    """Strict CSV reader; malformed input fails closed with a named rule."""
    try:
        path = root / relative
        raw = path.read_bytes()
        if not raw.endswith(b"\n"):
            raise ValueError("missing final newline")
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != list(columns):
                raise ValueError(f"expected columns {list(columns)}")
            result = list(reader)
        if any(None in row or None in row.values() for row in result):
            raise ValueError("row field count differs from header")
        return result
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        report.fail("analysis input", f"{relative}: {error}")
        return None


def read_json(root, relative, report):
    """Reject duplicate keys and non-standard non-finite JSON numbers."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"non-finite number {value}")

    try:
        value = json.loads((root / relative).read_text(encoding="utf-8"),
                           object_pairs_hook=unique, parse_constant=nonfinite)
        if not isinstance(value, dict):
            raise ValueError("root must be a JSON object")
        return value
    except (OSError, UnicodeError, ValueError) as error:
        report.fail("analysis input", f"{relative}: {error}")
        return None


def files_digest(files, article_id):
    """Fingerprint the current supplied main/SI inventory of one article."""
    entries = sorted([r["file"], r["role"], r["sha256"]]
                     for r in files if r["article_id"] == str(article_id))
    raw = json.dumps(entries, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def check_coverage(root, report, ids, claims, article=None):
    """Validate reading attestations without consulting numerical inputs.

    Called only when the ledger exists or analysis was explicitly requested.
    Legacy claim-only checks without a ledger are not analysis certification.
    """
    before = report.failures
    ledger = rows(root, "results/extraction_status.csv", STATUS_COLUMNS, report)
    files = rows(root, "data/files.csv", ("article_id", "file", "role", "sha256"), report)
    negatives = rows(root, "results/no_claims.csv",
                     ("article_id", "file", "page", "quote", "reason"), report)
    if ledger is None or files is None or negatives is None:
        return {}
    scope = {str(aid) for aid in ids}
    # In --article mode other articles' rows are outside this readiness check.
    selected = [r for r in ledger if article is None or r["article_id"] == str(article)]
    statuses = {}
    with_claims = {c["article_id"] for c in claims}
    negative_counts = Counter(r["article_id"] for r in negatives)
    if article is None:
        for aid in negative_counts.keys() - scope:
            report.fail("claims §8", f"no_claims: unknown article {aid}")
    for row in selected:
        aid, status = row["article_id"], row["status"]
        if aid not in scope or aid in statuses:
            report.fail("claims §9", f"status: unknown or duplicate article {aid}")
            continue
        statuses[aid] = status
        if status not in STATUSES:
            report.fail("claims §9", f"article {aid}: invalid status {status!r}")
        if row["files_sha256"] != files_digest(files, aid):
            report.fail("claims §9", f"article {aid}: stale PDF inventory attestation")
        if not row["reason"].strip():
            report.fail("claims §9", f"article {aid}: reading status needs a reason")
        n = negative_counts[aid]
        if status == "complete":
            if not ((aid in with_claims and n == 0) or (aid not in with_claims and n == 1)):
                report.fail("claims §8", f"article {aid}: complete requires claims XOR one no_claims row")
        elif n:
            report.fail("claims §8", f"article {aid}: unassessed article cannot be no_claims")
    for aid in sorted(scope - statuses.keys()):
        report.fail("claims §9", f"article {aid}: missing extraction status")
    if report.failures == before:
        counts = ", ".join(f"{status}={sum(s == status for s in statuses.values())}" for status in STATUSES)
        report.ok(f"reading status attestations: {counts}")
    return statuses


def fingerprints(root, report):
    result = {}
    for relative in INPUT_PATHS:
        try:
            result[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        except OSError as error:
            report.fail("results §6", f"cannot fingerprint {relative}: {error}")
    return result


def candidates(claims, series):
    """Mechanical permissive candidate coverage, not a physical matcher."""
    expected = set()
    for claim in claims:
        matches = {(claim["claim_id"], sid) for sid, s in series.items()
                   if str(s["article_id"]) == claim["article_id"]
                   and claim["medium_class"] in ("unspecified", s["medium_class"])}
        expected |= matches or {(claim["claim_id"], "")}
    return expected


def check_pairs(report, name, records, expected):
    actual = Counter((r["claim_id"], r["series_id"]) for r in records)
    for pair in sorted(expected - actual.keys()):
        report.fail("results §5", f"{name}: missing pair {pair}")
    for pair, count in actual.items():
        if pair not in expected or count != 1:
            report.fail("results §5", f"{name}: unexpected or duplicate pair {pair} ({count})")


def check_audit(report, audit, expected):
    check_pairs(report, "matching_audit", audit, expected)
    for row in audit:
        pair = (row["claim_id"], row["series_id"])
        if row["decision"] not in DECISIONS:
            report.fail("results §5", f"audit {pair}: invalid decision")
        if (not row["series_id"]) != (row["decision"] == "no_candidates"):
            report.fail("results §5", f"audit {pair}: no_candidates requires an empty series_id only")
        if not row["reason"].strip() or not row["caveats"].strip():
            report.fail("results §5", f"audit {pair}: reason and caveats required (use 'none' explicitly)")
        if row["decision"] == "include":
            if row["assessment"] not in ASSESSMENTS:
                report.fail("results §5", f"audit {pair}: included pair needs an assessment")
            if row["assessment"] != "direct" and row["caveats"].strip().lower() == "none":
                report.fail("results §5", f"audit {pair}: qualified/unassessable pair needs substantive caveats")
        elif row["assessment"]:
            report.fail("results §5", f"audit {pair}: excluded/no_candidates assessment must be empty")


def check_comparisons(report, comparison, audit, claims, series):
    included = {(r["claim_id"], r["series_id"]): r for r in audit if r["decision"] == "include"}
    check_pairs(report, "comparison", comparison, set(included))
    by_id = {c["claim_id"]: c for c in claims}
    for row in comparison:
        pair = (row["claim_id"], row["series_id"])
        if pair not in included or row["claim_id"] not in by_id or row["series_id"] not in series:
            continue
        decision, claim, s = included[pair], by_id[row["claim_id"]], series[row["series_id"]]
        if row["direction"] != claim["direction"] or row["assessment"] != decision["assessment"]:
            report.fail("results §5", f"comparison {pair}: direction/assessment differs from source")
        if not row["note"].strip():
            report.fail("results §5", f"comparison {pair}: note required (use 'none' explicitly)")
        for model in MODELS:
            shape = s[f"shape_{model}"]
            if row[f"shape_{model}"] != shape:
                report.fail("results §5", f"comparison {pair}: shape_{model} differs from tools")
            expected = "" if decision["assessment"] == "unassessable" else str(shape in AGREES[claim["direction"]]).lower()
            if row[f"agree_{model}"] != expected:
                report.fail("results §5", f"comparison {pair}: agree_{model} must be {expected!r}")


def outcome(values):
    """Conservative claim outcome; an unknown never becomes an agreement."""
    values = set(values)
    if {"true", "false"} <= values:
        return "mixed"
    if values == {"true"}:
        return "all_agree"
    if values == {"false"}:
        return "all_disagree"
    return "unassessable"


def tally_pairs(records, model):
    values = Counter(r[f"agree_{model}"] for r in records)
    return {"n_included": len(records), "n_assessable": values["true"] + values["false"],
            "agree": values["true"], "disagree": values["false"], "unassessable": values[""]}


def expected_summary(claims, statuses, audit, comparison, series, inputs, stage):
    """Independent tally oracle, never used to produce agent outputs.

    It deliberately consumes checked records, not src/ implementations.
    """
    complete = {aid for aid, status in statuses.items() if status == "complete"}
    claims = [c for c in claims if c["article_id"] in complete]
    qualified = [c for c in claims if c["variable"] in VARIABLES]

    def n_articles(records):
        return len({c["article_id"] for c in records})

    numerator, denominator = n_articles(qualified), len(complete)
    articles = {
        "n_corpus": len(statuses),
        **{f"n_{status}": sum(s == status for s in statuses.values()) for status in STATUSES},
        "prevalence": {"numerator": numerator, "denominator": denominator,
                       "fraction": numerator / denominator if denominator else None},
        "n_with_unspecified_claim": n_articles([c for c in claims if c["variable"] == "unspecified"]),
        "by_basis": {b: n_articles([c for c in qualified if c["basis"] == b]) for b in BASES},
        "by_direction": {d: n_articles([c for c in qualified if c["direction"] == d]) for d in DIRECTIONS},
        "by_basis_and_direction": {
            b: {d: n_articles([c for c in qualified if c["basis"] == b and c["direction"] == d])
                for d in DIRECTIONS} for b in BASES},
    }
    own = [c for c in claims if c["basis"] == "own_data"]
    by_claim = {c["claim_id"]: [r for r in comparison if r["claim_id"] == c["claim_id"]] for c in own}
    outcomes = {cid: {**{m: outcome(r[f"agree_{m}"] for r in records) for m in MODELS},
                      "n_included": len(records),
                      "n_qualified": sum(r["assessment"] == "qualified" for r in records),
                      "n_unassessable": sum(r["assessment"] == "unassessable" for r in records)}
                for cid, records in by_claim.items()}
    no_candidates = sum(r["decision"] == "no_candidates" for r in audit)
    with_included = sum(bool(records) for records in by_claim.values())
    comparison_summary = {
        "n_own_data_claims": len(own), "n_with_candidates": len(own) - no_candidates,
        "n_without_candidates": no_candidates, "n_with_included_series": with_included,
        "n_all_candidates_excluded": len(own) - no_candidates - with_included,
        "n_candidate_pairs": sum(bool(r["series_id"]) for r in audit),
        "n_included_pairs": len(comparison),
        "n_excluded_pairs": sum(r["decision"] == "exclude" for r in audit),
        "claim_outcomes": outcomes,
        "by_model": {m: {
            "claims": {"denominator": len(own), **{o: sum(r[m] == o for r in outcomes.values()) for o in OUTCOMES}},
            "pairs": tally_pairs(comparison, m),
            "pairs_by_assessment": {a: tally_pairs([r for r in comparison if r["assessment"] == a], m)
                                    for a in ASSESSMENTS},
        } for m in MODELS},
    }
    shapes = {}
    for model in MODELS:
        counts = {s: sum(r[f"shape_{model}"] == s for r in series.values()) for s in SHAPES}
        n = counts["increasing"] + counts["decreasing"]
        # Historical secondary sign-test definition, not an independence claim.
        p = sum(math.comb(n, k) for k in range(counts["increasing"], n + 1)) / 2**n if n else None
        shapes[model] = {"counts": counts, "n_test": n, "p_value": p}
    return {"contract_version": 1, "stage": stage, "inputs": inputs,
            "articles": articles, "comparison": comparison_summary, "series": shapes}


def differences(expected, stored, where="summary"):
    """Exact keys/types/counts; finite floats within relative tolerance 1e-9."""
    if isinstance(expected, dict):
        if not isinstance(stored, dict) or expected.keys() != stored.keys():
            return [f"{where}: keys differ"]
        return [message for key in expected for message in differences(expected[key], stored[key], f"{where}.{key}")]
    if type(expected) is float and type(stored) in (int, float):
        try:
            if math.isfinite(stored) and math.isclose(expected, stored, rel_tol=1e-9, abs_tol=1e-12):
                return []
        except OverflowError:
            pass  # a JSON integer too large for float is not a matching fraction
    elif type(expected) is type(stored) and expected == stored:
        return []
    return [f"{where}: {stored!r}, expected {expected!r}"]


def check_review(root, report, inputs):
    review = read_json(root, "checks/matching_review.json", report)
    if not isinstance(review, dict) or set(review) != {"decision", "reviewer", "date", "inputs"}:
        report.fail("results §6", "matching_review: expected decision, reviewer, date, inputs")
        return
    if review["decision"] != "accepted" or not isinstance(review["reviewer"], str) or not review["reviewer"].strip():
        report.fail("results §6", "matching_review: curator acceptance and reviewer required")
    try:
        if not isinstance(review["date"], str) or date.fromisoformat(review["date"]).isoformat() != review["date"]:
            raise ValueError("expected YYYY-MM-DD")
    except ValueError:
        report.fail("results §6", "matching_review: invalid date")
    for message in differences(inputs, review["inputs"], "matching_review.inputs"):
        report.fail("results §6", message)


def check_analysis(root, report, ids, claims, statuses, tools, stage):
    """Verify drafts/finals. Never write results or make scientific judgments."""
    before = report.failures
    audit = rows(root, "results/matching_audit.csv", AUDIT_COLUMNS, report)
    comparison = rows(root, "results/comparison.csv", COMPARISON_COLUMNS, report)
    stored = read_json(root, "results/summary.json", report)
    if audit is None or comparison is None or stored is None:
        return
    series = {}
    try:
        for aid in sorted(ids):
            for s in tools.list_series(aid):
                sid = s["series_id"]
                if sid in series or s["article_id"] != aid or any(s[f"shape_{m}"] not in SHAPES for m in MODELS):
                    raise ValueError(f"invalid/duplicate series {sid}")
                series[sid] = s
    except Exception as error:  # report a tool failure, never a success fallback
        report.fail("results §4", f"series tools failed: {error}")
        return
    own = [c for c in claims if c["basis"] == "own_data" and statuses.get(c["article_id"]) == "complete"]
    check_audit(report, audit, candidates(own, series))
    check_comparisons(report, comparison, audit, own, series)
    inputs = fingerprints(root, report)
    if stage == "final":
        if "pending" in statuses.values():
            report.fail("results §6", "final analysis cannot contain pending articles")
        check_review(root, report, inputs)
    if report.failures != before:
        return
    expected = expected_summary(claims, statuses, audit, comparison, series, inputs, stage)
    for message in differences(expected, stored):
        report.fail("results §6", message)
    if report.failures == before:
        report.ok(f"analysis {stage}: coverage, audit, pairs and summary verified")
