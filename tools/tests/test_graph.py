"""Tests of tools/graph.py on a fixture project tree (--root).

Run from the project root: ``.venv/bin/python -m pytest tools/tests``.
The fixture has one corpus article (80094) and made-up OpenAlex ids.
"""

import csv
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "tools" / "graph.py"

Tables = dict[str, list[list[str]]]

TITLE_80094 = ("Structural properties of gold-silicon nanohybrids formed by "
               "femtosecond laser ablation in water at different fluences")


def valid_tables() -> Tables:
    """Return literature tables that pass every check."""
    return {
        "data/corpus.csv": [
            ["article_id", "doi", "title", "year"],
            ["80094", "10.1117/12.2217777", TITLE_80094, "2016"]],
        "data/files.csv": [["article_id", "file", "role", "sha256"]],
        "results/queries.csv": [
            ["query_id", "database", "tool", "work", "relation", "request",
             "retrieved", "n_found", "n_kept"],
            ["q1", "openalex", "openalex_work", "10.1117/12.2217777", "",
             "https://api.openalex.org/works/https://doi.org/10.1117/"
             "12.2217777", "2026-10-15", "1", "1"],
            ["q2", "openalex", "openalex_search", "", "",
             "https://api.openalex.org/works?search=gold", "2026-10-15",
             "120", "2"],
            ["q3", "openalex", "openalex_links", "W100", "cited_by",
             "https://api.openalex.org/works?filter=cites:W100",
             "2026-10-15", "40", "1"]],
        "results/sources.csv": [
            ["source_id", "found_by", "doi", "title", "venue", "year",
             "cited_by_count", "screening", "screening_reason",
             "article_id"],
            ["W100", "q1", "10.1117/12.2217777", TITLE_80094, "Proc. SPIE",
             "2016", "5", "relevant", "", "80094"],
            ["W200", "q2", "10.1000/abc", "Gold nanoparticle size and "
             "fluence", "J. Phys. Chem. C", "2015", "50", "relevant",
             "abstract reports sizes at several fluences", ""],
            ["W300", "q2;q3", "", "Spectral aging of colloids", "Opt. Lett.",
             "2019", "11", "excluded", "no laser parameter is varied", ""]],
        "results/citations.csv": [
            ["citing", "cited", "query_id"],
            ["W300", "W100", "q3"]],
        "checks/source_checks.csv": [
            ["source_id", "checked", "outcome", "note"],
            ["W100", "2026-10-15", "discrepancy", "pages 1-8, not 1"]],
    }


def run(tmp: Path, tables: Tables, *args: str) -> subprocess.CompletedProcess:
    """Write the fixture tree and run graph.py on it."""
    shutil.copy(ROOT / "ontology.yaml", tmp / "ontology.yaml")
    for path, rows in tables.items():
        (tmp / path).parent.mkdir(parents=True, exist_ok=True)
        with (tmp / path).open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    return subprocess.run(
        [sys.executable, str(GRAPH), "--root", str(tmp), *args],
        capture_output=True, text=True, check=False)


def test_valid_tables_pass(tmp_path: Path) -> None:
    result = run(tmp_path, valid_tables(), "--validate")
    assert result.returncode == 0, result.stdout
    assert "PASSED" in result.stdout


def test_notes_written_then_checked(tmp_path: Path) -> None:
    assert run(tmp_path, valid_tables()).returncode == 0
    source = (tmp_path / "notes" / "Source W100.md").read_text()
    assert "- foundBy: [[Query q1]]" in source
    assert "- describes: [[Article 80094]]" in source
    assert "Checked 2026-10-15: discrepancy - pages 1-8, not 1" in source
    citing = (tmp_path / "notes" / "Source W300.md").read_text()
    assert "- cites: [[Source W100]]" in citing
    assert (tmp_path / "notes" / "Query q3.md").exists()
    assert (tmp_path / "ontology" / "Source.md").exists()
    result = run(tmp_path, valid_tables(), "--check")
    assert result.returncode == 0, result.stdout


def edit(path: str, row: int, column: str, value: str) -> Callable[[Tables], None]:
    """Return a mutation that sets one cell (row 1 = first data row)."""
    def apply(tables: Tables) -> None:
        header = tables[path][0]
        tables[path][row][header.index(column)] = value
    return apply


def add_row(path: str, row: list[str]) -> Callable[[Tables], None]:
    """Return a mutation that appends a row."""
    return lambda tables: tables[path].append(row)


def set_header(path: str, header: list[str]) -> Callable[[Tables], None]:
    """Return a mutation that replaces a header."""
    def apply(tables: Tables) -> None:
        tables[path][0] = header
    return apply


S, Q, C = "results/sources.csv", "results/queries.csv", "results/citations.csv"

BROKEN = {
    "R8 wrong DOI": (edit(S, 1, "doi", "10.1117/12.9999999"), "rule R8"),
    "R8 unknown article": (edit(S, 2, "article_id", "1"), "rule R8"),
    "R9 missing describes": (edit(S, 1, "article_id", ""), "rule R9"),
    "R7 no query": (edit(S, 2, "found_by", ""), "found_by is empty"),
    "unknown query": (edit(S, 2, "found_by", "q9"), "q9, not in"),
    "duplicate source": (
        add_row(S, ["W200", "q2", "", "Again", "X", "2015", "1", "relevant",
                    "", ""]), "repeats line"),
    "direction word": (
        edit(S, 2, "screening_reason", "size grows with fluence"),
        "must not state"),
    "excluded without reason": (
        edit(S, 3, "screening_reason", ""), "needs a screening_reason"),
    "screening value": (edit(S, 2, "screening", "candidate"), "is not one of"),
    "DOI with prefix": (
        edit(S, 2, "doi", "https://doi.org/10.1000/abc"), "lower case"),
    "line break": (edit(S, 2, "title", "A\n## Links"), "line break"),
    "fake link": (edit(S, 2, "title", "see [[Article 80094]]"), "[[ ]]"),
    "n_kept": (edit(Q, 2, "n_kept", "3"), "n_kept 3"),
    "related": (edit(Q, 3, "relation", "related"), "openalex_links needs"),
    "work with search": (edit(Q, 2, "work", "W1"), "no work"),
    "query id": (edit(Q, 1, "query_id", "Q1"), "not q<number>"),
    "citation end": (edit(C, 1, "cited", "W200"), "asked for the"),
    "citation unknown source": (edit(C, 1, "citing", "W999"), "not in"),
    "header": (set_header(C, ["from", "to", "query_id"]), "header"),
    "check outcome": (
        edit("checks/source_checks.csv", 1, "outcome", "fine"),
        "not ok or discrepancy"),
}


@pytest.mark.parametrize("name", BROKEN)
def test_broken_tables_fail(tmp_path: Path, name: str) -> None:
    mutate, expected = BROKEN[name]
    tables = valid_tables()
    mutate(tables)
    result = run(tmp_path, tables, "--validate")
    assert result.returncode == 1, result.stdout
    assert expected in result.stdout, result.stdout
