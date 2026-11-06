# Method: verifying the series shapes of ablation_db data

Here, “code” means the Python tools `tools/series.py` and
`tools/ablation_db.py`: they read a fixed database snapshot, group experiments
with compatible stated conditions into nanoparticle-size-versus-fluence
(or pulse-energy) series, and classify each as flat, increasing, decreasing, peak, valley
or irregular, accounting for size errors. The verifier checks that these tools
implement the specified rules correctly; a resampling experiment then measures
how sensitive their classifications are to the assumed size errors. Neither
part verifies the extraction of textual claims or the correctness of the
curated database values.

Sections 0–10 follow the course template `METHOD_TEMPLATE.md` (week 6).
Sections 1–7 were fixed before the first run; any subsequent curator-authorized
revision is disclosed in §9. Sections 8–10 are filled as work goes.
This file names no database values except the reference article 80094,
whose shapes `checks/results_spec.md` §7.5 already states.

## 0. Passport

| Field | Value |
|---|---|
| Task | check the code that groups ablation_db experiments into size-versus-fluence series and gives each series a shape (`results_spec.md` §2–§3), and measure how stable each shape is under the size errors |
| Discipline | materials science (laser ablation in liquids) |
| Verifier type | property tests and a data contract |
| Method recorded | 2026-10-27, before the first run |
| Git tag | `exp-verifier`; the submission is tagged `hw2` |

## 1. Idea

- **Question:** does the code compute the series and shapes that
  `results_spec.md` §2–§3 define, and would a series' shape, and so its
  agreement with a claim, survive a re-measurement within the stated errors?
- **Hypothesis:** the code holds every property in §5. Shapes resting on
  size changes much larger than the errors are stable; shapes resting on
  changes near the error limit, such as 80094-s2 (`peak` / `flat`), are not.
- **Answer:** the verifier's verdict (exit code 0 or 1); for each series,
  its shape under both error models, the share of resampled draws that
  keep that shape with a 95 % interval, and the difference from the
  no-dependence baseline (§7).
- **Known before this file was written:** a sketch of the shape rule
  resampled 80094-s2 (sizes as in the spec's reference case, not from the
  snapshot) and kept `peak` (primary) in about 31 % of draws and `flat`
  (lenient) in about 29 %; a rough grouping of a test export found about
  9 series in 6 articles. No shape was computed from the snapshot.

## 2. Setup

| What | Value |
|---|---|
| Varied | error model: `primary` (fallback 0.10 × size) and `lenient` (0.20 × size); in resampling, the noise draw (seed) |
| Fixed | the snapshot (§3), the series compatibility rules (§3 below and §2 of the spec), the anchor-walk rule (§3 of the spec), the noise model (§7.2) |
| Measured | shape (one of six names); stability = share of draws whose shape equals the series' shape on the unperturbed data (0–1); Δ = stability − baseline share (−1 to 1) |
| Baseline | the same series with every size replaced by the error-weighted mean of its sizes: no dependence on fluence, same x and errors |

## 3. Data

| What | Value |
|---|---|
| Source | ablation_db (curated database of laser-ablation experiments), read-only account, exported with `ablation_db snapshot` |
| Version | `data/ablation_snapshot.json`, SHA-256 `c5380620d896237ad655bfde0ce166d3f638b84a3e9b0b996cc09226f6b8303f`; format 1, schema change `0095`, metadata hash `c129120a031257f6e46e3a46d0762bef`, exported 2026-10-27T11:18:47Z from live; committed in `9db97cf` |
| Export options | gold as the sole target material, completed articles only; no manufacturers, instrument details, measurement settings or provenance; compact materials; nulls omitted |
| Size | 19 articles, 118 experiments, 753 KB |
| Split | none: every usable series is evaluated; histogram modes, when requested, are fitted locally with a lognormal distribution |

### Series key

Series are formed from experiments of individual articles. The experiments additionally must share the following paramters to form a series:

