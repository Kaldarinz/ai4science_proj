#!/usr/bin/env python3
"""Generate the main Results table from the approved final artifacts.

Presentation-only generator (AGENTS.md section 3): it reads saved evidence
and writes LaTeX. It never recomputes a scientific result from raw data and
never writes outside paper/.

Inputs (read-only):
    results/summary.json      -- approved final aggregate
    results/comparison.csv    -- one row per included claim-series pair
    results/claims.csv        -- claim inventory (own-data denominators)

Outputs:
    paper/tables/main_results.tex         -- LaTeX float, \\input-able
    paper/tables/main_results_checks.txt  -- verification log and flip report

The generator recomputes every count independently from the per-pair rows and
aborts if the result disagrees with results/summary.json. A silent mismatch
between the table and the approved summary is therefore impossible.

Run from the project root:
    .venv/bin/python paper/generate_results_table.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "results" / "summary.json"
COMPARISON = ROOT / "results" / "comparison.csv"
CLAIMS = ROOT / "results" / "claims.csv"
OUT_DIR = ROOT / "paper" / "tables"
OUT_TEX = OUT_DIR / "main_results.tex"
OUT_LOG = OUT_DIR / "main_results_checks.txt"

MODELS = ("primary", "lenient")
MODEL_LABEL = {"primary": "Primary (10\\%)", "lenient": "Lenient (20\\%)"}
ASSESSMENTS = ("direct", "qualified", "unassessable")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load() -> tuple[dict, list[dict], list[dict]]:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    with COMPARISON.open(encoding="utf-8", newline="") as fh:
        pairs = list(csv.DictReader(fh))
    with CLAIMS.open(encoding="utf-8", newline="") as fh:
        claims = list(csv.DictReader(fh))
    if summary.get("stage") != "final":
        fail(f"summary stage is {summary.get('stage')!r}, expected 'final'")
    return summary, pairs, claims


def claim_outcome(values: list[str]) -> str:
    """Conservative claim outcome, checks/results_spec.md section 5.3."""
    seen = set(values)
    if {"true", "false"} <= seen:
        return "mixed"
    if seen == {"true"}:
        return "all_agree"
    if seen == {"false"}:
        return "all_disagree"
    return "unassessable"


def recompute(pairs: list[dict], claims: list[dict]) -> dict:
    own = [c for c in claims if c["basis"] == "own_data"]
    by_claim: dict[str, list[dict]] = defaultdict(list)
    for row in pairs:
        by_claim[row["claim_id"]].append(row)

    claim_counts = {}
    for model in MODELS:
        outcomes = Counter()
        for claim in own:
            rows = by_claim.get(claim["claim_id"], [])
            outcomes[claim_outcome([r[f"agree_{model}"] for r in rows])] += 1
        claim_counts[model] = outcomes

    pair_counts = {}
    for model in MODELS:
        total = Counter()
        per_assessment = {a: Counter() for a in ASSESSMENTS}
        for row in pairs:
            value = row[f"agree_{model}"]
            total[value] += 1
            per_assessment[row["assessment"]][value] += 1
        pair_counts[model] = {"total": total, "by_assessment": per_assessment}

    return {
        "n_own_data_claims": len(own),
        "claim_counts": claim_counts,
        "pair_counts": pair_counts,
        "n_included_pairs": len(pairs),
    }


def verify(summary: dict, computed: dict, pairs: list[dict]) -> list[str]:
    """Cross-check recomputed counts against the approved summary."""
    log: list[str] = []
    cmp_summary = summary["comparison"]
    problems: list[str] = []

    def check(label: str, got, want) -> None:
        ok = got == want
        log.append(f"{'ok  ' if ok else 'FAIL'} {label}: table={got} summary={want}")
        if not ok:
            problems.append(label)

    check("own-data claims (denominator)",
          computed["n_own_data_claims"], cmp_summary["n_own_data_claims"])
    check("included pairs", computed["n_included_pairs"], cmp_summary["n_included_pairs"])

    for model in MODELS:
        want_claims = cmp_summary["by_model"][model]["claims"]
        got_claims = computed["claim_counts"][model]
        for key in ("all_agree", "all_disagree", "mixed", "unassessable"):
            check(f"claims/{model}/{key}", got_claims[key], want_claims[key])
        check(f"claims/{model}/denominator", sum(got_claims.values()),
              want_claims["denominator"])

        want_pairs = cmp_summary["by_model"][model]["pairs"]
        got_total = computed["pair_counts"][model]["total"]
        check(f"pairs/{model}/agree", got_total["true"], want_pairs["agree"])
        check(f"pairs/{model}/disagree", got_total["false"], want_pairs["disagree"])
        check(f"pairs/{model}/unassessable", got_total[""], want_pairs["unassessable"])
        check(f"pairs/{model}/n_included", sum(got_total.values()), want_pairs["n_included"])

        want_by = cmp_summary["by_model"][model]["pairs_by_assessment"]
        got_by = computed["pair_counts"][model]["by_assessment"]
        for assessment in ASSESSMENTS:
            check(f"pairs/{model}/{assessment}/n_included",
                  sum(got_by[assessment].values()), want_by[assessment]["n_included"])
            check(f"pairs/{model}/{assessment}/agree",
                  got_by[assessment]["true"], want_by[assessment]["agree"])
            check(f"pairs/{model}/{assessment}/disagree",
                  got_by[assessment]["false"], want_by[assessment]["disagree"])
            check(f"pairs/{model}/{assessment}/unassessable",
                  got_by[assessment][""], want_by[assessment]["unassessable"])

    # Claim-level outcomes must also match the per-claim record in the summary.
    by_claim: dict[str, list[dict]] = defaultdict(list)
    for row in pairs:
        by_claim[row["claim_id"]].append(row)
    for claim_id, want in cmp_summary["claim_outcomes"].items():
        for model in MODELS:
            got = claim_outcome([r[f"agree_{model}"] for r in by_claim.get(claim_id, [])])
            check(f"claim_outcome/{claim_id}/{model}", got, want[model])

    if problems:
        fail("table disagrees with results/summary.json: " + ", ".join(problems))
    return log


def flips(pairs: list[dict], claims: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pairs and claims whose verdict differs between the two tolerances."""
    pair_flips = [
        r for r in pairs
        if r["agree_primary"] != r["agree_lenient"]
    ]
    by_claim: dict[str, list[dict]] = defaultdict(list)
    for row in pairs:
        by_claim[row["claim_id"]].append(row)
    claim_flips = []
    for claim in claims:
        if claim["basis"] != "own_data":
            continue
        rows = by_claim.get(claim["claim_id"], [])
        p = claim_outcome([r["agree_primary"] for r in rows])
        l = claim_outcome([r["agree_lenient"] for r in rows])
        if p != l:
            claim_flips.append({"claim_id": claim["claim_id"], "primary": p, "lenient": l})
    return pair_flips, claim_flips


