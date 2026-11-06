"""The nine preregistered METHOD §5 properties, with deterministic examples.

Dyadic grids keep metamorphic transformations exact in binary arithmetic.
The grouping oracle enumerates subsets, not production keys or clique code.
"""

import itertools
import math
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from checks.verifier.contract import check_series
from checks.verifier.fixtures import experiment, snapshot
from tools.series import build_series, classify_shape, histogram_statistics, size_error

PROPERTY = settings(max_examples=150, derandomize=True, deadline=None, database=None)


@st.composite
def walks(draw):
    """Finite sizes/errors and unique x on an exactly representable grid."""
    n = draw(st.integers(2, 12))
    xs = sorted(draw(st.lists(st.integers(1, 1000), min_size=n, max_size=n, unique=True)))
    sizes = [v / 8 for v in draw(st.lists(st.integers(1, 800), min_size=n, max_size=n))]
    errors = [v / 8 for v in draw(st.lists(st.integers(0, 80), min_size=n, max_size=n))]
    return xs, sizes, errors


@PROPERTY
@given(walks(), st.data())
def test_point_order_does_not_matter(walk, data):
    x, y, e = walk
    order = data.draw(st.permutations(range(len(x))))
    assert classify_shape([x[i] for i in order], [y[i] for i in order], [e[i] for i in order]) == classify_shape(x, y, e)


@PROPERTY
@given(walks(), st.integers(-16, 16))
def test_size_unit_does_not_matter(walk, exponent):
    x, y, e = walk
    assert classify_shape(x, [math.ldexp(v, exponent) for v in y], [math.ldexp(v, exponent) for v in e]) == classify_shape(x, y, e)


@PROPERTY
@given(walks())
def test_mirror_swaps_direction(walk):
    x, y, e = walk
    mirror = {"flat": "flat", "increasing": "decreasing", "decreasing": "increasing",
              "peak": "valley", "valley": "peak", "irregular": "irregular"}
    assert classify_shape(x, [max(y) + min(y) - v for v in y], e) == mirror[classify_shape(x, y, e)]


@PROPERTY
@given(walks())
def test_only_order_of_x_matters(walk):
    x, y, e = walk
    assert classify_shape([v**3 + 7 for v in x], y, e) == classify_shape(x, y, e)


@PROPERTY
@given(walks(), st.one_of(st.none(), st.integers(0, 30)),
       st.one_of(st.none(), st.integers(0, 50)), st.one_of(st.none(), st.integers(1, 500)),
       st.sampled_from(["mean", "median", "mode"]))
def test_lenient_flat_when_primary_flat(walk, se, sd, n, statistic):
    x, y, _ = walk
    kwargs = {"reported_se": se, "sd": sd, "particles_counted": n, "statistic": statistic}
    primary = [size_error(v, "primary", **kwargs)[0] for v in y]
    lenient = [size_error(v, "lenient", **kwargs)[0] for v in y]
    assert all(a <= b for a, b in zip(primary, lenient, strict=True))
    if classify_shape(x, y, primary) == "flat":
        assert classify_shape(x, y, lenient) == "flat"


@PROPERTY
@given(walks())
def test_repeated_last_point_changes_nothing(walk):
    x, y, e = walk
    assert classify_shape([*x, x[-1] + 1], [*y, y[-1]], [*e, e[-1]]) == classify_shape(x, y, e)


@PROPERTY
@given(st.lists(st.tuples(st.integers(1, 20), st.integers(0, 100)), min_size=1, max_size=15),
       st.integers(-10, 10))
def test_distribution_mean(bins, exponent):
    edges, counts, left = [], [], 0
    for width, count in bins:
        edges.append([left, left + width])
        counts.append(count + 1)  # positive total without rejected examples
        left += width + 1
    h = {"sizes": edges, "size_counts": counts}
    mean, sd, _ = histogram_statistics(h, "mean")
    expected = math.fsum((lo + hi) / 2 * w for (lo, hi), w in zip(edges, counts, strict=True)) / sum(counts)
    assert edges[0][0] <= mean <= edges[-1][1]
    assert mean == pytest.approx(expected)
    scaled = {**h, "size_counts": [math.ldexp(w, exponent) for w in counts]}
    other, other_sd, _ = histogram_statistics(scaled, "mean")
    assert (other, other_sd) == pytest.approx((mean, sd))


@PROPERTY
@given(st.integers(1, 1000), st.one_of(st.none(), st.integers(0, 100)),
       st.one_of(st.none(), st.integers(0, 100)), st.one_of(st.none(), st.integers(1, 10000)),
       st.sampled_from(["mean", "median", "mode"]))
def test_error_priority(size, se, sd, n, statistic):
    for model, fraction in (("primary", .1), ("lenient", .2)):
        actual, source = size_error(size, model, reported_se=se, sd=sd, particles_counted=n, statistic=statistic)
        if se is not None:
            expected, expected_source = se, "reported_se"
        elif statistic == "mean" and sd is not None and n is not None:
            expected, expected_source = sd / math.sqrt(n), "sd_over_sqrt_n"
        else:
            expected, expected_source = fraction * size, "fallback"
        assert actual == pytest.approx(expected)
        assert source == expected_source


@PROPERTY
@given(st.lists(st.tuples(st.sampled_from([None, 532, 1064]), st.sampled_from([None, 1000, 2000]),
                         st.sampled_from([None, "tem", "sem"]), st.sampled_from([None, "particle_count", "scattering_intensity"]),
                         st.sampled_from([None, "core"]), st.sampled_from(["mean", "median", "peak"]),
                         st.sampled_from([77, 78])), min_size=2, max_size=7), st.data())
def test_series_compatibility(parameters, data):
    experiments = []
    for i, (wavelength, rate, technique, weighting, component, statistic, aid) in enumerate(parameters, 1):
        e = experiment(i, article_id=aid, wavelength=wavelength, technique=technique,
                       weighting=weighting, component=component, statistic=statistic)
        if rate is not None:
            e["repetition_rate"] = rate
        experiments.append(e)
    raw = snapshot(experiments)
    saved = deepcopy(raw)

    def fits(i, j):
        a, b = parameters[i], parameters[j]
        # The generated varying conditions are exactly wavelength and rate;
        # technique/weighting/component/statistic/article are exact labels.
        return (a[2:] == b[2:] and all(x is None or y is None or x == y
                                     for x, y in zip(a[:2], b[:2], strict=True)))

    cliques = [frozenset(group) for n in range(1, len(parameters) + 1)
               for group in itertools.combinations(range(len(parameters)), n)
               if all(fits(i, j) for i, j in itertools.combinations(group, 2))]
    expected = {frozenset(i + 1 for i in group) for group in cliques
                if len(group) >= 2 and not any(group < bigger for bigger in cliques)}
    results = [s for aid in (77, 78) for s in build_series(raw, aid).series]
    observed = {frozenset(m.experiment_id for m in s.measurements) for s in results}
    assert len(observed) == len(results)  # no duplicate selected series
    assert observed == expected
    for s in results:
        assert not check_series(raw, {"series": s.row, "points": s.points()})
        assert not check_series(raw, {"series": s.row, "points": s.points("lenient")}, model="lenient")
    assert raw == saved
    reordered = deepcopy(raw)
    for article in reordered["articles"]:
        article["experiments"] = list(data.draw(st.permutations(article["experiments"])))
    reordered["articles"].reverse()
    after = [s for aid in (77, 78) for s in build_series(reordered, aid).series]
    assert [(s.row, s.points()) for s in after] == [(s.row, s.points()) for s in results]
