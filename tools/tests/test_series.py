"""Unit tests of the scientific rules on small synthetic snapshots.

These are implementation tests, not the future HW2 Hypothesis verifier.
"""

import math
from copy import deepcopy

import numpy as np
import pytest
from scipy.special import ndtr

from tools.series import (
    build_series,
    classify_shape,
    condition_key,
    curve_statistics,
    fit_histogram_mode,
    histogram_statistics,
    normalize_statistic,
    size_error,
)
from tools.tests.series_fixtures import curve, experiment, histogram, scalar, snapshot


@pytest.mark.parametrize("statistic, expected", [
    (None, "mean"), ("z_average", "mean"), ("peak", "mode"),
    ("mode", "mode"), ("median", "median"),
])
def test_statistic_normalization(statistic, expected):
    assert normalize_statistic(statistic) == expected


@pytest.mark.parametrize("model, fraction", [("primary", .1), ("lenient", .2)])
def test_error_priority(model, fraction):
    assert size_error(20., model, reported_se=.3, sd=5., particles_counted=25) == (.3, "reported_se")
    assert size_error(20., model, sd=5., particles_counted=25) == (1., "sd_over_sqrt_n")
    assert size_error(20., model, sd=5.) == (20. * fraction, "fallback")
    assert size_error(20., model, sd=0., particles_counted=25) == (0., "sd_over_sqrt_n")
    for statistic in ("mode", "median"):
        assert size_error(20., model, sd=5., particles_counted=25, statistic=statistic) == (20. * fraction, "fallback")


@pytest.mark.parametrize("kwargs", [
    {"model": "other"}, {"sd": -1.}, {"reported_se": float("nan")},
    {"particles_counted": 0}, {"particles_counted": True},
    {"particles_counted": 2.5},
])
def test_bad_error_inputs(kwargs):
    with pytest.raises(ValueError):
        size_error(10., **kwargs)


def test_histogram_mean_and_scale():
    h = histogram()
    mean, sd, residual = histogram_statistics(h, "mean")
    assert mean == pytest.approx((2 * 2 + 3 * 5 + 1 * 10) / 6)
    assert sd > 0 and residual is None
    h["size_counts"] = [v * 123.4 for v in h["size_counts"]]
    assert histogram_statistics(h, "mean")[:2] == pytest.approx((mean, sd))
    assert histogram_statistics(h, "median")[0] == pytest.approx(3 + 4 / 3)


def lognormal_histogram(mu=None, sigma=.4):
    mu = math.log(10.) if mu is None else mu
    edges = np.geomspace(.5, 80., 35)
    probabilities = np.diff(ndtr((np.log(edges) - mu) / sigma))
    return histogram(sizes=np.column_stack((edges[:-1], edges[1:])).tolist(),
                     size_counts=(probabilities * 732).tolist())


def test_histogram_mode_is_a_real_lognormal_fit():
    mu, sigma = math.log(10.), .4
    h = lognormal_histogram(mu, sigma)
    mode, residual = fit_histogram_mode(h)
    assert mode == pytest.approx(math.exp(mu - sigma ** 2), rel=1e-6)
    assert residual < 1e-8
    centre_of_tallest_bar = np.mean(h["sizes"][np.argmax(h["size_counts"])])
    assert abs(mode - centre_of_tallest_bar) > .1
    h["size_counts"] = [v * 12 for v in h["size_counts"]]
    assert fit_histogram_mode(h)[0] == pytest.approx(mode, rel=1e-8)
    assert histogram_statistics(h, "mode")[0] == pytest.approx(mode)


@pytest.mark.parametrize("changes", [
    {"size_counts": [0., 0., 0.]}, {"size_counts": [-1., 2., 3.]},
    {"sizes": [[1., 4.], [3., 6.], [7., 9.]]},
    {"sizes": [[1., 1.], [2., 3.], [4., 5.]]},
    {"size_counts": [1., 2.]}, {"size_counts": [1., float("nan"), 2.]},
])
def test_bad_histograms(changes):
    with pytest.raises(ValueError):
        histogram_statistics(histogram(**changes), "mean")


def test_failed_histogram_mode_never_uses_tallest_bin():
    with pytest.raises(ValueError, match="three positive"):
        fit_histogram_mode(histogram(size_counts=[0., 3., 1.]))


