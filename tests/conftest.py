"""Synthetic comparison inputs only; never read real articles or decisions."""

import csv
import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from src.comparison.inputs import (
    AUDIT_COLUMNS,
    BASE_INPUT_PATHS,
    CLAIM_COLUMNS,
    CORPUS_COLUMNS,
    FILES_COLUMNS,
    NEGATIVE_COLUMNS,
    STATUS_COLUMNS,
)


def write_csv(root, relative, columns, rows):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class Tools:
    def __init__(self, rows):
        self.rows = rows

    def list_series(self, aid):
        return deepcopy([row for row in self.rows if row["article_id"] == aid])


def make_fixture(root):
    for relative in BASE_INPUT_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic input\n", encoding="utf-8")
    corpus = [
        {"article_id": str(aid), "doi": "", "title": f"Synthetic {aid}", "year": "2026"}
        for aid in range(1, 8)
    ]
    files = [
        {"article_id": str(aid), "file": "main.pdf", "role": "main", "sha256": "a" * 64}
        for aid in range(1, 8)
    ]
    files.append(
        {
            "article_id": "1",
            "file": "supplement.pdf",
            "role": "supplement",
            "sha256": "b" * 64,
        }
    )
    claims = []
    for aid, number, variable, direction, basis, medium in [
        (1, 1, "fluence", "increase", "own_data", "water"),
        (1, 2, "energy", "decrease", "cited", "water"),
        (1, 3, "unspecified", "affects", "own_data", "unspecified"),
        (2, 1, "power", "no_effect", "general", "water"),
        (3, 1, "fluence", "decrease", "own_data", "water"),
        (4, 1, "fluence", "increase", "own_data", "water"),
        (7, 1, "intensity", "non_monotonic", "own_data", "colloid"),
    ]:
        row = dict.fromkeys(CLAIM_COLUMNS, "synthetic text")
        row.update(
            claim_id=f"{aid}-c{number}",
            article_id=str(aid),
            file="main.pdf",
            page="1",
            variable=variable,
            direction=direction,
            basis=basis,
            medium_class=medium,
        )
        claims.append(row)
    negatives = [
        {
            "article_id": "6",
            "file": "main.pdf",
            "page": "1",
            "quote": "A synthetic non-claim.",
            "reason": "No dependence stated.",
        }
    ]
    ledger = []
    for aid in range(1, 8):
        triples = sorted(
            [row["file"], row["role"], row["sha256"]]
            for row in files
            if row["article_id"] == str(aid)
        )
        raw = json.dumps(triples, ensure_ascii=True, separators=(",", ":")).encode()
        ledger.append(
            {
                "article_id": str(aid),
                "status": "pending"
                if aid == 4
                else "unreadable"
                if aid == 5
                else "complete",
                "files_sha256": hashlib.sha256(raw).hexdigest(),
                "reason": "Synthetic reading record",
            }
        )
    series = []
    for aid, index, medium, primary, lenient in [
        (1, 1, "water", "increasing", "increasing"),
        (1, 2, "water", "decreasing", "increasing"),
        (1, 3, "organic", "flat", "flat"),
        (3, 1, "water", "increasing", "flat"),
        (4, 1, "organic", "flat", "flat"),
    ]:
        series.append(
            {
                "article_id": aid,
                "series_id": f"{aid}-s{index}",
                "n_points": 2,
                "medium_class": medium,
                "shape_primary": primary,
                "shape_lenient": lenient,
                "x_quantity": "pulse_energy",
                "size_quantity": "geometric_diameter",
                "size_statistic": "mean",
                "size_technique": "tem",
                "size_weighting": "particle_count",
                "size_component": None,
                "size_source": "scalar",
                "wavelength_nm": 532,
                "pulse_duration_fs": 100,
                "pulse_duration_class": "fs",
                "storage_duration_h": None,
                "spearman_rho": 0.5,
                "notes": "synthetic context",
            }
        )
    audit = []
    for cid, sid, decision, assessment in [
        ("1-c1", "1-s1", "include", "direct"),
        ("1-c1", "1-s2", "include", "qualified"),
        ("1-c3", "1-s1", "include", "unassessable"),
        ("1-c3", "1-s2", "include", "direct"),
        ("1-c3", "1-s3", "include", "direct"),
        ("3-c1", "3-s1", "exclude", ""),
        ("7-c1", "", "no_candidates", ""),
    ]:
        audit.append(
            {
                "claim_id": cid,
                "series_id": sid,
                "decision": decision,
                "assessment": assessment,
                "reason": "Synthetic evidence, main.pdf p. 1",
                "caveats": "Synthetic conditional comparison",
            }
        )
    write_csv(root, "data/corpus.csv", CORPUS_COLUMNS, corpus)
    write_csv(root, "data/files.csv", FILES_COLUMNS, files)
    write_csv(root, "results/claims.csv", CLAIM_COLUMNS, claims)
    write_csv(root, "results/no_claims.csv", NEGATIVE_COLUMNS, negatives)
    write_csv(root, "results/extraction_status.csv", STATUS_COLUMNS, ledger)
    return SimpleNamespace(
        root=root,
        corpus=corpus,
        files=files,
        claims=claims,
        negatives=negatives,
        ledger=ledger,
        series=series,
        audit=audit,
        tools=Tools(series),
    )


@pytest.fixture
def f(tmp_path):
    return make_fixture(tmp_path)


@pytest.fixture
def prepared(f):
    from src.comparison import prepare

    prepare(f.root, tools=f.tools)
    write_csv(f.root, "results/matching_audit.csv", AUDIT_COLUMNS, f.audit)
    return f
