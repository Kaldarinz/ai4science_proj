"""Generate the project graph from ontology.yaml and the result tables.

Usage::

    .venv/bin/python tools/graph.py              # check, then write the notes
    .venv/bin/python tools/graph.py --check      # compare the notes on disk
    .venv/bin/python tools/graph.py --validate   # check the tables only

The project root is an Obsidian vault. This script writes one class note
per class of ontology.yaml to ontology/ and one object note per row to
notes/: Article (data/corpus.csv), Claim (results/claims.csv), Check
(checks/claim_checks.csv), Source (results/sources.csv) and Query
(results/queries.csv). Notes are never edited by hand: run the script
again instead. Notes in notes/ of other types are left alone.

Before writing, every attribute value, link target and link range is
checked against ontology.yaml, and so are the rules with a ``check``
(closed world: a link not written is a link that does not exist). The
literature tables (queries, sources, citations, source checks) also get
row checks, among them R8 and R9. On any failure nothing is written and
the exit code is 1. With --check nothing is written either; the exit code
is 1 when the notes on disk differ from the generated ones. --validate is
the agent's check after a literature task: tables, rules and a committed
results/, no comparison with the notes on disk. --root runs on another
project tree (test fixtures); it skips the commit check.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml

ROOT: Path = Path(__file__).resolve().parent.parent
ONTOLOGY: Path = ROOT / "ontology.yaml"
CLASS_DIR: Path = ROOT / "ontology"
NOTE_DIR: Path = ROOT / "notes"
VAULT: Path = ROOT / ".obsidian"

CLAIMS: Final[str] = "results/claims.csv"
NO_CLAIMS: Final[str] = "results/no_claims.csv"
CHECKS: Final[str] = "checks/claim_checks.csv"
COMPARISON: Final[str] = "results/comparison.csv"
QUERIES: Final[str] = "results/queries.csv"
SOURCES: Final[str] = "results/sources.csv"
CITATIONS: Final[str] = "results/citations.csv"
SOURCE_CHECKS: Final[str] = "checks/source_checks.csv"

#: Columns of the literature tables, in order.
COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    QUERIES: ("query_id", "database", "tool", "work", "relation", "request",
              "retrieved", "n_found", "n_kept"),
    SOURCES: ("source_id", "found_by", "doi", "title", "venue", "year",
              "cited_by_count", "screening", "screening_reason",
              "article_id"),
    CITATIONS: ("citing", "cited", "query_id"),
    SOURCE_CHECKS: ("source_id", "checked", "outcome", "note"),
}

#: OpenAlex tools that may find Sources, and the relations of links.
TOOLS: Final[frozenset[str]] = frozenset(
    {"openalex_search", "openalex_links", "openalex_work"})
RELATIONS: Final[frozenset[str]] = frozenset({"references", "cited_by"})

SOURCE_ID: Final[re.Pattern[str]] = re.compile(r"W\d+")
QUERY_ID: Final[re.Pattern[str]] = re.compile(r"q\d+")
DATE: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}")
#: A screening reason must not say which way size depends on the laser
#: parameter: extraction must stay blind to an earlier reading.
DIRECTION_WORDS: Final[re.Pattern[str]] = re.compile(
    r"\b(increas\w*|decreas\w*|grow|grows|growing|grew|larger|smaller)\b",
    re.I)

#: Classes whose notes this script owns in notes/.
GENERATED: Final[frozenset[str]] = frozenset(
    {"Article", "Claim", "Check", "Source", "Query"})

TYPE_LINE: Final[re.Pattern[str]] = re.compile(r"^type: *(\S+)", re.M)

VAULT_FILES: Final[dict[str, object]] = {
    "app.json": {"showUnsupportedFiles": True},
    "graph.json": {
        "showAttachments": True, "showOrphans": True, "showArrow": True,
        "colorGroups": [
            {"query": "path:ontology", "color": {"a": 1, "rgb": 9474192}},
            {"query": "[verdict:disagrees OR model_dependent]",
             "color": {"a": 1, "rgb": 14701138}},
            {"query": "[type:Check]", "color": {"a": 1, "rgb": 1153422}},
            {"query": "path:notes", "color": {"a": 1, "rgb": 5987296}},
        ],
    },
}


@dataclass
class Note:
    """One object note: class, attributes, body lines and links."""

    name: str
    cls: str
    attrs: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)

    def render(self) -> str:
        """Return the note's Markdown text.

        Returns
        -------
        str
            Front matter, title, body and ``## Links``.
        """
        front = [f"type: {self.cls}"]
        front += [f"{k}: {v}" for k, v in self.attrs.items()]
        links = [f"- type: [[{self.cls}]]"]
        links += [f"- {rel}: [[{target}]]" for rel, target in self.links]
        return "\n".join(
            ["---", *front, "---", f"# {self.name}", "", *self.body, "",
             "## Links", *links, ""])


class Report:
    """Count failures and print each one as it is found."""

    def __init__(self) -> None:
        """Start with no failures."""
        self.failures: int = 0

    def fail(self, rule: str, message: str) -> None:
        """Record and print one failure.

        Parameters
        ----------
        rule : str
            What the failure breaks, e.g. ``rule R1`` or ``ontology``.
        message : str
            What is wrong and where.
        """
        self.failures += 1
        print(f"FAIL [{rule}] {message}")

    def ok(self, message: str) -> None:
        """Print a passed step.

        Parameters
        ----------
        message : str
            What was checked.
        """
        print(f"ok   {message}")


def read_rows(path: str) -> list[dict[str, str]] | None:
    """Read a CSV file of the project.

    Parameters
    ----------
    path : str
        Path from the project root.

    Returns
    -------
    list[dict[str, str]] | None
        The rows, or None when the file does not exist.
    """
    file = ROOT / path
    if not file.exists():
        return None
    with file.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_list(value: str | list[str]) -> list[str]:
    """Return a domain or range of ontology.yaml as a list.

    Parameters
    ----------
    value : str | list[str]
        One class or a list of classes.

    Returns
    -------
    list[str]
        The classes.
    """
    return value if isinstance(value, list) else [value]


def use_root(root: Path) -> None:
    """Point the script at another project tree.

    Parameters
    ----------
    root : Path
        The project root, e.g. a test fixture.
    """
    global ROOT, ONTOLOGY, CLASS_DIR, NOTE_DIR, VAULT
    ROOT = root.resolve()
    ONTOLOGY = ROOT / "ontology.yaml"
    CLASS_DIR = ROOT / "ontology"
    NOTE_DIR = ROOT / "notes"
    VAULT = ROOT / ".obsidian"


def norm_doi(doi: str) -> str:
    """Return a DOI in lower case without a resolver prefix.

    Parameters
    ----------
    doi : str
        A DOI as written in a table, possibly ``https://doi.org/…``.

    Returns
    -------
    str
        The bare DOI, e.g. ``10.1117/12.2217777``; empty for an empty one.
    """
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        doi = doi.removeprefix(prefix)
    return doi


def split_ids(value: str) -> list[str]:
    """Return the ids of a ``;``-separated cell.

    Parameters
    ----------
    value : str
        E.g. ``q1;q3``.

    Returns
    -------
    list[str]
        The ids, without blanks.
    """
    return [v.strip() for v in value.split(";") if v.strip()]


def verdict(
    cid: str, row: dict[str, str], comparison: list[dict[str, str]] | None,
) -> str | None:
    """Return the verdict of an own_data claim from its comparison rows.

    No comparison.csv yet → no verdict. No row with a series →
    ``unmatched``; all rows agree under both error models → ``agrees``;
    all disagree under both → ``disagrees``; anything else →
    ``model_dependent``.

    Parameters
    ----------
    cid : str
        The claim_id.
    row : dict[str, str]
        Its row of results/claims.csv.
    comparison : list[dict[str, str]] | None
        Rows of results/comparison.csv, None before the file exists.

    Returns
    -------
    str | None
        The verdict, or None when the claim has none.
    """
    if comparison is None or row["basis"] != "own_data":
        return None
    rows = [r for r in comparison if r["claim_id"] == cid and r["series_id"]]
    if not rows:
        return "unmatched"
    pairs = {(r["agree_primary"].lower(), r["agree_lenient"].lower())
             for r in rows}
    if pairs == {("true", "true")}:
        return "agrees"
    if pairs == {("false", "false")}:
        return "disagrees"
    return "model_dependent"


def build_objects(lit: dict[str, list[dict[str, str]] | None]) -> list[Note]:
    """Build the object notes from the result tables.

    Parameters
    ----------
    lit : dict[str, list[dict[str, str]] | None]
        Rows of the literature tables by path, None for a missing table.

    Returns
    -------
    list[Note]
        Article, Claim, Check, Source and Query notes, in table order.
    """
    corpus = read_rows("data/corpus.csv") or []
    files = read_rows("data/files.csv") or []
    claims = read_rows(CLAIMS) or []
    no_claims = {r["article_id"] for r in read_rows(NO_CLAIMS) or []}
    checks = read_rows(CHECKS) or []
    comparison = read_rows(COMPARISON)

    notes: list[Note] = []
    for row in corpus:
        aid = row["article_id"]
        note = Note(f"Article {aid}", "Article",
                    body=[f"{row['title']}, {row['year']}, {row['doi']}"])
        for f in files:
            if f["article_id"] == aid:
                note.links.append(
                    ("storedIn", f"data/articles/{aid}/{f['file']}"))
        if aid in no_claims:
            note.links.append(("noClaimReasonIn", NO_CLAIMS))
        notes.append(note)
    for row in claims:
        cid = row["claim_id"]
        note = Note(f"Claim {cid}", "Claim",
                    attrs={"direction": row["direction"],
                           "basis": row["basis"],
                           "variable": row["variable"],
                           "medium_class": row["medium_class"]},
                    body=[f"material: {row['material']}; page: "
                          f"{row['page']}"])
        v = verdict(cid, row, comparison)
        if v is not None:
            note.attrs["verdict"] = v
        note.links.append(("extractedFrom", f"Article {row['article_id']}"))
        for r in comparison or []:
            if r["claim_id"] == cid and r["series_id"]:
                note.links.append(("comparedWith", f"Series {r['series_id']}"))
        note.links.append(("storedIn", CLAIMS))
        notes.append(note)
    for row in checks:
        note = Note(f"Check {row['claim_id']} {row['reason']}", "Check",
                    attrs={"reason": row["reason"]},
                    body=[f"Outcome: {row['outcome']}",
                          f"wrong_fields: {row['wrong_fields']}; curator: "
                          f"{row['curator']}; date: {row['date']}"])
        note.links.append(("checks", f"Claim {row['claim_id']}"))
        note.links.append(("storedIn", CHECKS))
        notes.append(note)
    return notes + literature_objects(lit)


def literature_objects(
    lit: dict[str, list[dict[str, str]] | None],
) -> list[Note]:
    """Build the Source and Query notes from the literature tables.

    Parameters
    ----------
    lit : dict[str, list[dict[str, str]] | None]
        Rows of the literature tables by path, None for a missing table.

    Returns
    -------
    list[Note]
        Source notes, then Query notes, in table order.
    """
    citations = lit[CITATIONS] or []
    checked = lit[SOURCE_CHECKS] or []
    notes: list[Note] = []
    for row in lit[SOURCES] or []:
        sid = row["source_id"]
        note = Note(
            f"Source {sid}", "Source", attrs={"screening": row["screening"]},
            body=[f"{row['title']}, {row['venue']}, {row['year']}, "
                  f"{row['doi'] or 'no DOI'}",
                  f"cited_by_count: {row['cited_by_count']}",
                  f"screening_reason: {row['screening_reason']}"])
        for c in checked:
            if c["source_id"] == sid:
                note.body.append(f"Checked {c['checked']}: {c['outcome']}"
                                 + (f" - {c['note']}" if c["note"] else ""))
        note.links += [("foundBy", f"Query {q}")
                       for q in split_ids(row["found_by"])]
        if row["article_id"]:
            note.links.append(("describes", f"Article {row['article_id']}"))
        note.links += [("cites", f"Source {c['cited']}")
                       for c in citations if c["citing"] == sid]
        note.links.append(("storedIn", SOURCES))
        notes.append(note)
    for row in lit[QUERIES] or []:
        note = Note(
            f"Query {row['query_id']}", "Query",
            attrs={"database": row["database"]},
            body=[f"tool: {row['tool']}; work: {row['work'] or '-'}; "
                  f"relation: {row['relation'] or '-'}",
                  f"request: {row['request']}",
                  f"retrieved: {row['retrieved']}; found: {row['n_found']}; "
                  f"kept: {row['n_kept']}"])
        note.links.append(("storedIn", QUERIES))
        notes.append(note)
    return notes


def class_note(name: str, onto: dict) -> str:
    """Return the class note of one class.

    Parameters
    ----------
    name : str
        Class name.
    onto : dict
        Parsed ontology.yaml.

    Returns
    -------
    str
        Markdown text of ``ontology/<name>.md``.
    """
    definition = onto["classes"][name]["definition"]
    relations = [p for p, d in onto["properties"].items()
                 if name in as_list(d["domain"])]
    attributes = [f"{a} ({', '.join(d['values'])})"
                  for a, d in onto["attributes"].items()
                  if name in as_list(d["domain"])]
    return "\n".join([
        "---", "kind: class", "---", f"# {name}", "",
        definition[0].upper() + definition[1:], "",
        f"Relations from this class: {', '.join(relations) or 'none'}.",
        f"Attributes: {'; '.join(attributes) or 'none'}.", "",
        "## Links", ""])


def members(name: str, onto: dict, notes: dict[str, Note]) -> set[str]:
    """Return the notes of a class, or of a class defined by a rule.

    Parameters
    ----------
    name : str
        Class name, or the ``name`` of a ``defined_value`` rule.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All object notes by name.

    Returns
    -------
    set[str]
        Names of the member notes.
    """
    for rule in onto["rules"]:
        check = rule.get("check", {})
        if check.get("kind") == "defined_value" and check["name"] == name:
            return {n for n in members(check["class"], onto, notes)
                    if notes[n].attrs.get(check["attribute"])
                    in check["values"]}
    return {n for n, x in notes.items() if x.cls == name}


def check_graph(report: Report, onto: dict, notes: dict[str, Note]) -> None:
    """Check attribute values, links and rules against the ontology.

    Parameters
    ----------
    report : Report
        Collects failures.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All object notes by name.
    """
    before = report.failures
    attributes, properties = onto["attributes"], onto["properties"]
    for note in notes.values():
        for key, value in note.attrs.items():
            spec = attributes.get(key)
            if spec is None or note.cls not in as_list(spec["domain"]):
                report.fail("ontology", f"«{note.name}»: attribute {key} "
                            f"is not defined for {note.cls}")
            elif value not in spec["values"]:
                report.fail("ontology", f"«{note.name}»: {key} «{value}» "
                            f"is not one of {spec['values']}")
        for rel, target in note.links:
            spec = properties.get(rel)
            if spec is None or note.cls not in as_list(spec["domain"]):
                report.fail("ontology", f"«{note.name}»: relation {rel} is "
                            f"not defined for {note.cls}")
                continue
            ranges = as_list(spec["range"])
            if target in notes:
                if notes[target].cls not in ranges:
                    report.fail("ontology", f"«{note.name}»: {rel} points "
                                f"to a {notes[target].cls}, not {ranges}")
            elif "File" not in ranges:
                report.fail("ontology", f"«{note.name}»: {rel} points to "
                            f"«{target}», which has no note")
            elif not (ROOT / target).exists():
                report.fail("ontology", f"«{note.name}»: {rel} points to "
                            f"{target}, which does not exist")
    if report.failures == before:
        report.ok("attributes, links and their ranges match ontology.yaml")

    def targets(name: str, rel: str) -> list[str]:
        return [t for r, t in notes[name].links if r == rel]

    for rule in onto["rules"]:
        check = rule.get("check")
        if check is None or check["kind"] == "defined_value":
            continue
        kind, bad = check["kind"], []
        for name in sorted(members(check["class"], onto, notes)):
            if kind == "some":
                ok = members(check["target"], onto, notes)
                if not any(t in ok for t in targets(name, check["property"])):
                    bad.append(name)
            elif kind == "some_inverse":
                src = members(check["source"], onto, notes)
                if not any(name in targets(s, check["property"])
                           for s in src):
                    bad.append(name)
            else:
                report.fail(f"rule {rule['id']}",
                            f"check kind {kind} is not supported")
                break
        for name in bad:
            report.fail(f"rule {rule['id']}", f"«{name}»: {rule['text']}")
        if not bad:
            report.ok(f"rule {rule['id']}: {rule['text']}")


def read_literature(
    report: Report,
) -> dict[str, list[dict[str, str]] | None]:
    """Read the literature tables and check their shape.

    A table with a wrong header or a row with a wrong number of fields is
    reported and treated as missing, so no note is built from it.

    Parameters
    ----------
    report : Report
        Collects failures.

    Returns
    -------
    dict[str, list[dict[str, str]] | None]
        Rows by path, None for a missing or malformed table.
    """
    lit: dict[str, list[dict[str, str]] | None] = {}
    for path, columns in COLUMNS.items():
        rows = read_rows(path)
        lit[path] = rows
        if rows is None:
            continue
        with (ROOT / path).open(newline="", encoding="utf-8") as f:
            header = tuple(next(csv.reader(f), []))
        bad = [i for i, r in enumerate(rows, 2)
               if None in r or None in r.values()]
        if header != columns:
            report.fail("table", f"{path}: header {list(header)}, expected "
                        f"{list(columns)}")
            lit[path] = None
        elif bad:
            report.fail("table", f"{path}: wrong number of fields in "
                        f"line(s) {bad}")
            lit[path] = None
    return lit


def check_literature(
    report: Report, lit: dict[str, list[dict[str, str]] | None],
) -> None:
    """Check the rows of the literature tables, R8 and R9 among them.

    Parameters
    ----------
    report : Report
        Collects failures.
    lit : dict[str, list[dict[str, str]] | None]
        Rows of the literature tables by path, None for a missing table.
    """
    before = report.failures
    queries = lit[QUERIES] or []
    sources = lit[SOURCES] or []
    citations = lit[CITATIONS] or []

    def fail(path: str, line: int, message: str) -> None:
        report.fail("table", f"{path}:{line}: {message}")

    for path, rows in lit.items():
        for i, row in enumerate(rows or [], 2):
            for key, value in row.items():
                if "\n" in value or "\r" in value or "[[" in value \
                        or "]]" in value:
                    fail(path, i, f"{key} holds a line break or [[ ]]")

    seen: dict[tuple[str, ...], int] = {}
    for path, key in ((QUERIES, ("query_id",)), (SOURCES, ("source_id",)),
                      (CITATIONS, ("citing", "cited"))):
        for i, row in enumerate(lit[path] or [], 2):
            k = (path, *(row[c] for c in key))
            if k in seen:
                fail(path, i, f"{'/'.join(key)} {k[1:]} repeats line "
                     f"{seen[k]}")
            seen.setdefault(k, i)

    query_rows = {q["query_id"]: q for q in queries}
    for i, q in enumerate(queries, 2):
        if not QUERY_ID.fullmatch(q["query_id"]):
            fail(QUERIES, i, f"query_id «{q['query_id']}» is not q<number>")
        if not DATE.fullmatch(q["retrieved"]):
            fail(QUERIES, i, f"retrieved «{q['retrieved']}» is not a date")
        if not (q["n_found"].isdigit() and q["n_kept"].isdigit()):
            fail(QUERIES, i, "n_found and n_kept must be whole numbers")
            continue
        found, kept = int(q["n_found"]), int(q["n_kept"])
        if kept < 1 or found < kept:
            fail(QUERIES, i, f"need 1 <= n_kept <= n_found, got {kept} "
                 f"and {found}")
        if q["database"] != "openalex":
            continue
        tool, work, rel = q["tool"], q["work"], q["relation"]
        if tool not in TOOLS:
            fail(QUERIES, i, f"tool «{tool}» is not one of {sorted(TOOLS)}")
        elif tool == "openalex_search" and (work or rel):
            fail(QUERIES, i, "a search has no work and no relation")
        elif tool == "openalex_work" and (not work or rel
                                          or (found, kept) != (1, 1)):
            fail(QUERIES, i, "openalex_work: work given, no relation, "
                 "n_found = n_kept = 1")
        elif tool == "openalex_links" and (
                not SOURCE_ID.fullmatch(work) or rel not in RELATIONS):
            fail(QUERIES, i, f"openalex_links needs a W id and a relation "
                 f"in {sorted(RELATIONS)}")
        n_sources = sum(q["query_id"] in split_ids(s["found_by"])
                        for s in sources)
        if n_sources != kept:
            fail(QUERIES, i, f"n_kept {kept}, but {n_sources} source(s) "
                 "name this query in found_by")
        if tool == "openalex_links":
            n_cites = sum(c["query_id"] == q["query_id"] for c in citations)
            if n_cites != kept:
                fail(QUERIES, i, f"n_kept {kept}, but {n_cites} citation "
                     "row(s) name this query")

    corpus = read_rows("data/corpus.csv") or []
    by_doi = {norm_doi(r["doi"]): r for r in corpus if r["doi"].strip()}
    by_id = {r["article_id"]: r for r in corpus}
    source_ids = {s["source_id"] for s in sources}
    for i, s in enumerate(sources, 2):
        sid, doi, aid = s["source_id"], s["doi"], s["article_id"]
        if not SOURCE_ID.fullmatch(sid):
            fail(SOURCES, i, f"source_id «{sid}» is not W<number>")
        if doi and (doi != norm_doi(doi) or not doi.startswith("10.")):
            fail(SOURCES, i, f"doi «{doi}»: lower case, no prefix, 10.…")
        for field_ in ("year", "cited_by_count"):
            if s[field_] and not s[field_].isdigit():
                fail(SOURCES, i, f"{field_} «{s[field_]}» is not a number")
        found_by = split_ids(s["found_by"])
        if not found_by:
            fail(SOURCES, i, "found_by is empty")
        for q in found_by:
            if q not in query_rows:
                fail(SOURCES, i, f"found_by names {q}, not in {QUERIES}")
        if s["screening"] == "excluded" and not s["screening_reason"]:
            fail(SOURCES, i, "an excluded source needs a screening_reason")
        if m := DIRECTION_WORDS.search(s["screening_reason"]):
            fail(SOURCES, i, f"screening_reason says «{m[0]}»: it must not "
                 "state the direction of a dependence")
        article = by_doi.get(norm_doi(doi)) if doi else None
        if aid:
            if aid not in by_id:
                report.fail("rule R8", f"{SOURCES}:{i}: article_id {aid} "
                            "is not in data/corpus.csv")
            elif norm_doi(by_id[aid]["doi"]) != norm_doi(doi):
                report.fail("rule R8", f"{SOURCES}:{i}: {sid} has DOI "
                            f"«{doi}», Article {aid} has "
                            f"«{by_id[aid]['doi']}»")
            else:
                a = by_id[aid]
                if s["year"] != a["year"] or " ".join(
                        s["title"].casefold().split()) != " ".join(
                        a["title"].casefold().split()):
                    print(f"info {sid} and Article {aid} differ in title "
                          "or year")
        if article and aid != article["article_id"]:
            report.fail("rule R9", f"{SOURCES}:{i}: {sid} has the DOI of "
                        f"Article {article['article_id']} but does not "
                        "describe it")

    for i, c in enumerate(citations, 2):
        for end in ("citing", "cited"):
            if c[end] not in source_ids:
                fail(CITATIONS, i, f"{end} {c[end]} is not in {SOURCES}")
        q = query_rows.get(c["query_id"])
        if q is None or q["tool"] != "openalex_links":
            fail(CITATIONS, i, f"query {c['query_id']} is not an "
                 "openalex_links query")
        elif q["work"] != c["citing" if q["relation"] == "references"
                           else "cited"]:
            fail(CITATIONS, i, f"query {c['query_id']} asked for the "
                 f"{q['relation']} of {q['work']}, not of this work")

    for i, c in enumerate(lit[SOURCE_CHECKS] or [], 2):
        if c["source_id"] not in source_ids:
            fail(SOURCE_CHECKS, i, f"{c['source_id']} is not in {SOURCES}")
        if not DATE.fullmatch(c["checked"]):
            fail(SOURCE_CHECKS, i, f"checked «{c['checked']}» is not a date")
        if c["outcome"] not in ("ok", "discrepancy"):
            fail(SOURCE_CHECKS, i, f"outcome «{c['outcome']}» is not ok or "
                 "discrepancy")
        elif c["outcome"] == "discrepancy" and not c["note"]:
            fail(SOURCE_CHECKS, i, "a discrepancy needs a note")

    if report.failures == before:
        report.ok(f"literature tables: {len(queries)} queries, "
                  f"{len(sources)} sources, {len(citations)} citations; "
                  "rules R8, R9")


def check_committed(report: Report) -> None:
    """Check that results/ has no uncommitted changes.

    Parameters
    ----------
    report : Report
        Receives the failure.
    """
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "results/"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    if status.returncode != 0:
        report.fail("commit", f"git status failed: {status.stderr.strip()}")
    elif status.stdout:
        report.fail("commit", "uncommitted changes in results/: git add "
                    "results/ && git commit -m \"<what>\"")
    else:
        report.ok("commit: results/ committed")


def owned_notes() -> dict[Path, str]:
    """Return the notes on disk that this script generates.

    Returns
    -------
    dict[Path, str]
        Text of each class note and each note in notes/ whose type is one of
        GENERATED, by path.
    """
    found: dict[Path, str] = {}
    for path in sorted(CLASS_DIR.glob("*.md")):
        found[path] = path.read_text(encoding="utf-8")
    for path in sorted(NOTE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = TYPE_LINE.search(text)
        if match and match.group(1) in GENERATED:
            found[path] = text
    return found


def main() -> int:
    """Generate the graph, or compare it with the notes on disk.

    Returns
    -------
    int
        0 when the graph passes its checks (and, with --check, matches the
        notes on disk), 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="compare with the notes on disk, write nothing")
    mode.add_argument("--validate", action="store_true",
                      help="check the tables and rules only, write nothing")
    parser.add_argument("--root", type=Path,
                        help="project tree to run on (test fixtures)")
    args = parser.parse_args()
    if args.root:
        use_root(args.root)

    with ONTOLOGY.open(encoding="utf-8") as f:
        onto = yaml.safe_load(f)
    report = Report()
    lit = read_literature(report)
    objects = build_objects(lit)
    notes = {n.name: n for n in objects}
    if len(notes) != len(objects):
        report.fail("graph", "two notes share a name")
    check_graph(report, onto, notes)
    check_literature(report, lit)
    if args.validate:
        if not args.root:
            check_committed(report)
        if report.failures:
            print(f"\nFAILED: {report.failures} failure(s)")
            return 1
        print("\nPASSED: tables and rules")
        return 0

    wanted = {CLASS_DIR / f"{c}.md": class_note(c, onto)
              for c in onto["classes"]}
    wanted |= {NOTE_DIR / f"{n.name}.md": n.render() for n in objects}
    counts = {c: sum(n.cls == c for n in objects) for c in sorted(GENERATED)}
    n_links = sum(len(n.links) + 1 for n in objects)
    print(f"info graph: {len(onto['classes'])} class notes, objects "
          f"{counts}, {n_links} links")
    if report.failures:
        print(f"\nFAILED: {report.failures} failure(s); nothing written")
        return 1

    on_disk = owned_notes()
    stale = sorted(p for p in on_disk if p not in wanted)
    changed = sorted(p for p, t in wanted.items() if on_disk.get(p) != t)
    if args.check:
        for path in stale:
            report.fail("graph", f"{path.relative_to(ROOT)} is not "
                        "generated any more")
        for path in changed:
            state = "differs from" if path in on_disk else "is missing,"
            report.fail("graph", f"{path.relative_to(ROOT)} {state} the "
                        "generated note: run tools/graph.py")
        if report.failures:
            print(f"\nFAILED: {report.failures} failure(s)")
            return 1
        print("\nPASSED: notes on disk match the tables")
        return 0

    for path in stale:
        path.unlink()
    for path in changed:
        path.parent.mkdir(exist_ok=True)
        path.write_text(wanted[path], encoding="utf-8")
    VAULT.mkdir(exist_ok=True)
    for name, settings in VAULT_FILES.items():
        if not (VAULT / name).exists():
            (VAULT / name).write_text(json.dumps(settings, indent=1) + "\n",
                                      encoding="utf-8")
    print(f"\nPASSED: {len(changed)} note(s) written, {len(stale)} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
