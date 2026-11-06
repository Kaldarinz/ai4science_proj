# Results specification

Defines the database tools' output, `results/comparison.csv` and
`results/summary.json`, and what `checks/check.py` verifies. Claims are
defined in `claims_spec.md`. Change this file, `check.py` and
`ontology.yaml` together, never one alone; `check.py` fails when a value
list here differs from `ontology.yaml`.

## 1. Format

- CSV: UTF-8, comma separator, header row, `.` as decimal point, no index
  column, empty field for a missing value, every line ending with a
  newline (the last one too). Fields containing a comma, quote or newline
  are double-quoted (RFC 4180); every row has as many fields as the header.
- JSON: UTF-8, `null` for a missing value.
- `series_id` is `<article_id>-s<k>`, series of one article numbered from 1
  in order of their smallest `experiment_id`, then quantity, technique,
  statistic, weighting and component (missing labels sort as empty strings),
  then the canonical candidate profiles to break remaining ties.
  IDs describe this snapshot and grouping rules, not a permanent identity.

## 2. Series (produced by `tools/`)

A series contains experiments of one article with a gold-only ablation
target and pairwise-compatible fixed conditions. The profile includes every
exported experiment condition except its ids, product colloids, pulse fluence,
pulse energy, average power and spot diameter. In particular it keeps
scanning, duration, beam path, target, medium, feedstock identity and
fractions, gas, and the full ordered post-processing protocol. Shared
objects are compared by their exported contents, not their surrogate ids;
feedstock colloid ids are retained as identities. Constituent, additive and
feedstock list order is immaterial. The product's liquid medium is also
part of the profile. Compare known scalar values exactly in snapshot units;
missing/null scalar values and optional condition subobjects are wildcards,
including missing details inside listed records. Absent/null/empty condition
collections mean none, not unknown: an absent feedstock, additive, beam-path
or post-processing list cannot match a nonempty one. Collections must have
the same length; unordered lists need a compatible one-to-one matching.

Compatibility is symmetric but not transitive. Within an article and exact
measurement kind/statistic, construct all maximal pairwise-compatible
candidate groups, then apply storage, representation and x selection below.
Do not use connected components: a missing wavelength can join both a
532 nm group and a 1064 nm group but cannot bridge those conflicting values.
**Overlapping series are allowed**, even for the same experiment/kind/statistic;
an experiment occurs at most once within each series. Deduplicate identical
selected series after exclusions. Mark surviving series sharing an
experiment/kind/statistic with `overlapping_series` in `notes`.
`condition_key` is only a canonical profile fingerprint, not an equality
key for wildcard grouping. See also METHOD.md §3, Series key.

Size measurement kinds are separated by quantity, technique, weighting,
component and normalized location statistic. After the statistic normalization
below, these labels are exact, not wildcard conditions: an absent label does
not match a stated one. Whole-particle and component sizes never mix, nor do
number- and intensity-weighted sizes. Supported
size quantities are geometric diameter, hydrodynamic diameter and particle
size; unrelated spectra/properties are not size measurements.

**Statistic selection.** Within each article and measurement kind (before
adding statistic to the key), request all scalar location statistics:
`mean`, `mode` (also called `peak`) and `median`. If none occur, request
`mean`. Widths such as SD and FWHM do not request another series. By the
curator's project assumptions, scalar `z_average` is normalized to `mean`,
and a missing scalar statistic is treated as `mean`; original labels and
these assumptions remain on the points. The snapshot schema normally
requires a statistic. Other scalar size statistics get an explicit
unsupported-statistic diagnostic, not a fabricated conversion.

All members use the shortest storage duration available in every member
for this kind/statistic. Null is a distinct duration, not zero, and is
chosen only if no common numeric duration exists. Do not split or salvage
a group with no common duration. At that duration, prefer a matching
scalar, then a histogram, then a curve. Multiple candidates at the same
priority are ambiguous and that experiment is excluded with a diagnostic.

**x.** Prefer fluence (J/cm²) when every member has it; otherwise use pulse
energy (µJ) when every member has it. Spot diameter is excluded and imposes
no additional condition, whether stated, missing or varying, for either
x choice. Never derive fluence. Missing x is not a condition wildcard. A
series needs at least two distinct x values; repeated x values are
excluded as an ambiguous series rather than averaged or ordered
arbitrarily. Unusable groups and points are returned by `list_exclusions`.

**size.** Use the matching scalar when present. For histograms, mean is
`Σ nᵢ·cᵢ / Σ nᵢ`, with cᵢ the stored bar centre; median interpolates within
the bar containing half of the counts. Mode MUST come from a fitted
zero-location lognormal, not the tallest bin: fit amplitude, log-scale
and log-width by least squares against the integrated mass in each stored
bar extent, then take its global density maximum `exp(mu - sigma²)`.
Require at least three positive bars; report failed/degenerate fits.
The fit residual is retained on the point. Stored bar extents can differ
from true bin boundaries; this is a fitting limitation.

