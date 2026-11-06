"""Check the checker on synthetic corruptions, plus the pinned reference case."""

from copy import deepcopy

import pytest

from checks.verifier.contract import (
    CONDITION_FIELDS,
    SCHEMA_PATH,
    SNAPSHOT_PATH,
    SNAPSHOT_SHA256,
    check_series,
    check_snapshot,
    compatible,
    load_json,
)
from checks.verifier.fixtures import experiment, snapshot
from checks.verifier.run import digest, evaluate, main
from tools.ablation_db import SnapshotTools
from tools.series import build_series, classify_shape


def payload(raw):
    """One public-format response for the default synthetic series."""
    built = build_series(raw, 77).series[0]
    return {"series": built.row, "points": built.points()}


def codes(errors):
    return {e.code for e in errors}


def test_snapshot_contract_and_reference():
    assert digest(SNAPSHOT_PATH) == SNAPSHOT_SHA256
    raw = load_json(SNAPSHOT_PATH)
    assert not check_snapshot(raw)
    db = SnapshotTools()
    references = [(r["series_id"], r["n_points"], r["x_quantity"], r["shape_primary"], r["shape_lenient"])
                  for r in db.list_series(80094)]
    assert references == [("80094-s1", 6, "pulse_energy", "increasing", "increasing"),
                          ("80094-s2", 6, "pulse_energy", "peak", "flat")]
    for a in db.find_articles():
        for r in db.list_series(a["article_id"]):
            for model in ("primary", "lenient"):
                assert not check_series(raw, db.get_series(r["series_id"], model), model=model)


def test_synthetic_is_schema_valid_and_condition_list_covers_export():
    raw = snapshot()
    assert not check_snapshot(raw)
    assert not check_series(raw, payload(raw))
    exported = set(load_json(SCHEMA_PATH)["$defs"]["experiments"]["properties"])
    assert set(CONDITION_FIELDS) == exported - {"id", "article_id", "colloids", "pulse_fluence", "pulse_energy", "average_power", "spot_diameter"}


@pytest.mark.parametrize("corruption,expected", [
    ("header", "header_mismatch"), ("unit", "unit_mismatch"), ("route", "unit_mismatch"),
    ("duplicate", "duplicate_experiment"), ("article", "wrong_article"), ("target", "non_gold_target"),
    ("energy", "out_of_range"), ("size", "out_of_range"), ("sd", "out_of_range"),
    ("bins", "bad_bins"), ("counts", "bad_bins"), ("n", "out_of_range"),
    ("curve", "bad_curve"), ("reference", "broken_reference"), ("schema", "schema_mismatch"),
])
def test_raw_corruptions_are_named(corruption, expected):
    raw = snapshot()
    e = raw["articles"][0]["experiments"][0]
    c = e["colloids"][0]
    h = {"sizes": [[1, 2], [2, 3]], "size_counts": [1, 2], "technique": "tem",
         "x_quantity": "geometric_diameter", "y_quantity": "particle_count"}
    if corruption == "header":
        raw["options"]["omit_nulls"] = False
    elif corruption == "unit":
        raw["units"]["pulse_energy"] = "mJ"
    elif corruption == "route":
        raw["field_units"]["experiments"]["pulse_energy"] = {"quantity": "fluence"}
    elif corruption == "duplicate":
        raw["articles"][0]["experiments"].append(deepcopy(e))
    elif corruption == "article":
        e["article_id"] = 999
    elif corruption == "target":
        raw["shared"]["base_materials"]["4"]["formula"] = "Ag"
    elif corruption == "energy":
        e["pulse_energy"] = 1e6 + 1
    elif corruption == "size":
        c["measured_properties"][0]["value"] = 0
    elif corruption == "sd":
        c["measured_properties"].append({"quantity": "geometric_diameter", "statistic": "standard_deviation", "value": -1})
    elif corruption in ("bins", "counts", "n"):
        c["size_distributions"] = [h]
        if corruption == "bins":
            h["sizes"][1][0] = 1.5
        elif corruption == "counts":
            h["size_counts"] = [0, 0]
        else:
            h["particles_counted"] = 0
    elif corruption == "curve":
        c["measurement_curves"] = [{"technique": "dls", "x_quantity": "hydrodynamic_diameter",
                                     "y_quantity": "scattering_intensity", "x": [1, 1], "y": [1, 2]}]
    elif corruption == "reference":
        del raw["shared"]["materials"]["3"]
    else:
        del e["laser"]
    assert expected in codes(check_snapshot(raw))


@pytest.mark.parametrize("source", ["scalar", "histogram", "curve"])
@pytest.mark.parametrize("tail", [0, 1])
def test_sizes_and_distribution_support_have_no_upper_bound(source, tail):
    raw = snapshot()
    for e in raw["articles"][0]["experiments"]:
        c = e["colloids"][0]
        if source == "scalar":
            c["measured_properties"][0]["value"] = 12000 + e["id"]
        else:
            del c["measured_properties"]
            labels = {"technique": "tem", "x_quantity": "geometric_diameter", "y_quantity": "particle_count"}
            if source == "histogram":
                c["size_distributions"] = [{**labels, "sizes": [[1, 2], [10000, 12000]], "size_counts": [1, tail]}]
            else:
                c["measurement_curves"] = [{**labels, "x": [1, 2, 3, 10000, 12000], "y": [1, 1, 0, tail, tail]}]
    assert not check_snapshot(raw)
    built = build_series(raw, 77).series
    assert len(built) == 1
    for model in ("primary", "lenient"):
        data = {"series": built[0].row, "points": built[0].points(model)}
        assert not check_series(raw, data, model=model)
        if source == "scalar" or tail:
            assert all(p["size"] > 1000 for p in data["points"])
        else:
            assert all(p["size"] < 3 for p in data["points"])


