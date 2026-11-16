"""Strict, read-only inputs for the supplied comparison pipeline.

Constants implement the published specification, not the independent checker.
PDF quote validation remains the responsibility of checks/check.py.
"""

import csv
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from tools.snapshot_scope import article_snapshot

MODELS = ("primary", "lenient")
BASES = ("own_data", "cited", "general")
DIRECTIONS = ("increase", "decrease", "no_effect", "non_monotonic", "affects")
SHAPES = ("flat", "increasing", "decreasing", "peak", "valley", "irregular")
ASSESSMENTS = ("direct", "qualified", "unassessable")
OUTCOMES = ("all_agree", "all_disagree", "mixed", "unassessable")
STATUSES = ("complete", "pending", "unreadable")
VARIABLES = ("fluence", "energy", "power", "intensity")
MEDIA = ("water", "aqueous", "organic", "colloid", "other")
CORPUS_COLUMNS = ("article_id", "doi", "title", "year")
FILES_COLUMNS = ("article_id", "file", "role", "sha256")
CLAIM_COLUMNS = (
    "claim_id",
    "article_id",
    "file",
    "page",
    "quote",
    "variable_written",
    "variable",
    "direction",
    "basis",
    "material",
    "medium_class",
    "conditions",
)
NEGATIVE_COLUMNS = ("article_id", "file", "page", "quote", "reason")
STATUS_COLUMNS = ("article_id", "status", "files_sha256", "reason")
AUDIT_COLUMNS = ("claim_id", "series_id", "decision", "assessment", "reason", "caveats")
COMPARISON_COLUMNS = (
    "claim_id",
    "series_id",
    "direction",
    "shape_primary",
    "shape_lenient",
    "agree_primary",
    "agree_lenient",
    "assessment",
    "note",
)
# The v1 contract's fingerprint inputs, excluding the two build-time tables.
BASE_INPUT_PATHS = (
    "data/corpus.csv",
    "data/files.csv",
    "data/ablation_snapshot.json",
    "data/ablation_snapshot.schema.json",
    "results/claims.csv",
    "results/no_claims.csv",
    "results/extraction_status.csv",
    "checks/claims_spec.md",
    "checks/results_spec.md",
    "ontology.yaml",
    "checks/analysis.py",
    "checks/check.py",
    "tools/ablation_db.py",
    "tools/series.py",
)
WORKSPACE = "results/matching_candidates.json"
AUDIT = "results/matching_audit.csv"
COMPARISON = "results/comparison.csv"
SUMMARY = "results/summary.json"
REVIEW = "checks/matching_review.json"
SCOPED_TABLES = {
    "data/corpus.csv": CORPUS_COLUMNS,
    "data/files.csv": FILES_COLUMNS,
    "results/claims.csv": CLAIM_COLUMNS,
    "results/no_claims.csv": NEGATIVE_COLUMNS,
    "results/extraction_status.csv": STATUS_COLUMNS,
}


def artifact_path(relative, article=None):
    if article is None:
        return relative
    require(type(article) is int and article > 0, "article must be a positive integer")
    return f"results/articles/{article}/{Path(relative).name}"


def scope_marker(article):
    return {"article_id": article, "binding": "article-v1"}


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class PipelineError(ValueError):
    """An actionable input or workflow error; never a success fallback."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_object(raw, name):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"non-finite JSON number {value}")

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            nonfinite(value)
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=nonfinite,
            parse_float=finite_float,
        )
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")  # noqa: TRY004 -- malformed document, not an API argument
        return value
    except (ValueError, UnicodeError) as error:
        raise PipelineError(f"{name}: {error}") from error


class Sources:
    """Capture source bytes and reject modifications during one operation."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.raw = {}

    def read(self, relative):
        if relative not in self.raw:
            try:
                path = self.root / relative
                require(
                    path.resolve().is_relative_to(self.root),
                    f"input outside project: {relative}",
                )
                self.raw[relative] = path.read_bytes()
            except OSError as error:
                raise PipelineError(f"{relative}: {error}") from error
        return self.raw[relative]

    def table(self, relative, columns):
        try:
            raw = self.read(relative)
            if not raw.endswith(b"\n"):
                raise ValueError("missing final newline")
            reader = csv.DictReader(
                io.StringIO(raw.decode("utf-8"), newline=""), strict=True
            )
            if reader.fieldnames != list(columns):
                raise ValueError(f"expected columns {','.join(columns)}")
            rows = list(reader)
            if any(None in row or None in row.values() for row in rows):
                raise ValueError("row field count differs from header")
            return rows
        except (ValueError, UnicodeError, csv.Error) as error:
            raise PipelineError(f"{relative}: {error}") from error

    def hashes(self, paths):
        return {path: digest(self.read(path)) for path in paths}

    def verify_unchanged(self):
        for path, raw in self.raw.items():
            try:
                source = self.root / path
                require(
                    source.resolve().is_relative_to(self.root),
                    f"input outside project: {path}",
                )
                unchanged = source.read_bytes() == raw
            except OSError as error:
                raise PipelineError(
                    f"input changed during operation: {path}"
                ) from error
            if not unchanged:
                raise PipelineError(f"input changed during operation: {path}")


@dataclass
class Inputs:
    sources: Sources
    ids: tuple
    claims: list
    statuses: dict
    hashes: dict
    article: int | None = None
    snapshot: dict | None = None

    def path(self, relative):
        return artifact_path(relative, self.article)

    @property
    def own_claims(self):
        return [
            row
            for row in self.claims
            if row["basis"] == "own_data"
            and self.statuses[row["article_id"]] == "complete"
        ]


def require(condition, message):
    if not condition:
        raise PipelineError(message)


