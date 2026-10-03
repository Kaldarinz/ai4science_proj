# Results specification

Defines the three files in `results/` and how every value in them is
derived. `checks/check.py` enforces it. Change this file and `check.py`
together, never one alone.

## 1. Format

- CSV: UTF-8, comma separator, header row, `.` as decimal point, no index
  column, empty field for a missing value. JSON: UTF-8, `null` for a missing
  value.
- Rows are sorted by `series_id`, then by `x` in `points.csv`.
- `series_id` is `<article_id>-<k>`, where series of one article are numbered
  from 1 in order of their smallest `experiment_id`.

## 2. Series

A series is the set of experiments of one article that share all of:

- target: gold as the only constituent;
- laser: wavelength, pulse duration, repetition rate;
- medium: liquid, additives with their concentrations, feedstock colloid;
- centrifugation protocol (or its absence);
- size measurement: quantity, statistic, technique;

and differ in fluence or pulse energy. A series has at least 2 points, and
its `x` values are distinct. Two experiments with the same `x` in one series
mean the series is not well defined: stop and ask the human.

All points of a series use the same colloid storage duration: the shortest
one at which every experiment of the series has a size. If there is none,
stop and ask the human.

## 3. Derivations

**x.** Fluence (J/cm²) when every point of the series has it. Otherwise
pulse energy (µJ), only if the spot diameter is equal for all points or
missing for all points; in the second case write `spot unknown` in `notes`.
Mixed spot diameters: stop and ask the human.

**size.** The stored scalar for the series' statistic. If the experiment
stores only a size distribution, compute it from the distribution: the
number-weighted mean `Σ nᵢ·cᵢ / Σ nᵢ`, with `cᵢ` the centre of bin `i` taken
from its stored bar edges. A distribution not weighted by number: stop and
ask the human.

**size_err**, the standard error of `size`, the first that applies:

| `err_source` | Rule |
|---|---|
| `reported_se` | A standard error stored with the size. |
| `sd_over_sqrt_n` | A stored standard deviation, or one computed from a distribution with absolute counts, divided by √N, where N is the number of particles measured. |
| `fallback` | 0.10 × `size`. Also when only an SD is known and N is not. |

**shape.** Take the points in order of increasing `x`. Set the anchor to the
first point. For each next point, a change is counted when
`|size − anchor_size| > √(size_err² + anchor_err²)`; the counted change's
sign is recorded only if it differs from the last recorded sign, and the
point becomes the new anchor. The recorded signs give the shape:

| Recorded signs | `shape` |
|---|---|
| none | `flat` |
| + | `increasing` |
| − | `decreasing` |
| +, − | `peak` |
| −, + | `valley` |
| three or more | `irregular` |

**spearman_rho.** `scipy.stats.spearmanr(x, size)`; empty when undefined
(all sizes equal).

**pulse_duration_class.** `fs` below 1e3 fs, `ps` from 1e3 to below 1e6 fs,
`ns` from 1e6 fs.

**medium_class**, the first that applies:

| Value | Medium |
|---|---|
| `colloid` | Contains a feedstock colloid. |
| `water` | Water with no additives. |
| `aqueous` | Water with additives (salts, surfactants, ligands). |
| `organic` | One organic liquid, with or without additives. |
| `other` | Anything else, such as liquid mixtures. |

## 4. `results/points.csv`

One row per point of every series.

| Column | Type | Unit | Rule |
|---|---|---|---|
| `series_id` | str | — | §1 |
| `experiment_id` | int | — | as in `data/` |
| `x` | float > 0 | J/cm² or µJ | §3, unit given by `x_quantity` of the series |
| `size` | float > 0 | nm | §3 |
| `size_err` | float > 0 | nm | §3 |
| `err_source` | str | — | `reported_se`, `sd_over_sqrt_n`, `fallback` |

## 5. `results/series.csv`

One row per series.

| Column | Type | Unit | Rule |
|---|---|---|---|
| `article_id` | int | — | as in `data/` |
| `series_id` | str | — | §1 |
| `n_points` | int ≥ 2 | — | rows of this series in `points.csv` |
| `x_quantity` | str | — | `fluence_j_per_cm2` or `pulse_energy_uj` |
| `size_quantity` | str | — | as stored, e.g. `geometric_diameter` |
| `size_statistic` | str | — | as stored, e.g. `mean`, `median`, `mode` |
| `size_technique` | str | — | as stored, e.g. `TEM`, `DLS` |
| `size_source` | str | — | `stored`, `computed` (from a distribution), `mixed` |
| `storage_duration_h` | float ≥ 0 | h | §2; empty when not stated |
| `shape` | str | — | §3 |
| `spearman_rho` | float in [−1, 1] | — | §3 |
| `pulse_duration_fs` | float > 0 | fs | as stored |
| `pulse_duration_class` | str | — | §3 |
| `wavelength_nm` | float > 0 | nm | as stored |
| `medium_class` | str | — | §3 |
| `notes` | str | — | excluded experiments with reasons; `spot unknown`; sizes stored as a range midpoint |

## 6. `results/sign_test.json`

```json
{
  "overall": {"counts": {...}, "n_test": 0, "p_value": null},
  "by_pulse_duration_class": {"fs": {...}, "ps": {...}, "ns": {...}},
  "by_medium_class": {"water": {...}, "...": {...}}
}
```

Every group has the same three keys:

- `counts`: the number of series of each of the six shapes, all six present;
- `n_test`: `increasing + decreasing`;
- `p_value`: `scipy.stats.binomtest(increasing, n_test, 0.5,
  alternative="greater").pvalue`; `null` when `n_test` is 0.

Groups with no series are omitted.

## 7. What `check.py` verifies

1. The files exist, parse, and have exactly the columns and keys above.
2. Every value meets its type, unit range and allowed values.
3. `series_id` sets of the two CSV files are equal; `n_points` matches.
4. `shape`, `spearman_rho` and the sign test recomputed from `points.csv`
   equal the stored values.
5. The reference series in `checks/expected_series.csv` match.