@pytest.mark.parametrize("technique", ["tem", "dls"])
def test_all_curves_are_densities_over_stored_diameter(technique):
    c = curve(technique=technique)
    assert curve_statistics(c, "mean")[0] == pytest.approx(5.5)
    assert curve_statistics(c, "median")[0] == pytest.approx(5.5)
    assert curve_statistics(c, "mode")[0] == 1.  # tie -> smallest diameter
    c["x"].reverse()
    c["y"].reverse()
    assert curve_statistics(c, "mean")[0] == pytest.approx(5.5)
    c["y"] = [v * 151 for v in c["y"]]
    assert curve_statistics(c, "mean")[0] == pytest.approx(5.5)


def test_curve_median_integrates_linear_segments():
    assert curve_statistics(curve(x=[1., 2., 3.], y=[1., 2., 3.]), "median")[0] == pytest.approx(math.sqrt(5.))


@pytest.mark.parametrize("changes", [
    {"x": [1., 2., 2.]}, {"x": [1., 3., 2.]}, {"x": [-1., 2., 3.]},
    {"y": [0., 0., 0.]}, {"y": [1., -1., 1.]},
    {"y": [1., float("inf"), 1.]}, {"y": [1.]},
])
def test_bad_curves(changes):
    with pytest.raises(ValueError):
        curve_statistics(curve(**changes), "mean")


@pytest.mark.parametrize("sizes, expected", [
    ([1., 1., 1., 1.], "flat"), ([1., 2., 3., 4.], "increasing"),
    ([4., 3., 2., 1.], "decreasing"), ([1., 3., 4., 2.], "peak"),
    ([4., 2., 1., 3.], "valley"), ([1., 3., 1., 3.], "irregular"),
])
def test_all_shape_labels(sizes, expected):
    assert classify_shape([1., 2., 3., 4.], sizes, [0.] * 4) == expected


def test_threshold_is_strict_and_anchor_moves_on_repeated_sign():
    assert classify_shape([1., 2.], [1., 2.], [1., 0.]) == "flat"
    assert classify_shape([1., 2., 3., 4.], [0., 3., 6., 3.], [1.] * 4) == "peak"


def test_shape_invariances():
    x, y, e = [1., 2., 3.], [3., 9., 4.], [1., 1., 1.]
    assert classify_shape(x[::-1], y[::-1], e[::-1]) == "peak"
    assert classify_shape([v ** 3 for v in x], y, e) == "peak"
    assert classify_shape(x, [v * 8 for v in y], [v * 8 for v in e]) == "peak"
    assert classify_shape(x, [20 - v for v in y], e) == "valley"


@pytest.mark.parametrize("x, sizes, errors", [
    ([1., 1.], [1., 2.], [0., 0.]), ([1.], [1.], [-1.]),
    ([], [], []), ([1., 2.], [1.], [1.]),
])
def test_bad_shape_inputs(x, sizes, errors):
    with pytest.raises(ValueError):
        classify_shape(x, sizes, errors)


def test_basic_build_is_pure_sorted_and_deterministic():
    s = snapshot()
    original = deepcopy(s)
    result = build_series(s, 77)
    assert s == original
    assert len(result.series) == 1 and result.exclusions == []
    built = result.series[0]
    assert built.row["series_id"] == "77-s1"
    assert built.row["medium_class"] == "water"
    assert built.row["shape_primary"] == built.row["shape_lenient"] == "increasing"
    assert built.row["spearman_rho"] == 1.
    assert [p["x"] for p in built.points()] == [100., 200., 300.]
    s["articles"][0]["experiments"].reverse()
    assert build_series(s, 77).series[0].row == built.row
    assert build_series(s, 999).series == []


@pytest.mark.parametrize("field, value", [
    ("wavelength", 400.), ("pulse_duration", 1000.), ("repetition_rate", 2000.),
    ("free_surf_entrance", False), ("beam_diameter", 2.),
])
def test_fixed_conditions_split_series(field, value):
    es = [experiment(100, beam_diameter=1.), experiment(200, 20., **{field: value})]
    assert not build_series(snapshot(es), 77).series


@pytest.mark.parametrize("field, value", [
    ("beam_movement_speed", 4.), ("beam_movement_type", "stationary"),
    ("beam_movement_passes", 2), ("liquid_layer_thickness", 3.),
])
def test_scanning_and_ablation_conditions_are_not_dropped(field, value):
    es = [experiment(100), experiment(200)]
    es[0]["ablation"][field] = {"beam_movement_speed": 1., "beam_movement_type": "scanner",
                                "beam_movement_passes": 1, "liquid_layer_thickness": 1.}[field]
    es[1]["ablation"][field] = value
    assert not build_series(snapshot(es), 77).series


def test_average_power_is_not_a_fixed_key():
    es = [experiment(100, average_power=1.), experiment(200, average_power=2.)]
    assert len(build_series(snapshot(es), 77).series) == 1


