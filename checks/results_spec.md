# Results specification

Defines the database tools' output, `results/comparison.csv` and
`results/summary.json`, and what `checks/check.py` verifies. Claims are
defined in `claims_spec.md`. Change this file and `check.py` together, never
one alone.

## 1. Format

- CSV: UTF-8, comma separator, header row, `.` as decimal point, no index
  column, empty field for a missing value, every line ending with a
  newline (the last one too). Fields containing a comma, quote or newline
  are double-quoted (RFC 4180); every row has as many fields as the header.
- JSON: UTF-8, `null` for a missing value.
- `series_id` is `<article_id>-s<k>`, series of one article numbered from 1
  in order of their smallest `experiment_id`.

## 2. Series (produced by `tools/`)

A series is the set of experiments of one article that share all of:

- target: gold as the only constituent;
- laser: wavelength, pulse duration, repetition rate;
- medium: liquid, additives with their concentrations, feedstock colloid;
- centrifugation protocol (or its absence);
- size measurement: quantity, statistic, technique;

and differ in fluence or pulse energy. A series has at least 2 points with
distinct `x`. All points use the same colloid storage duration: the shortest
at which every experiment of the series has a size.

**x.** Fluence (J/cm²) when every point has it; otherwise pulse energy (µJ),
when the spot diameter is equal for all points or missing for all.

**size.** The stored scalar for the series' statistic; if only a size
distribution is stored, its number-weighted mean `Σ nᵢ·cᵢ / Σ nᵢ`, with `cᵢ`
the centre of bin `i` from its stored bar edges.

**size_err**, the first that applies: a stored standard error
(`reported_se`); a standard deviation divided by √N, N the number of
particles measured (`sd_over_sqrt_n`); otherwise `fallback`, whose value
depends on the error model (§3).

**medium_class**, the first that applies: `colloid` (contains a feedstock
colloid), `water` (no additives), `aqueous` (water with additives),
`organic` (one organic liquid), `other`.

**pulse_duration_class.** `fs` below 1e3 fs, `ps` below 1e6 fs, else `ns`.

## 3. Shape

Two error models differ only in the fallback error: `primary` uses
0.10 × `size`, `lenient` uses 0.20 × `size`. Each series gets a shape under
each model.

Take the points in order of increasing `x`; the anchor is the first point.
For each next point, a change is counted when
`|size − anchor_size| > √(size_err² + anchor_err²)`; its sign is recorded if
it differs from the last recorded sign, and the point becomes the anchor.

| Recorded signs | Shape |
|---|---|
| none | `flat` |
| + | `increasing` |
| − | `decreasing` |
| +, − | `peak` |
| −, + | `valley` |
| three or more | `irregular` |

## 4. Tool contract

`tools/ablation_db.py` is the only access to the database. It reads through
the read-only account and returns plain Python data:

| Function | Returns |
|---|---|
| `find_articles(material="Au")` | list of `{article_id, doi, title, year, n_experiments}` |
| `list_series(article_id)` | list of series rows, columns as in the table below |
| `get_series(series_id)` | `{"series": <row>, "points": [{experiment_id, x, size, size_err, err_source}]}` |

Series row: `article_id, series_id, n_points, x_quantity, size_quantity,
size_statistic, size_technique, size_source, storage_duration_h,
pulse_duration_fs, pulse_duration_class, wavelength_nm, medium_class,
shape_primary, shape_lenient, spearman_rho, notes`.

## 5. `results/comparison.csv`

One row per pair of an `own_data` claim and a series of the same article
whose `medium_class` equals the claim's, or any series of the article when
the claim's is `unspecified`. A claim with no such series gets one row with
an empty `series_id` and the reason in `note`.

| Column | Type | Rule |
|---|---|---|
| `claim_id` | str | from `results/claims.csv` |
| `series_id` | str | §1; empty when unmatched |
| `direction` | str | the claim's |
| `shape_primary`, `shape_lenient` | str | the series' (§3) |
| `agree_primary`, `agree_lenient` | bool | by the table below; empty when unmatched |
| `note` | str | e.g. `article has no curated experiments` |

| `direction` | Agrees with shape |
|---|---|
| `increase` | `increasing` |
| `decrease` | `decreasing` |
| `no_effect` | `flat` |
| `non_monotonic` | `peak`, `valley`, `irregular` |
| `affects` | any shape but `flat` |

## 6. `results/summary.json`

```json
{
  "claims": {"by_basis_and_direction": {"own_data": {"increase": 0, "...": 0}, "cited": {}, "general": {}}},
  "agreement": {"primary": {"n": 0, "agree": 0}, "lenient": {"n": 0, "agree": 0}},
  "series": {
    "primary": {"counts": {}, "n_test": 0, "p_value": null},
    "lenient": {"counts": {}, "n_test": 0, "p_value": null}
  }
}
```

- `by_basis_and_direction`: claim counts, all five directions under each
  basis.
- `agreement`: over matched comparison rows; `n` rows, `agree` of them true.
- `series`: counts of the six shapes over all series; `n_test` is
  `increasing + decreasing`; `p_value` is
  `scipy.stats.binomtest(increasing, n_test, 0.5, alternative="greater").pvalue`,
  `null` when `n_test` is 0.

## 7. What `check.py` verifies

1. Every file parses and has exactly the columns, keys and allowed values
   of the specs.
2. Every PDF in `data/articles/` matches its SHA-256 in `data/files.csv`,
   and every claim's quote is found on its page of its file
   (`claims_spec.md` §4).
3. `comparison.csv` holds exactly the pairs of §5, and its agreement columns
   follow the table.
4. `summary.json` recomputed from the CSV files equals the stored one.
5. Reference article 80094:

| Claim | Series | Shape primary / lenient | Agrees primary / lenient |
|---|---|---|---|
| Au in water, `increase`, `own_data` | `80094-s1` | `increasing` / `increasing` | yes / yes |
| AuSi in Si colloid, `no_effect`, `own_data` | `80094-s2` | `peak` / `flat` | no / yes |

6. With `--gold` only, it prints, and does not fail on, precision and
   recall of the claims against the hand-labelled `checks/claims_gold.csv`,
   matching on `(article_id, variable, direction, basis, medium_class)`.
   The human runs it with `--gold` after the agent's run; the agent never
   does, so its own check cannot tell it how it scored.
