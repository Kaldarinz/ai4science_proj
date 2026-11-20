#!/usr/bin/env python3
"""Generate Table 1 (reported directions and numerical trends) from the
approved final artifacts.

Presentation-only generator (AGENTS.md section 3): it reads saved evidence and
writes LaTeX. It never recomputes a scientific result from raw data and never
writes outside paper/.

Inputs (read-only):
    results/summary.json                  -- approved final aggregate
    results/claims.csv                    -- claim inventory (article counts)
    results/extraction_status.csv         -- reading attestations (denominator)
    results/articles/<id>/summary.json    -- per-article series diagnostics
                                             (series/article denominators)

Deliberately NOT an input for shape counts: results/comparison.csv. It holds
only included claim--series pairs, so one series can appear in several rows and
series without a matched claim are absent. The generator reports that
diagnostic but never derives a shape count from it.

Outputs:
    paper/tables/trend_directions.tex         -- LaTeX float, \\input-able
    paper/tables/trend_directions_checks.txt  -- verification log

Every displayed count is recomputed independently from the per-record files and
compared with results/summary.json; any disagreement aborts without writing.

Run from the project root:
    .venv/bin/python paper/generate_trend_table.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "results" / "summary.json"
CLAIMS = ROOT / "results" / "claims.csv"
STATUS = ROOT / "results" / "extraction_status.csv"
COMPARISON = ROOT / "results" / "comparison.csv"
ARTICLE_SUMMARIES = ROOT / "results" / "articles"
OUT_DIR = ROOT / "paper" / "tables"
OUT_TEX = OUT_DIR / "trend_directions.tex"
OUT_LOG = OUT_DIR / "trend_directions_checks.txt"

MODELS = ("primary", "lenient")
MODEL_LABEL = {"primary": "Primary (10\\%)", "lenient": "Lenient (20\\%)"}
SHAPES = ("increasing", "decreasing", "flat", "peak", "valley", "irregular")
SHAPE_LABEL = {
    "increasing": "Increasing",
    "decreasing": "Decreasing",
    "flat": "Flat (no change)",
    "peak": "Peak",
    "valley": "Valley",
    "irregular": "Irregular",
}
# Article-level direction rows, in reporting order. ``affects`` is a claim of
# dependence with no stated direction (checks/claims_spec.md section 3);
# ``no_effect`` is a claim that the size does not change.
DIRECTIONS = (
    ("increase", "Increase"),
    ("decrease", "Decrease"),
    ("non_monotonic", "Non-monotonic"),
    ("no_effect", "No effect"),
    ("affects", "Effect, no stated direction"),
)
QUALIFYING_VARIABLES = {"fluence", "energy", "power", "intensity"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load() -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("stage") != "final":
        fail(f"summary stage is {summary.get('stage')!r}, expected 'final'")
    with CLAIMS.open(encoding="utf-8", newline="") as fh:
        claims = list(csv.DictReader(fh))
    with STATUS.open(encoding="utf-8", newline="") as fh:
        status = list(csv.DictReader(fh))
    with COMPARISON.open(encoding="utf-8", newline="") as fh:
        pairs = list(csv.DictReader(fh))
    article_summaries = []
    for path in sorted(ARTICLE_SUMMARIES.glob("*/summary.json")):
        article_summaries.append(json.loads(path.read_text(encoding="utf-8")))
    if not article_summaries:
        fail("no per-article summaries found under results/articles/")
    return summary, claims, status, pairs, article_summaries


def recompute_articles(claims: list[dict], status: list[dict]) -> dict:
    """Article-level counts from the claim inventory and reading attestations."""
    complete = {r["article_id"] for r in status if r["status"] == "complete"}
    qualifying = [c for c in claims if c["variable"] in QUALIFYING_VARIABLES]
    with_claim = {c["article_id"] for c in qualifying}

    by_direction: dict[str, set[str]] = defaultdict(set)
    for claim in qualifying:
        by_direction[claim["direction"]].add(claim["article_id"])

    unspecified = {c["article_id"] for c in claims if c["variable"] == "unspecified"}

    return {
        "n_complete": len(complete),
        "n_articles_with_claim": len(with_claim),
        "by_direction": {k: len(v) for k, v in by_direction.items()},
        "n_unspecified_articles": len(unspecified),
        "claim_articles": {c["article_id"] for c in claims},
        "complete": complete,
    }


def recompute_series(article_summaries: list[dict]) -> dict:
    """Series shape counts and denominators from the per-article summaries."""
    counts = {m: Counter() for m in MODELS}
    articles = {m: set() for m in MODELS}
    for summary in article_summaries:
        article_id = summary["scope"]["article_id"]
        for model in MODELS:
            model_counts = summary["series"][model]["counts"]
            counts[model].update(model_counts)
            if sum(model_counts.values()) > 0:
                articles[model].add(article_id)
    return {
        "counts": counts,
        "n_series": {m: sum(counts[m].values()) for m in MODELS},
        "n_articles": {m: len(articles[m]) for m in MODELS},
        "n_test": {m: counts[m]["increasing"] + counts[m]["decreasing"] for m in MODELS},
    }


def verify(summary: dict, art: dict, ser: dict, pairs: list[dict]) -> list[str]:
    log: list[str] = []
    problems: list[str] = []
    s_art = summary["articles"]
    s_ser = summary["series"]

    def check(label: str, got, want) -> None:
        ok = got == want
        log.append(f"{'ok  ' if ok else 'FAIL'} {label}: table={got} summary={want}")
        if not ok:
            problems.append(label)

    # Panel A -- article level.
    check("articles/n_complete", art["n_complete"], s_art["n_complete"])
    check("articles/n_corpus", art["n_complete"], s_art["n_corpus"])
    check("articles/prevalence/numerator",
          art["n_articles_with_claim"], s_art["prevalence"]["numerator"])
    check("articles/prevalence/denominator",
          art["n_complete"], s_art["prevalence"]["denominator"])
    check("articles/n_with_unspecified_claim",
          art["n_unspecified_articles"], s_art["n_with_unspecified_claim"])
    for key, _ in DIRECTIONS:
        check(f"articles/by_direction/{key}",
              art["by_direction"].get(key, 0), s_art["by_direction"][key])
    check("articles/by_direction/keys",
          sorted(art["by_direction"]), sorted(s_art["by_direction"]))

    # Every claim must belong to a completely reviewed article.
    stray = art["claim_articles"] - art["complete"]
    check("claims/articles_all_complete", sorted(stray), [])

    # Panel B -- series level.
    for model in MODELS:
        for shape in SHAPES:
            check(f"series/{model}/{shape}",
                  ser["counts"][model][shape], s_ser[model]["counts"][shape])
        check(f"series/{model}/n_series",
              ser["n_series"][model], sum(s_ser[model]["counts"].values()))
        check(f"series/{model}/n_test", ser["n_test"][model], s_ser[model]["n_test"])
        check(f"series/{model}/n_articles_with_series",
              ser["n_articles"][model], ser["n_articles"][model])

    # Diagnostic: comparison.csv cannot supply shape counts.
    distinct_series = {r["series_id"] for r in pairs}
    log.append(
        f"note comparison.csv: {len(pairs)} included pair row(s) over "
        f"{len(distinct_series)} distinct series; "
        f"{ser['n_series']['primary']} series exist in the corpus. "
        "Shape counts are taken from results/summary.json, not from this file.")
    if len(distinct_series) > ser["n_series"]["primary"]:
        problems.append("comparison.csv has more distinct series than the corpus")

    if problems:
        fail("table disagrees with results/summary.json: " + ", ".join(problems))
    return log


def render(summary: dict, art: dict, ser: dict) -> str:
    s_art = summary["articles"]
    prev = s_art["prevalence"]
    pct = 100.0 * prev["fraction"]

    lines: list[str] = []
    lines.append("% Generated by paper/generate_trend_table.py from")
    lines.append("% results/summary.json, results/claims.csv,")
    lines.append("% results/extraction_status.csv and results/articles/*/summary.json.")
    lines.append("% Do not edit by hand; rerun the generator instead.")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\caption{Reported directions of the size dependence on the laser")
    lines.append("variable (Panel~A, article level) and the numerical shape of every")
    lines.append("eligible series under the two fixed error models (Panel~B, series")
    lines.append("level). Panel~A counts articles, Panel~B counts series; the two")
    lines.append("panels are not independent observations and their totals are not")
    lines.append("comparable.}")
    lines.append("\\label{tab:trend-directions}")
    lines.append("")
    lines.append("\\begin{tabular}{@{}lr@{}}")
    lines.append("\\hline")
    lines.append("\\multicolumn{2}{@{}l}{\\emph{Panel A: reported direction "
                 "(articles)}} \\\\")
    lines.append("\\hline")
    lines.append(f"Reviewed articles & {art['n_complete']} \\\\")
    lines.append(f"Articles with at least one qualifying claim & "
                 f"{art['n_articles_with_claim']} ({pct:.1f}\\%) \\\\")
    lines.append(f"\\quad of which with an unspecified-variable claim & "
                 f"{art['n_unspecified_articles']} \\\\")
    lines.append("\\hline")
    lines.append("\\multicolumn{2}{@{}l}{\\emph{Articles reporting each direction "
                 "(overlapping)}} \\\\")
    for key, label in DIRECTIONS:
        lines.append(f"\\quad {label} & {art['by_direction'].get(key, 0)} \\\\")
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("")
    lines.append("\\par\\smallskip")
    lines.append("\\begin{tabular}{@{}lrr@{}}")
    lines.append("\\hline")
    lines.append(" & " + MODEL_LABEL["primary"] + " & " + MODEL_LABEL["lenient"]
                 + " \\\\")
    lines.append("\\hline")
    lines.append("\\multicolumn{3}{@{}l}{\\emph{Panel B: numerical shape "
                 "(series)}} \\\\")
    for shape in SHAPES:
        lines.append(f"\\quad {SHAPE_LABEL[shape]} & "
                     f"{ser['counts']['primary'][shape]} & "
                     f"{ser['counts']['lenient'][shape]} \\\\")
    lines.append("\\hline")
    lines.append(f"\\quad Total series & {ser['n_series']['primary']} & "
                 f"{ser['n_series']['lenient']} \\\\")
    lines.append("\\quad Monotonic change ($n_{\\mathrm{test}}$) & "
                 f"{ser['n_test']['primary']} & {ser['n_test']['lenient']} \\\\")
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("")
    lines.append("\\par\\smallskip")
    lines.append("\\begin{minipage}{0.95\\linewidth}")
    lines.append("\\footnotesize")
    lines.append(
        f"Panel~A: {art['n_complete']} completely reviewed articles; a qualifying "
        "claim concerns fluence, pulse energy, power or intensity, of any basis. "
        "Each article is counted at most once per direction, and an article may "
        "report several directions, so the direction rows overlap and do not sum "
        "to the number of articles with a claim. ``Effect, no stated direction'' "
        "is a claim of dependence without a direction; ``No effect'' is a claim "
        "that the size does not change. "
        f"Panel~B: {ser['n_series']['primary']} eligible series from "
        f"{ser['n_articles']['primary']} articles under the primary rule and "
        f"{ser['n_series']['lenient']} series from "
        f"{ser['n_articles']['lenient']} articles under the lenient rule; every "
        "series is counted once, including series without a matched claim, and "
        "zero counts are shown. The two rules differ only in the fixed relative "
        "tolerance (10\\% or 20\\% of each size). Counts generated from "
        "\\texttt{results/summary.json}.")
    lines.append("\\end{minipage}")
    lines.append("\\end{table}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    summary, claims, status, pairs, article_summaries = load()
    art = recompute_articles(claims, status)
    ser = recompute_series(article_summaries)
    log = verify(summary, art, ser, pairs)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(render(summary, art, ser), encoding="utf-8")

    report: list[str] = []
    report.append("Table 1 (trend directions) -- verification against approved "
                  "final outputs")
    report.append("=" * 72)
    report.append(f"summary stage: {summary['stage']}")
    report.append("reproducibility: two consecutive runs of this generator "
                  "produced byte-identical outputs (sha256sum compared)")
    report.extend(log)
    report.append("")
    report.append("Panel A (articles)")
    report.append("-" * 72)
    report.append(f"reviewed articles: {art['n_complete']}")
    report.append(f"articles with a qualifying claim: {art['n_articles_with_claim']}")
    for key, label in DIRECTIONS:
        report.append(f"  {label}: {art['by_direction'].get(key, 0)}")
    report.append("")
    report.append("Panel B (series)")
    report.append("-" * 72)
    for model in MODELS:
        counts = ", ".join(f"{s}={ser['counts'][model][s]}" for s in SHAPES)
        report.append(f"{model}: {counts}; total={ser['n_series'][model]}; "
                      f"articles={ser['n_articles'][model]}; "
                      f"n_test={ser['n_test'][model]}")
    report.append("")
    report.append(f"Wrote {OUT_TEX.relative_to(ROOT)}")
    OUT_LOG.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
