"""File ownership, containment and recoverable publication failures."""

import os

import pytest

from src.comparison import prepare
from src.comparison.inputs import AUDIT, COMPARISON, SUMMARY, PipelineError
from src.comparison.outputs import publish


def test_repeated_preparation_preserves_completed_audit(prepared):
    path = prepared.root / AUDIT
    before = path.read_bytes()
    prepare(prepared.root, tools=prepared.tools)
    assert path.read_bytes() == before


def test_new_lock_is_group_accessible_even_with_private_umask(f):
    previous = os.umask(0o077)
    try:
        prepare(f.root, tools=f.tools)
    finally:
        os.umask(previous)
    assert (f.root / "results/.comparison.lock").stat().st_mode & 0o777 == 0o660
    assert (f.root / "results/matching_candidates.json").stat().st_mode & 0o777 == 0o660


def test_input_symlink_cannot_escape_project(f, tmp_path_factory):
    external = tmp_path_factory.mktemp("outside-project") / "claims.csv"
    path = f.root / "results/claims.csv"
    external.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(external)
    with pytest.raises(PipelineError, match="input outside project"):
        prepare(f.root, tools=f.tools)
    assert not (f.root / "results/matching_candidates.json").exists()


def test_failed_publish_removes_newly_installed_files(tmp_path, monkeypatch):
    replace = os.replace

    def fail_last(source, target):
        if target.name == "summary.json":
            raise OSError("simulated publication failure")
        replace(source, target)

    monkeypatch.setattr(os, "replace", fail_last)
    with pytest.raises(OSError, match="simulated"):
        publish(tmp_path, {COMPARISON: b"comparison", SUMMARY: b"summary"})
    assert not (tmp_path / COMPARISON).exists()
    assert not (tmp_path / SUMMARY).exists()
    assert not list((tmp_path / "results").glob("*.tmp"))


def test_staging_finishes_before_any_output_is_replaced(tmp_path, monkeypatch):
    directory = tmp_path / "results"
    directory.mkdir()
    (tmp_path / COMPARISON).write_bytes(b"original comparison")
    (tmp_path / SUMMARY).write_bytes(b"original summary")
    calls = 0

    def fail_during_staging(fd):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("simulated staging failure")

    def forbidden(*args):
        pytest.fail("replacement started before all bytes were staged")

    monkeypatch.setattr(os, "fsync", fail_during_staging)
    monkeypatch.setattr(os, "replace", forbidden)
    with pytest.raises(OSError, match="staging failure"):
        publish(tmp_path, {COMPARISON: b"new comparison", SUMMARY: b"new summary"})
    assert (tmp_path / COMPARISON).read_bytes() == b"original comparison"
    assert (tmp_path / SUMMARY).read_bytes() == b"original summary"
    assert not list(directory.glob("*.tmp"))


def test_failed_rollback_keeps_original_recovery_copy(tmp_path, monkeypatch):
    directory = tmp_path / "results"
    directory.mkdir()
    (tmp_path / COMPARISON).write_bytes(b"original comparison")
    (tmp_path / SUMMARY).write_bytes(b"original summary")
    replace = os.replace
    calls = 0

    def failing_replace(source, target):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("filesystem unavailable")
        replace(source, target)

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(PipelineError, match="manual recovery needed") as error:
        publish(tmp_path, {COMPARISON: b"new comparison", SUMMARY: b"new summary"})
    backups = list(directory.glob("*.tmp"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"original comparison"
    assert str(backups[0]) in str(error.value)
    assert (tmp_path / SUMMARY).read_bytes() == b"original summary"
