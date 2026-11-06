"""Pure snapshot-to-series calculations; see checks/results_spec.md §§2–4.

No file access, database connection, randomness or claim extraction here.
All curve ordinates are deliberately treated as densities over diameter.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares
from scipy.special import ndtr
from scipy.stats import spearmanr

SIZE_QUANTITIES = frozenset({
    "geometric_diameter", "hydrodynamic_diameter", "particle_size",
})
LOCATION_STATISTICS = frozenset({"mean", "median", "mode"})
WIDTH_STATISTICS = frozenset({"standard_deviation", "standard_error", "fwhm"})
FALLBACK = {"primary": 0.10, "lenient": 0.20}
# Shared references have semantic contents; colloid references retain identity.
REFERENCES = {
    "laser": "instruments", "instrument": "instruments",
    "objective": "objectives", "target": "targets",
    "material": "materials", "base_material": "base_materials",
    "particle": "particles", "medium": "liquid_media",
    "synthesis_medium": "liquid_media", "redispersion_medium": "liquid_media",
    "resulting_medium": "liquid_media", "liquid": "liquids",
    "base_liquid": "base_liquids", "entrance_mat": "materials",
    "pumping_gas": "gases", "base_gas": "base_gases",
    "target_position_ref_type": "target_position_ref_types",
}
VARIABLE_FIELDS = frozenset({
    "id", "article_id", "colloids", "pulse_fluence", "pulse_energy",
    "average_power", "spot_diameter",
})


@dataclass(frozen=True)
class SizeKind:
    """A compatible measurement kind, without its location statistic."""

    quantity: str
    technique: str | None
    weighting: str | None
    component: str | None


@dataclass(frozen=True)
class Measurement:
    """One selected location estimate and its traceable error inputs."""

    experiment_id: int
    colloid_id: int
    storage_duration: float | None
    kind: SizeKind
    statistic: str
    size: float
    source: str
    original_statistic: str | None = None
    sd: float | None = None
    particles_counted: int | None = None
    reported_se: float | None = None
    assumptions: tuple[str, ...] = ()
    fit_residual: float | None = None


@dataclass
class BuiltSeries:
    """Internal series representation, materialized as plain API data."""

    row: dict
    measurements: tuple[Measurement, ...]
    x: tuple[float, ...]
    condition_key: str

    def points(self, model: str = "primary") -> list[dict]:
        """Return independent, x-sorted point records for an error model."""
        validate_model(model)
        return [
            {
                "experiment_id": m.experiment_id,
                "colloid_id": m.colloid_id,
                "x": x, "size": m.size,
                "size_err": size_error(
                    m.size, model, reported_se=m.reported_se, sd=m.sd,
                    particles_counted=m.particles_counted,
                    statistic=m.statistic,
                )[0],
                "err_source": size_error(
                    m.size, model, reported_se=m.reported_se, sd=m.sd,
                    particles_counted=m.particles_counted,
                    statistic=m.statistic,
                )[1],
                "size_source": m.source,
                "original_statistic": m.original_statistic,
                "sd": m.sd, "particles_counted": m.particles_counted,
                "assumptions": list(m.assumptions),
                "fit_residual": m.fit_residual,
            }
            for x, m in zip(self.x, self.measurements, strict=True)
        ]


@dataclass
class BuildResult:
    """Usable series and explicit measurement/group exclusion diagnostics."""

    series: list[BuiltSeries] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)


def validate_model(model: str) -> None:
    """Reject an unknown error model instead of choosing a default."""
    if not isinstance(model, str) or model not in FALLBACK:
        raise ValueError(f"unknown error model {model!r}")


def number(value: object, name: str, *, positive: bool = False) -> float:
    """Return a finite numeric value, optionally requiring positivity."""
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be numeric")  # noqa: TRY004 -- malformed data value
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"invalid {name}: {value!r}")
    return result


def normalize_statistic(statistic: str | None) -> str:
    """Apply the curator's mean assumption and size-mode label alias."""
    if statistic in (None, "z_average"):
        return "mean"
    return "mode" if statistic == "peak" else statistic


