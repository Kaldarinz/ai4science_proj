# Method: verifying the series shapes of ablation_db data

Sections 0–10 follow the course template `METHOD_TEMPLATE.md` (week 6).
Sections 1–7 are fixed before the first run; 8–10 are filled as work goes.
This file names no database values except the reference article 80094,
whose shapes `checks/results_spec.md` §7.5 already states.

## 0. Passport

| Field | Value |
|---|---|
| Task | check the code that groups ablation_db experiments into size-versus-fluence series and gives each series a shape (`results_spec.md` §2–§3), and measure how stable each shape is under the size errors |
| Discipline | materials science (laser ablation in liquids, gold nanoparticles) |
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
| Fixed | the snapshot (§3), the series key (§2 of the spec), the anchor-walk rule (§3 of the spec), the noise model (§7.2) |
| Measured | shape (one of six names); stability = share of draws whose shape equals the series' shape on the unperturbed data (0–1); Δ = stability − baseline share (0–1) |
| Baseline | the same series with every size replaced by the error-weighted mean of its sizes: no dependence on fluence, same x and errors |

## 3. Data

| What | Value |
|---|---|
| Source | ablation_db (curated database of laser-ablation experiments), read-only account, exported with `ablation_db snapshot` |
| Version | `data/ablation_snapshot.json`, SHA-256 `c5380620d896237ad655bfde0ce166d3f638b84a3e9b0b996cc09226f6b8303f`; format 1, schema change `0095`, metadata hash `c129120a031257f6e46e3a46d0762bef`, exported 2026-10-27T11:18:47Z from live; exporter at ablation_db commit `<fill in>`; committed in `9db97cf` |
| Export options | gold as the sole target material, completed articles only; no manufacturers, instrument details, measurement settings or provenance; compact materials; nulls omitted |
| Licence | none stated; included only so that the check can be reproduced |
| Size | 19 articles, 118 experiments, 753 KB |
| Split | none: nothing is fitted; every series of the snapshot is used |

**Data contract**, checked by `checks/verifier/contract.py` on the snapshot
and on the series built from it. Each rule returns named violations; an
unknown violation fails the check.

| Rule | How it is checked | Violation |
|---|---|---|
| header: format 1, the export options above | compare with constants | `header_mismatch` |
| experiment ids unique; each experiment's `article_id` is its article's | count and compare | `duplicate_experiment`, `wrong_article` |
| every ablation target is gold only | resolve the target in `shared` | `non_gold_target` |
| units: fluence J/cm², pulse energy µJ, spot diameter µm, sizes nm | the snapshot's `units` table | `unit_mismatch` |
| ranges: 0 < fluence ≤ 1000 J/cm², 0 < energy ≤ 10⁶ µJ, 0 < size ≤ 1000 nm, SD ≥ 0 | per value | `out_of_range` |
| distribution bins ascending, not overlapping, counts ≥ 0 with a positive sum | per distribution | `bad_bins` |
| a series has ≥ 2 distinct x, all fluence or all energy, never both | per series | `mixed_x`, `short_series` |
| energy as x only when the spot diameter is equal for all points or missing for all | per series | `spot_varies` |
| members of a series share every key condition | compare the key of each member | `key_mismatch` |
| each (experiment, size kind) in at most one series | count | `point_in_two_series` |

**Known violations:** none recorded yet. An experiment that cannot join a
series (no varied x, mixed x, varying spot) is dropped with a note, not a
violation.

## 4. Code and environment

- Code: pure functions in `tools/series.py` (series key, x, size, size_err,
  shape); `tools/ablation_db.py` reads the snapshot and serves the
  `results_spec.md` §4 functions. No database connection.
- Command: `.venv/bin/python -m pytest checks/verifier -q`; resampling:
  `.venv/bin/python checks/verifier/run.py <step>` (§6).
- Environment: Python 3.14.4; `requirements.txt` pins numpy 2.5.4,
  scipy 1.18.1, pytest 9.1.1, PyYAML 6.0.3, pypdf 6.20.0 and hypothesis
  (version fixed when installed).
- Seeds: resampling seeds 0–4, each a `numpy.random.default_rng(seed)`;
  hypothesis runs with `derandomize=True`, so its examples repeat.

## 5. Verifier

- **Checks:** the properties below, the data contract (§3), and the
  reference case: 80094-s1 `increasing` / `increasing`, 80094-s2 `peak` /
  `flat` (`results_spec.md` §7.5).
- **Command:** `.venv/bin/python -m pytest checks/verifier -q`.
- **Location:** `checks/verifier/`, read-only for the agent (ban 1).
  Outputs go to `results/verifier/`, which holds shapes, so ban 3 must
  name it before the first run.
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
| 8 | the error is the stored SE if any, else SD/√N, else the fallback | `results_spec.md` §2 priority | `test_error_priority` |
| 9 | on generated experiments, each (experiment, size kind) lands in at most one series, and all members share the key | the series key is a partition | `test_series_partition` |

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
   that same shape; both unitless, 0–1.
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
| | | | | |

## 10. Limitations

- The snapshot has no provenance: sizes read from figures, and x values
  the curator assumed, look the same as reported values.
- The noise model assumes independent normal errors. Resampling around
  measured values adds the noise a second time, so stability is a lower
  bound.
- SD/√N counts particle-sampling error only; one colloid per point hides
  the scatter between syntheses.
- The fallback fractions (0.10, 0.20) and the thresholds in §7 are
  choices, not measurements.
- About 9 series: enough to test the code, too few for a strong sign test
  in `summary.json`.
- The check says nothing about whether the database matches the articles,
  or whether the agent's claims are right.
