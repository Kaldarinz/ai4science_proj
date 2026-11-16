"""Fail-closed workflow, publication and synthetic final-approval tests."""

import fcntl
import json
import os
from copy import deepcopy

import pytest
from conftest import write_csv, write_json
from test_comparison import check_generated

from src.comparison import build, prepare
from src.comparison.__main__ import main
from src.comparison.inputs import (
    AUDIT,
    AUDIT_COLUMNS,
    COMPARISON,
    STATUS_COLUMNS,
    SUMMARY,
    WORKSPACE,
    PipelineError,
)
from src.comparison.outputs import publish


def outputs(f):
    return {
        path: (f.root / path).read_bytes() if (f.root / path).exists() else None
        for path in (COMPARISON, SUMMARY)
    }


def final_fixture(f):
    f.ledger[3]["status"] = "unreadable"
    write_csv(f.root, "results/extraction_status.csv", STATUS_COLUMNS, f.ledger)
    (f.root / AUDIT).unlink(missing_ok=True)
    prepare(f.root, tools=f.tools)
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, f.audit)
    return build(f.root, stage="draft", tools=f.tools)


def approve(f, summary):
    write_json(
        f.root,
        "checks/matching_review.json",
        {
            "decision": "accepted",
            "reviewer": "Synthetic test curator",
            "date": "2026-11-16",
            "inputs": summary["inputs"],
        },
    )


def test_draft_review_final_roundtrip(prepared):
    f = prepared
    draft = final_fixture(f)
    approve(f, draft)
    path = f.root / "checks/matching_review.json"
    before = path.read_bytes()
    comparison = (f.root / COMPARISON).read_bytes()
    result = build(f.root, stage="final", tools=f.tools)
    assert result == {**draft, "stage": "final"}
    assert (f.root / COMPARISON).read_bytes() == comparison
    assert path.read_bytes() == before
    check_generated(f, "final")
    first = outputs(f)
    build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == first


def test_pending_prevents_final_without_touching_outputs(prepared):
    f = prepared
    draft = build(f.root, stage="draft", tools=f.tools)
    approve(f, draft)
    before = outputs(f)
    with pytest.raises(PipelineError, match="pending"):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r.update(decision="rejected"), "acceptance"),
        (lambda r: r.update(reviewer=" "), "reviewer"),
        (lambda r: r.update(reviewer=1), "reviewer"),
        (lambda r: r.update(date="2026-1-1"), "date"),
        (lambda r: r.update(date=3), "date"),
        (lambda r: r.update(date="2026-02-30"), "date"),
        (lambda r: r.update(extra=True), "keys"),
        (lambda r: r["inputs"].update({"results/claims.csv": "0" * 64}), "stale"),
        (lambda r: r.update(inputs=[]), "stale"),
    ],
)
def test_invalid_approval_preserves_draft(prepared, mutation, message):
    f = prepared
    draft = final_fixture(f)
    review = {
        "decision": "accepted",
        "reviewer": "Synthetic curator",
        "date": "2026-11-16",
        "inputs": deepcopy(draft["inputs"]),
    }
    mutation(review)
    write_json(f.root, "checks/matching_review.json", review)
    before = outputs(f)
    with pytest.raises(PipelineError, match=message):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before


def test_missing_approval_is_not_created(prepared):
    f = prepared
    final_fixture(f)
    before = outputs(f)
    with pytest.raises(PipelineError, match="matching_review"):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before
    assert not (f.root / "checks/matching_review.json").exists()


def test_changed_audit_requires_new_draft_and_new_approval(prepared):
    f = prepared
    draft = final_fixture(f)
    approve(f, draft)
    f.audit[0]["reason"] = "New synthetic evidence"
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, f.audit)
    before = outputs(f)
    with pytest.raises(PipelineError, match="comparison from a generated draft"):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before
    build(f.root, stage="draft", tools=f.tools)
    with pytest.raises(PipelineError, match="stale"):
        build(f.root, stage="final", tools=f.tools)


@pytest.mark.parametrize("target", [COMPARISON, SUMMARY])
def test_final_requires_existing_unchanged_draft(prepared, target):
    f = prepared
    draft = final_fixture(f)
    approve(f, draft)
    (f.root / target).unlink()
    before = outputs(f)
    with pytest.raises(PipelineError):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before