def size_error(
    size: float, model: str = "primary", *,
    reported_se: float | None = None, sd: float | None = None,
    particles_counted: int | None = None, statistic: str = "mean",
) -> tuple[float, str]:
    """Select SE, mean's SD/sqrt(N), or the explicit model fallback.

    N is supplied only from a reported particle count, never digitized
    histogram heights. A distribution width is not a mode/median SE.
    """
    validate_model(model)
    size = number(size, "size", positive=True)
    for name, value in (("SE", reported_se), ("SD", sd)):
        if value is not None and number(value, name) < 0:
            raise ValueError(f"{name} must be nonnegative")
    if particles_counted is not None and (
        isinstance(particles_counted, bool)
        or not isinstance(particles_counted, int)
        or particles_counted <= 0
    ):
        raise ValueError("particles_counted must be a positive integer")
    if reported_se is not None:
        return float(reported_se), "reported_se"
    if statistic == "mean" and sd is not None and particles_counted is not None:
        return sd / math.sqrt(particles_counted), "sd_over_sqrt_n"
    return FALLBACK[model] * size, "fallback"


def histogram_arrays(histogram: dict) -> tuple[np.ndarray, np.ndarray]:
    """Validate stored bar extents and arbitrary nonnegative counts."""
    edges = np.asarray(histogram["sizes"], dtype=float)
    counts = np.asarray(histogram["size_counts"], dtype=float)
    if (edges.ndim != 2 or edges.shape[1] != 2 or len(edges) == 0
            or counts.shape != (len(edges),)
            or not np.isfinite(edges).all() or not np.isfinite(counts).all()
            or (edges < 0).any() or (edges[:, 1] <= edges[:, 0]).any()
            or (edges[1:, 0] < edges[:-1, 1]).any()
            or (counts < 0).any() or not (counts > 0).any()):
        raise ValueError("invalid histogram bars or counts")
    return edges, counts / counts.max()


def fit_histogram_mode(histogram: dict) -> tuple[float, float]:
    """Fit a zero-location lognormal to bar masses; return mode and RMS.

    This is an actual nonlinear fit, not a modal-bin or moment estimate.
    The fitted amplitude absorbs arbitrary count scale and missing tails.
    Stored bar extents are used as bin limits, a documented approximation.
    """
    edges, counts = histogram_arrays(histogram)
    if np.count_nonzero(counts) < 3:
        raise ValueError("lognormal fit needs at least three positive bars")
    centres = edges.mean(axis=1)
    logs = np.log(centres)
    mu0 = float(np.average(logs, weights=counts))
    sigma0 = max(float(np.sqrt(np.average((logs - mu0) ** 2, weights=counts))), .1)
    log_left = np.full(len(edges), -np.inf)
    np.log(edges[:, 0], out=log_left, where=edges[:, 0] > 0)
    log_right = np.log(edges[:, 1])

    def masses(parameters: np.ndarray) -> np.ndarray:
        """Integrate the fitted density over every recorded bar."""
        log_amplitude, mu, log_sigma = parameters
        sigma = np.exp(log_sigma)
        # Use survival differences in the upper tail to avoid cancellation.
        low, high = (log_left - mu) / sigma, (log_right - mu) / sigma
        probability = np.where(
            low > 0, ndtr(-low) - ndtr(-high), ndtr(high) - ndtr(low))
        return np.exp(log_amplitude) * probability

    initial = np.array([0., mu0, math.log(sigma0)])
    initial[0] = math.log(counts.sum() / max(masses(initial).sum(), 1e-15))
    lower = np.array([-30., logs.min() - 10., math.log(.001)])
    upper = np.array([30., logs.max() + 10., math.log(5.)])
    initial = np.clip(initial, lower + 1e-6, upper - 1e-6)
    fit = least_squares(
        lambda p: masses(p) - counts, initial, bounds=(lower, upper),
        max_nfev=3000, ftol=1e-12, xtol=1e-12, gtol=1e-12,
    )
    if not fit.success or np.any(fit.active_mask):
        raise ValueError("lognormal fit failed or reached a parameter bound")
    mode = math.exp(float(fit.x[1] - math.exp(2 * fit.x[2])))
    if not math.isfinite(mode) or mode <= 0:
        raise ValueError("lognormal fit has no finite positive mode")
    return mode, float(np.sqrt(np.mean(fit.fun ** 2)))