def render(summary: dict, computed: dict) -> str:
    art = summary["articles"]
    prev = art["prevalence"]
    n_articles = art["n_corpus"]
    n_with = prev["numerator"]
    pct = 100.0 * prev["fraction"]
    cmp_summary = summary["comparison"]

    cc = computed["claim_counts"]
    pc = computed["pair_counts"]

    def row(label: str, key: str, counts: dict, indent: bool = False) -> str:
        pad = "\\quad " if indent else ""
        return (f"{pad}{label} & {counts['primary'][key]} & {counts['lenient'][key]} \\\\")

    lines: list[str] = []
    lines.append("% Generated by paper/generate_results_table.py from")
    lines.append("% results/summary.json and results/comparison.csv.")
    lines.append("% Do not edit by hand; rerun the generator instead.")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\caption{Agreement between textual claims and numerical size trends")
    lines.append("under the two fixed error models. Panel~A is article-level, Panel~B")
    lines.append("claim-level and Panel~C pair-level; the three panels are not")
    lines.append("independent observations. Denominators are given in the row labels.}")
    lines.append("\\label{tab:main-results}")
    lines.append("\\begin{tabular}{@{}lrr@{}}")
    lines.append("\\hline")
    lines.append(" & " + MODEL_LABEL["primary"] + " & " + MODEL_LABEL["lenient"] + " \\\\")
    lines.append("\\hline")
    lines.append("\\multicolumn{3}{@{}l}{\\emph{Panel A: article-level prevalence}} \\\\")
    lines.append(f"Reviewed articles & \\multicolumn{{2}}{{c}}{{{n_articles}}} \\\\")
    lines.append(f"Articles with at least one claim & \\multicolumn{{2}}{{c}}"
                 f"{{{n_with} ({pct:.1f}\\%)}} \\\\")
    lines.append("\\hline")
    lines.append(f"\\multicolumn{{3}}{{@{{}}l}}{{\\emph{{Panel B: own-data claims "
                 f"($n={computed['n_own_data_claims']}$)}}}} \\\\")
    lines.append(row("All included pairs agree", "all_agree", cc))
    lines.append(row("All included pairs disagree", "all_disagree", cc))
    lines.append(row("Mixed", "mixed", cc))
    lines.append(row("Unassessable", "unassessable", cc))
    lines.append("\\hline")
    lines.append(f"\\multicolumn{{3}}{{@{{}}l}}{{\\emph{{Panel C: included claim--series "
                 f"pairs ($n={computed['n_included_pairs']}$)}}}} \\\\")
    for assessment, label in (("direct", "Direct"), ("qualified", "Qualified")):
        for key, word in (("true", "agree"), ("false", "disagree")):
            counts = {
                m: pc[m]["by_assessment"][assessment] for m in MODELS
            }
            lines.append(row(f"{label}, {word}", key, counts, indent=True))
    counts = {m: pc[m]["by_assessment"]["unassessable"] for m in MODELS}
    lines.append(row("Unassessable", "", counts, indent=True))
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("")
    lines.append("\\par\\smallskip")
    lines.append("\\begin{minipage}{0.95\\linewidth}")
    lines.append("\\footnotesize")
    lines.append(f"Candidate pairs {cmp_summary['n_candidate_pairs']}; "
                 f"excluded {cmp_summary['n_excluded_pairs']}; "
                 f"included {cmp_summary['n_included_pairs']}. "
                 f"Own-data claims without an included series: "
                 f"{cmp_summary['n_without_candidates'] + cmp_summary['n_all_candidates_excluded']}. "
                 "Counts generated from \\texttt{results/summary.json} and "
                 "\\texttt{results/comparison.csv}.")
    lines.append("\\end{minipage}")
    lines.append("\\end{table}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    summary, pairs, claims = load()
    computed = recompute(pairs, claims)
    log = verify(summary, computed, pairs)
    pair_flips, claim_flips = flips(pairs, claims)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(render(summary, computed), encoding="utf-8")

    report: list[str] = []
    report.append("Main Results table -- verification against approved final outputs")
    report.append("=" * 72)
    report.extend(log)
    report.append("")
    report.append("Verdict flips between tolerances (identical aggregate counts)")
    report.append("-" * 72)
    for r in pair_flips:
        report.append(
            f"pair {r['claim_id']}/{r['series_id']} [{r['assessment']}]: "
            f"direction={r['direction']} "
            f"shape primary={r['shape_primary']} -> agree={r['agree_primary']}; "
            f"shape lenient={r['shape_lenient']} -> agree={r['agree_lenient']}")
    for c in claim_flips:
        report.append(
            f"claim {c['claim_id']}: primary={c['primary']} -> lenient={c['lenient']}")
    report.append("")
    report.append(f"Wrote {OUT_TEX.relative_to(ROOT)}")
    OUT_LOG.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