| Part | Exported fields compared |
|---|---|
| Laser and optics | Laser description, wavelength, pulse duration, repetition rate, output beam diameter, polarization, spatial mode and ordered beam path |
| Ablation setup | Complete `ablation` record: target, target position, liquid-layer thickness, scanning parameters and batch/flow settings |
| Materials and media | Synthesis medium, feedstock colloid identities and fractions, and the selected product's liquid medium |
| Beam entrance and gas | Entrance material, free-surface entrance flag, pumping gas, flow rate, duration and whether pumping occurs during processing |
| Post-processing | Complete ordered protocol and its parameters |


A missing or null scalar condition or optional condition is a
wildcard matching any stated value. Missing details inside listed records
are wildcards too. **Absent, null or empty condition collections mean none**,
not unknown: no feedstock does not match a nonempty feedstock list. Beam-path
and post-processing order is significant.

**Data contract**, checked by `checks/verifier/contract.py` on the snapshot
and on the series built from it. Each rule returns named violations; an
unknown violation fails the check.

| Rule | How it is checked | Violation |
|---|---|---|
| header: format 1, the export options above | compare with constants | `header_mismatch` |
| experiment ids unique; each experiment's `article_id` is its article's | count and compare | `duplicate_experiment`, `wrong_article` |
| every ablation target is gold only | resolve the target in `shared` | `non_gold_target` |
| units: fluence J/cm², pulse energy µJ, spot diameter µm, sizes nm | the snapshot's `units` table | `unit_mismatch` |
| ranges: finite values; 0 < fluence ≤ 1000 J/cm², 0 < energy ≤ 10⁶ µJ, size > 0, SD ≥ 0; no upper bound on sizes or distribution-axis coordinates | per value | `out_of_range` |
| distribution bins ascending, not overlapping, counts ≥ 0 with a positive sum | per distribution | `bad_bins` |
| a series has ≥ 2 distinct x, all fluence or all energy, never mixed | per series | `mixed_x`, `short_series` |
| members share the article and exact measurement identity and have pairwise-compatible fixed conditions (Series key above) | independently reconstruct profiles and check every pair, not equality of serialized keys | `key_mismatch` |
| an experiment occurs at most once within each series; overlap between series is allowed | count within each series | `duplicate_point` |

**Known violations:** no accepted exceptions. The initial size-upper-bound
failures and the curator's subsequent removal of that rule are recorded in §9.
An experiment that cannot join a series (no varied x or mixed x) is dropped
with a note, not a violation.

## 4. Code and environment

- Code: pure functions in `tools/series.py` (condition compatibility,
  overlapping groups, x, size, size_err, shape); `tools/ablation_db.py` reads
  the snapshot and serves the
  `results_spec.md` §4 functions, including `get_series(id, model="primary")`
  and `list_exclusions(article_id)`. No database connection.
- Tool implementation tests: `.venv/bin/python -m pytest tools/tests -q`.
  These are separate from the HW2 verifier and planned resampling runs.
- Verifier commands: `.venv/bin/python checks/verifier/run.py dry`, then
  `.venv/bin/python -m pytest checks/verifier -q`.
  Resampling: `.venv/bin/python checks/verifier/run.py smoke`, then
  `.venv/bin/python checks/verifier/run.py full` (§6). Both run the contract and
  property/reference preflight; full requires a passing smoke manifest and
  complete CSV with matching snapshot and source hashes.
- Implementation environment: Python 3.12.3; `requirements.txt` pins the
  installed numpy 2.5.3, scipy 1.18.1, pytest 9.1.1, pandas 3.0.6,
  PyYAML 6.0.3 and pypdf 6.19.0. At verifier implementation, Hypothesis
  6.170.15 and jsonschema 4.26.0 were installed and pinned along with
  their new dependencies; this environment realization is recorded in §9.
- Seeds: resampling seeds 0–4, each a `numpy.random.default_rng(seed)`;
  hypothesis runs with `derandomize=True`, so its examples repeat.

## 5. Verifier

- **Checks:** the properties below, the data contract (§3), and the
  reference case: 80094-s1 `increasing` / `increasing`, 80094-s2 `peak` /
  `flat` (`results_spec.md` §7.5).