def histogram_statistics(histogram: dict, statistic: str) -> tuple[float, float, float | None]:
    """Return a histogram's location, midpoint SD and optional fit RMS."""
    edges, counts = histogram_arrays(histogram)
    centres = edges.mean(axis=1)
    mean = float(np.average(centres, weights=counts))
    sd = float(np.sqrt(np.average((centres - mean) ** 2, weights=counts)))
    if statistic == "mean":
        return mean, sd, None
    if statistic == "mode":
        mode, residual = fit_histogram_mode(histogram)
        return mode, sd, residual
    if statistic == "median":
        cumulative = np.cumsum(counts)
        half = cumulative[-1] / 2
        i = int(np.searchsorted(cumulative, half))
        before = cumulative[i - 1] if i else 0.
        value = edges[i, 0] + (half - before) / counts[i] * np.diff(edges[i])[0]
        return float(value), sd, None
    raise ValueError(f"unsupported histogram statistic {statistic!r}")


def curve_arrays(curve: dict) -> tuple[np.ndarray, np.ndarray]:
    """Validate and orient a diameter-density curve without logging x."""
    x, y = np.asarray(curve["x"], dtype=float), np.asarray(curve["y"], dtype=float)
    if (x.ndim != 1 or len(x) < 2 or y.shape != x.shape
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or (x < 0).any() or (y < 0).any()):
        raise ValueError("invalid size curve")
    if (np.diff(x) < 0).all():
        x, y = x[::-1], y[::-1]
    if not (np.diff(x) > 0).all() or not (y > 0).any():
        raise ValueError("size curve needs monotone x and positive area")
    return x, y / y.max()


def curve_statistics(curve: dict, statistic: str) -> tuple[float, float]:
    """Compute location and SD treating every y as a density over d."""
    x, y = curve_arrays(curve)
    area = float(np.trapezoid(y, x))
    mean = float(np.trapezoid(x * y, x) / area)
    sd = float(np.sqrt(np.trapezoid((x - mean) ** 2 * y, x) / area))
    if statistic == "mean":
        return mean, sd
    if statistic == "mode":
        return float(x[np.argmax(y)]), sd
    if statistic == "median":
        masses = np.diff(x) * (y[:-1] + y[1:]) / 2
        cumulative = np.concatenate(([0.], np.cumsum(masses)))
        i = min(int(np.searchsorted(cumulative, area / 2, side="right")) - 1, len(x) - 2)
        needed = area / 2 - cumulative[i]
        width = x[i + 1] - x[i]
        slope = (y[i + 1] - y[i]) / width
        # Solve y0*t + slope*t²/2 = needed without cancellation.
        root = math.sqrt(max(float(y[i] ** 2 + 2 * slope * needed), 0.))
        denominator = y[i] + root
        distance = 0. if needed <= 0 else 2 * needed / denominator
        return float(x[i] + np.clip(distance, 0., width)), sd
    raise ValueError(f"unsupported curve statistic {statistic!r}")


def classify_shape(x: list[float] | tuple, sizes: list[float] | tuple,
                   errors: list[float] | tuple) -> str:
    """Classify a unique-x anchor walk with a strict error threshold.

    Move the anchor on every significant change, including when its sign
    equals the previous recorded sign. Equality to the threshold is flat.
    Sizes may be signed here so mirrored/resampled inputs can be tested.
    """
    if len(x) != len(sizes) or len(x) != len(errors) or not len(x):
        raise ValueError("shape arrays must have equal nonzero lengths")
    points = sorted(
        (number(a, "x"), number(b, "size"), number(c, "error"))
        for a, b, c in zip(x, sizes, errors, strict=True))
    if len({p[0] for p in points}) != len(points) or any(p[2] < 0 for p in points):
        raise ValueError("shape needs unique x and nonnegative errors")
    _, anchor_size, anchor_error = points[0]
    signs: list[int] = []
    for _, size, error in points[1:]:
        delta = size - anchor_size
        if abs(delta) > math.hypot(error, anchor_error):
            sign = 1 if delta > 0 else -1
            if not signs or sign != signs[-1]:
                signs.append(sign)
            anchor_size, anchor_error = size, error
    return {
        (): "flat", (1,): "increasing", (-1,): "decreasing",
        (1, -1): "peak", (-1, 1): "valley",
    }.get(tuple(signs), "irregular")


