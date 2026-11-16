"""Malformed and incomplete scientific inputs cannot produce a successful build."""

from copy import deepcopy

import pytest
from conftest import write_csv

from src.comparison import build, prepare
from src.comparison.inputs import (
    AUDIT,
    AUDIT_COLUMNS,
    CLAIM_COLUMNS,
    FILES_COLUMNS,
    NEGATIVE_COLUMNS,
    STATUS_COLUMNS,
    PipelineError,
    json_object,
)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r.pop(), "missing pairs"),
        (lambda r: r.append(deepcopy(r[0])), "duplicate pair"),
        (lambda r: r[0].update(series_id="99-s1"), "unexpected"),
        (lambda r: r[0].update(claim_id="4-c1"), "unexpected"),
        (lambda r: r[0].update(decision="pending"), "invalid decision"),
        (lambda r: r[0].update(decision="no_candidates"), "no_candidates"),
        (
            lambda r: r[-1].update(decision="include", assessment="direct"),
            "no_candidates",
        ),
        (lambda r: r[0].update(reason=" "), "reason and caveats"),
        (lambda r: r[0].update(caveats=""), "reason and caveats"),
        (lambda r: r[0].update(assessment=""), "assessment required"),
        (lambda r: r[1].update(caveats="NONE"), "substantive caveats"),
        (lambda r: r[2].update(caveats="none"), "substantive caveats"),
        (lambda r: r[-2].update(assessment="direct"), "assessment must be empty"),
        (lambda r: r[-1].update(assessment="qualified"), "assessment must be empty"),
    ],
)
def test_invalid_audit_does_not_replace_outputs(prepared, mutation, message):
    f = prepared
    build(f.root, stage="draft", tools=f.tools)
    comparison = (f.root / "results/comparison.csv").read_bytes()
    summary = (f.root / "results/summary.json").read_bytes()
    mutation(f.audit)
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, f.audit)
    with pytest.raises(PipelineError, match=message):
        build(f.root, stage="draft", tools=f.tools)
    assert (f.root / "results/comparison.csv").read_bytes() == comparison
    assert (f.root / "results/summary.json").read_bytes() == summary


@pytest.mark.parametrize(
    "table, mutation, message",
    [
        ("claims", lambda r: r.append(deepcopy(r[0])), "duplicate claim ID"),
        ("claims", lambda r: r[0].update(article_id="999"), "unknown article/PDF"),
        ("claims", lambda r: r[0].update(page="0"), "invalid page"),
        ("claims", lambda r: r[0].update(direction="bigger"), "invalid direction"),
        ("claims", lambda r: r[0].update(basis="uncertain"), "invalid basis"),
        ("claims", lambda r: r[0].update(variable="temperature"), "invalid variable"),
        (
            "claims",
            lambda r: r[0].update(medium_class="vacuum"),
            "invalid medium_class",
        ),
        ("claims", lambda r: r[0].update(quote=""), "empty quote"),
        ("ledger", lambda r: r.pop(), "missing reading status"),
        ("ledger", lambda r: r.append(deepcopy(r[0])), "duplicate reading status"),
        ("ledger", lambda r: r[0].update(status="done"), "invalid reading status"),
        ("ledger", lambda r: r[0].update(reason=""), "invalid reading status"),
        ("ledger", lambda r: r[0].update(files_sha256="f" * 64), "stale PDF"),
        ("ledger", lambda r: r[5].update(status="pending"), "unassessed article"),
        ("ledger", lambda r: r[4].update(status="complete"), "requires claims XOR"),
        ("files", lambda r: r.append(deepcopy(r[0])), "duplicate PDF"),
        ("files", lambda r: r[0].update(file="../outside.pdf"), "invalid PDF filename"),
        ("files", lambda r: r[0].update(role="attachment"), "invalid PDF role"),
        ("negatives", lambda r: r.append(deepcopy(r[0])), "duplicate/invalid no-claim"),
    ],
)
def test_invalid_extraction_input_prevents_preparation(f, table, mutation, message):
    columns, path = {
        "claims": (CLAIM_COLUMNS, "results/claims.csv"),
        "files": (FILES_COLUMNS, "data/files.csv"),
        "ledger": (STATUS_COLUMNS, "results/extraction_status.csv"),
        "negatives": (NEGATIVE_COLUMNS, "results/no_claims.csv"),
    }[table]
    records = getattr(f, table)
    mutation(records)
    write_csv(f.root, path, columns, records)
    with pytest.raises(PipelineError, match=message):
        prepare(f.root, tools=f.tools)
    assert not (f.root / "results/matching_candidates.json").exists()


