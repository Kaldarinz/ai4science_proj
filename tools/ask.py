"""Answer the competency questions of ontology.yaml from the project graph.

Usage::

    .venv/bin/python tools/ask.py          # all questions
    .venv/bin/python tools/ask.py q1 q4    # some of them

Reads the notes in notes/ (written by tools/graph.py) and prints each
question with its answer as a Markdown table. A link to a file is followed
only to read the row it points to (the reason in results/no_claims.csv).
"""

import argparse
import csv
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
LINK: Final[re.Pattern[str]] = re.compile(r"^- (\w+): \[\[(.+)\]\]$")


@dataclass
class Note:
    """A note of the graph: class, attributes, body lines and links."""

    name: str
    cls: str
    attrs: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)

    def targets(self, rel: str) -> list[str]:
        """Return the targets of one relation.

        Parameters
        ----------
        rel : str
            Relation name.

        Returns
        -------
        list[str]
            Note names or file paths, in the note's order.
        """
        return [t for r, t in self.links if r == rel]


def load_notes() -> dict[str, Note]:
    """Parse every note in notes/.

    Returns
    -------
    dict[str, Note]
        Notes by name (the file name without .md).
    """
    notes: dict[str, Note] = {}
    for path in sorted((ROOT / "notes").glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        end = lines.index("---", 1)
        front = dict(line.split(": ", 1) for line in lines[1:end])
        note = Note(path.stem, front.pop("type", ""), front)
        in_links = False
        for line in lines[end + 1:]:
            if line == "## Links":
                in_links = True
            elif in_links and (m := LINK.match(line)) and m[1] != "type":
                note.links.append((m[1], m[2]))
            elif not in_links and line and not line.startswith("# "):
                note.body.append(line)
        notes[note.name] = note
    return notes


def of(notes: dict[str, Note], cls: str) -> list[Note]:
    """Return the notes of one class, sorted by name.

    Parameters
    ----------
    notes : dict[str, Note]
        All notes.
    cls : str
        Class name.

    Returns
    -------
    list[Note]
        Its notes.
    """
    return [n for n in notes.values() if n.cls == cls]


def table(header: list[str], rows: list[list[str]], empty: str) -> str:
    """Format rows as a Markdown table.

    Parameters
    ----------
    header : list[str]
        Column names.
    rows : list[list[str]]
        Cells.
    empty : str
        Text printed instead of a table with no rows.

    Returns
    -------
    str
        The table, or `empty`.
    """
    if not rows:
        return empty
    lines = ["| " + " | ".join(header) + " |",
             "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def q1(notes: dict[str, Note]) -> str:
    """Claims by article, with their basis."""
    rows = [[c.targets("extractedFrom")[0], c.name.removeprefix("Claim "),
             c.attrs["variable"], c.attrs["direction"], c.attrs["basis"],
             c.attrs["medium_class"]]
            for c in of(notes, "Claim")]
    return table(["Article", "Claim", "variable", "direction", "basis",
                  "medium_class"], sorted(rows), "No claims yet.")


def q2(notes: dict[str, Note]) -> str:
    """Series by article, with their shapes."""
    rows = [[s.targets("reportedIn")[0], s.name.removeprefix("Series "),
             s.attrs.get("shape_primary", ""), s.attrs.get("shape_lenient", "")]
            for s in of(notes, "Series")]
    return table(["Article", "Series", "shape_primary", "shape_lenient"],
                 sorted(rows), "No Series notes yet: they come with "
                 "tools/ablation_db.py.")


def q3(notes: dict[str, Note]) -> str:
    """Articles with no claim, and claims with no matching series."""
    reasons: dict[str, str] = {}
    path = ROOT / "results" / "no_claims.csv"
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            reasons = {r["article_id"]: r["reason"] for r in csv.DictReader(f)}
    rows = []
    for a in of(notes, "Article"):
        for target in a.targets("noClaimReasonIn"):
            aid = a.name.removeprefix("Article ")
            rows.append([a.name, "no claim in the text",
                         f"{target}: {reasons.get(aid, '')}"])
    claims = of(notes, "Claim")
    for c in claims:
        if c.attrs.get("verdict") == "unmatched":
            rows.append([c.targets("extractedFrom")[0],
                         f"no matching series for {c.name}", ""])
    answer = table(["Article", "Why", "Reason"], sorted(rows),
                   "Every article has a claim.")
    if not any("verdict" in c.attrs for c in claims):
        answer += ("\n\nNo verdicts yet, so no claim is known to lack "
                   "series: they come with results/comparison.csv.")
    return answer


def q4(notes: dict[str, Note]) -> str:
    """Curator checks, with their reason and outcome."""
    rows = []
    for ch in of(notes, "Check"):
        outcome = next((b.removeprefix("Outcome: ") for b in ch.body
                        if b.startswith("Outcome: ")), "")
        details = next((b for b in ch.body if b.startswith("wrong_fields")),
                       "")
        rows.append([ch.targets("checks")[0], ch.attrs["reason"], outcome,
                     details])
    return table(["Claim", "reason", "outcome", "details"], sorted(rows),
                 "No curator checks yet.")


def q5(notes: dict[str, Note]) -> str:
    """Files of each article: PDFs, claims, the code of its series."""
    claims_of: dict[str, set[str]] = {}
    for c in of(notes, "Claim"):
        claims_of.setdefault(c.targets("extractedFrom")[0], set()).update(
            c.targets("storedIn"))
    code_of: dict[str, set[str]] = {}
    for s in of(notes, "Series"):
        code_of.setdefault(s.targets("reportedIn")[0], set()).update(
            s.targets("computedBy"))
    rows = []
    for a in of(notes, "Article"):
        results = claims_of.get(a.name, set()) | set(
            a.targets("noClaimReasonIn"))
        rows.append([a.name, ", ".join(a.targets("storedIn")),
                     ", ".join(sorted(results)),
                     ", ".join(sorted(code_of.get(a.name, set()))) or "–"])
    return table(["Article", "PDF", "Claims or no-claim row", "Code"],
                 sorted(rows), "No articles yet.")


QUERIES: Final[dict[str, Callable[[dict[str, Note]], str]]] = {
    "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
}


def main() -> int:
    """Print the asked questions and their answers.

    Returns
    -------
    int
        0, or 2 for an unknown question name.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", metavar="qN",
                        help=f"questions to answer: {', '.join(QUERIES)}; "
                             "all by default")
    args = parser.parse_args()
    names = args.names or list(QUERIES)
    unknown = [n for n in names if n not in QUERIES]
    if unknown:
        parser.error(f"unknown question(s): {', '.join(unknown)}")
    with (ROOT / "ontology.yaml").open(encoding="utf-8") as f:
        questions = yaml.safe_load(f)["competency_questions"]
    notes = load_notes()
    for name in names:
        text = questions[int(name[1:]) - 1]
        print(f"## {name}. {text}\n\n{QUERIES[name](notes)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
