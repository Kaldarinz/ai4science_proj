"""Generate the project graph from ontology.yaml and the result tables.

Usage::

    .venv/bin/python tools/graph.py           # check, then write the notes
    .venv/bin/python tools/graph.py --check   # compare the notes on disk

The project root is an Obsidian vault. This script writes one class note
per class of ontology.yaml to ontology/ and one object note per row to
notes/: Article (data/corpus.csv), Claim (results/claims.csv) and Check
(checks/claim_checks.csv). Notes are never edited by hand: run the script
again instead. Notes in notes/ of other types are left alone.

Before writing, every attribute value, link target and link range is
checked against ontology.yaml, and so are the rules with a ``check``
(closed world: a link not written is a link that does not exist). On any
failure nothing is written and the exit code is 1. With --check nothing is
written either; the exit code is 1 when the notes on disk differ from the
generated ones.
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
ONTOLOGY: Final[Path] = ROOT / "ontology.yaml"
CLASS_DIR: Final[Path] = ROOT / "ontology"
NOTE_DIR: Final[Path] = ROOT / "notes"
VAULT: Final[Path] = ROOT / ".obsidian"

CLAIMS: Final[str] = "results/claims.csv"
NO_CLAIMS: Final[str] = "results/no_claims.csv"
CHECKS: Final[str] = "checks/claim_checks.csv"
COMPARISON: Final[str] = "results/comparison.csv"

#: Classes whose notes this script owns in notes/.
GENERATED: Final[frozenset[str]] = frozenset({"Article", "Claim", "Check"})

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


def build_objects() -> list[Note]:
    """Build the object notes from the result tables.

    Returns
    -------
    list[Note]
        Article, Claim and Check notes, sorted by name within each class.
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
    parser.add_argument("--check", action="store_true",
                        help="compare with the notes on disk, write nothing")
    args = parser.parse_args()

    with ONTOLOGY.open(encoding="utf-8") as f:
        onto = yaml.safe_load(f)
    report = Report()
    objects = build_objects()
    notes = {n.name: n for n in objects}
    if len(notes) != len(objects):
        report.fail("graph", "two notes share a name")
    check_graph(report, onto, notes)

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
