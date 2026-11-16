"""Article isolation, resumability and aggregation, using synthetic data only."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from conftest import write_csv, write_json
from test_comparison import Report, check_generated

from checks import analysis, check
from src.comparison import aggregate, build, prepare
from src.comparison.__main__ import main
from src.comparison.inputs import (
    AUDIT,
    AUDIT_COLUMNS,
    CLAIM_COLUMNS,
    COMPARISON,
    CORPUS_COLUMNS,
    FILES_COLUMNS,
    NEGATIVE_COLUMNS,
    STATUS_COLUMNS,
    SUMMARY,
    WORKSPACE,
    PipelineError,
    artifact_path,
    load_inputs,
)
from tools import ablation_db
from tools.ablation_db import SnapshotTools
from tools.snapshot_scope import article_snapshot
from tools.tests.series_fixtures import experiment, snapshot


@pytest.fixture
def scoped(f):
    project = Path(__file__).resolve().parents[1]
    # Schema and implementation text only; no real scientific data or outputs.
    for relative in ("data/ablation_snapshot.schema.json", "tools/snapshot_scope.py"):
        (f.root / relative).write_bytes((project / relative).read_bytes())
    raw = snapshot()
    raw["articles"] = [
        {
            "id": aid,
            "title": f"Synthetic {aid}",
            "year": 2026,
            "experiments": [
                experiment(aid * 100 + i, 10.0 * i, article_id=aid) for i in range(1, 4)
            ],
        }
        for aid in range(1, 8)
    ]
    write_json(f.root, "data/ablation_snapshot.json", raw)
    f.snapshot = raw
    return f


def checkpoint(f, aid, *, real=False):
    tools = None if real else f.tools
    prepare(f.root, article=aid, tools=tools)
    decisions = [row for row in f.audit if row["claim_id"].startswith(f"{aid}-")]
    write_csv(f.root, artifact_path(AUDIT, aid), AUDIT_COLUMNS, decisions)
    return build(f.root, article=aid, stage="draft", tools=tools)


def all_checkpoints(f):
    for row in f.ledger:
        if row["status"] == "complete":
            checkpoint(f, int(row["article_id"]))


def check_article(f, aid=1, *, real=False):
    report = Report()
    claims = [c for c in f.claims if c["article_id"] == str(aid)]
    statuses = analysis.check_coverage(f.root, report, {aid}, claims, article=aid)
    analysis.check_analysis(
        f.root,
        report,
        {aid},
        claims,
        statuses,
        ablation_db if real else f.tools,
        "draft",
        article=aid,
    )
    return report


def test_article_finishes_with_no_other_reading_attestations(scoped):
    f = scoped
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, [f.ledger[0]])
    summary = checkpoint(f, 1)
    assert summary["scope"] == {"article_id": 1, "binding": "article-v1"}
    assert summary["articles"]["n_corpus"] == summary["articles"]["n_complete"] == 1
    assert summary["articles"]["prevalence"] == {
        "numerator": 1,
        "denominator": 1,
        "fraction": 1.0,
    }
    assert summary["comparison"]["n_included_pairs"] == 5
    assert summary["comparison"]["claim_outcomes"]["1-c1"]["primary"] == "mixed"
    assert summary["series"]["primary"]["counts"] == {
        "increasing": 1,
        "decreasing": 1,
        "flat": 1,
        "peak": 0,
        "valley": 0,
        "irregular": 0,
    }
    for relative in (AUDIT, COMPARISON, SUMMARY, WORKSPACE):
        assert not (f.root / relative).exists()
        assert (f.root / artifact_path(relative, 1)).exists()
    assert not (f.root / "checks/matching_review.json").exists()
    report = check_article(f)
    assert report.failures == 0, report.messages


def test_unrelated_changes_do_not_invalidate_or_rewrite_article(scoped):
    f = scoped
    checkpoint(f, 1)
    paths = [
        f.root / artifact_path(relative, 1)
        for relative in (AUDIT, COMPARISON, SUMMARY, WORKSPACE)
    ]
    before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
    f.claims[-1]["quote"] = "Another article was re-read."
    write_csv(f.root, "results/claims.csv", CLAIM_COLUMNS, list(reversed(f.claims)))
    f.ledger[-1]["status"] = "pending"
    write_csv(
        f.root,
        "results/extraction_status.csv",
        STATUS_COLUMNS,
        list(reversed(f.ledger)),
    )
    f.files[-2]["sha256"] = "c" * 64
    write_csv(f.root, "data/files.csv", FILES_COLUMNS, list(reversed(f.files)))
    f.corpus[-1]["title"] = "Unrelated corrected metadata"
    write_csv(f.root, "data/corpus.csv", CORPUS_COLUMNS, list(reversed(f.corpus)))
    f.snapshot["articles"][-1]["experiments"][0]["pulse_energy"] = 987.0
    f.snapshot["shared"]["base_liquids"]["99"] = {"formula": "CH4"}
    f.snapshot["exported_at"] = "2026-11-17T00:00:00Z"
    write_json(f.root, "data/ablation_snapshot.json", f.snapshot)
    prepare(f.root, article=1, tools=f.tools)
    build(f.root, article=1, stage="draft", tools=f.tools)
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths] == before
    report = check_article(f)
    assert report.failures == 0, report.messages


@pytest.mark.parametrize(
    "changed",
    ["claim", "corpus", "reading", "inventory", "numbers", "shared", "code", "spec"],
)
def test_relevant_changes_stale_only_that_preparation(scoped, changed):
    f = scoped
    checkpoint(f, 1)
    if changed == "claim":
        f.claims[0]["quote"] += " updated evidence"
        write_csv(f.root, "results/claims.csv", CLAIM_COLUMNS, f.claims)
    elif changed == "corpus":
        f.corpus[0]["title"] += " corrected"
        write_csv(f.root, "data/corpus.csv", CORPUS_COLUMNS, f.corpus)
    elif changed == "reading":
        f.ledger[0]["reason"] += " corrected reading"
        write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    elif changed == "inventory":
        f.files[0]["sha256"] = "d" * 64
        f.ledger[0]["files_sha256"] = analysis.files_digest(f.files, 1)
        write_csv(f.root, "data/files.csv", FILES_COLUMNS, f.files)
        write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    elif changed == "numbers":
        f.snapshot["articles"][0]["experiments"][0]["colloids"][0][
            "measured_properties"
        ][0]["value"] = 12.0
        write_json(f.root, "data/ablation_snapshot.json", f.snapshot)
    elif changed == "shared":
        f.snapshot["shared"]["base_liquids"]["12"]["formula"] = "D2O"
        write_json(f.root, "data/ablation_snapshot.json", f.snapshot)
    else:
        path = f.root / (
            "tools/snapshot_scope.py" if changed == "code" else "checks/results_spec.md"
        )
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(PipelineError, match="stale"):
        build(f.root, article=1, stage="draft", tools=f.tools)
    with pytest.raises(PipelineError, match="archive the old audit"):
        prepare(f.root, article=1, tools=f.tools)
    report = check_article(f)
    assert report.failures, report.messages


def test_real_adapter_never_builds_other_articles(scoped, monkeypatch):
    f = scoped
    # A malformed unrelated article must not be validated or numerically built.
    f.snapshot["articles"][-1]["experiments"] = "unrelated broken data"
    write_json(f.root, "data/ablation_snapshot.json", f.snapshot)
    f.claims = [f.claims[0]]
    f.audit = [dict(f.audit[0])]
    write_csv(f.root, "results/claims.csv", CLAIM_COLUMNS, f.claims)
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, [f.ledger[0]])
    calls = []
    original = SnapshotTools._article

    def article_only(self, aid):
        assert aid == 1
        calls.append(aid)
        return original(self, aid)

    monkeypatch.setattr(SnapshotTools, "_article", article_only)
    assert main(["prepare", "--article", "1"], root=f.root) == 0
    write_csv(f.root, artifact_path(AUDIT, 1), AUDIT_COLUMNS, f.audit)
    assert main(["build", "--article", "1", "--stage", "draft"], root=f.root) == 0
    summary = json.loads((f.root / artifact_path(SUMMARY, 1)).read_text())
    assert summary["comparison"]["claim_outcomes"]["1-c1"]["primary"] == "all_agree"
    report = check_article(f, real=True)
    assert report.failures == 0, report.messages
    assert calls and set(calls) == {1}


@pytest.mark.parametrize("aid", [4, 5, 99, 0, -1])
def test_incomplete_or_unknown_article_cannot_be_compared(scoped, aid):
    with pytest.raises(PipelineError):
        prepare(scoped.root, article=aid, tools=scoped.tools)
    assert not (scoped.root / artifact_path(WORKSPACE, 1)).exists()


@pytest.mark.parametrize("aid", [2, 6, 7])
def test_no_own_claim_no_claim_and_no_candidate_articles_are_checkpoints(scoped, aid):
    summary = checkpoint(scoped, aid)
    assert summary["articles"]["n_complete"] == 1
    assert summary["comparison"]["n_included_pairs"] == 0
    assert summary["comparison"]["n_without_candidates"] == int(aid == 7)
    report = check_article(scoped, aid)
    assert report.failures == 0, report.messages


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "foreign"])
def test_article_audit_coverage_is_exhaustive(scoped, mutation):
    f = scoped
    checkpoint(f, 1)
    rows = [r for r in f.audit if r["claim_id"].startswith("1-")]
    if mutation == "missing":
        rows.pop()
    else:
        rows.append(rows[0] if mutation == "duplicate" else f.audit[-1])
    write_csv(f.root, artifact_path(AUDIT, 1), AUDIT_COLUMNS, rows)
    with pytest.raises(PipelineError):
        build(f.root, article=1, stage="draft", tools=f.tools)
    assert check_article(f).failures


def test_article_has_no_final_or_approval_shortcut(scoped, monkeypatch):
    f = scoped
    checkpoint(f, 1)
    write_json(f.root, "checks/matching_review.json", {"decision": "accepted"})
    review = (f.root / "checks/matching_review.json").read_bytes()
    with pytest.raises(PipelineError, match="corpus-wide"):
        build(f.root, article=1, stage="final", tools=f.tools)
    monkeypatch.setattr(
        check.sys, "argv", ["check.py", "--article", "1", "--analysis", "final"]
    )
    with pytest.raises(SystemExit) as error:
        check.main()
    assert error.value.code == 2
    assert (f.root / "checks/matching_review.json").read_bytes() == review


def test_article_check_cli_scopes_coverage_and_numerics(scoped, monkeypatch):
    f = scoped
    checkpoint(f, 1)
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, [f.ledger[0]])
    monkeypatch.setattr(
        check.sys, "argv", ["check.py", "--article", "1", "--analysis", "draft"]
    )
    monkeypatch.setattr(check, "ROOT", f.root)
    monkeypatch.setattr(check, "RESULTS", f.root / "results")
    monkeypatch.setattr(check, "check_data", lambda *args: ({1}, {}))
    monkeypatch.setattr(check, "check_vocabulary", lambda *args: None)
    monkeypatch.setattr(
        check,
        "check_claims",
        lambda *args: [c for c in f.claims if c["article_id"] == "1"],
    )
    monkeypatch.setattr(check, "check_no_claims", lambda *args: None)
    committed = []
    monkeypatch.setattr(
        check, "check_committed", lambda report, article=None: committed.append(article)
    )
    monkeypatch.setattr(check, "load_tools", lambda *args: f.tools)
    assert check.main() == 0
    assert committed == [1]


def test_readiness_ignores_semantically_broken_unrelated_records(scoped, monkeypatch):
    f = scoped
    for row in f.files:
        if row["article_id"] == "1":
            path = f.root / "data/articles/1" / row["file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic PDF placeholder")
            row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    f.ledger[0]["files_sha256"] = analysis.files_digest(f.files, 1)
    f.corpus[-1]["year"] = "unfinished metadata"
    f.files[-2]["role"] = "unfinished role"
    f.files[-2]["sha256"] = "unfinished inventory"
    f.negatives.append(
        {"article_id": "unfinished", "file": "", "page": "", "quote": "", "reason": ""}
    )
    write_csv(f.root, "data/corpus.csv", CORPUS_COLUMNS, f.corpus)
    write_csv(f.root, "data/files.csv", FILES_COLUMNS, f.files)
    write_csv(f.root, "results/no_claims.csv", NEGATIVE_COLUMNS, f.negatives)
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, [f.ledger[0]])
    checkpoint(f, 1)
    monkeypatch.setattr(
        check.sys, "argv", ["check.py", "--article", "1", "--analysis", "draft"]
    )
    monkeypatch.setattr(check, "ROOT", f.root)
    monkeypatch.setattr(check, "DATA", f.root / "data")
    monkeypatch.setattr(check, "RESULTS", f.root / "results")
    monkeypatch.setattr(check, "check_vocabulary", lambda *args: None)
    # Quote mechanics have their own tests; inventory/negative/ledger checks here are real.
    monkeypatch.setattr(
        check,
        "check_claims",
        lambda *args: [c for c in f.claims if c["article_id"] == "1"],
    )
    monkeypatch.setattr(check, "check_committed", lambda *args: None)
    monkeypatch.setattr(check, "load_tools", lambda *args: f.tools)
    assert check.main() == 0
    report = Report()
    check.check_data(report, None)
    assert report.failures  # The full-corpus validation was not weakened.


def test_real_adapter_aggregation_cli_and_independent_checker(scoped):
    f = scoped
    f.claims = [f.claims[0], {**f.claims[0], "claim_id": "2-c1", "article_id": "2"}]
    f.audit = [f.audit[0], {**f.audit[0], "claim_id": "2-c1", "series_id": "2-s1"}]
    for row in f.ledger:
        row["status"] = "complete" if row["article_id"] in {"1", "2"} else "pending"
    write_csv(f.root, "results/claims.csv", CLAIM_COLUMNS, f.claims)
    write_csv(f.root, "results/no_claims.csv", NEGATIVE_COLUMNS, [])
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    for aid in (1, 2):
        checkpoint(f, aid, real=True)
    assert main(["aggregate"], root=f.root) == 0
    summary = json.loads((f.root / SUMMARY).read_text())
    assert summary["articles"]["n_corpus"] == 7
    assert summary["articles"]["n_complete"] == 2
    assert summary["comparison"]["n_included_pairs"] == 2
    assert summary["comparison"]["by_model"]["primary"]["pairs"]["agree"] == 2
    report = Report()
    statuses = analysis.check_coverage(f.root, report, set(range(1, 8)), f.claims)
    analysis.check_analysis(
        f.root,
        report,
        set(range(1, 8)),
        f.claims,
        statuses,
        SnapshotTools(f.root / "data/ablation_snapshot.json"),
        "draft",
    )
    assert report.failures == 0, report.messages


def test_aggregation_has_hand_counted_corpus_totals_and_independent_check(scoped):
    f = scoped
    all_checkpoints(f)
    before = {
        p: p.read_bytes()
        for p in (f.root / "results/articles").rglob("*")
        if p.is_file()
    }
    summary = aggregate(f.root, tools=f.tools)
    assert "scope" not in summary
    assert summary["articles"]["n_corpus"] == 7
    assert summary["articles"]["n_complete"] == 5
    assert summary["articles"]["prevalence"] == {
        "numerator": 4,
        "denominator": 5,
        "fraction": 0.8,
    }
    assert summary["comparison"]["n_own_data_claims"] == 4
    assert summary["comparison"]["n_included_pairs"] == 5
    assert summary["comparison"]["n_excluded_pairs"] == 1
    assert summary["comparison"]["n_without_candidates"] == 1
    assert summary["comparison"]["n_all_candidates_excluded"] == 1
    assert {p: p.read_bytes() for p in before} == before
    assert not (f.root / "checks/matching_review.json").exists()
    check_generated(f, "draft")
    paths = [f.root / p for p in (AUDIT, COMPARISON, SUMMARY, WORKSPACE)]
    snapshots = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
    aggregate(f.root, tools=f.tools)
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths] == snapshots


@pytest.mark.parametrize(
    "broken",
    [
        "absent",
        "missing_comparison",
        "bad_summary",
        "bad_comparison",
        "stale_context",
        "missing_no_claim_checkpoint",
    ],
)
def test_aggregation_rejects_missing_stale_or_corrupt_checkpoints(scoped, broken):
    f = scoped
    all_checkpoints(f)
    aggregate(f.root, tools=f.tools)
    before = {
        p: (f.root / p).read_bytes() for p in (AUDIT, COMPARISON, SUMMARY, WORKSPACE)
    }
    if broken == "absent":
        (f.root / artifact_path(AUDIT, 3)).unlink()
    elif broken == "missing_no_claim_checkpoint":
        (f.root / artifact_path(SUMMARY, 6)).unlink()
    elif broken == "missing_comparison":
        (f.root / artifact_path(COMPARISON, 1)).unlink()
    elif broken == "bad_comparison":
        path = f.root / artifact_path(COMPARISON, 1)
        path.write_text(path.read_text().replace("increasing", "flat"))
    elif broken == "bad_summary":
        path = artifact_path(SUMMARY, 1)
        value = json.loads((f.root / path).read_text())
        value["articles"]["n_complete"] = 999
        write_json(f.root, path, value)
    else:
        path = artifact_path(WORKSPACE, 1)
        value = json.loads((f.root / path).read_text())
        value["inputs"]["results/claims.csv"] = "0" * 64
        write_json(f.root, path, value)
    with pytest.raises((PipelineError, OSError)):
        aggregate(f.root, tools=f.tools)
    assert {p: (f.root / p).read_bytes() for p in before} == before
    report = Report()
    statuses = {r["article_id"]: r["status"] for r in f.ledger}
    analysis.check_analysis(
        f.root, report, set(range(1, 8)), f.claims, statuses, f.tools, "draft"
    )
    assert report.failures, report.messages


def test_final_requires_current_aggregation_and_new_curator_approval(scoped):
    f = scoped
    f.ledger[3]["status"] = "unreadable"
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    all_checkpoints(f)
    summary = aggregate(f.root, tools=f.tools)
    with pytest.raises(PipelineError):
        build(f.root, stage="final", tools=f.tools)
    review = {
        "decision": "accepted",
        "reviewer": "Synthetic human curator",
        "date": "2026-11-17",
        "inputs": summary["inputs"],
    }
    write_json(f.root, "checks/matching_review.json", review)
    build(f.root, stage="final", tools=f.tools)
    check_generated(f, "final")
    approval = (f.root / "checks/matching_review.json").read_bytes()
    f.audit[0]["reason"] += "; corrected evidence citation"
    write_csv(
        f.root,
        artifact_path(AUDIT, 1),
        AUDIT_COLUMNS,
        [r for r in f.audit if r["claim_id"].startswith("1-")],
    )
    build(f.root, article=1, stage="draft", tools=f.tools)
    with pytest.raises(PipelineError, match="checkpoints changed"):
        build(f.root, stage="final", tools=f.tools)
    aggregate(f.root, tools=f.tools)
    assert (f.root / "checks/matching_review.json").read_bytes() == approval
    with pytest.raises(PipelineError, match="stale"):
        build(f.root, stage="final", tools=f.tools)
    review["inputs"] = json.loads((f.root / SUMMARY).read_text())["inputs"]
    write_json(f.root, "checks/matching_review.json", review)
    build(f.root, stage="final", tools=f.tools)
    check_generated(f, "final")


def test_article_publication_contains_paths_and_rolls_back(
    scoped, tmp_path, monkeypatch
):
    from src.comparison import outputs

    f = scoped
    checkpoint(f, 1)
    comparison = f.root / artifact_path(COMPARISON, 1)
    summary = f.root / artifact_path(SUMMARY, 1)
    before = comparison.read_bytes(), summary.read_bytes()
    f.audit[0]["caveats"] += "; amended caveat"
    write_csv(
        f.root,
        artifact_path(AUDIT, 1),
        AUDIT_COLUMNS,
        [r for r in f.audit if r["claim_id"].startswith("1-")],
    )
    replace = outputs.os.replace
    failed = False

    def fail_once(source, destination):
        nonlocal failed
        if Path(destination) == summary and not failed:
            failed = True
            raise OSError("synthetic publication failure")
        return replace(source, destination)

    monkeypatch.setattr(outputs.os, "replace", fail_once)
    with pytest.raises(OSError, match="publication failure"):
        build(f.root, article=1, stage="draft", tools=f.tools)
    assert (comparison.read_bytes(), summary.read_bytes()) == before
    assert not list(summary.parent.glob(".*.tmp"))
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (f.root / "results/articles/2").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PipelineError, match="outside project"):
        prepare(f.root, article=2, tools=f.tools)
    assert not list(outside.iterdir())


def test_article_output_cannot_alias_another_directory_inside_project(scoped):
    f = scoped
    target = f.root / "results/articles/2"
    target.mkdir(parents=True)
    (f.root / "results/articles/1").symlink_to(target, target_is_directory=True)
    with pytest.raises(PipelineError, match="symlink"):
        prepare(f.root, article=1, tools=f.tools)
    assert not list(target.iterdir())


def test_shared_and_document_dependency_closure(scoped):
    f = scoped
    schema = json.loads((f.root / "data/ablation_snapshot.schema.json").read_text())
    raw = deepcopy(f.snapshot)
    # A stock from article 2 depends on a medium unused directly by article 1.
    stock = raw["articles"][1]["experiments"][0]["colloids"][0]
    stock["medium"] = 20
    raw["shared"]["liquid_media"]["20"] = {
        "constituents": [{"liquid": 21, "fraction": 1.0}]
    }
    raw["shared"]["liquids"]["21"] = {"base_liquid": 22}
    raw["shared"]["base_liquids"]["22"] = {"formula": "D2O"}
    raw["shared"]["base_liquids"]["99"] = {"formula": "CH4"}
    raw["articles"][0]["experiments"][0]["feedstock"] = [
        {"colloid": stock["id"], "fraction": 0.1}
    ]
    projected = article_snapshot(raw, schema, 1)
    assert [a["id"] for a in projected["articles"]] == [1]
    assert [row["id"] for row in projected["referenced_colloids"]] == [stock["id"]]
    assert set(projected["shared"]["base_liquids"]) == {"12", "22"}
    assert projected["shared"]["base_liquids"]["22"] == {"formula": "D2O"}
    write_json(f.root, "data/ablation_snapshot.json", raw)
    before = load_inputs(f.root, article=1).hashes
    stock["measured_properties"][0]["value"] += 1.0
    write_json(f.root, "data/ablation_snapshot.json", raw)
    assert load_inputs(f.root, article=1).hashes != before
    del raw["shared"]["base_liquids"]["22"]
    with pytest.raises(KeyError):
        article_snapshot(raw, schema, 1)
