"""Paired, fixed-error normal sensitivity experiment from METHOD §§2, 6–7.

No refitting, regrouping, clipping of negative draws, or error recomputation.
All statistical inference uses the five per-seed estimates, not pooled draws.
"""

from __future__ import annotations

import math
import time

import numpy as np
from scipy.stats import t

from tools.series import classify_shape

CONFIGS = {"smoke": {"seeds": (0,), "draws": 100},
           "full": {"seeds": (0, 1, 2, 3, 4), "draws": 1000}}
MODELS = ("primary", "lenient")
RUN_FIELDS = (
    "step", "seed", "model", "article_id", "series_id", "n_points", "x_quantity",
    "shape", "draws", "observed_hits", "baseline_hits", "stability", "baseline_share",
    "delta", "baseline_size_nm", "nonpositive_observed_draws", "nonpositive_baseline_draws",
    "series_elapsed_seconds", "git_commit",
)


def weighted_baseline(sizes: list[float], errors: list[float]) -> float:
    """Inverse-primary-variance mean; zero SE needs an explicit future policy."""
    if len(sizes) != len(errors) or not sizes or any(
            not math.isfinite(s) or not math.isfinite(e) or s <= 0 or e <= 0
            for s, e in zip(sizes, errors, strict=True)):
        raise ValueError("baseline requires positive finite sizes and primary errors; no zero-error convention is specified")
    # Scaling the inverse-variance weights avoids overflow for small errors.
    smallest = min(errors)
    weights = [(smallest / e) ** 2 for e in errors]
    return math.fsum(s * w for s, w in zip(sizes, weights, strict=True)) / math.fsum(weights)


def sample_case(case: dict, *, seed: int, draws: int, rng: np.random.Generator) -> list[dict]:
    """Sample once, reuse the same z for both models and the flat baseline."""
    if type(draws) is not int or draws <= 0:
        raise ValueError("draws must be a positive integer")
    x, sizes = case["x"], case["sizes"]
    primary, lenient = case["errors"]["primary"], case["errors"]["lenient"]
    if len(x) < 2 or not len(x) == len(sizes) == len(primary) == len(lenient):
        raise ValueError("series arrays must align and have at least two points")
    baseline = weighted_baseline(sizes, primary)
    if any(not math.isfinite(e) or e < p for p, e in zip(primary, lenient, strict=True)):
        raise ValueError("lenient errors must be finite and at least primary errors")
    z = rng.standard_normal((draws, len(sizes)))
    perturbation = np.asarray(primary) * z
    observed = np.asarray(sizes) + perturbation
    null = baseline + perturbation
    nonpositive_observed = int(np.count_nonzero(np.any(observed <= 0, axis=1)))
    nonpositive_baseline = int(np.count_nonzero(np.any(null <= 0, axis=1)))
    results = []
    for model in MODELS:
        errors = case["errors"][model]
        shape = classify_shape(x, sizes, errors)
        if shape != case["shapes"][model]:
            raise ValueError(f"{case['series_id']}: stored {model} shape does not match original points")
        observed_hits = sum(classify_shape(x, y, errors) == shape for y in observed)
        baseline_hits = sum(classify_shape(x, y, errors) == shape for y in null)
        results.append({
            "seed": seed, "model": model, "article_id": case["article_id"],
            "series_id": case["series_id"], "n_points": len(x), "x_quantity": case["x_quantity"],
            "shape": shape, "draws": draws, "observed_hits": observed_hits, "baseline_hits": baseline_hits,
            "stability": observed_hits / draws, "baseline_share": baseline_hits / draws,
            "delta": (observed_hits - baseline_hits) / draws, "baseline_size_nm": baseline,
            "nonpositive_observed_draws": nonpositive_observed,
            "nonpositive_baseline_draws": nonpositive_baseline,
        })
    return results


def collect_cases(db) -> list[dict]:
    """Freeze both public error-model payloads before any random draw."""
    cases = []
    for article in db.find_articles():
        for row in db.list_series(article["article_id"]):
            payloads = {m: db.get_series(row["series_id"], m)["points"] for m in MODELS}
            primary, lenient = payloads["primary"], payloads["lenient"]
            def identity(p: dict) -> tuple:
                return p["experiment_id"], p["colloid_id"], p["x"], p["size"]

            if list(map(identity, primary)) != list(map(identity, lenient)):
                raise ValueError("error models must have identical members, x and sizes")
            cases.append({
                "article_id": row["article_id"], "series_id": row["series_id"], "x_quantity": row["x_quantity"],
                "x": [p["x"] for p in primary], "sizes": [p["size"] for p in primary],
                "errors": {m: [p["size_err"] for p in ps] for m, ps in payloads.items()},
                "shapes": {m: row[f"shape_{m}"] for m in MODELS},
            })
    return sorted(cases, key=lambda c: (c["article_id"], c["series_id"]))


