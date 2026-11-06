"""Wildcard conditions and overlapping series: deterministic implementation tests."""

import itertools
import json
from copy import deepcopy

import pytest

from tools.series import (
    build_series,
    condition_key,
    conditions_compatible,
    maximal_condition_groups,
)
from tools.tests.series_fixtures import experiment, scalar, snapshot


@pytest.mark.parametrize("field, stated", [
    ("wavelength", 532.), ("pulse_duration", 100.), ("repetition_rate", 1000.),
    ("beam_diameter", 2.), ("polarization", "linear"), ("spatial_mode", "TEM00"),
    ("free_surf_entrance", False), ("pumping_flow_rate", 10.),
    ("pumping_duration", 1.), ("pumping_during_processing", False),
])
def test_missing_and_null_scalar_conditions_match_stated_values(field, stated):
    es = [experiment(100), experiment(200), experiment(300)]
    es[0][field] = stated
    es[1][field] = None
    es[2].pop(field, None)
    result = build_series(snapshot(es), 77)
    assert len(result.series) == 1 and result.series[0].row["n_points"] == 3
    assert not result.exclusions
    if field == "wavelength":
        assert result.series[0].row["wavelength_nm"] == stated


def test_unknown_condition_overlaps_without_bridging_conflicting_values():
    es = [experiment(100, wavelength=532.), experiment(200, wavelength=None),
          experiment(300, wavelength=1064.)]
    s = snapshot(es)
    original = deepcopy(s)
    result = build_series(s, 77)
    assert s == original and not result.exclusions
    assert [{p["experiment_id"] for p in built.points()} for built in result.series] == [
        {100, 200}, {200, 300},
    ]
    assert [b.row["wavelength_nm"] for b in result.series] == [532., 1064.]
    assert all("overlapping_series" in b.row["notes"] for b in result.series)
    assert [b.row["series_id"] for b in result.series] == ["77-s1", "77-s2"]
    # A later stated value is still exposed even when the first member lacks it.
    assert result.series[1].row["pulse_duration_fs"] == 100.
    s["articles"][0]["experiments"].reverse()
    again = build_series(s, 77)
    assert [b.row for b in again.series] == [b.row for b in result.series]
    assert [b.points() for b in again.series] == [b.points() for b in result.series]


def test_nested_shared_conditions_use_wildcards_without_mutating_shared_rows():
    s = snapshot([experiment(100), experiment(200)])
    medium = deepcopy(s["shared"]["liquid_media"]["10"])
    medium["ph"] = 7.
    s["shared"]["liquid_media"]["20"] = medium
    s["articles"][0]["experiments"][1]["synthesis_medium"] = 20
    s["articles"][0]["experiments"][0]["ablation"]["liquid_layer_thickness"] = 2.
    original = deepcopy(s)
    assert len(build_series(s, 77).series) == 1
    assert s == original
    s["shared"]["liquid_media"]["10"]["ph"] = 5.
    assert not build_series(s, 77).series


def test_group_metadata_uses_stated_values_not_the_first_missing_member():
    s = snapshot([experiment(100, pulse_duration=None, wavelength=None),
                  experiment(200, pulse_duration=200., wavelength=532.)])
    row = build_series(s, 77).series[0].row
    assert (row["pulse_duration_fs"], row["pulse_duration_class"], row["wavelength_nm"]) == (200., "fs", 532.)
    es = s["articles"][0]["experiments"]
    assert es[0]["pulse_duration"] is None and es[0]["wavelength"] is None
    s["shared"]["base_liquids"]["22"] = deepcopy(s["shared"]["base_liquids"]["12"])
    del s["shared"]["base_liquids"]["12"]["formula"]
    s["shared"]["liquids"]["21"] = {"base_liquid": 22}
    s["shared"]["liquid_media"]["20"] = {"constituents": [{"liquid": 21, "fraction": 1.}]}
    es[1]["synthesis_medium"] = 20
    assert build_series(s, 77).series[0].row["medium_class"] == "water"


def test_all_unknown_conditions_form_one_group_not_arbitrary_subsets():
    es = [experiment(100), experiment(200), experiment(300)]
    for e in es:
        e.pop("wavelength")
        e.pop("pulse_duration")
    built = build_series(snapshot(es), 77).series
    assert len(built) == 1 and built[0].row["n_points"] == 3
    assert built[0].row["wavelength_nm"] is None
    assert built[0].row["pulse_duration_fs"] is None
    assert "overlapping_series" not in built[0].row["notes"]