def test_shared_contents_not_ids_and_missing_equals_null():
    s = snapshot([experiment(100), experiment(200)])
    s["shared"]["instruments"]["40"] = deepcopy(s["shared"]["instruments"]["4"])
    s["shared"]["targets"]["20"] = deepcopy(s["shared"]["targets"]["1"])
    second = s["articles"][0]["experiments"][1]
    second["laser"] = 40
    second["ablation"]["target"] = 20
    second["polarization"] = None
    second["wavelength"] = 800  # JSON integer and float encode the same condition.
    assert len(build_series(s, 77).series) == 1


def test_unordered_lists_but_ordered_protocol():
    s = snapshot()
    first, second = s["articles"][0]["experiments"][:2]
    first["feedstock"] = [{"colloid": 123, "fraction": .3}, {"colloid": 456, "fraction": .7}]
    second["feedstock"] = first["feedstock"][::-1]
    assert condition_key(first, s["shared"], 10) == condition_key(second, s["shared"], 10)
    first["postprocessing_steps"] = [{"step": 1, "described": {"procedure": "wash"}},
                                     {"step": 2, "described": {"procedure": "dry"}}]
    second["postprocessing_steps"] = [{"step": 2, "described": {"procedure": "wash"}},
                                      {"step": 1, "described": {"procedure": "dry"}}]
    assert condition_key(first, s["shared"], 10) != condition_key(second, s["shared"], 10)


@pytest.mark.parametrize("field, value", [
    ("technique", "sem"), ("quantity", "hydrodynamic_diameter"),
    ("weighting_quantity", "scattering_intensity"), ("component", "satellite"),
])
def test_measurement_kinds_do_not_mix(field, value):
    es = [experiment(100), experiment(200)]
    es[1]["colloids"][0]["measured_properties"][0][field] = value
    assert not build_series(snapshot(es), 77).series


def test_z_average_and_missing_statistic_group_as_mean_with_original_labels():
    es = [experiment(100), experiment(200), experiment(300)]
    for e, statistic in zip(es, ["mean", "z_average", None], strict=True):
        e["colloids"][0]["measured_properties"] = [scalar(e["id"] / 10, statistic)]
    built = build_series(snapshot(es), 77).series[0]
    assert built.row["size_statistic"] == "mean"
    points = built.points()
    assert [p["original_statistic"] for p in points] == ["mean", "z_average", None]
    assert points[1]["assumptions"] == ["z_average_as_mean"]
    assert points[2]["assumptions"] == ["missing_statistic_as_mean"]


def test_scalar_statistic_requests_the_same_histogram_statistic():
    es = [experiment(100), experiment(200), experiment(300)]
    es[0]["colloids"][0]["measured_properties"] = [scalar(9., "mode")]
    for e in es[1:]:
        e["colloids"][0] = {"id": e["id"] + 1000, "medium": 10,
                             "size_distributions": [lognormal_histogram()]}
    result = build_series(snapshot(es), 77)
    assert len(result.series) == 1
    built = result.series[0]
    assert built.row["size_statistic"] == "mode" and built.row["size_source"] == "mixed"
    assert [p["size_source"] for p in built.points()] == ["scalar", "histogram", "histogram"]
    assert built.points()[1]["fit_residual"] < 1e-8


def test_default_mean_for_histogram_and_curve_without_scalars():
    es = [experiment(100), experiment(200)]
    es[0]["colloids"][0] = {"id": 1100, "medium": 10, "size_distributions": [histogram()]}
    es[1]["colloids"][0] = {"id": 1200, "medium": 10, "measurement_curves": [curve()]}
    built = build_series(snapshot(es), 77).series[0]
    assert built.row["size_statistic"] == "mean"
    assert built.points()[1]["assumptions"] == ["density_over_diameter"]


def test_scalar_precedence_sd_and_explicit_particle_count():
    es = [experiment(100), experiment(200)]
    for e in es:
        c = e["colloids"][0]
        c["measured_properties"].append(scalar(5., "standard_deviation"))
        c["size_distributions"] = [histogram(particles_counted=25)]
    built = build_series(snapshot(es), 77).series[0]
    assert built.row["size_source"] == "scalar"
    for model in ["primary", "lenient"]:
        assert built.points(model)[0]["size_err"] == 1.
        assert built.points(model)[0]["err_source"] == "sd_over_sqrt_n"
    for e in es:
        del e["colloids"][0]["size_distributions"][0]["particles_counted"]
    assert build_series(snapshot(es), 77).series[0].points()[0]["err_source"] == "fallback"