def sweep(cases: list[dict], step: str, git_commit: str) -> list[dict]:
    """One RNG per seed, deterministic series order, both models per series."""
    config = CONFIGS[step]
    rows = []
    if not cases or len({c["series_id"] for c in cases}) != len(cases):
        raise ValueError("expected nonempty cases with unique series ids")
    for seed in config["seeds"]:
        rng = np.random.default_rng(seed)
        for case in sorted(cases, key=lambda c: (c["article_id"], c["series_id"])):
            started = time.monotonic()
            sampled = sample_case(case, seed=seed, draws=config["draws"], rng=rng)
            elapsed = round(time.monotonic() - started, 6)
            rows.extend({**row, "step": step, "git_commit": git_commit, "series_elapsed_seconds": elapsed} for row in sampled)
    return rows


def interval(values: list[float], *, bounds: tuple[float, float]) -> tuple[float, float, float, float]:
    """Mean and 95% t interval across seeds, intersected with the metric range."""
    n = len(values)
    if n != 5 or any(not math.isfinite(v) or not bounds[0] <= v <= bounds[1] for v in values):
        raise ValueError("full inference requires five finite per-seed estimates in range")
    mean = math.fsum(values) / n
    se = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / (n - 1) / n)
    margin = float(t.ppf(.975, n - 1)) * se
    return mean, max(bounds[0], mean - margin), min(bounds[1], mean + margin), se


def holm(pvalues: list[float]) -> list[float]:
    """Holm adjusted p values across the entire series × model family."""
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("p values must be finite probabilities")
    adjusted, largest = [0.] * len(pvalues), 0.
    for rank, i in enumerate(sorted(range(len(pvalues)), key=lambda i: (pvalues[i], i))):
        largest = max(largest, min(1., (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = largest
    return adjusted


def summarize(rows: list[dict]) -> list[dict]:
    """Evaluate fixed practical/significance/stability rules, including negative Δ."""
    if not rows or any(r["step"] != "full" or r["draws"] != 1000 for r in rows):
        raise ValueError("inference is only defined for the full 1000-draw step")
    groups = {}
    for row in rows:
        groups.setdefault((row["series_id"], row["model"]), []).append(row)
    result = []
    for (sid, model), group in sorted(groups.items()):
        group.sort(key=lambda r: r["seed"])
        if [r["seed"] for r in group] != list(range(5)) or len({r["shape"] for r in group}) != 1:
            raise ValueError("each series/model needs seeds 0–4 and one original shape")
        stability, slo, shi, _ = interval([r["stability"] for r in group], bounds=(0, 1))
        baseline, blo, bhi, _ = interval([r["baseline_share"] for r in group], bounds=(0, 1))
        delta, dlo, dhi, se = interval([r["delta"] for r in group], bounds=(-1, 1))
        # Round the exact aggregate count ratio once, so the practical .20
        # boundary cannot be lost to averaging rounded per-seed proportions.
        delta = sum(r["observed_hits"] - r["baseline_hits"] for r in group) / 5000
        if se == 0:
            # Explicit limiting convention, not NaN or a hidden epsilon.
            pvalue = 0. if delta > 0 else 1.
        else:
            pvalue = float(t.sf(delta / se, 4))
        result.append({
            "article_id": group[0]["article_id"], "series_id": sid, "model": model,
            "shape": group[0]["shape"], "n_seeds": 5, "draws_per_seed": 1000,
            "stability": stability, "stability_ci95_low": slo, "stability_ci95_high": shi,
            "baseline_share": baseline, "baseline_ci95_low": blo, "baseline_ci95_high": bhi,
            "delta": delta, "delta_ci95_low": dlo, "delta_ci95_high": dhi,
            "delta_standard_error": se, "zero_between_seed_variance": se == 0,
            "p_one_sided": pvalue, "stable": slo >= .80,
        })
    families = {}
    for sid, model in groups:
        families.setdefault(sid, set()).add(model)
    if any(models != set(MODELS) for models in families.values()):
        raise ValueError("Holm family must include both models for every series")
    for row, adjusted in zip(result, holm([r["p_one_sided"] for r in result]), strict=True):
        row["p_holm"] = adjusted
        row["supported"] = adjusted < .05 and row["delta"] >= .20
        row["verdict"] = "supported" if row["supported"] else "not distinguishable from no dependence"
    return result