def test_maximal_groups_against_exhaustive_small_independent_oracle():
    # Nine profiles, 512 subsets. The oracle only compares stated scalar
    # values; it does not call the production compatibility/clique functions.
    profiles = [{"a": a, "b": b} for a, b in itertools.product((None, 1, 2), repeat=2)]
    keys = [json.dumps(p, sort_keys=True) for p in profiles]

    def valid(indices):
        return all(
            profiles[i][k] is None or profiles[j][k] is None
            or profiles[i][k] == profiles[j][k]
            for i, j in itertools.combinations(indices, 2) for k in ("a", "b")
        )

    expected = set()
    for n in range(1, len(keys) + 1):
        for subset in itertools.combinations(range(len(keys)), n):
            if valid(subset) and not any(
                valid((*subset, other)) for other in range(len(keys)) if other not in subset
            ):
                expected.add(tuple(sorted(keys[i] for i in subset)))
    assert set(maximal_condition_groups(keys)) == expected
    assert maximal_condition_groups(keys[::-1] + keys) == sorted(expected)
    assert maximal_condition_groups([]) == []


@pytest.mark.parametrize("field", ["feedstock", "additives", "beam_path", "postprocessing_steps", "constituents"])
def test_absent_or_empty_collections_mean_none_not_unknown(field):
    assert conditions_compatible({}, {field: []})
    assert conditions_compatible({field: None}, {field: []})
    assert not conditions_compatible({}, {field: [{"value": 1}]})
    assert not conditions_compatible({field: [{"value": 1}]}, {})


def test_unordered_lists_need_a_perfect_matching_not_greedy_or_sorted_zip():
    left = {"additives": [{}, {"material": "NaCl", "concentration": None}]}
    right = {"additives": [{"material": "NaCl", "concentration": 2.},
                           {"material": "citrate", "concentration": 1.}]}
    assert conditions_compatible(left, right)
    assert conditions_compatible(right, left)
    assert conditions_compatible(left, {"additives": right["additives"][::-1]})
    assert not conditions_compatible({"additives": [{"material": "NaCl", "concentration": 3.}, {}]}, right)
    assert not conditions_compatible(left, {"additives": right["additives"][:1]})


def test_ordered_lists_and_stated_false_or_zero_remain_significant():
    a = {"beam_path": [{"path_order": 1, "optic": "lens"}, {"path_order": 2, "optic": "aperture"}]}
    b = {"beam_path": [{"path_order": 1, "optic": "aperture"}, {"path_order": 2, "optic": "lens"}]}
    assert not conditions_compatible(a, b)
    assert conditions_compatible({"stirring": False, "ph": 0.}, {})
    assert not conditions_compatible({"stirring": False}, {"stirring": True})
    assert not conditions_compatible({"ph": 0.}, {"ph": 7.})


@pytest.mark.parametrize("fluence", [False, True])
@pytest.mark.parametrize("spots", [(10., 20.), (None, 20.), (None, None)])
def test_spot_diameter_never_restricts_either_x_choice(fluence, spots):
    es = [experiment(100, spot_diameter=spots[0]), experiment(200, spot_diameter=spots[1])]
    if fluence:
        es[0]["pulse_fluence"], es[1]["pulse_fluence"] = 1., 2.
    built = build_series(snapshot(es), 77)
    assert len(built.series) == 1 and not built.exclusions
    assert built.series[0].row["x_quantity"] == ("fluence" if fluence else "pulse_energy")
    assert built.series[0].x == ((1., 2.) if fluence else (100., 200.))


@pytest.mark.parametrize("field", ["technique", "weighting_quantity", "component"])
def test_missing_measurement_identity_is_not_a_condition_wildcard(field):
    es = [experiment(100), experiment(200)]
    es[0]["colloids"][0]["measured_properties"][0][field] = None
    es[1]["colloids"][0]["measured_properties"][0][field] = "stated"
    assert not build_series(snapshot(es), 77).series


def test_missing_x_and_storage_duration_are_not_condition_wildcards():
    es = [experiment(100, pulse_energy=None), experiment(200)]
    assert any(e["reason"] == "mixed_x" for e in build_series(snapshot(es), 77).exclusions)
    es[0]["pulse_energy"] = 100.
    es[1]["colloids"][0]["storage_duration"] = 0.
    assert any(e["reason"] == "no_common_storage" for e in build_series(snapshot(es), 77).exclusions)


def test_selection_deduplicates_identical_series_and_uses_selected_metadata():
    es = [experiment(100, wavelength=None), experiment(200, wavelength=None),
          experiment(300, wavelength=532.), experiment(400, wavelength=1064.)]
    for e in es[2:]:
        e["colloids"][0]["measured_properties"].append(scalar(11.))
    result = build_series(snapshot(es), 77)
    assert len(result.series) == 1
    built = result.series[0]
    assert [p["experiment_id"] for p in built.points()] == [100, 200]
    assert built.row["wavelength_nm"] is None
    assert "overlapping_series" not in built.row["notes"]
    assert {e["experiment_ids"][0] for e in result.exclusions if e["reason"] == "ambiguous_measurement"} == {300, 400}


def test_compatible_keys_are_not_equal_keys():
    s = snapshot([experiment(100, wavelength=532.), experiment(200, wavelength=None)])
    a, b = s["articles"][0]["experiments"]
    ka, kb = condition_key(a, s["shared"], 10), condition_key(b, s["shared"], 10)
    assert ka != kb
    assert conditions_compatible(json.loads(ka), json.loads(kb))
