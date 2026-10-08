"""Readiness check for claims_spec.md and results_spec.md.

Usage::

    .venv/bin/python checks/check.py                  # everything
    .venv/bin/python checks/check.py --article 80094  # one article

Exits with 0 when every rule holds and 1 otherwise; each failure is
printed with the spec section it breaks. Precision and recall against
checks/claims_gold.csv are printed and never fail the check
(results_spec.md §7.6).
"""

import argparse
import csv
import hashlib
import importlib
import json
import logging
import math
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Final, NamedTuple, Protocol, TypeAlias, TypedDict, cast

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DATA: Final[Path] = ROOT / "data"
RESULTS: Final[Path] = ROOT / "results"
GOLD: Final[Path] = ROOT / "checks" / "claims_gold.csv"

# Font warnings for some PDFs run to ~90 lines per read and would flood
# the agent's context; text extraction works without fontTools.
logging.getLogger("pypdf").setLevel(logging.ERROR)

CORPUS_COLUMNS: Final[tuple[str, ...]] = (
    "article_id", "doi", "title", "year",
)
FILES_COLUMNS: Final[tuple[str, ...]] = (
    "article_id", "file", "role", "sha256",
)
CLAIMS_COLUMNS: Final[tuple[str, ...]] = (
    "claim_id", "article_id", "file", "page", "quote",
    "variable_written", "variable", "direction", "basis", "material",
    "medium_class", "conditions",
)
NO_CLAIMS_COLUMNS: Final[tuple[str, ...]] = (
    "article_id", "file", "page", "quote", "reason",
)
COMPARISON_COLUMNS: Final[tuple[str, ...]] = (
    "claim_id", "series_id", "direction", "shape_primary",
    "shape_lenient", "agree_primary", "agree_lenient", "note",
)
GOLD_KEY: Final[tuple[str, ...]] = (
    "article_id", "variable", "direction", "basis", "medium_class",
)

ROLES: Final[frozenset[str]] = frozenset({"main", "supplement"})
VARIABLES: Final[frozenset[str]] = frozenset(
    {"fluence", "energy", "power", "intensity", "unspecified"})
DIRECTIONS: Final[tuple[str, ...]] = (
    "increase", "decrease", "no_effect", "non_monotonic", "affects",
)
BASES: Final[tuple[str, ...]] = ("own_data", "cited", "general")
MEDIUM_CLASSES: Final[frozenset[str]] = frozenset(
    {"colloid", "water", "aqueous", "organic", "other"})
SHAPES: Final[tuple[str, ...]] = (
    "increasing", "decreasing", "flat", "peak", "valley", "irregular",
)
MODELS: Final[tuple[str, ...]] = ("primary", "lenient")

AGREES: Final[dict[str, frozenset[str]]] = {
    "increase": frozenset({"increasing"}),
    "decrease": frozenset({"decreasing"}),
    "no_effect": frozenset({"flat"}),
    "non_monotonic": frozenset({"peak", "valley", "irregular"}),
    "affects": frozenset(s for s in SHAPES if s != "flat"),
}

Row: TypeAlias = dict[str, str]
FileKey: TypeAlias = tuple[int, str]


class Article(TypedDict):
    """An article as `find_articles` returns it (results_spec §4)."""

    article_id: int
    doi: str
    title: str
    year: int
    n_experiments: int


class Series(TypedDict):
    """A series row as `list_series` returns it (results_spec §4)."""

    article_id: int
    series_id: str
    n_points: int
    x_quantity: str
    size_quantity: str
    size_statistic: str
    size_technique: str
    size_source: str
    storage_duration_h: float | None
    pulse_duration_fs: float
    pulse_duration_class: str
    wavelength_nm: float
    medium_class: str
    shape_primary: str
    shape_lenient: str
    spearman_rho: float | None
    notes: str