@pytest.mark.parametrize(
    "raw",
    [
        b"claim_id,wrong\n",
        b"claim_id,series_id,decision,assessment,reason,caveats",  # missing newline
        b"claim_id,series_id,decision,assessment,reason,caveats\n1-c1,1-s1\n",
        b'claim_id,series_id,decision,assessment,reason,caveats\n"unterminated\n',
        b"\xff\n",
    ],
)
def test_malformed_csv_fails_closed(prepared, raw):
    (prepared.root / AUDIT).write_bytes(raw)
    with pytest.raises(PipelineError, match="matching_audit.csv"):
        build(prepared.root, stage="draft", tools=prepared.tools)
    assert not (prepared.root / "results/comparison.csv").exists()


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e309}', b"[]", b"\xff"],
)
def test_strict_json(raw):
    with pytest.raises(PipelineError):
        json_object(raw, "synthetic.json")


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r.append(deepcopy(r[0])), "duplicate series"),
        (lambda r: r[0].update(series_id="not-a-series"), "invalid series ID"),
        (lambda r: r[0].update(shape_primary="unknown"), "invalid series shape"),
        (lambda r: r[0].update(medium_class="unspecified"), "invalid series medium"),
    ],
)
def test_invalid_tool_response_fails_closed(f, mutation, message):
    mutation(f.series)
    with pytest.raises(PipelineError, match=message):
        prepare(f.root, tools=f.tools)


def test_tool_error_is_not_a_no_candidates_result(f):
    class BrokenTools:
        def list_series(self, aid):
            raise RuntimeError("synthetic numerical failure")

    with pytest.raises(PipelineError, match="series tools failed"):
        prepare(f.root, tools=BrokenTools())


def test_no_complete_articles_has_null_prevalence_and_zero_comparisons(f):
    from test_comparison import check_generated

    for row in f.ledger:
        row["status"] = "unreadable"
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    write_csv(f.root, "results/no_claims.csv", NEGATIVE_COLUMNS, [])
    prepare(f.root, tools=f.tools)
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, [])
    summary = build(f.root, stage="draft", tools=f.tools)
    assert summary["articles"]["prevalence"] == {
        "numerator": 0,
        "denominator": 0,
        "fraction": None,
    }
    assert summary["comparison"]["n_own_data_claims"] == 0
    assert summary["comparison"]["claim_outcomes"] == {}
    check_generated(f, "draft")


def test_no_series_retains_every_own_claim_and_null_secondary_test(f):
    f.series.clear()
    prepare(f.root, tools=f.tools)
    audit = [
        {
            "claim_id": cid,
            "series_id": "",
            "decision": "no_candidates",
            "assessment": "",
            "reason": "No series from synthetic tools",
            "caveats": "none",
        }
        for cid in ("1-c1", "1-c3", "3-c1", "7-c1")
    ]
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, audit)
    summary = build(f.root, stage="draft", tools=f.tools)
    assert summary["comparison"]["n_without_candidates"] == 4
    assert summary["comparison"]["n_own_data_claims"] == 4
    assert summary["series"]["primary"]["p_value"] is None
    from test_comparison import check_generated

    check_generated(f, "draft")