def test_multiple_statistics_have_distinct_deterministic_ids():
    es = [experiment(100), experiment(200)]
    for e in es:
        e["colloids"][0]["measured_properties"].append(scalar(9., "mode"))
    built = build_series(snapshot(es), 77).series
    assert [(s.row["series_id"], s.row["size_statistic"]) for s in built] == [
        ("77-s1", "mean"), ("77-s2", "mode")]


def test_shortest_common_storage_duration_not_null_as_zero():
    es = [experiment(100), experiment(200)]
    for e in es:
        c = e["colloids"][0]
        c["storage_duration"] = 5.
        later = deepcopy(c)
        later["id"] += 10
        later["storage_duration"] = 10.
        unknown = deepcopy(c)
        unknown["id"] += 20
        unknown.pop("storage_duration")
        e["colloids"].extend([later, unknown])
    earlier = deepcopy(es[0]["colloids"][0])
    earlier["id"] += 30
    earlier["storage_duration"] = 0.
    es[0]["colloids"].append(earlier)
    assert build_series(snapshot(es), 77).series[0].row["storage_duration_h"] == 5.
    es[1]["colloids"] = [es[1]["colloids"][-1]]
    assert build_series(snapshot(es), 77).series[0].row["storage_duration_h"] is None


def test_no_common_storage_is_explicit_not_salvaged():
    es = [experiment(100), experiment(200)]
    es[0]["colloids"][0]["storage_duration"] = 0.
    result = build_series(snapshot(es), 77)
    assert not result.series
    assert result.exclusions[0]["reason"] == "no_common_storage"


@pytest.mark.parametrize("changes, reason", [
    ({"pulse_energy": None}, "mixed_x"),
    ({"pulse_energy": 100.}, "short_series"),
])
def test_unusable_x_diagnostics(changes, reason):
    result = build_series(snapshot([experiment(100), experiment(200, **changes)]), 77)
    assert not result.series
    assert any(d["reason"] == reason for d in result.exclusions)


def test_duplicate_x_does_not_order_replicates_arbitrarily():
    result = build_series(snapshot([experiment(100), experiment(200), experiment(300, pulse_energy=100.)]), 77)
    assert not result.series
    assert result.exclusions[0]["reason"] == "duplicate_x"


def test_fluence_preferred_and_energy_not_derived():
    es = [experiment(100, pulse_fluence=1.), experiment(200, pulse_fluence=2.)]
    assert build_series(snapshot(es), 77).series[0].row["x_quantity"] == "fluence"
    del es[1]["pulse_fluence"]
    assert build_series(snapshot(es), 77).series[0].row["x_quantity"] == "pulse_energy"


def test_ambiguous_measurement_and_bad_fit_are_explicit():
    es = [experiment(100), experiment(200)]
    es[0]["colloids"][0]["measured_properties"].append(scalar(11.))
    result = build_series(snapshot(es), 77)
    assert not result.series
    assert any(d["reason"] == "ambiguous_measurement" for d in result.exclusions)
    es[0]["colloids"][0]["measured_properties"] = [scalar(10., "mode")]
    es[1]["colloids"][0] = {"id": 1200, "medium": 10,
                             "size_distributions": [histogram(size_counts=[0., 2., 1.])]}
    result = build_series(snapshot(es), 77)
    assert any("three positive" in d["detail"] for d in result.exclusions)


def test_unrelated_properties_and_widths_do_not_request_series():
    es = [experiment(100), experiment(200)]
    for e in es:
        e["colloids"][0]["measured_properties"] = [scalar(4., "fwhm"), scalar(500., "peak", quantity="wavelength")]
    result = build_series(snapshot(es), 77)
    assert not result.series and all(d["reason"] == "no_size" for d in result.exclusions)


def test_non_gold_target_and_unknown_statistic_are_reported():
    s = snapshot()
    s["shared"]["base_materials"]["3"]["formula"] = "Ag"
    assert all(d["reason"] == "not_gold_ablation" for d in build_series(s, 77).exclusions)
    s = snapshot([experiment(100)])
    s["articles"][0]["experiments"][0]["colloids"][0]["measured_properties"] = [scalar(4., "onset")]
    assert any(d["reason"] == "unsupported_statistic" for d in build_series(s, 77).exclusions)


def test_missing_laser_metadata_stays_null_and_constant_correlation_is_null():
    es = [experiment(100), experiment(200)]
    for e in es:
        e.pop("pulse_duration")
        e.pop("wavelength")
    row = build_series(snapshot(es), 77).series[0].row
    assert row["pulse_duration_class"] is None and row["wavelength_nm"] is None
    assert row["spearman_rho"] is None


