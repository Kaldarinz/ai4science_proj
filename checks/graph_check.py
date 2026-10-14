"""Check of the project graph against ontology.yaml and the result tables.

Usage::

    .venv/bin/python checks/graph_check.py

Reads the notes in ontology/, notes/ and tasks/ (checks/graph_spec.md) and
exits with 0 when every rule holds and 1 otherwise; each failure is printed
with the spec section it breaks. It never reads checks/claims_gold.csv: a
check the agent runs must not tell it how its claims compare with the gold
labels.
"""

import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
FOLDERS: Final[tuple[str, ...]] = ("ontology", "notes", "tasks")
LINK: Final[re.Pattern[str]] = re.compile(r"\[\[([^\]]+)\]\]")
LINK_LINE: Final[re.Pattern[str]] = re.compile(r"^- (\w+): (.*)$")
BAD_NAME: Final[re.Pattern[str]] = re.compile(r"[/\\:#|\[\]]")
DONE: Final[frozenset[str]] = frozenset({"done", "accepted"})


@dataclass
class Note:
    """One Markdown note of the vault."""

    name: str
    path: Path
    meta: dict[str, str]
    links: list[tuple[str, str]] = field(default_factory=list)
    sections: set[str] = field(default_factory=set)
    text: str = ""

    @property
    def cls(self) -> str:
        """Return the note's class: ``type``, or the class it describes."""
        if self.meta.get("kind") == "class":
            return "<class>"
        return self.meta.get("type", "")


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
            Spec section the failure breaks, e.g. ``graph §2.2``.
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


def read_rows(path: Path) -> list[dict[str, str]] | None:
    """Read a CSV as dictionaries, or None when the file does not exist.

    Parameters
    ----------
    path : Path
        CSV file.

    Returns
    -------
    list[dict[str, str]] | None
        The rows, or None.
    """
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_note(path: Path) -> Note:
    """Parse front matter, links and section titles of one note.

    Parameters
    ----------
    path : Path
        The Markdown file.

    Returns
    -------
    Note
        The parsed note; links are the ``- relation: [[target]]`` lines of
        its ``## Links`` section.
    """
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end > 0:
            for line in text[4:end].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            body = text[end + 4:]
    note = Note(path.stem, path, meta, text=body)
    in_links = False
    for line in body.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            note.sections.add(title)
            in_links = title == "Links"
            continue
        if in_links and line.strip():
            match = LINK_LINE.match(line.strip())
            note.links.append(
                (match.group(1), match.group(2)) if match else ("", line))
    return note


def load_notes(report: Report) -> dict[str, Note]:
    """Read every note in ontology/, notes/ and tasks/.

    Parameters
    ----------
    report : Report
        Receives a failure for a duplicate name or a nested folder.

    Returns
    -------
    dict[str, Note]
        Notes by name (file name without ``.md``).
    """
    notes: dict[str, Note] = {}
    for folder in FOLDERS:
        base = ROOT / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if path.parent != base:
                report.fail("graph §2.2", f"{path.relative_to(ROOT)}: notes "
                            "in subfolders (a `/` in a name?)")
                continue
            note = parse_note(path)
            if note.name in notes:
                report.fail("graph §2.2", f"two notes named «{note.name}»")
            notes[note.name] = note
    return notes


def check_classes(
    report: Report, onto: dict, notes: dict[str, Note],
) -> None:
    """One class note per class of ontology.yaml, in ontology/.

    Parameters
    ----------
    report : Report
        Receives the failures.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All notes.
    """
    classes = set(onto["classes"])
    found = {n.name for n in notes.values()
             if n.path.parent.name == "ontology"}
    for name in sorted(classes - found):
        report.fail("graph §2.1", f"class {name} has no note in ontology/")
    for name in sorted(found - classes):
        report.fail("graph §2.1", f"ontology/{name}.md is not a class of "
                    "ontology.yaml")
    for name in sorted(found & classes):
        if notes[name].meta.get("kind") != "class":
            report.fail("graph §2.1", f"ontology/{name}.md lacks "
                        "`kind: class`")
    if found == classes:
        report.ok(f"class notes: {len(classes)}, one per class")


