"""Week 10 student self-check, adapted to the existing project layout.

Run the independent final analysis check separately. This checks structure,
reference bookkeeping and basic PDF anonymity, not scientific correctness,
adequacy of AI disclosure, or the main-text page count.
"""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md", "STATUS.md", "diary.md", "ontology.yaml", "GLOSSARY.md",
    "WRITING.md", "research/problem.md", "lit/lit.md", "paper/paper.tex",
    "paper/ai4science_ysda.cls", "results/summary.json", "results/comparison.csv",
    "results/matching_audit.csv", "checks/matching_review.json",
)
IDENTIFIER = re.compile(r"(?:10\.\d{4,}/\S+|W\d{6,})", re.IGNORECASE)


def read(root, name):
    path = root / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def issues(root, pdf):
    for name in REQUIRED:
        if not (root / name).is_file():
            yield f"Missing {name}"

    try:
        summary = json.loads(read(root, "results/summary.json"))
    except ValueError:
        summary = None
    if not isinstance(summary, dict) or summary.get("stage") != "final":
        yield "results/summary.json must contain the final corpus summary"

    paper = re.sub(r"(?<!\\)%[^\n]*", "", read(root, "paper/paper.tex"))
    documentclass = re.search(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}", paper)
    options = set()
    if documentclass and documentclass[1]:
        options = {opt.strip() for opt in documentclass[1].split(",")}
    if (not documentclass or documentclass[2] != "ai4science_ysda"
            or "english" not in options or options & {"final", "russian"}):
        yield "Use the anonymous ai4science_ysda class with the english option and without final or russian"
    if re.search(r"\\PaperTODO\b", paper):
        yield "Resolve all manuscript placeholders and remove the PaperTODO definition"
    for title in ("Verification", "Limitations", "Reproducibility"):
        if not re.search(r"\\section\*?\s*\{" + title + r"\}", paper):
            yield f"Missing manuscript section: {title}"
    if not re.search(r"\\begin\{aiusage\}.*?\\end\{aiusage\}", paper, re.DOTALL):
        yield "Missing the AI-use table"
    body = re.sub(r"\\begin\{aiusage\}.*?\\end\{aiusage\}", "", paper, flags=re.DOTALL)
    if not re.search(r"\\(?:porozhdeno|napisano|istochnik|generated|written|sourced)\b", body):
        yield "Missing authorship markers in the paper text"

    registered = set()
    for line in read(root, "lit/lit.md").splitlines():
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line[1:-1].split("|")]
        key = cells[0]
        if key == "Key" or key.startswith("---"):
            continue
        if len(cells) != 5 or not all(cells) or not IDENTIFIER.fullmatch(cells[1]):
            yield f"Incomplete literature record for {key or '(missing key)'}"
            continue
        if key in registered:
            yield f"Duplicate literature key: {key}"
        registered.add(key)
    cited = {
        key.strip()
        for group in re.findall(r"\\cite\s*(?:\[[^\]]*\]\s*)?\{([^{}]*)\}", paper)
        for key in group.split(",")
    }
    bibitems = set(re.findall(r"\\bibitem\s*(?:\[[^\]]*\]\s*)?\{([^{}]*)\}", paper))
    if not 5 <= len(cited) <= 10:
        yield "Cite 5–10 relevant references"
    if cited - bibitems:
        yield "Missing bibliography entries: " + ", ".join(sorted(cited - bibitems))
    if (cited | bibitems) - registered:
        yield "Missing literature records: " + ", ".join(sorted((cited | bibitems) - registered))

    if not pdf.is_file():
        yield f"Missing compiled PDF: {pdf}"
        return
    try:
        env = {**os.environ, "LC_ALL": "C.UTF-8"}
        metadata = subprocess.check_output(["pdfinfo", str(pdf)], text=True, env=env)
        first_page = subprocess.check_output(
            ["pdftotext", "-f", "1", "-l", "1", str(pdf), "-"], text=True, env=env,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        yield f"Cannot inspect compiled PDF: {error}"
        return
    if any(line.partition(":")[2].strip() for line in metadata.splitlines() if line.startswith("Author:")):
        yield "PDF Author metadata is not empty"
    if not re.search(r"\bAnonymous\s+authors\b", first_page):
        yield "First PDF page does not display the English 'Anonymous authors' label"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=ROOT / "paper/build/paper.pdf")
    args = parser.parse_args()
    failures = list(issues(ROOT, args.pdf))
    for message in failures:
        print(f"FAIL: {message}")
    if failures:
        return 1
    print("PASS: paper structure, reference bookkeeping and basic PDF anonymity.")
    print("Manually verify main-text length (4–8 pages), scientific claims and disclosure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