- **Command:** `.venv/bin/python -m pytest checks/verifier -q`.
- **Location:** `checks/verifier/`, read-only for the agent (ban 1).
  Outputs go to `results/verifier/`, already covered by ban 3 because
  they hold shapes. Tool implementation tests do not write verifier outputs.
- **Does not check:** that the database values match the articles
  (curation); claim extraction (`check.py` does); whether the fallback
  fractions 0.10 and 0.20 are right; anything the snapshot left out
  (provenance, measurement settings).

| # | Property | Why it must hold | Test |
|---|---|---|---|
| 1 | shuffling the points does not change the shape | the rule sorts by x first | `test_point_order_does_not_matter` |
| 2 | multiplying sizes and errors by 2ᵏ does not change the shape | a shape cannot depend on the size unit | `test_size_unit_does_not_matter` |
| 3 | mirroring sizes (c − size, errors kept) swaps increasing ↔ decreasing and peak ↔ valley | the rule treats growth and shrinkage alike | `test_mirror_swaps_direction` |
| 4 | a strictly increasing map of x does not change the shape | x enters only through its order | `test_only_order_of_x_matters` |
| 5 | if `primary` gives `flat`, `lenient` gives `flat` | lenient errors are never smaller, and a flat walk never moves its anchor | `test_lenient_flat_when_primary_flat` |
| 6 | appending a copy of the last point at a larger x does not change the shape | a copy is never farther than the error from the anchor | `test_repeated_last_point_changes_nothing` |
| 7 | the number-weighted mean of a distribution lies within its bin edges and does not change when all counts are scaled | digitized counts have an arbitrary scale | `test_distribution_mean` |
| 8 | the error is the matching stored SE if any, else SD/√N for a mean with explicitly reported N, else the fallback | `results_spec.md` §2 priority | `test_error_priority` |
| 9 | generated series have exact article/measurement identity, pairwise-compatible fixed conditions and no repeated experiment within a series; reordering inputs preserves the groups | unknowns may overlap but never bridge conflicting stated values; grouping is not a partition | `test_series_compatibility` |

## 6. Depth steps