@pytest.mark.parametrize("size", [0, -1, float("inf"), float("nan")])
def test_invalid_scalar_sizes_still_fail(size):
    raw = snapshot()
    raw["articles"][0]["experiments"][0]["colloids"][0]["measured_properties"][0]["value"] = size
    assert "out_of_range" in codes(check_snapshot(raw))


@pytest.mark.parametrize("corruption,expected", [
    ("duplicate", "duplicate_point"), ("short", "short_series"), ("article", "key_mismatch"),
    ("x", "mixed_x"), ("quantity", "key_mismatch"), ("size", "out_of_range"),
    ("n", "value_mismatch"), ("error", "value_mismatch"), ("storage", "key_mismatch"),
])
def test_public_response_corruptions_are_detected(corruption, expected):
    raw = snapshot()
    data = payload(raw)
    if corruption == "duplicate":
        data["points"][1] = deepcopy(data["points"][0])
    elif corruption == "short":
        data["points"].pop()
    elif corruption == "article":
        data["series"]["article_id"] = 78
    elif corruption == "x":
        data["points"][0]["x"] += 1
    elif corruption == "quantity":
        data["series"]["size_quantity"] = "hydrodynamic_diameter"
    elif corruption == "size":
        data["points"][0]["size"] = -1
    elif corruption == "n":
        data["points"][0]["particles_counted"] = 100
    elif corruption == "error":
        data["points"][0]["size_err"] *= 2
    else:
        data["series"]["storage_duration_h"] = 0
    assert expected in codes(check_series(raw, data))


@pytest.mark.parametrize("field,value", [("wavelength", 1064), ("repetition_rate", 2000),
                                         ("free_surf_entrance", False), ("pulse_duration", 200)])
def test_independent_profile_rejects_conflict_even_with_unchanged_serialized_key(field, value):
    raw = snapshot()
    experiments = raw["articles"][0]["experiments"]
    experiments[0][field] = 100 if field not in ("wavelength", "free_surf_entrance") else experiments[0][field]
    experiments[1][field] = experiments[0][field]
    data = payload(raw)
    experiments[1][field] = value
    assert "key_mismatch" in codes(check_series(raw, data))


def test_shared_contents_and_ignored_spot():
    raw = snapshot()
    data = payload(raw)
    raw["shared"]["liquid_media"]["8"] = deepcopy(raw["shared"]["liquid_media"]["7"])
    e = raw["articles"][0]["experiments"][1]
    e["synthesis_medium"] = e["colloids"][0]["medium"] = 8
    e["spot_diameter"] = 250
    assert not check_series(raw, data)
    raw["shared"]["liquid_media"]["8"]["ph"] = 7
    raw["shared"]["liquid_media"]["7"]["ph"] = 9
    assert "key_mismatch" in codes(check_series(raw, data))


@pytest.mark.parametrize("field", ["feedstock", "additives", "constituents", "beam_path", "postprocessing_steps"])
def test_collection_absence_and_details(field):
    assert compatible({}, {field: []})
    assert not compatible({}, {field: [{"value": 1}]})
    assert compatible({field: [{}]}, {field: [{"value": 1}]})
    assert not compatible({field: [{"value": 2}]}, {field: [{"value": 1}]})


def test_unordered_matching_and_nontransitivity():
    assert compatible({"additives": [{}, {"material": 1}]}, {"additives": [{"material": 1}, {"material": 2}]})
    assert not compatible({"beam_path": [{"x": 1}, {"x": 2}]}, {"beam_path": [{"x": 2}, {"x": 1}]})
    assert compatible({"wavelength": 532}, {}) and compatible({}, {"wavelength": 1064})
    assert not compatible({"wavelength": 532}, {"wavelength": 1064})


def test_actual_overlapping_series_are_not_a_partition():
    raw = snapshot([experiment(1, wavelength=532), experiment(2, wavelength=None), experiment(3, wavelength=1064)])
    built = build_series(raw, 77).series
    assert {frozenset(m.experiment_id for m in s.measurements) for s in built} == {frozenset({1, 2}), frozenset({2, 3})}
    for s in built:
        assert not check_series(raw, {"series": s.row, "points": s.points()})


@pytest.mark.parametrize("sizes,expected", [([1, 1, 1], "flat"), ([1, 2, 3], "increasing"),
                                           ([3, 2, 1], "decreasing"), ([1, 3, 1], "peak"),
                                           ([3, 1, 3], "valley"), ([1, 3, 1, 3], "irregular")])
def test_shape_names_have_nonvacuous_examples(sizes, expected):
    assert classify_shape(list(range(len(sizes))), sizes, [0] * len(sizes)) == expected


def test_strict_threshold_and_anchor_moves_with_repeated_sign():
    assert classify_shape([1, 2], [0, 5], [3, 4]) == "flat"
    assert classify_shape([1, 2, 3, 4], [0, 2, 4, 2], [1, 1, 1, 1]) == "peak"


def test_dry_hash_guard_and_cli_rejects_unknown_step(tmp_path):
    changed = tmp_path / "changed.json"
    changed.write_text('{"format": 1}', encoding="utf-8")
    assert "snapshot_hash_mismatch" in {v["code"] for v in evaluate(changed)["violations"]}
    with pytest.raises(SystemExit) as error:
        main(["unknown"])
    assert error.value.code == 2
    with pytest.raises(SystemExit):
        main(["dry", "--output", str(tmp_path / "outside.json")])