def resolve(target: str, notes: dict[str, Note]) -> str | None:
    """Return the class of a link target, or None if it does not exist.

    Parameters
    ----------
    target : str
        Text inside ``[[…]]``.
    notes : dict[str, Note]
        All notes.

    Returns
    -------
    str | None
        ``File`` for an existing project path, the note's class for a
        note, None otherwise.
    """
    if target in notes:
        return notes[target].cls
    path = ROOT / target
    if "/" in target and path.exists() and ROOT in path.resolve().parents:
        return "File"
    return None


def as_list(value: str | list[str]) -> list[str]:
    """Return a domain or range as a list."""
    return value if isinstance(value, list) else [value]


def check_objects(
    report: Report, onto: dict, notes: dict[str, Note],
) -> Counter:
    """Format, attributes and links of object and task notes.

    Parameters
    ----------
    report : Report
        Receives the failures.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All notes.

    Returns
    -------
    Counter
        Number of typed links by relation.
    """
    classes = set(onto["classes"])
    props, attrs = onto["properties"], onto["attributes"]
    counted: Counter = Counter()
    for note in notes.values():
        if note.cls == "<class>":
            continue
        where = f"{note.path.relative_to(ROOT)}"
        if note.cls not in classes or note.cls == "File":
            report.fail("graph §2.2", f"{where}: `type: {note.cls}` is not a "
                        "class with notes (new type: the human decides)")
            continue
        if (note.cls == "Task") != (note.path.parent.name == "tasks"):
            report.fail("graph §3", f"{where}: Task notes, and only they, "
                        "live in tasks/")
        if note.name in classes:
            report.fail("graph §2.2", f"{where}: a note named as a class")
        if BAD_NAME.search(note.name):
            report.fail("graph §2.2", f"{where}: `/ \\ : # | [ ]` in the name")
        if "`[[" in note.text:
            report.fail("graph §2.2", f"{where}: a link in backticks")
        for key, value in note.meta.items():
            if key == "type":
                continue
            spec = attrs.get(key)
            if spec is None or spec["domain"] != note.cls:
                report.fail("graph §2.2", f"{where}: `{key}` is not an "
                            f"attribute of {note.cls}")
            elif value not in spec["values"]:
                report.fail("graph §2.2", f"{where}: {key} «{value}» not in "
                            f"{spec['values']}")
        types = [t for rel, t in note.links if rel == "type"]
        if types != [f"[[{note.cls}]]"]:
            report.fail("graph §2.2", f"{where}: needs exactly one line "
                        f"`- type: [[{note.cls}]]` in ## Links")
        for rel, value in note.links:
            if rel == "type":
                continue
            targets = LINK.findall(value)
            if not rel or len(targets) != 1 or LINK.sub("", value).strip():
                report.fail("graph §2.2", f"{where}: «- {rel}: {value}» is "
                            "not one `- relation: [[target]]` link")
                continue
            target = targets[0]
            spec = props.get(rel)
            if spec is None:
                report.fail("graph §2.2", f"{where}: relation `{rel}` is not "
                            "in ontology.yaml")
                continue
            if note.cls not in as_list(spec["domain"]):
                report.fail("graph §2.2", f"{where}: {rel} starts from "
                            f"{as_list(spec['domain'])}, not {note.cls}")
            target_cls = resolve(target, notes)
            if target_cls is None:
                report.fail("graph §2.2", f"{where}: [[{target}]] does not "
                            "exist")
            elif target_cls == "<class>":
                report.fail("graph §2.2", f"{where}: {rel} leads to a class; "
                            "only `type` does")
            elif target_cls not in as_list(spec["range"]):
                report.fail("graph §2.2", f"{where}: {rel} leads to "
                            f"{as_list(spec['range'])}, [[{target}]] is "
                            f"{target_cls}")
            counted[rel] += 1
    return counted