| Step | Command | Condition to go on | Time |
|---|---|---|---|
| Dry run | `run.py dry`: read the snapshot, run the contract, list series (ids and point counts, no shapes) | no unknown violation; 80094 gives two series of 6 points on energy | seconds |
| Short check | `pytest checks/verifier -q` | every property and the reference case pass | under a minute |
| Small sweep | `run.py smoke`: seed 0, 100 draws, all series | every series resampled, one log row per series and model | seconds |
| Full run | `run.py full`: seeds 0–4, 1000 draws each, both models, observed and baseline | the acceptance rule (§7) evaluated, outputs in `results/verifier/` | about a minute (estimate the full run from the smoke step's time) |

## 7. Acceptance rule (written before the first run)

1. **Metric:** for each series and error model, stability (share of
   draws keeping the series' shape) and Δ = stability − baseline share of
   that same shape; both unitless: stability ranges from 0 to 1 and Δ from
   −1 to 1 (notation clarified after the run; see §9).
2. **Repeats and noise:** 5 seeds (0–4) × 1000 draws. A draw moves each
   size by σ·z with z ~ N(0, 1), σ the size's `primary` error (stored, or
   0.10 × size). The same z feeds both error models and the baseline, so
   all comparisons are paired.
3. **Comparison:** per series and model, the 5 per-seed values of Δ;
   mean, 95 % t-interval (df = 4), one-sided paired t-test of Δ > 0;
   Holm correction over all series × models; significance level 0.05.
4. **Practical threshold:** Δ ≥ 0.20, i.e. the data keep their shape at
   least one draw in five more often than data without any dependence
   would. A shape is *stable* when the lower bound of its stability
   interval is ≥ 0.80. The thresholds are a judgement, not a measured
   noise level.
5. **Verdict per series:** *supported* when Holm-adjusted p < 0.05 and
   mean Δ ≥ 0.20; otherwise *not distinguishable from no dependence*. A
   `flat` shape is expected to be not distinguishable: that is consistent
   with a `no_effect` claim, not a failure. Chosen by the mean over seeds,
   never by the best seed.
6. **Data for the conclusion:** every series of the snapshot in §3.
7. **Stop:** the contract finds an unknown violation, a property fails,
   or the reference case differs: stop, record it in §9, fix before
   going on.

## 8. Budget

- Computation: about 9 series × 2 models × 2 (data, baseline) × 5000
  draws; seconds to a minute.
- Agent: the course agent takes no part in this check. Code written with
  an assistant is marked in the report's authorship table.

## 9. Log and caught errors

- Results: `results/verifier/runs.csv` (one row per step, seed, model and
  series: shape, stability, baseline share, git commit, time);
  `results/verifier/caught_error_before.txt` and `…_after.txt`.
- Run notes: `diary.md`.

| Date | What was wrong | Caught by | Fixed by | Before / after |
|---|---|---|---|---|
| 2026-11-06 | Deliberate mutation on `bug/point-order`: removed sorting from the shape function. A two-point permutation changed increasing to decreasing. This is a planted defect, not a discovered error in main. | Existing §5 property 1, unchanged from baseline `776a2fe`; Hypothesis reduced the failing input. | Compared the faulty commit `cf188ed` with the original correct parent on main. No new repair or mutation was applied to main; the bug branch remains separate. | `results/verifier/caught_error_before.txt` exits 1; `caught_error_after.txt` exits 0. Full verifier: 82 pass; regression: 267 pass. Commands, patch and source/artifact fingerprints in `caught_error.md` and `caught_error_manifest.json`. |
| 2026-11-06 | First completed dry check reported three `out_of_range` violations from the former size upper bound, including stored axis coordinates with zero density. Short check and later steps stopped. | `checks/verifier/run.py dry` | Curator explicitly requested removing the size upper-bound check, not adding data-specific exceptions. Removed it for scalar sizes, selected representative sizes, histogram boundaries and curve axes; finite-value/positivity checks retained. Snapshot unchanged. This is a disclosed post-run revision to §3. | Original failure preserved in `results/verifier/dry_before_size_bound_removal.json`; corrected dry passes with zero violations. Short check: 65 tests pass, including the nine properties and reference. See `dry.json`, `short_check.txt` and `attempts.md` in `results/verifier/`. |

Verifier implementation dependencies were installed and pinned on 2026-11-06:
Hypothesis 6.170.15 and jsonschema 4.26.0 (plus their dependencies in
`requirements.txt`). This realizes the planned environment in §4. The only
post-run scientific-method revision so far is the curator-authorized removal
of the size upper bound described above; no fallback fractions, shape rules
or resampling acceptance thresholds have been changed. Implementation status
and environment wording in §4–§5 now reflect the installed verifier. The
verifier/resampling code was committed as `776a2fe` before the deliberate-error
demonstration. The demonstration evidence/documentation was committed as
`c50a2ff`; the curated HW2 report/package was committed as `bbd6f39`.
The subsequent fresh-environment evidence/status updates are included in this
submission package.
The initial verifier regression suite passed 250 tests.
Subsequent resampling implementation tests and execution status are recorded
in `results/verifier/attempts.md`; the claim-comparison pipeline remains disabled.

Before the first implemented resampling run, the following execution
conventions were recorded (no threshold or noise-distribution change):

- Retain the original primary and lenient error arrays for every draw and
  baseline classification; never recompute fallback errors from perturbed sizes.
  Draw once with the original primary σ and reuse z across models and baseline.
  Normal draws are not truncated, clipped or rejected when sizes become
  nonpositive; their frequency is logged. The shape function accepts signed sizes.
- Use one constant baseline centre per series, weighted by inverse original
  primary variance. Its precise centre cannot affect the anchor-walk shape:
  translation by a constant cancels all differences. If a future series has
  zero primary error, stop rather than invent a baseline weighting convention.
- For each seed, iterate series in stable ID order using one `default_rng(seed)`.
  CIs for mean stability, baseline share and Δ are 95% t-intervals across the five
  per-seed estimates (df = 4), intersected with the metric's legal range. They
  quantify Monte Carlo variation under the assumed model, not experimental
  repeat-measurement uncertainty. Smoke has no significance verdict or CI.
- For zero between-seed variance in Δ, use the t-test limiting convention:
  p = 0 for positive constant Δ, otherwise p = 1; retain a diagnostic flag.
  Holm adjustment includes every series × both models, without filtering.
- Corrected the notation in §2: a difference of two shares ranges from −1 to 1,
  not 0 to 1. Negative Δ is retained, not clipped; the Δ ≥ 0.20 criterion is unchanged.
  During report packaging, corrected the remaining duplicate 0–1 notation in §7.1
  to match §2 and the existing signed implementation. This is not a threshold,
  inference or experiment change.

HW2 report/package checkpoint (2026-11-06): `results/verifier/REPORT.md` records
results, a subgoal tree, attempt history, limitations and authorship. The initial
METHOD draft was generated with DeepSeek flash 4 and edited by Anton, who
subsequently identified the model while curating the report.
`results/verifier/report_metrics.csv` adds sample SD across the original five
per-seed estimates without changing the original summary or inference.
A clean local clone of `c50a2ff` passed the verifier and dry/smoke/full sequence;
the scientific rows and summary reproduced exactly. A separate bug worktree
failed the existing order property. Commands, outputs and scope are recorded in
`results/verifier/reproduction/`. The original sweep source hashes match
`776a2fe` exactly; later documentation does not retroactively change those runs.
That initial reproduction reused the installed pinned venv. Subsequently,
Anton installed requirements in a new venv of a clean local clone at `bbd6f39`.
The verifier, full regression, gated experiment and planted-error detection
were repeated with that environment; the scientific outputs reproduced exactly.
Evidence and package inventory: `results/verifier/fresh_environment/`.
No method/threshold/code/data changes were made during this reproduction.
Release identifiers are `exp-verifier` at `776a2fe` and `hw2` at the submission
commit. Remote publication and instructor access are separate operator steps.

## 10. Limitations

- The snapshot has no provenance: sizes read from figures, and x values
  the curator assumed, look the same as reported values.
- By the curator's toy-project decision, all size curves, including DLS,
  are treated as ordinary densities over stored diameter in nm. Mean is
  `∫d*y dd / ∫y dd`: no ln-d integration, Jacobian or exponentiation of x.
  This overrides the snapshot schema's DLS y convention, not its x units.
- By the curator's decision, scalar `z_average` is grouped as `mean`;
  missing scalar statistic is assumed to be mean. Original labels and
  assumptions remain on the points; quantity, technique, weighting and
  component remain distinct. Nothing in the database is rewritten.
- Histogram mode is the global maximum of a fitted lognormal density,
  never the tallest bin. The fit uses stored bar extents as bin limits;
  those can differ from actual bin boundaries. Fit failures are reported,
  and residuals are retained; fitting does not establish unimodality.
- Unsupported statistics, ambiguous measurements, duplicate x and groups
  without a common storage duration are explicitly excluded. Counts
  depend on these rules; the historical estimate of nine series is not
  an acceptance target.
- Missing condition details are wildcards and spot diameter is ignored.
  This may combine physically different experiments. Absent collections still
  mean none, and conflicting stated values are never joined transitively.
- Series may share experiments; they are not independent observations.
  `overlapping_series` notes expose this reuse, but do not remove dependence.
- The noise model assumes independent normal errors. Resampling measures
  sensitivity under the assumed noise model; it does not establish
  repeat-measurement stability.
- SD/√N is used only for means with an explicit reported particle count;
  it counts particle-sampling error only. It is not the uncertainty of a
  fitted mode or median. One colloid per point hides synthesis scatter.
- The fallback fractions (0.10, 0.20) and the thresholds in §7 are
  choices, not measurements.
- About 9 series: enough to test the code, too few for a strong sign test
  in `summary.json`.
- The check says nothing about whether the database matches the articles,
  or whether the agent's claims are right.
