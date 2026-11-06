"""Snapshot adapter tests, including the fixed 80094 reference case.

No database, network, claim extraction or HW2 resampling is invoked.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools import ablation_db
from tools.ablation_db import SnapshotTools
from tools.tests.series_fixtures import experiment, snapshot

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def snapshot_path(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot()), encoding="utf-8")
    return path


def test_api_output_and_model_selection(snapshot_path):
    tools = SnapshotTools(snapshot_path)
    assert tools.find_articles() == [{
        "article_id": 77, "doi": None, "title": "Synthetic example",
        "year": 2020, "n_experiments": 3,
    }]
    assert tools.find_articles("gold") == tools.find_articles("Au")
    rows = tools.list_series(77)
    assert len(rows) == 1
    primary = tools.get_series(rows[0]["series_id"])
    lenient = tools.get_series(rows[0]["series_id"], model="lenient")
    assert primary["series"] == lenient["series"]
    assert primary["points"][0]["size_err"] == 1.
    assert lenient["points"][0]["size_err"] == 2.
    assert tools.list_exclusions(77) == []
    json.dumps(primary, allow_nan=False)


def test_responses_are_not_mutable_cache_references(snapshot_path):
    tools = SnapshotTools(snapshot_path)
    original = tools.get_series("77-s1")
    changed = tools.get_series("77-s1")
    changed["series"]["shape_primary"] = "wrong"
    changed["points"][0]["assumptions"].append("wrong")
    changed["points"][0]["size"] = -10.
    tools.list_series(77)[0]["notes"] = "wrong"
    assert tools.get_series("77-s1") == original


def test_fixed_instance_and_fresh_module_calls(snapshot_path, monkeypatch):
    monkeypatch.setattr(ablation_db, "SNAPSHOT_PATH", snapshot_path)
    fixed = SnapshotTools()
    assert ablation_db.find_articles()[0]["title"] == "Synthetic example"
    assert len(ablation_db.list_series(77)) == 1
    assert ablation_db.get_series("77-s1")["points"][0]["size"] == 10.
    assert ablation_db.list_exclusions(77) == []
    updated = snapshot()
    updated["articles"][0]["title"] = "Updated fixture"
    updated["articles"][0]["experiments"][0]["colloids"][0]["measured_properties"][0]["value"] = 12.
    snapshot_path.write_text(json.dumps(updated), encoding="utf-8")
    assert fixed.find_articles()[0]["title"] == "Synthetic example"
    assert fixed.get_series("77-s1")["points"][0]["size"] == 10.
    assert ablation_db.find_articles()[0]["title"] == "Updated fixture"
    assert ablation_db.get_series("77-s1")["points"][0]["size"] == 12.


def test_unknown_article_and_series(snapshot_path):
    tools = SnapshotTools(snapshot_path)
    assert tools.list_series(999) == [] and tools.list_exclusions(999) == []
    with pytest.raises(KeyError):
        tools.get_series("77-s99")
    with pytest.raises(KeyError):
        tools.get_series("999-s1")


@pytest.mark.parametrize("series_id", ["", "77", "77-s0", "077-s1", "77-s-1", None, 1])
def test_malformed_series_id(snapshot_path, series_id):
    with pytest.raises(ValueError):
        SnapshotTools(snapshot_path).get_series(series_id)


@pytest.mark.parametrize("article_id", [0, -1, "77", True, None])
def test_malformed_article_id(snapshot_path, article_id):
    with pytest.raises(ValueError):
        SnapshotTools(snapshot_path).list_series(article_id)


def test_bad_material_and_model(snapshot_path):
    tools = SnapshotTools(snapshot_path)
    with pytest.raises(ValueError, match="Au/gold"):
        tools.find_articles("Ag")
    with pytest.raises(ValueError, match="error model"):
        tools.get_series("77-s1", "typo")


@pytest.mark.parametrize("header, value", [
    ("format", 2), ("format", True), ("interval_unit", "s"),
    ("filter", {"sole_target_material": "silver", "completed_only": True}),
])
def test_incompatible_snapshot_header(snapshot_path, header, value):
    s = snapshot()
    s[header] = value
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError):
        SnapshotTools(snapshot_path)


@pytest.mark.parametrize("quantity, wrong_unit", [
    ("fluence", "mJ/cm²"), ("pulse_energy", "J"),
    ("geometric_diameter", "μm"), ("spot_diameter", "nm"),
])
def test_units_are_checked_not_silently_converted(snapshot_path, quantity, wrong_unit):
    s = snapshot()
    s["units"][quantity] = wrong_unit
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError, match="unit"):
        SnapshotTools(snapshot_path)


def test_parameter_unit_route_is_checked(snapshot_path):
    s = snapshot()
    s["parameter_quantities"]["pulse_energy"] = "average_power"
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError, match="parameter"):
        SnapshotTools(snapshot_path)


@pytest.mark.parametrize("damage", ["duplicate_article", "duplicate_experiment", "wrong_article"])
def test_broken_identifiers(snapshot_path, damage):
    s = snapshot()
    if damage == "duplicate_article":
        s["articles"].append(deepcopy(s["articles"][0]))
    elif damage == "duplicate_experiment":
        s["articles"][0]["experiments"].append(deepcopy(s["articles"][0]["experiments"][0]))
    else:
        s["articles"][0]["experiments"][0]["article_id"] = 99
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError):
        SnapshotTools(snapshot_path)


def test_missing_or_corrupt_file_never_falls_back(snapshot_path):
    with pytest.raises(FileNotFoundError):
        SnapshotTools(snapshot_path.parent / "missing.json")
    snapshot_path.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        SnapshotTools(snapshot_path)
    snapshot_path.write_text('{"format": NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        SnapshotTools(snapshot_path)


def test_missing_shared_reference_fails_explicitly(snapshot_path):
    s = snapshot()
    del s["shared"]["targets"]["1"]
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError, match="missing shared reference"):
        SnapshotTools(snapshot_path).list_series(77)


def test_exclusions_are_available_and_independent(snapshot_path):
    s = snapshot()
    s["articles"][0]["experiments"] = s["articles"][0]["experiments"][:1]
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    tools = SnapshotTools(snapshot_path)
    assert tools.list_series(77) == []
    exclusions = tools.list_exclusions(77)
    assert exclusions[0]["reason"] == "short_series"
    exclusions[0]["experiment_ids"].clear()
    assert tools.list_exclusions(77)[0]["experiment_ids"] == [100]
    assert tools.find_articles()[0]["n_experiments"] == 1


def test_real_snapshot_reference_80094():
    tools = SnapshotTools(ROOT / "data" / "ablation_snapshot.json")
    rows = tools.list_series(80094)
    assert [(r["series_id"], r["n_points"], r["x_quantity"], r["shape_primary"], r["shape_lenient"])
            for r in rows] == [
        ("80094-s1", 6, "pulse_energy", "increasing", "increasing"),
        ("80094-s2", 6, "pulse_energy", "peak", "flat"),
    ]
    assert [r["medium_class"] for r in rows] == ["water", "colloid"]
    assert tools.list_exclusions(80094) == []


def test_real_snapshot_all_articles_are_json_ready_and_ids_deterministic():
    tools = SnapshotTools(ROOT / "data" / "ablation_snapshot.json")
    assert len(tools.find_articles()) == 19
    assert sum(a["n_experiments"] for a in tools.find_articles()) == 118
    original = deepcopy(tools._snapshot)
    for article in tools.find_articles():
        aid = article["article_id"]
        rows = tools.list_series(aid)
        assert [row["series_id"] for row in rows] == [f"{aid}-s{i}" for i in range(1, len(rows) + 1)]
        for row in rows:
            for model in ("primary", "lenient"):
                data = tools.get_series(row["series_id"], model)
                assert len(data["points"]) == row["n_points"]
                assert len({p["x"] for p in data["points"]}) == row["n_points"]
                json.dumps(data, allow_nan=False)
        json.dumps(tools.list_exclusions(aid), allow_nan=False)
    assert tools._snapshot == original
    # Reordering JSON collections cannot renumber series or change values.
    reordered = deepcopy(original)
    reordered["articles"].reverse()
    for article in reordered["articles"]:
        article["experiments"].reverse()
        for exp in article["experiments"]:
            exp["colloids"].reverse()
            for colloid in exp["colloids"]:
                for key in ("measured_properties", "size_distributions", "measurement_curves"):
                    colloid.get(key, []).reverse()
    from tools.series import build_series

    for article in tools.find_articles():
        aid = article["article_id"]
        rebuilt = build_series(reordered, aid)
        assert [s.row for s in rebuilt.series] == tools.list_series(aid)
        assert rebuilt.exclusions == tools.list_exclusions(aid)


def test_field_unit_route_is_checked(snapshot_path):
    s = snapshot()
    s["field_units"]["experiments"]["pulse_fluence"] = {"quantity": "pulse_energy"}
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError, match="unit route"):
        SnapshotTools(snapshot_path)


def test_overlapping_series_api_is_independent_and_stable_on_tied_ids(snapshot_path):
    s = snapshot([experiment(100, wavelength=None), experiment(200, wavelength=532.),
                  experiment(300, wavelength=1064.)])
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    tools = SnapshotTools(snapshot_path)
    rows = tools.list_series(77)
    assert len(rows) == 2
    assert {r["wavelength_nm"] for r in rows} == {532., 1064.}
    expected = [tools.get_series(r["series_id"]) for r in rows]
    assert all(d["points"][0]["experiment_id"] == 100 for d in expected)
    assert all(d["series"]["notes"] == "overlapping_series" for d in expected)
    changed = tools.get_series(rows[0]["series_id"])
    changed["points"][0]["size"] = -1.
    changed["points"][0]["assumptions"].append("wrong")
    assert [tools.get_series(r["series_id"]) for r in rows] == expected
    s["articles"][0]["experiments"].reverse()
    snapshot_path.write_text(json.dumps(s), encoding="utf-8")
    fresh = SnapshotTools(snapshot_path)
    assert fresh.list_series(77) == rows
    assert [fresh.get_series(r["series_id"]) for r in rows] == expected