def check_sources(report: Report, notes: dict[str, Note]) -> None:
    """Article, Claim, Series and Check notes against the result tables.

    Parameters
    ----------
    report : Report
        Receives the failures.
    notes : dict[str, Note]
        All notes.
    """
    corpus = {r["article_id"] for r in read_rows(ROOT / "data/corpus.csv")
              or []}
    claims = {r["claim_id"]: r for r in read_rows(ROOT / "results/claims.csv")
              or []}
    reviews = {(r["claim_id"], r["reason"]): r
               for r in read_rows(ROOT / "checks/claim_checks.csv") or []}
    comparison = read_rows(ROOT / "results/comparison.csv")
    by_cls: dict[str, dict[str, Note]] = {}
    for note in notes.values():
        by_cls.setdefault(note.cls, {})[note.name] = note

    for name, note in by_cls.get("Article", {}).items():
        if name.removeprefix("Article ") not in corpus:
            report.fail("graph §2.2", f"«{name}»: no such article_id in "
                        "data/corpus.csv")

    found = {n.removeprefix("Claim "): n for n in by_cls.get("Claim", {})}
    for cid in sorted(set(claims) - set(found)):
        report.fail("graph §2.2", f"claim {cid} of results/claims.csv has no "
                    f"note «Claim {cid}»")
    for cid in sorted(set(found) - set(claims)):
        report.fail("graph §2.2", f"«{found[cid]}»: no such claim_id in "
                    "results/claims.csv")
    for cid in sorted(set(found) & set(claims)):
        note, row = notes[found[cid]], claims[cid]
        for key in ("direction", "basis"):
            if note.meta.get(key) != row[key]:
                report.fail("graph §2.2", f"«{note.name}»: {key} "
                            f"«{note.meta.get(key)}», results/claims.csv has "
                            f"«{row[key]}»")
        article = f"[[Article {row['article_id']}]]"
        if ("extractedFrom", article) not in note.links:
            report.fail("graph §2.2", f"«{note.name}»: needs `- "
                        f"extractedFrom: {article}`")
        expected = verdict(cid, row, comparison)
        if note.meta.get("verdict") != expected:
            report.fail("graph §2.3", f"«{note.name}»: verdict "
                        f"«{note.meta.get('verdict')}», expected "
                        f"«{expected}»")

    if by_cls.get("Series"):
        report.fail("graph §2.2", "Series notes exist, but tools/ablation_db.py "
                    "does not; their source cannot be checked")

    for name, note in by_cls.get("Check", {}).items():
        cid, _, reason = name.removeprefix("Check ").rpartition(" ")
        if note.meta.get("reason") != reason:
            report.fail("graph §2.2", f"«{name}»: name and `reason` differ")
        if ("checks", f"[[Claim {cid}]]") not in note.links:
            report.fail("graph §2.2", f"«{name}»: needs `- checks: "
                        f"[[Claim {cid}]]`")
        stated = re.search(r"^Outcome: (\w+)", note.text, re.M)
        outcome = stated.group(1) if stated else None
        if (cid, reason) not in reviews:
            report.fail("graph §2.2", f"«{name}»: no row ({cid}, {reason}) in "
                        "checks/claim_checks.csv")
        elif outcome != reviews[(cid, reason)]["outcome"]:
            report.fail("graph §2.2", f"«{name}»: `Outcome:` differs from "
                        "checks/claim_checks.csv")

    checks = set(by_cls.get("Check", {}))
    for cid, reason in sorted(reviews):
        if f"Check {cid} {reason}" not in checks:
            report.fail("graph §2.2", f"row ({cid}, {reason}) of "
                        f"checks/claim_checks.csv has no note «Check {cid} "
                        f"{reason}»")