class AblationTools(Protocol):
    """The part of the tool contract this check uses."""

    def find_articles(self, material: str = "Au") -> list[Article]:
        """List the articles holding experiments with `material`."""
        ...

    def list_series(self, article_id: int) -> list[Series]:
        """List the series of one article."""
        ...


class QuotePosition(NamedTuple):
    """Where a claim's quote stands in its article."""

    article_id: int
    number: int
    role: str
    file: str
    page: int
    offset: int


class Reference(NamedTuple):
    """Expected pairing of one 80094 claim (results_spec §7.5)."""

    series_id: str
    shape_primary: str
    shape_lenient: str
    agree_primary: bool
    agree_lenient: bool


# Keyed by the own_data claim's (direction, medium_class).
REFERENCE: Final[dict[tuple[str, str], Reference]] = {
    ("increase", "water"):
        Reference("80094-s1", "increasing", "increasing", True, True),
    ("no_effect", "colloid"):
        Reference("80094-s2", "peak", "flat", False, True),
}


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
            Spec section the failure breaks, e.g. ``claims §4``.
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


class Pages:
    """Normalized page texts, read once per PDF with pypdf."""

    def __init__(self) -> None:
        """Start with an empty cache."""
        self._cache: dict[FileKey, list[str]] = {}

    def get(self, article_id: int, file: str) -> list[str]:
        """Return the normalized text of every page of one PDF.

        Parameters
        ----------
        article_id : int
            Article whose folder holds the PDF.
        file : str
            File name of the PDF inside that folder.

        Returns
        -------
        list[str]
            One normalized text per page, page 1 first.
        """
        key = (article_id, file)
        if key not in self._cache:
            from pypdf import PdfReader

            path = DATA / "articles" / f"{article_id}" / file
            reader = PdfReader(path)
            self._cache[key] = [
                normalize(page.extract_text() or "")
                for page in reader.pages
            ]
        return self._cache[key]


def read_csv(
    path: Path, columns: Sequence[str], report: Report, rule: str,
) -> list[Row] | None:
    """Read a CSV whose header must equal `columns`.

    Parameters
    ----------
    path : Path
        CSV file to read.
    columns : Sequence[str]
        Expected header, in order.
    report : Report
        Receives a failure when the file is missing or misshaped.
    rule : str
        Spec section to cite in that failure.

    Returns
    -------
    list[Row] | None
        The rows, or None when the file cannot be used.
    """
    name = path.relative_to(ROOT)
    if not path.exists():
        report.fail(rule, f"{name} does not exist")
        return None
    if not path.read_bytes().endswith(b"\n"):
        # An appended row would merge into the last one.
        report.fail("results §1", f"{name} does not end with a newline")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(columns):
            report.fail(
                rule,
                f"{name} columns are {reader.fieldnames}, "
                f"expected {list(columns)}",
            )
            return None
        rows = []
        for row in reader:
            # DictReader puts extra fields under None and fills missing
            # ones with None: an unquoted comma shifts the columns.
            if None in row or None in row.values():
                report.fail(
                    "results §1",
                    f"{name} line {reader.line_num}: field count differs "
                    f"from the header",
                )
                continue
            rows.append(row)
        return rows


def as_int(value: str, minimum: int | None = None) -> int | None:
    """Parse an integer field.

    Parameters
    ----------
    value : str
        Field as read from a CSV.
    minimum : int | None
        Smallest accepted value, if any.

    Returns
    -------
    int | None
        The integer, or None when the field is not one or is below
        `minimum`.
    """
    if not re.fullmatch(r"-?\d+", value or ""):
        return None
    number = int(value)
    if minimum is not None and number < minimum:
        return None
    return number