For curves, sort a descending x array into ascending order, require
strictly monotone nonnegative x, finite nonnegative y and positive area. Mean and SD
use trapezoidal integration; median is the half-area point of the
piecewise-linear curve; mode is the smallest x attaining the global y
maximum. Treat ALL size-curve y values, including DLS, as ordinary
densities over the stored diameter d: mean = `∫d*y dd / ∫y dd`.
No logarithmic integration, Jacobian or exponentiation of x is used.
This deliberate toy-project approximation overrides the snapshot schema's
DLS y convention; it does not change the snapshot or database.

**size_err**, the first applicable: a matching stored SE (`reported_se`),
then SD/√N for a mean (`sd_over_sqrt_n`), otherwise the model's fallback
(§3). The current snapshot has no SE statistic; the priority is retained
for future inputs and pure-function tests. Use a matching scalar SD, else
the selected histogram/curve's computed SD. N must be explicitly stored
as `particles_counted` on a matching histogram; never use the sum of
arbitrary digitized counts as N. Do not turn FWHM into SD. SD/√N does not
apply to a median or fitted mode. Preserve source, colloid id, original
statistic, SD, N, error source and assumptions on every returned point.

**medium_class**, the first that applies: `colloid` (contains a feedstock
colloid), `water` (one water constituent and no additives), `aqueous`
(water with additives), `organic` (one non-water liquid), `other`. Use stated
synthesis-medium information across selected members, not just the first
member if its condition details are missing.

**pulse_duration_class.** `fs` below 1e3 fs, `ps` below 1e6 fs, else `ns`.
Series wavelength and pulse duration use the stated value among selected
members; null only if all members lack it. These scalar fields cannot have
conflicting stated values in one compatible series. Original point/snapshot
values are not imputed.

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

`tools/ablation_db.py` reads only the committed
`data/ablation_snapshot.json`, never a database or credentials, and returns
plain JSON-ready Python data. Its pure calculations live in `tools/series.py`.

| Function | Returns |
|---|---|
| `find_articles(material="Au")` | list of `{article_id, doi, title, year, n_experiments}`, including articles with no usable series; missing DOI/year are null |
| `list_series(article_id)` | list of series rows, columns below; `[]` for an article absent from the snapshot |
| `get_series(series_id, model="primary")` | `{"series": <row>, "points": [...]}` with point errors under the requested model |
| `list_exclusions(article_id)` | list of `{article_id, experiment_ids, reason, detail}`, including unusable measurements/groups |

Series row: `article_id, series_id, n_points, x_quantity, size_quantity,
size_statistic, size_technique, size_weighting, size_component, size_source,
storage_duration_h, pulse_duration_fs, pulse_duration_class, wavelength_nm,
medium_class, shape_primary, shape_lenient, spearman_rho, notes`.
`size_source` is `scalar`, `histogram`, `curve` or `mixed`. Undefined
Spearman correlation (constant sizes) is null, never NaN.

Points are sorted by x and contain `experiment_id, colloid_id, x, size,
size_err, err_source, size_source, original_statistic, sd, particles_counted,
assumptions, fit_residual`. Derived points have null original statistic;
fit residual is null except for histogram mode. Optional metadata stays
null rather than being invented.

`SnapshotTools(path)` reads a particular snapshot once for callers/tests
that need a fixed view. Module-level convenience calls load the default
snapshot afresh: there is no stale global cache. Returned dictionaries are
independent, so mutating a response cannot corrupt subsequent calls.
Only `Au`/`gold` is supported by this gold-only snapshot. Unsupported
material/model or malformed IDs raise ValueError; an unknown well-formed
series ID raises KeyError. Missing/corrupt files and unsupported format or
units fail explicitly, never falling back to another source.

Tool tests: `.venv/bin/python -m pytest tools/tests -q`. These are unit and
adapter integration tests, not the HW2 verifier or resampling experiment.
For a fresh checkout, create a Python 3.12 virtual environment with
`python3.12 -m venv .venv`, then install the pinned tool/test dependencies
with `.venv/bin/python -m pip install -r requirements.txt`. Run commands
from the project root; the course agent cannot install packages itself.

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

6. With `--gold` only, it prints, and does not fail on, the hits of the
   claims against the hand-labelled `checks/claims_gold.csv`, matching on
   `(article_id, variable, direction, basis, medium_class)`, as raw
   precision and recall k/n for each set of `checks/gold_articles.csv`:
   `test` (labelled before any agent run, scored on its first run that
   writes `claims.csv` or `no_claims.csv` rows; aborted runs are not
   scored) and `dev` (a spec or memory change was prompted by its errors).
   Only `test` counts for error rates. The human runs it with `--gold`
   after the agent's run; the agent never does, so its own check cannot
   tell it how it scored. Which articles are labelled, and their set,
   stand only in `checks/gold_articles.csv`: `diary.md`, `memory/` and
   commit messages never name them, since the agent reads those.