def verdict(
    cid: str, row: dict[str, str], comparison: list[dict[str, str]] | None,
) -> str | None:
    """Return the verdict a claim note must carry (graph_spec §2.3).

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
        The verdict, or None when the claim must have none.
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


def check_tasks(report: Report, notes: dict[str, Note]) -> Counter:
    """Task layout and statuses (graph_spec §3).

    Parameters
    ----------
    report : Report
        Receives the failures.
    notes : dict[str, Note]
        All notes.

    Returns
    -------
    Counter
        Tasks by status.
    """
    tasks = {n: t for n, t in notes.items() if t.cls == "Task"}
    children: dict[str, list[str]] = {}
    for name, task in tasks.items():
        for rel, value in task.links:
            if rel == "subtaskOf":
                children.setdefault(value.strip("[]"), []).append(name)
    statuses: Counter = Counter()
    for name, task in tasks.items():
        status = task.meta.get("status")
        statuses[status] += 1
        if status is None:
            report.fail("graph §3", f"task «{name}» has no `status`")
        if not re.search(r"^Done when: \S", task.text, re.M):
            report.fail("graph §3", f"task «{name}» has no `Done when:`")
        is_sub = any(rel == "subtaskOf" for rel, _ in task.links)
        if is_sub == bool(re.search(r"^Request: ", task.text, re.M)):
            report.fail("graph §3", f"task «{name}»: `Request:` belongs to "
                        "top-level tasks only, and every one has it")
        if status in DONE | {"blocked"} and "Summary" not in task.sections:
            report.fail("graph §3", f"task «{name}» is {status} without "
                        "## Summary")
        if status == "accepted" and "Accepted by the user:" not in task.text:
            report.fail("graph §3", f"task «{name}» is accepted without "
                        "`Accepted by the user:`")
        if status in DONE:
            if not children.get(name) and not any(
                    rel == "resolvedBy" for rel, _ in task.links):
                report.fail("rule R8", f"task «{name}» is {status} with "
                            "neither `resolvedBy` nor subtasks")
    return statuses


def members(
    name: str, onto: dict, notes: dict[str, Note],
) -> dict[str, Note]:
    """Return the notes of a class, or of a class defined by a rule.

    Parameters
    ----------
    name : str
        Class name, or the ``name`` of a ``defined_value`` rule.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All notes.

    Returns
    -------
    dict[str, Note]
        Member notes by name.
    """
    for rule in onto["rules"]:
        check = rule.get("check", {})
        if check.get("kind") == "defined_value" and check["name"] == name:
            base = members(check["class"], onto, notes)
            return {n: x for n, x in base.items()
                    if x.meta.get(check["attribute"]) in check["values"]}
    return {n: x for n, x in notes.items() if x.cls == name}


def check_rules(report: Report, onto: dict, notes: dict[str, Note]) -> None:
    """Check each rule with a `check` on the graph, closed world.

    Parameters
    ----------
    report : Report
        Receives one failure per violating note.
    onto : dict
        Parsed ontology.yaml.
    notes : dict[str, Note]
        All notes.
    """
    def targets(note: Note, rel: str) -> list[str]:
        return [LINK.sub(r"\1", v) for r, v in note.links if r == rel]

    for rule in onto["rules"]:
        check = rule.get("check")
        if check is None or check["kind"] == "defined_value":
            continue
        rid, kind = rule["id"], check["kind"]
        bad: list[str] = []
        for name, note in members(check["class"], onto, notes).items():
            if kind == "some":
                ok = members(check["target"], onto, notes)
                if not any(t in ok for t in targets(note, check["property"])):
                    bad.append(name)
            elif kind == "some_inverse":
                src = members(check["source"], onto, notes)
                if not any(name in targets(s, check["property"])
                           for s in src.values()):
                    bad.append(name)
            elif kind == "all_inverse":
                src = members(check["source"], onto, notes)
                linked = [n for n, x in notes.items()
                          if name in targets(x, check["property"])]
                if any(n not in src for n in linked):
                    bad.append(name)
            elif kind == "section":
                if check["section"] not in note.sections:
                    bad.append(name)
            else:
                report.fail("graph", f"rule {rid}: check kind {kind} is not "
                            "supported")
                break
        for name in bad:
            report.fail(f"rule {rid}", f"«{name}»: {rule['text']}")
        if not bad:
            report.ok(f"rule {rid}: {rule['text']}")


def main() -> int:
    """Run all checks and print a summary.

    Returns
    -------
    int
        0 when nothing failed, 1 otherwise.
    """
    report = Report()
    onto = yaml.safe_load((ROOT / "ontology.yaml").read_text(encoding="utf-8"))
    notes = load_notes(report)
    check_classes(report, onto, notes)
    links = check_objects(report, onto, notes)
    check_sources(report, notes)
    statuses = check_tasks(report, notes)
    check_rules(report, onto, notes)
    objects = Counter(n.cls for n in notes.values() if n.cls != "<class>")
    print(f"info objects: {dict(sorted(objects.items()))}; links: "
          f"{sum(links.values())}; tasks: {dict(statuses)}")
    if report.failures:
        print(f"\nFAILED: {report.failures} failure(s)")
        return 1
    print("\nPASSED: 0 failure(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