def normalize(text: str) -> str:
    """Normalize text for quote matching (claims_spec §4).

    Parameters
    ----------
    text : str
        A quote or a page's extracted text.

    Returns
    -------
    str
        The text after NFKD without combining marks, case folding,
        removal of a hyphen before a line break, and collapsing of
        whitespace runs.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    text = text.replace("\r\n", "\n").replace("-\n", "")
    return re.sub(r"\s+", " ", text).strip()


def check_data(
    report: Report, article: int | None,
) -> tuple[set[int], dict[FileKey, str]]:
    """Check corpus.csv, files.csv and the PDFs' hashes.

    Parameters
    ----------
    report : Report
        Receives every failure.
    article : int | None
        Limit the PDF checks to this article, or None for all.

    Returns
    -------
    tuple[set[int], dict[FileKey, str]]
        The checked article ids, and the role of each listed PDF keyed
        by (article id, file name).
    """
    corpus = read_csv(
        DATA / "corpus.csv", CORPUS_COLUMNS, report, "claims §1")
    files = read_csv(
        DATA / "files.csv", FILES_COLUMNS, report, "claims §1")
    if corpus is None or files is None:
        return set(), {}

    ids: set[int] = set()
    for row in corpus:
        aid = as_int(row["article_id"], 1)
        if aid is None or aid in ids:
            report.fail(
                "claims §1",
                f"corpus.csv: bad or repeated article_id "
                f"{row['article_id']!r}",
            )
        elif as_int(row["year"], 1900) is None:
            report.fail(
                "claims §1",
                f"corpus.csv: article {aid} has year {row['year']!r}",
            )
        else:
            ids.add(aid)

    roles: dict[FileKey, str] = {}
    for row in files:
        aid = as_int(row["article_id"], 1)
        if aid is None or aid not in ids:
            report.fail(
                "claims §1",
                f"files.csv: article {row['article_id']!r} is not in "
                f"corpus.csv",
            )
            continue
        if article is not None and aid != article:
            continue
        if row["role"] not in ROLES:
            report.fail(
                "claims §1",
                f"files.csv: {row['file']} has role {row['role']!r}",
            )
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            report.fail(
                "claims §1",
                f"files.csv: {row['file']} has a malformed sha256",
            )
        roles[(aid, row["file"])] = row["role"]
        path = DATA / "articles" / f"{aid}" / row["file"]
        name = path.relative_to(ROOT)
        if not path.exists():
            report.fail("results §7.2", f"{name} is listed but missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            report.fail("results §7.2", f"{name} does not match its sha256")

    for path in sorted((DATA / "articles").glob("*/*.pdf")):
        aid = as_int(path.parent.name)
        if article is not None and aid != article:
            continue
        if aid is None or (aid, path.name) not in roles:
            report.fail(
                "results §7.2",
                f"{path.relative_to(ROOT)} is not listed in files.csv",
            )

    if article is not None:
        if article not in ids:
            report.fail(
                "claims §1", f"article {article} is not in corpus.csv")
        ids &= {article}
    report.ok(f"data: {len(ids)} article(s), {len(roles)} PDF(s) checked")
    return ids, roles


def check_claims(
    report: Report,
    ids: set[int],
    roles: dict[FileKey, str],
    article: int | None,
) -> list[Row]:
    """Check results/claims.csv against claims_spec §2–§4.

    Parameters
    ----------
    report : Report
        Receives every failure.
    ids : set[int]
        Article ids of the corpus that are being checked.
    roles : dict[FileKey, str]
        Role of each listed PDF, keyed by (article id, file name).
    article : int | None
        Check only this article's claims, or None for all.

    Returns
    -------
    list[Row]
        The claims that passed the row checks and whose quote was found.
    """
    rows = read_csv(
        RESULTS / "claims.csv", CLAIMS_COLUMNS, report, "claims §3")
    if rows is None:
        return []
    enums: tuple[tuple[str, frozenset[str]], ...] = (
        ("variable", VARIABLES),
        ("direction", frozenset(DIRECTIONS)),
        ("basis", frozenset(BASES)),
        ("medium_class", MEDIUM_CLASSES | {"unspecified"}),
    )
    pages = Pages()
    claims: list[Row] = []
    seen: set[str] = set()
    numbers: dict[int, list[int]] = {}
    positions: dict[str, QuotePosition] = {}

    for row in rows:
        cid = row["claim_id"]
        aid = as_int(row["article_id"])
        if article is not None and aid != article:
            continue
        where = f"claim {cid!r}"
        match = re.fullmatch(r"(\d+)-c(\d+)", cid)
        if aid is None or not match or int(match.group(1)) != aid:
            report.fail(
                "claims §3", f"{where}: claim_id must be <article_id>-c<k>")
            continue
        if cid in seen:
            report.fail("claims §3", f"{where}: repeated claim_id")
            continue
        seen.add(cid)
        number = int(match.group(2))
        numbers.setdefault(aid, []).append(number)
        if aid not in ids:
            report.fail(
                "claims §3", f"{where}: article {aid} is not in corpus.csv")
            continue

        for column, allowed in enums:
            if row[column] not in allowed:
                report.fail(
                    "claims §3",
                    f"{where}: {column} {row[column]!r} not in "
                    f"{sorted(allowed)}",
                )
        for column in ("variable_written", "material", "quote"):
            if not row[column].strip():
                report.fail("claims §3", f"{where}: {column} is empty")

        found = find_quote(report, where, aid, row, roles, pages, "claims §3")
        if found is None:
            continue
        role, page, offset = found
        positions[cid] = QuotePosition(
            aid, number, role, row["file"], page, offset)
        claims.append(row)

    check_numbering(report, numbers, positions)
    check_duplicates(report, claims)
    report.ok(f"claims: {len(claims)} claim(s) checked")
    return claims


def find_quote(
    report: Report,
    where: str,
    aid: int,
    row: Row,
    roles: dict[FileKey, str],
    pages: Pages,
    rule: str,
) -> tuple[str, int, int] | None:
    """Locate a row's quote on its page (claims_spec §4).

    Parameters
    ----------
    report : Report
        Receives every failure.
    where : str
        Names the row in failure messages.
    aid : int
        Article id of the row.
    row : Row
        A row with `file`, `page` and `quote`.
    roles : dict[FileKey, str]
        Role of each listed PDF, keyed by (article id, file name).
    pages : Pages
        Page texts, read once per PDF.
    rule : str
        Spec section to cite for a bad `file` or `page`.

    Returns
    -------
    tuple[str, int, int] | None
        Role of the file, page and offset of the quote on it, or None
        when the quote cannot be located.
    """
    role = roles.get((aid, row["file"]))
    page = as_int(row["page"], 1)
    if role is None:
        report.fail(
            rule,
            f"{where}: file {row['file']!r} is not listed for article {aid}",
        )
        return None
    if page is None:
        report.fail(
            rule, f"{where}: page {row['page']!r} is not an integer ≥ 1")
        return None
    texts = pages.get(aid, row["file"])
    if page > len(texts):
        report.fail(
            rule,
            f"{where}: page {page} beyond the {len(texts)} pages of "
            f"{row['file']}",
        )
        return None
    quote = normalize(row["quote"])
    offset = texts[page - 1].find(quote)
    if not quote or offset < 0:
        report.fail(
            "claims §4",
            f"{where}: quote not found on page {page} of {row['file']}",
        )
        return None
    return role, page, offset


def check_no_claims(
    report: Report,
    ids: set[int],
    roles: dict[FileKey, str],
    claims: list[Row],
) -> None:
    """Check every article has claims or one no-claims row (claims_spec §8).

    Parameters
    ----------
    report : Report
        Receives every failure.
    ids : set[int]
        Article ids of the corpus that are being checked.
    roles : dict[FileKey, str]
        Role of each listed PDF, keyed by (article id, file name).
    claims : list[Row]
        Claims that passed `check_claims`.
    """
    path = RESULTS / "no_claims.csv"
    rows: list[Row] = []
    if path.exists():
        read = read_csv(path, NO_CLAIMS_COLUMNS, report, "claims §8")
        rows = read if read is not None else []
    pages = Pages()
    explained: Counter[int] = Counter()

    for row in rows:
        aid = as_int(row["article_id"])
        if aid is not None and aid not in ids:
            continue
        where = f"no_claims row for article {row['article_id']!r}"
        if aid is None:
            report.fail("claims §8", f"{where}: article_id is not an integer")
            continue
        explained[aid] += 1
        if not row["reason"].strip():
            report.fail("claims §8", f"{where}: reason is empty")
        find_quote(report, where, aid, row, roles, pages, "claims §8")

    with_claims = {int(c["article_id"]) for c in claims}
    for aid in sorted(ids):
        n = explained[aid]
        if aid in with_claims and n:
            report.fail(
                "claims §8",
                f"article {aid} has claims and a no_claims row",
            )
        elif aid not in with_claims and n != 1:
            report.fail(
                "claims §8",
                f"article {aid}: no valid claims, so no_claims.csv needs "
                f"exactly one row for it, found {n}",
            )
    report.ok(f"no_claims: {sum(explained.values())} row(s) checked")


def check_numbering(
    report: Report,
    numbers: dict[int, list[int]],
    positions: dict[str, QuotePosition],
) -> None:
    """Check claim numbers run 1..n in quote order (claims_spec §3).

    Parameters
    ----------
    report : Report
        Receives every failure.
    numbers : dict[int, list[int]]
        Every well-formed claim number, by article id.
    positions : dict[str, QuotePosition]
        Position of every located quote, by claim id.
    """
    for aid, ks in numbers.items():
        if sorted(ks) != list(range(1, len(ks) + 1)):
            report.fail(
                "claims §3",
                f"article {aid}: claim numbers are not 1..{len(ks)}",
            )
    by_article: dict[int, list[tuple[QuotePosition, str]]] = {}
    for cid, position in positions.items():
        by_article.setdefault(position.article_id, []).append(
            (position, cid))
    for items in by_article.values():
        items.sort(key=lambda item: item[0].number)
        for i, (a, a_id) in enumerate(items):
            for b, b_id in items[i + 1:]:
                swapped_roles = a.role == "supplement" and b.role == "main"
                swapped_place = a.file == b.file and (
                    (a.page, a.offset) > (b.page, b.offset))
                if swapped_roles or swapped_place:
                    report.fail(
                        "claims §3",
                        f"{a_id} is numbered before {b_id} but stands "
                        f"after it",
                    )


def check_duplicates(report: Report, claims: list[Row]) -> None:
    """Check one claim per distinct key in an article (claims_spec §2).

    Parameters
    ----------
    report : Report
        Receives every failure.
    claims : list[Row]
        Claims that passed the row checks.
    """
    columns = ("material", "medium_class", "variable", "direction", "basis")
    keys = Counter(
        (c["article_id"], *(c[column] for column in columns))
        for c in claims
    )
    for key, n in keys.items():
        if n > 1:
            report.fail(
                "claims §2",
                f"article {key[0]}: {n} claims share {key[1:]}",
            )


def report_gold(claims: list[Row], article: int | None) -> None:
    """Print precision and recall against the hand labels.

    Never fails: results_spec §7.6.

    Parameters
    ----------
    claims : list[Row]
        Claims that passed the row checks.
    article : int | None
        Compare only this article, or None for all labelled ones.
    """
    if not GOLD.exists():
        print("info no checks/claims_gold.csv: precision and recall "
              "not computed")
        return
    with GOLD.open(newline="", encoding="utf-8") as f:
        gold = [
            row for row in csv.DictReader(f)
            if article is None or as_int(row["article_id"]) == article
        ]
    labelled = {row["article_id"] for row in gold}
    expected = Counter(tuple(row[k] for k in GOLD_KEY) for row in gold)
    found = Counter(
        tuple(c[k] for k in GOLD_KEY)
        for c in claims if c["article_id"] in labelled
    )
    hits = sum((expected & found).values())
    n_found = sum(found.values())
    n_expected = sum(expected.values())
    precision = hits / n_found if n_found else math.nan
    recall = hits / n_expected if n_expected else math.nan
    print(
        f"info gold: {len(labelled)} article(s); precision "
        f"{precision:.2f} ({hits}/{n_found}), recall {recall:.2f} "
        f"({hits}/{n_expected})"
    )


def parse_bool(value: str) -> bool | None:
    """Parse a boolean CSV field.

    Parameters
    ----------
    value : str
        Field as read from a CSV.

    Returns
    -------
    bool | None
        True or False for ``true`` or ``false`` in any case, None for
        anything else.
    """
    return {"true": True, "false": False}.get(value.strip().lower())


def shape_of(series: Series, model: str) -> str:
    """Return a series' shape under one error model.

    Parameters
    ----------
    series : Series
        Series row from the tools.
    model : str
        ``primary`` or ``lenient``.

    Returns
    -------
    str
        The shape under that model.
    """
    if model == "primary":
        return series["shape_primary"]
    return series["shape_lenient"]


def load_tools(report: Report) -> AblationTools | None:
    """Import tools/ablation_db.py.

    Parameters
    ----------
    report : Report
        Receives a failure when the import fails.

    Returns
    -------
    AblationTools | None
        The tools module, or None when it cannot be imported.
    """
    # Imported by name: the module is maintained separately and may not
    # exist yet, so a static import would not resolve.
    sys.path.insert(0, f"{ROOT}")
    try:
        module = importlib.import_module("tools.ablation_db")
    except Exception as error:
        report.fail(
            "results §4",
            f"tools/ablation_db.py cannot be imported: {error}",
        )
        return None
    return cast(AblationTools, module)


def check_comparison(
    report: Report,
    claims: list[Row],
    ids: set[int],
    tools: AblationTools,
) -> list[Row] | None:
    """Check results/comparison.csv against results_spec §5 and §7.5.

    Parameters
    ----------
    report : Report
        Receives every failure.
    claims : list[Row]
        Claims that passed the claim checks.
    ids : set[int]
        Article ids of the corpus.
    tools : AblationTools
        Database tools giving each article's series.

    Returns
    -------
    list[Row] | None
        The comparison rows, or None when the file cannot be used.
    """
    rows = read_csv(
        RESULTS / "comparison.csv", COMPARISON_COLUMNS, report,
        "results §5")
    if rows is None:
        return None
    by_id = {c["claim_id"]: c for c in claims}
    series: dict[int, dict[str, Series]] = {
        aid: {s["series_id"]: s for s in tools.list_series(aid)}
        for aid in ids
    }

    expected: set[tuple[str, str]] = set()
    for c in claims:
        if c["basis"] != "own_data":
            continue
        candidates = {
            (c["claim_id"], sid)
            for sid, s in series[int(c["article_id"])].items()
            if c["medium_class"] in ("unspecified", s["medium_class"])
        }
        expected |= candidates or {(c["claim_id"], "")}
    actual = Counter((r["claim_id"], r["series_id"]) for r in rows)
    for pair in sorted(expected - set(actual)):
        report.fail("results §5", f"missing comparison row {pair}")
    for pair, n in sorted(actual.items()):
        if pair not in expected:
            report.fail("results §5", f"unexpected comparison row {pair}")
        elif n > 1:
            report.fail(
                "results §5", f"comparison row {pair} appears {n} times")

    for row in rows:
        claim = by_id.get(row["claim_id"])
        if claim is None or (row["claim_id"], row["series_id"]) not in expected:
            continue
        check_comparison_row(report, row, claim, series)

    check_reference(report, claims, rows)
    report.ok(f"comparison: {len(rows)} row(s) checked")
    return rows


def check_comparison_row(
    report: Report,
    row: Row,
    claim: Row,
    series: dict[int, dict[str, Series]],
) -> None:
    """Check one expected comparison row's values (results_spec §5).

    Parameters
    ----------
    report : Report
        Receives every failure.
    row : Row
        The comparison row.
    claim : Row
        The claim the row refers to.
    series : dict[int, dict[str, Series]]
        Series of every article, by article id and series id.
    """
    where = f"comparison {row['claim_id']}/{row['series_id'] or '-'}"
    if row["direction"] != claim["direction"]:
        report.fail(
            "results §5", f"{where}: direction differs from the claim's")
    if not row["series_id"]:
        filled = ("shape_primary", "shape_lenient",
                  "agree_primary", "agree_lenient")
        if any(row[column] for column in filled):
            report.fail(
                "results §5",
                f"{where}: unmatched row must leave shapes and "
                f"agreement empty",
            )
        if not row["note"].strip():
            report.fail(
                "results §5", f"{where}: unmatched row needs a note")
        return
    s = series[int(claim["article_id"])][row["series_id"]]
    for model in MODELS:
        shape = shape_of(s, model)
        if row[f"shape_{model}"] != shape:
            report.fail(
                "results §5",
                f"{where}: shape_{model} {row[f'shape_{model}']!r}, "
                f"series has {shape!r}",
            )
        agree = parse_bool(row[f"agree_{model}"])
        if agree is None:
            report.fail(
                "results §5",
                f"{where}: agree_{model} {row[f'agree_{model}']!r} is "
                f"not true/false",
            )
        elif agree != (shape in AGREES[claim["direction"]]):
            report.fail(
                "results §5",
                f"{where}: agree_{model} does not follow the table",
            )


def check_reference(
    report: Report, claims: list[Row], rows: list[Row],
) -> None:
    """Check the reference article 80094 (results_spec §7.5).

    Parameters
    ----------
    report : Report
        Receives every failure.
    claims : list[Row]
        Claims that passed the claim checks.
    rows : list[Row]
        Comparison rows.
    """
    own = {
        (c["direction"], c["medium_class"]): c["claim_id"]
        for c in claims
        if c["article_id"] == "80094" and c["basis"] == "own_data"
    }
    for key, ref in REFERENCE.items():
        cid = own.get(key)
        if cid is None:
            report.fail(
                "results §7.5", f"80094: no own_data claim {key}")
            continue
        row = next(
            (r for r in rows
             if r["claim_id"] == cid and r["series_id"] == ref.series_id),
            None,
        )
        if row is None:
            report.fail(
                "results §7.5",
                f"80094: claim {cid} is not paired with {ref.series_id}",
            )
            continue
        actual = (
            row["shape_primary"], row["shape_lenient"],
            parse_bool(row["agree_primary"]),
            parse_bool(row["agree_lenient"]),
        )
        if actual != tuple(ref)[1:]:
            report.fail(
                "results §7.5",
                f"80094: {cid}/{ref.series_id} is {actual}, expected "
                f"{tuple(ref)[1:]}",
            )


def check_summary(
    report: Report,
    claims: list[Row],
    rows: list[Row],
    tools: AblationTools,
) -> None:
    """Recompute results/summary.json and compare (results_spec §6).

    Parameters
    ----------
    report : Report
        Receives every failure.
    claims : list[Row]
        Claims that passed the claim checks.
    rows : list[Row]
        Comparison rows.
    tools : AblationTools
        Database tools giving every gold series.
    """
    path = RESULTS / "summary.json"
    if not path.exists():
        report.fail("results §6", "results/summary.json does not exist")
        return
    try:
        stored = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        report.fail("results §6", f"summary.json does not parse: {error}")
        return

    counts = {b: {d: 0 for d in DIRECTIONS} for b in BASES}
    for c in claims:
        counts[c["basis"]][c["direction"]] += 1
    matched = [r for r in rows if r["series_id"]]
    agreement = {
        m: {
            "n": len(matched),
            "agree": sum(
                parse_bool(r[f"agree_{m}"]) is True for r in matched),
        }
        for m in MODELS
    }
    all_series = [
        s for a in tools.find_articles(material="Au")
        for s in tools.list_series(a["article_id"])
    ]
    shapes: dict[str, dict[str, object]] = {}
    for m in MODELS:
        shape_counts = {shape: 0 for shape in SHAPES}
        for s in all_series:
            shape_counts[shape_of(s, m)] += 1
        n_test = shape_counts["increasing"] + shape_counts["decreasing"]
        p_value = None
        if n_test:
            p_value = sign_test_p_value(shape_counts["increasing"], n_test)
        shapes[m] = {
            "counts": shape_counts, "n_test": n_test, "p_value": p_value,
        }
    expected = {
        "claims": {"by_basis_and_direction": counts},
        "agreement": agreement,
        "series": shapes,
    }
    for difference in compare_json(expected, stored, "summary"):
        report.fail("results §6", difference)
    report.ok("summary: recomputed and compared")


def sign_test_p_value(increasing: int, n_test: int) -> float:
    """Return the one-sided sign-test p-value (results_spec §6).

    Exactly P(X >= increasing) for X ~ Binomial(n_test, 0.5), the
    value of ``scipy.stats.binomtest(increasing, n_test, 0.5,
    alternative="greater").pvalue``, computed without scipy.

    Parameters
    ----------
    increasing : int
        Number of increasing series.
    n_test : int
        Number of increasing plus decreasing series; at least 1.

    Returns
    -------
    float
        The p-value.
    """
    tail = sum(math.comb(n_test, k) for k in range(increasing, n_test + 1))
    return tail / 2**n_test


def compare_json(expected: object, actual: object, where: str) -> list[str]:
    """List the differences between two JSON values.

    Floats are compared with a relative tolerance of 1e-9.

    Parameters
    ----------
    expected : object
        The recomputed value.
    actual : object
        The stored value.
    where : str
        Path of the value, for the messages.

    Returns
    -------
    list[str]
        One message per difference; empty when the values agree.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            got = (sorted(actual) if isinstance(actual, dict)
                   else type(actual).__name__)
            return [f"{where}: keys {got}, expected {sorted(expected)}"]
        return [
            difference
            for key in expected
            for difference in compare_json(
                expected[key], actual[key], f"{where}.{key}")
        ]
    is_number = (isinstance(actual, (int, float))
                 and not isinstance(actual, bool))
    if isinstance(expected, float) and is_number:
        if math.isclose(expected, cast(float, actual), rel_tol=1e-9):
            return []
        return [f"{where}: {actual}, expected {expected}"]
    if expected != actual or type(expected) is not type(actual):
        return [f"{where}: {actual!r}, expected {expected!r}"]
    return []


def main() -> int:
    """Run the check selected on the command line.

    Returns
    -------
    int
        Exit code: 0 when every rule holds, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description="Readiness check for the project specs.")
    parser.add_argument(
        "--article", type=int,
        help="check only this article's claims",
    )
    args = parser.parse_args()
    article = cast(int | None, args.article)

    report = Report()
    ids, roles = check_data(report, article)
    claims = check_claims(report, ids, roles, article)
    check_no_claims(report, ids, roles, claims)
    report_gold(claims, article)

    if article is None:
        tools = load_tools(report)
        if tools is not None:
            rows = check_comparison(report, claims, ids, tools)
            if rows is not None:
                check_summary(report, claims, rows, tools)

    verdict = "FAILED" if report.failures else "PASSED"
    print(f"\n{verdict}: {report.failures} failure(s)")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