def test_zero_diameter_boundary_and_extreme_curve_scales():
    for scale in (1e-250, 1., 1e250):
        assert curve_statistics(curve(x=[0., 1., 2.], y=[scale] * 3), "mean")[0] == pytest.approx(1.)


def test_compact_gold_without_formula_is_supported():
    s = snapshot()
    del s["shared"]["base_materials"]["3"]["formula"]
    assert len(build_series(s, 77).series) == 1


def test_particle_target_material_is_resolved():
    s = snapshot()
    s["shared"]["particles"] = {"50": {"material": 2}}
    s["shared"]["targets"]["1"]["constituents"] = [{"particle": 50, "fraction": 1.}]
    assert len(build_series(s, 77).series) == 1


def test_curve_mode_requested_by_scalar_and_matching_weighting():
    es = [experiment(100), experiment(200)]
    es[0]["colloids"][0]["measured_properties"] = [scalar(2., "mode")]
    es[1]["colloids"][0] = {"id": 1200, "medium": 10,
                             "measurement_curves": [curve(x=[1., 2., 3.], y=[0., 1., 0.])]}
    built = build_series(snapshot(es), 77).series[0]
    assert built.row["size_statistic"] == "mode"
    assert built.points()[1]["size"] == 2.
    assert built.points()[1]["err_source"] == "fallback"


def test_fwhm_is_not_a_standard_deviation_and_n_is_not_digitized_counts():
    es = [experiment(100), experiment(200)]
    for e in es:
        c = e["colloids"][0]
        c["measured_properties"].append(scalar(100., "fwhm"))
        c["size_distributions"] = [histogram()]
    points = build_series(snapshot(es), 77).series[0].points()
    assert points[0]["sd"] is None
    assert points[0]["particles_counted"] is None
    assert points[0]["err_source"] == "fallback"


def test_distinct_product_media_can_share_experiments():
    s = snapshot()
    s["shared"]["liquid_media"]["13"] = {
        "constituents": [{"liquid": 11, "fraction": 1.}],
        "additives": [{"material": 2}],
    }
    for e in s["articles"][0]["experiments"]:
        c = deepcopy(e["colloids"][0])
        c["id"] += 100
        c["medium"] = 13
        e["colloids"].append(c)
    result = build_series(s, 77)
    assert len(result.series) == 2 and not result.exclusions
    assert [{p["experiment_id"] for p in built.points()} for built in result.series] == [{100, 200, 300}] * 2
    assert all("overlapping_series" in built.row["notes"] for built in result.series)


def test_measurement_kinds_remain_separate_under_wildcards():
    s = snapshot()
    for e in s["articles"][0]["experiments"]:
        records = e["colloids"][0]["measured_properties"]
        records.extend([
            scalar(5., component="satellite"),
            scalar(20., weighting_quantity="scattering_intensity"),
        ])
    result = build_series(s, 77)
    seen = set()
    assert len(result.series) == 3
    for built in result.series:
        for m in built.measurements:
            member = (m.experiment_id, m.kind, m.statistic)
            assert member not in seen
            seen.add(member)


def test_physical_array_order_is_not_canonicalized_away():
    s = snapshot()
    s["shared"]["particles"] = {"50": {"material": 2, "measurement_curves": [curve(y=[1., 2., 3.])]}}
    s["shared"]["targets"]["1"]["constituents"] = [{"particle": 50, "fraction": 1.}]
    key = condition_key(s["articles"][0]["experiments"][0], s["shared"], 10)
    s["shared"]["particles"]["50"]["measurement_curves"][0]["y"] = [3., 2., 1.]
    other = condition_key(s["articles"][0]["experiments"][0], s["shared"], 10)
    assert key != other


def test_medium_classes():
    s = snapshot()
    for e in s["articles"][0]["experiments"]:
        e["feedstock"] = [{"colloid": 123, "fraction": 1.}]
    assert build_series(s, 77).series[0].row["medium_class"] == "colloid"
    for e in s["articles"][0]["experiments"]:
        e.pop("feedstock")
    s["shared"]["liquid_media"]["10"]["additives"] = [{"material": 2}]
    assert build_series(s, 77).series[0].row["medium_class"] == "aqueous"
    s["shared"]["liquid_media"]["10"].pop("additives")
    s["shared"]["base_liquids"]["12"]["formula"] = "C2H6O"
    assert build_series(s, 77).series[0].row["medium_class"] == "organic"
    s["shared"]["liquid_media"]["10"]["constituents"] = []
    assert build_series(s, 77).series[0].row["medium_class"] == "other"