def load_inputs(root, article=None):
    if article is not None:
        require(
            type(article) is int and article > 0, "article must be a positive integer"
        )
    sources = Sources(root)
    hashes = sources.hashes(BASE_INPUT_PATHS)

    def table(relative, columns):
        records = sources.table(relative, columns)
        return (
            records
            if article is None
            else [row for row in records if row["article_id"] == str(article)]
        )

    corpus = table("data/corpus.csv", CORPUS_COLUMNS)
    require(article is None or corpus, f"article {article} is not in corpus.csv")
    ids = [row["article_id"] for row in corpus]
    require(
        all(re.fullmatch(r"[1-9][0-9]*", aid) for aid in ids),
        "invalid corpus article ID",
    )
    require(len(ids) == len(set(ids)), "duplicate corpus article ID")
    scope = set(ids)
    files = table("data/files.csv", FILES_COLUMNS)
    inventory = {}
    for row in files:
        aid, name = row["article_id"], row["file"]
        key = (aid, name)
        require(
            aid in scope and key not in inventory,
            f"unknown/duplicate PDF inventory entry: {key}",
        )
        require(
            name and Path(name).name == name and name.endswith(".pdf"),
            f"invalid PDF filename: {name!r}",
        )
        require(row["role"] in ("main", "supplement"), f"invalid PDF role: {key}")
        require(
            re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), f"invalid PDF hash: {key}"
        )
        inventory[key] = row
    for aid in ids:
        require(
            any(row["article_id"] == aid and row["role"] == "main" for row in files),
            f"article {aid}: missing main PDF inventory",
        )

    def reference(row):
        aid = row["article_id"]
        require(
            (aid, row["file"]) in inventory,
            f"unknown article/PDF reference: {aid}/{row['file']}",
        )
        require(
            re.fullmatch(r"[1-9][0-9]*", row["page"]), f"article {aid}: invalid page"
        )
        require(row["quote"].strip(), f"article {aid}: empty quote")

    claims = table("results/claims.csv", CLAIM_COLUMNS)
    seen, distinct = set(), set()
    for row in claims:
        reference(row)
        cid, aid = row["claim_id"], row["article_id"]
        require(
            re.fullmatch(re.escape(aid) + r"-c[1-9][0-9]*", cid),
            f"invalid claim ID: {cid}",
        )
        require(cid not in seen, f"duplicate claim ID: {cid}")
        seen.add(cid)
        for key, allowed in (
            ("basis", BASES),
            ("direction", DIRECTIONS),
            ("variable", (*VARIABLES, "unspecified")),
            ("medium_class", (*MEDIA, "unspecified")),
        ):
            require(row[key] in allowed, f"{cid}: invalid {key}: {row[key]!r}")
        require(
            row["material"].strip() and row["variable_written"].strip(),
            f"{cid}: missing claim text fields",
        )
        key = tuple(
            row[k]
            for k in (
                "article_id",
                "material",
                "medium_class",
                "variable",
                "direction",
                "basis",
            )
        )
        require(key not in distinct, f"{cid}: duplicate distinct claim")
        distinct.add(key)

    negatives = table("results/no_claims.csv", NEGATIVE_COLUMNS)
    negative_ids = set()
    for row in negatives:
        reference(row)
        aid = row["article_id"]
        require(
            aid not in negative_ids and row["reason"].strip(),
            f"article {aid}: duplicate/invalid no-claim record",
        )
        negative_ids.add(aid)
    claim_ids = {row["article_id"] for row in claims}
    statuses = {}
    for row in table("results/extraction_status.csv", STATUS_COLUMNS):
        aid, status = row["article_id"], row["status"]
        require(
            aid in scope and aid not in statuses,
            f"unknown/duplicate reading status: {aid}",
        )
        require(
            status in STATUSES and row["reason"].strip(),
            f"article {aid}: invalid reading status/reason",
        )
        entries = sorted(
            [item["file"], item["role"], item["sha256"]]
            for item in files
            if item["article_id"] == aid
        )
        expected = digest(
            json.dumps(entries, ensure_ascii=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        require(
            row["files_sha256"] == expected,
            f"article {aid}: stale PDF inventory attestation",
        )
        if status == "complete":
            require(
                (aid in claim_ids) != (aid in negative_ids),
                f"article {aid}: complete requires claims XOR no-claim record",
            )
        else:
            require(
                aid not in negative_ids,
                f"article {aid}: unassessed article cannot have a no-claim record",
            )
        statuses[aid] = status
    require(set(statuses) == scope, "missing reading status for corpus articles")
    scoped_snapshot = None
    if article is not None:
        require(
            statuses[str(article)] == "complete",
            f"article {article}: extraction is not complete",
        )
        try:
            scoped_snapshot = article_snapshot(
                json_object(sources.read("data/ablation_snapshot.json"), "snapshot"),
                json_object(
                    sources.read("data/ablation_snapshot.schema.json"),
                    "snapshot schema",
                ),
                article,
            )
        except (ValueError, KeyError, TypeError) as error:
            raise PipelineError(
                f"article snapshot projection failed: {error}"
            ) from error
        for relative, columns in SCOPED_TABLES.items():
            records = sorted(table(relative, columns), key=canonical_bytes)
            hashes[relative] = digest(canonical_bytes(records))
        hashes["data/ablation_snapshot.json"] = digest(
            canonical_bytes(
                {
                    key: value
                    for key, value in scoped_snapshot.items()
                    if key != "exported_at"
                }
            )
        )
        hashes["tools/snapshot_scope.py"] = digest(
            sources.read("tools/snapshot_scope.py")
        )
    return Inputs(
        sources,
        tuple(sorted(map(int, ids))),
        claims,
        statuses,
        hashes,
        article,
        scoped_snapshot,
    )