def _canonical(value: object, shared: dict, trail: tuple = ()) -> object:
    """Resolve shared contents and canonicalize unordered condition lists."""
    if isinstance(value, dict):
        result = {}
        for key, child in sorted(value.items()):
            if child is None or child == []:
                continue
            if key in REFERENCES and type(child) is int:
                reference = (REFERENCES[key], str(child))
                if reference in trail:
                    raise ValueError(f"cyclic shared reference {reference}")
                try:
                    row = shared[reference[0]][reference[1]]
                except KeyError as error:
                    raise ValueError(f"missing shared reference {reference}") from error
                result[key] = _canonical(row, shared, (*trail, reference))
            else:
                normalized = _canonical(child, shared, trail)
                if key in {"constituents", "additives", "feedstock"}:
                    normalized = sorted(
                        normalized, key=lambda item: json.dumps(item, sort_keys=True))
                elif key in {"beam_path", "postprocessing_steps"}:
                    ordinal = "path_order" if key == "beam_path" else "step"
                    normalized = sorted(normalized, key=lambda item: item[ordinal])
                result[key] = normalized
        return result
    if isinstance(value, list):
        return [_canonical(item, shared, trail) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def condition_key(experiment: dict, shared: dict, product_medium: int) -> str:
    """Fingerprint fixed conditions, not a wildcard equality/grouping key."""
    fixed = {k: v for k, v in experiment.items() if k not in VARIABLE_FIELDS}
    fixed["medium"] = product_medium
    return json.dumps(_canonical(fixed, shared), sort_keys=True, allow_nan=False)


def conditions_compatible(left: object, right: object, *, field: str = "") -> bool:
    """Match canonical conditions; unknown details, but not lists, are wildcards.

    Absence of a collection means an empty collection. Unordered condition
    lists need a one-to-one compatible matching, not positional comparison.
    This relation is symmetric but deliberately not transitive.
    """
    if isinstance(left, list) or isinstance(right, list):
        left = [] if left is None else left
        right = [] if right is None else right
        if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
            return False
        if field not in {"constituents", "additives", "feedstock"}:
            return all(conditions_compatible(a, b) for a, b in zip(left, right, strict=True))
        edges = [[j for j, b in enumerate(right) if conditions_compatible(a, b)] for a in left]
        assigned: dict[int, int] = {}

        def match(i: int, visited: set[int]) -> bool:
            """Find an augmenting path for a perfect bipartite matching."""
            for j in edges[i]:
                if j not in visited:
                    visited.add(j)
                    if j not in assigned or match(assigned[j], visited):
                        assigned[j] = i
                        return True
            return False

        return all(match(i, set()) for i in range(len(left)))
    if left is None or right is None:
        return True
    if isinstance(left, dict) and isinstance(right, dict):
        return all(conditions_compatible(left.get(k), right.get(k), field=k)
                   for k in left.keys() | right.keys())
    return left == right


def maximal_condition_groups(keys: list[str]) -> list[tuple[str, ...]]:
    """Return all maximal pairwise-compatible profile sets, deterministically.

    Maximal cliques, not connected components: an unknown value must not
    bridge conflicting stated conditions. Identical profiles are coalesced
    before searching; a profile can participate in several cliques.
    """
    keys = sorted(set(keys))
    profiles = [json.loads(key) for key in keys]
    neighbors: dict[int, set[int]] = {i: set() for i in range(len(keys))}
    for i, left in enumerate(profiles):
        for j in range(i):
            if conditions_compatible(left, profiles[j]):
                neighbors[i].add(j)
                neighbors[j].add(i)
    groups = []

    def visit(chosen: set[int], possible: set[int], excluded: set[int]) -> None:
        """Enumerate maximal cliques with a deterministic Bron-Kerbosch pivot."""
        if not possible and not excluded:
            if chosen:
                groups.append(tuple(keys[i] for i in sorted(chosen)))
            return
        pivot = min(possible | excluded, key=lambda i: (-len(possible & neighbors[i]), i))
        for i in sorted(possible - neighbors[pivot]):
            visit(chosen | {i}, possible & neighbors[i], excluded & neighbors[i])
            possible.remove(i)
            excluded.add(i)

    visit(set(), set(neighbors), set())
    return sorted(groups)


def _compatible_measurement_groups(groups: dict) -> list[tuple]:
    """Combine profile buckets for each exact kind/statistic, allowing overlap."""
    buckets: dict[tuple, dict] = defaultdict(dict)
    for (key, kind, statistic), by_experiment in groups.items():
        buckets[(kind, statistic)][key] = by_experiment
    output = []
    for (kind, statistic), profiles in buckets.items():
        for keys in maximal_condition_groups(list(profiles)):
            combined: dict[int, dict] = {}
            for key in keys:
                for eid, times in profiles[key].items():
                    for duration, candidates in times.items():
                        combined.setdefault(eid, defaultdict(list))[duration].extend(candidates)
            # Preserve the profiles for reproducible sorting; do not impute
            # a missing condition on an individual experiment.
            key = json.dumps([json.loads(k) for k in keys], sort_keys=True, allow_nan=False)
            output.append((key, kind, statistic, combined))
    return output


def _kind(record: dict, scalar: bool) -> SizeKind:
    """Read representation-independent size quantity and weighting."""
    return SizeKind(
        record["quantity" if scalar else "x_quantity"], record.get("technique"),
        record.get("weighting_quantity" if scalar else "y_quantity"),
        record.get("component"),
    )


def _is_gold(constituent: dict) -> bool:
    """Recognize a compact gold material even when formula is omitted."""
    material = constituent.get("material") or constituent.get("particle", {}).get("material", {})
    base = material.get("base_material", {})
    if base.get("formula") is not None:
        return base["formula"] == "Au"
    return base.get("material", "").casefold() in {"gold", "au"}


def _medium_class(experiments: list[dict], shared: dict) -> str:
    """Classify using stated information across the compatible members."""
    if any(e.get("feedstock") for e in experiments):
        return "colloid"
    media = [
        _canonical({"synthesis_medium": e.get("synthesis_medium")}, shared).get("synthesis_medium")
        for e in experiments
    ]
    media = [m for m in media if m is not None]
    if not media or any(len(m.get("constituents", [])) != 1 for m in media):
        return "other"
    bases = [m["constituents"][0].get("liquid", {}).get("base_liquid", {}) for m in media]
    formulas = {b["formula"] for b in bases if b.get("formula") is not None}
    if formulas == {"H2O"}:
        return "aqueous" if any(m.get("additives") for m in media) else "water"
    return "organic"


def _location_records(article: dict) -> dict[SizeKind, set[str]]:
    """Determine requested statistics per article and measurement kind."""
    requested: dict[SizeKind, set[str]] = defaultdict(set)
    for experiment in article["experiments"]:
        for colloid in experiment.get("colloids", []):
            for record in colloid.get("measured_properties", []):
                if record["quantity"] in SIZE_QUANTITIES:
                    statistic = normalize_statistic(record.get("statistic"))
                    if statistic in LOCATION_STATISTICS:
                        requested[_kind(record, True)].add(statistic)
    return requested


def _measurements(
    experiment: dict, colloid: dict, requested: dict,
    report: Callable[[str, str, list[int]], None],
) -> list[Measurement]:
    """Extract candidates without silently substituting a failed estimate."""
    records = [
        (source, record, _kind(record, source == "scalar"))
        for source, key in (("scalar", "measured_properties"),
                            ("histogram", "size_distributions"),
                            ("curve", "measurement_curves"))
        for record in colloid.get(key, [])
        if record["quantity" if source == "scalar" else "x_quantity"] in SIZE_QUANTITIES
    ]
    output = []
    duration = colloid.get("storage_duration")
    if duration is not None:
        duration = number(duration, "storage duration")
        if duration < 0:
            raise ValueError("negative storage duration")
    for source, record, kind in records:
        scalar_statistic = normalize_statistic(record.get("statistic"))
        if source == "scalar" and scalar_statistic not in LOCATION_STATISTICS:
            if scalar_statistic not in WIDTH_STATISTICS:
                report("unsupported_statistic", str(record.get("statistic")), [experiment["id"]])
            continue
        stats = {scalar_statistic} if source == "scalar" else requested.get(kind, {"mean"})
        same_kind = [(s, r) for s, r, k in records if k == kind]
        sds = [r["value"] for s, r in same_kind if s == "scalar"
               and r.get("statistic") == "standard_deviation"]
        ses = [r["value"] for s, r in same_kind if s == "scalar"
               and r.get("statistic") == "standard_error"]
        ns = {r["particles_counted"] for s, r in same_kind
              if s == "histogram" and r.get("particles_counted") is not None}
        for statistic in sorted(stats):
            try:
                assumptions = []
                residual = None
                sd = sds[0] if len(sds) == 1 else None
                if source == "scalar":
                    size = number(record["value"], "size", positive=True)
                    if record.get("statistic") is None:
                        assumptions.append("missing_statistic_as_mean")
                    if record.get("statistic") == "z_average":
                        assumptions.append("z_average_as_mean")
                elif source == "histogram":
                    size, derived_sd, residual = histogram_statistics(record, statistic)
                    sd = sd if sd is not None else derived_sd
                    if statistic == "mode":
                        assumptions.append("lognormal_fit_to_stored_bar_extents")
                else:
                    size, derived_sd = curve_statistics(record, statistic)
                    sd = sd if sd is not None else derived_sd
                    assumptions.append("density_over_diameter")
                n = next(iter(ns)) if len(ns) == 1 else None
                se = ses[0] if statistic == "mean" and len(ses) == 1 else None
                size_error(size, sd=sd, particles_counted=n, reported_se=se, statistic=statistic)
                output.append(Measurement(
                    experiment["id"], colloid["id"], duration, kind, statistic,
                    size, source, record.get("statistic") if source == "scalar" else None,
                    sd, n, se, tuple(assumptions), residual,
                ))
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                report("invalid_measurement", f"colloid {colloid['id']}, {source}/{statistic}: {error}",
                       [experiment["id"]])
    return output


def build_series(snapshot: dict, article_id: int) -> BuildResult:
    """Build one article's series and exclusions without mutating inputs."""
    result = BuildResult()

    def diagnose(reason: str, detail: str, ids: list[int]) -> None:
        """Keep an explicit, deterministic reason for every exclusion."""
        result.exclusions.append({
            "article_id": article_id, "experiment_ids": sorted(ids),
            "reason": reason, "detail": detail,
        })

    articles = [a for a in snapshot["articles"] if a["id"] == article_id]
    if not articles:
        return result
    if len(articles) != 1:
        raise ValueError(f"duplicate article id {article_id}")
    article, shared = articles[0], snapshot["shared"]
    requested = _location_records(article)
    experiments = {e["id"]: e for e in article["experiments"]}
    if len(experiments) != len(article["experiments"]):
        raise ValueError(f"duplicate experiment id in article {article_id}")
    # Exact profile fingerprint, kind, statistic -> exp -> duration -> candidates
    groups: dict[tuple, dict[int, dict]] = {}
    for eid, experiment in sorted(experiments.items()):
        if experiment["article_id"] != article_id:
            raise ValueError(f"wrong article for experiment {eid}")
        if "ablation" not in experiment:
            diagnose("not_gold_ablation", "no ablation target", [eid])
            continue
        target = _canonical({"target": experiment["ablation"]["target"]}, shared)["target"]
        constituents = target.get("constituents", [])
        if not constituents or not all(_is_gold(c) for c in constituents):
            diagnose("not_gold_ablation", "target is not gold only", [eid])
            continue
        found = False
        for colloid in experiment.get("colloids", []):
            key = condition_key(experiment, shared, colloid["medium"])
            for measurement in _measurements(experiment, colloid, requested, diagnose):
                found = True
                group = groups.setdefault((key, measurement.kind, measurement.statistic), {})
                times = group.setdefault(eid, defaultdict(list))
                times[measurement.storage_duration].append(measurement)
        if not found:
            diagnose("no_size", "no usable size location measurement", [eid])
    for key, kind, statistic, by_experiment in _compatible_measurement_groups(groups):
        ids = sorted(by_experiment)
        common = set.intersection(*(set(times) for times in by_experiment.values()))
        if not common:
            diagnose("no_common_storage", f"{kind}/{statistic}", ids)
            continue
        duration = min(common, key=lambda value: (value is None, value or 0.))
        selected = []
        for eid in ids:
            candidates = by_experiment[eid][duration]
            priority = min({"scalar": 0, "histogram": 1, "curve": 2}[m.source] for m in candidates)
            preferred = [m for m in candidates if {"scalar": 0, "histogram": 1, "curve": 2}[m.source] == priority]
            if len(preferred) != 1:
                diagnose("ambiguous_measurement", f"{kind}/{statistic} at {duration}", [eid])
            else:
                selected.append(preferred[0])
        ids = [m.experiment_id for m in selected]
        if len(selected) < 2:
            diagnose("short_series", f"{kind}/{statistic}: fewer than two points", ids)
            continue
        members = [experiments[eid] for eid in ids]
        if all(e.get("pulse_fluence") is not None for e in members):
            x_field, x_quantity = "pulse_fluence", "fluence"
        elif all(e.get("pulse_energy") is not None for e in members):
            x_field, x_quantity = "pulse_energy", "pulse_energy"
        else:
            diagnose("mixed_x", f"{kind}/{statistic}: no common fluence or energy", ids)
            continue
        pairs = sorted(
            ((number(e[x_field], x_field, positive=True), m)
             for e, m in zip(members, selected, strict=True)),
            key=lambda pair: (pair[0], pair[1].experiment_id),
        )
        xs = tuple(p[0] for p in pairs)
        if len(set(xs)) < 2:
            diagnose("short_series", f"{kind}/{statistic}: fewer than two distinct x", ids)
            continue
        if len(set(xs)) != len(xs):
            diagnose("duplicate_x", f"{kind}/{statistic}: repeated x needs a replicate rule", ids)
            continue
        measurements = tuple(p[1] for p in pairs)
        sizes = tuple(m.size for m in measurements)
        pulse_duration = next((e["pulse_duration"] for e in members if e.get("pulse_duration") is not None), None)
        wavelength = next((e["wavelength"] for e in members if e.get("wavelength") is not None), None)
        pulse_class = None if pulse_duration is None else (
            "fs" if pulse_duration < 1e3 else "ps" if pulse_duration < 1e6 else "ns")
        sources = {m.source for m in measurements}
        row = {
            "article_id": article_id, "series_id": "", "n_points": len(xs),
            "x_quantity": x_quantity, "size_quantity": kind.quantity,
            "size_statistic": statistic, "size_technique": kind.technique,
            "size_weighting": kind.weighting, "size_component": kind.component,
            "size_source": next(iter(sources)) if len(sources) == 1 else "mixed",
            "storage_duration_h": duration, "pulse_duration_fs": pulse_duration,
            "pulse_duration_class": pulse_class, "wavelength_nm": wavelength,
            "medium_class": _medium_class(members, shared),
            "spearman_rho": None if len(set(sizes)) == 1 else float(spearmanr(xs, sizes).statistic),
            "notes": "; ".join(sorted({a for m in measurements for a in m.assumptions})),
        }
        built = BuiltSeries(row, measurements, xs, key)
        for model in FALLBACK:
            points = built.points(model)
            row[f"shape_{model}"] = classify_shape(xs, sizes, [p["size_err"] for p in points])
        result.series.append(built)
    result.series.sort(key=lambda s: (
        min(m.experiment_id for m in s.measurements),
        *(s.row[k] or "" for k in (
            "size_quantity", "size_technique", "size_statistic", "size_weighting", "size_component")),
        s.condition_key,
    ))
    # Different profile cliques can become identical after measurement
    # selection/exclusions. Expose the selected series only once.
    unique = {}
    for built in result.series:
        signature = (built.row["x_quantity"], built.x, built.measurements)
        unique.setdefault(signature, built)
    result.series = list(unique.values())
    membership: dict[tuple, list[int]] = defaultdict(list)
    for index, built in enumerate(result.series):
        for m in built.measurements:
            membership[(m.experiment_id, m.kind, m.statistic)].append(index)
    overlapping = {i for indices in membership.values() if len(indices) > 1 for i in indices}
    for index, built in enumerate(result.series):
        if index in overlapping:
            built.row["notes"] = "; ".join(filter(None, [built.row["notes"], "overlapping_series"]))
        built.row["series_id"] = f"{article_id}-s{index + 1}"
    result.exclusions.sort(key=lambda d: (d["experiment_ids"], d["reason"], d["detail"]))
    return result
