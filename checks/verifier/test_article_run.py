"""Article dry preflight must neither build nor report other articles' series."""

import json

import pytest

from checks.verifier import run
from checks.verifier.fixtures import experiment, snapshot
from tools.ablation_db import SnapshotTools


def test_article_dry_uses_only_selected_raw_data_and_series(tmp_path, monkeypatch):
    raw = snapshot(
        [
            experiment(1),
            experiment(2),
            experiment(3, article_id=88),
            experiment(4, article_id=88),
        ]
    )
    raw["articles"][1]["experiments"][0]["pulse_energy"] = "broken unrelated data"
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(run, "SNAPSHOT_SHA256", run.digest(path))
    original = SnapshotTools._article
    calls = []

    def selected_only(self, article):
        assert article == 77
        calls.append(article)
        return original(self, article)

    monkeypatch.setattr(SnapshotTools, "_article", selected_only)
    report = run.evaluate(path, article=77)
    assert report["status"] == "pass", report["violations"]
    assert report["scope"] == {"article_id": 77}
    assert [row["series_id"] for row in report["series"]] == ["77-s1"]
    assert calls and set(calls) == {77}
    assert run.evaluate(path, article=99)["status"] == "fail"


def test_article_dry_keeps_frozen_hash_guards(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot()), encoding="utf-8")
    assert "snapshot_hash_mismatch" in {
        v["code"] for v in run.evaluate(path, article=77)["violations"]
    }


def test_full_dry_still_requires_the_pinned_reference(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot()), encoding="utf-8")
    monkeypatch.setattr(run, "SNAPSHOT_SHA256", run.digest(path))
    # The synthetic corpus intentionally has no 80094; do not drop its guard.
    assert "reference_mismatch" in {v["code"] for v in run.evaluate(path)["violations"]}


def test_article_dry_cli_has_separate_output(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ROOT", tmp_path)
    calls = []

    def evaluate(*, article):
        calls.append(article)
        return {"status": "pass", "scope": {"article_id": article}, "violations": []}

    monkeypatch.setattr(run, "evaluate", evaluate)
    monkeypatch.setattr(run, "provenance", dict)
    assert run.main(["dry", "--article", "77"]) == 0
    assert calls == [77]
    assert (tmp_path / "results/verifier/articles/77/dry.json").exists()
    assert not (tmp_path / "results/verifier/dry.json").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["smoke", "--article", "77"],
        ["full", "--article", "77"],
        ["dry", "--article", "0"],
    ],
)
def test_article_dry_cli_rejects_resampling_or_bad_ids(args):
    with pytest.raises(SystemExit) as error:
        run.main(args)
    assert error.value.code == 2