def test_final_rejects_tampered_draft_summary(prepared):
    f = prepared
    draft = final_fixture(f)
    approve(f, draft)
    draft["articles"]["n_complete"] = 999
    write_json(f.root, SUMMARY, draft)
    before = outputs(f)
    with pytest.raises(PipelineError, match="draft inputs or results changed"):
        build(f.root, stage="final", tools=f.tools)
    assert outputs(f) == before


@pytest.mark.parametrize("change", ["claim", "snapshot", "files", "code", "workspace"])
def test_changed_preparation_inputs_fail_closed(prepared, change):
    f = prepared
    build(f.root, stage="draft", tools=f.tools)
    if change == "workspace":
        value = json.loads((f.root / WORKSPACE).read_text())
        value["candidates"].pop()
        write_json(f.root, WORKSPACE, value)
    else:
        path = {
            "claim": "results/claims.csv",
            "snapshot": "data/ablation_snapshot.json",
            "files": "data/files.csv",
            "code": "tools/series.py",
        }[change]
        with (f.root / path).open("a") as stream:
            stream.write("\n")
    before = outputs(f)
    with pytest.raises(PipelineError, match="stale or edited"):
        build(f.root, stage="draft", tools=f.tools)
    assert outputs(f) == before
    if change != "workspace":
        audit_before = (f.root / AUDIT).read_bytes()
        with pytest.raises(PipelineError, match="archive the old audit"):
            prepare(f.root, tools=f.tools)
        assert (f.root / AUDIT).read_bytes() == audit_before


def test_input_changed_during_tool_call_aborts(f):
    class ChangingTools:
        def list_series(self, aid):
            if aid == 7:
                with (f.root / "results/claims.csv").open("a") as stream:
                    stream.write("\n")
            return f.tools.list_series(aid)

    with pytest.raises(PipelineError, match="input changed during operation"):
        prepare(f.root, tools=ChangingTools())
    assert not (f.root / WORKSPACE).exists()


def test_existing_audit_without_preparation_is_not_adopted(f):
    write_csv(f.root, AUDIT, AUDIT_COLUMNS, f.audit)
    with pytest.raises(PipelineError, match="archive the old audit"):
        prepare(f.root, tools=f.tools)
    assert not (f.root / WORKSPACE).exists()


def test_failed_publish_restores_originals_and_modes(tmp_path, monkeypatch):
    directory = tmp_path / "results"
    directory.mkdir()
    first, last = directory / "comparison.csv", directory / "summary.json"
    first.write_bytes(b"old comparison")
    last.write_bytes(b"old summary")
    first.chmod(0o640)
    replace = os.replace
    failed = False

    def fail_once(source, target):
        nonlocal failed
        if target == last and not failed:
            failed = True
            raise OSError("simulated rename failure")
        replace(source, target)

    monkeypatch.setattr(os, "replace", fail_once)
    with pytest.raises(OSError, match="simulated"):
        publish(tmp_path, {COMPARISON: b"new comparison", SUMMARY: b"new summary"})
    assert first.read_bytes() == b"old comparison"
    assert last.read_bytes() == b"old summary"
    assert first.stat().st_mode & 0o777 == 0o640
    assert not list(directory.glob("*.tmp"))


def test_publish_refuses_output_symlink(tmp_path):
    directory = tmp_path / "results"
    directory.mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.write_bytes(b"untouched")
    (directory / "comparison.csv").symlink_to(outside)
    try:
        with pytest.raises(PipelineError, match="symlink"):
            publish(tmp_path, {COMPARISON: b"new"})
        assert outside.read_bytes() == b"untouched"
    finally:
        outside.unlink()


def test_new_outputs_are_group_readable(tmp_path):
    publish(tmp_path, {COMPARISON: b"new\n"})
    assert (tmp_path / COMPARISON).stat().st_mode & 0o777 == 0o660


def test_concurrent_operation_fails_instead_of_overwriting(f):
    lock = f.root / "results/.comparison.lock"
    with lock.open("w") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(PipelineError, match="another comparison operation"):
            prepare(f.root, tools=f.tools)
    assert not (f.root / WORKSPACE).exists()


def test_cli_help_and_missing_inputs(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_status:
        main(["--help"], root=tmp_path)
    assert exit_status.value.code == 0
    assert "prepare" in capsys.readouterr().out
    assert main(["prepare"], root=tmp_path) == 1
    assert "data/corpus.csv" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exit_status:
        main(["build", "--stage", "unknown"], root=tmp_path)
    assert exit_status.value.code == 2
