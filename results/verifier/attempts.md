# HW2 verifier implementation attempts — 2026-11-06

Baseline: `e9fecd3` (tools and curated METHOD committed before these runs).
Verifier changes are uncommitted. This is an implementation journal, not an
HW2 acceptance verdict or the deliberate-bug-branch demonstration.

## Subgoals

1. Independent raw snapshot contract: schema/metadata/units, identities,
   targets, ranges and distribution structure.
2. Public series contract: reconstruct condition profiles from exported
   contents, exact measurement identity, pairwise compatibility, x/storage,
   uniqueness and independent error inputs.
3. Nine deterministic Hypothesis properties, checker self-tests and reference
   case; proceed only after the dry contract passes.

## Attempts

| Attempt | Command/result | Action |
|---|---|---|
| Static preflight | Ruff reported import formatting, an unused noqa and a loop-variable closure warning; no verifier run occurred. | Fixed imports and bound the integration positions explicitly. |
| Dry 1 | Runtime error in the new checker: `AttributeError: 'dict' object has no attribute 'sort'`, in `resolve` while visiting `field_units` metadata. No contract verdict was produced. | Sort beam/postprocessing values only when they are lists. |
| Dry 2 | Runtime error in the new checker: `TypeError: string indices must be integers, not 'str'`, in the raw measured-property traversal. No contract verdict was produced. | Do not interpret the unit-routing metadata subtree as scientific records. |
| Dry 3 | Exit 1, three named `out_of_range` violations; original artifact preserved as `dry_before_size_bound_removal.json`. | Stopped and asked the curator; no exception added. |

The first two errors were verifier implementation bugs, not failures in the
scientific tools or malformed curated values. The third attempt produced the
first completed contract verdict. At that checkpoint, no property tests or
later stages had run. The curator-authorized revision and subsequent progress
are recorded below.

## Blocking observations (raw stored diameters, no resampling)

Article `538197`, DLS hydrodynamic-diameter curves:

| Experiment | Product colloid | Largest stored axis coordinate, nm |
|---|---|---|
| 539738 | 539744 | 6439 |
| 539770 | 539777 | 1484 |
| 539800 | 539806 | 8635 |

The failed checker interpreted the former METHOD §3 size bound as including
raw distribution-axis coordinates. These observations do not establish the
representative sizes or correctness of the curated values. At this stop,
property tests, independent series checks and reference shapes were unverified
by the new verifier: the raw-contract failure stopped it before building series.

## Curator-authorized revision after the first completed dry check

The curator explicitly requested: “Remove the upper bound check, we should not
really check it (it's logic was also flawed, since it counted any x values even
if the correspodning y=0)”.

Removed the size upper bound consistently for scalar values, extracted sizes,
histogram boundaries and curve axes. Finite-value, positivity/nonnegativity and
array-structure checks remain; the separate fluence/pulse-energy bounds remain.
Added regressions for large scalars, histogram and curve support, with both
zero and positive tail weights, plus invalid scalar sizes. This changes the
scientific contract after observing a failed run, not the data. METHOD §3 and
§9 disclose the revision; the original failure artifact is retained unchanged.

## Verification after the authorized revision

| Step | Result | Evidence |
|---|---|---|
| Dry 4 | Exit 0; zero violations; 10 series, 45 points; 75 exclusion records reported separately. Both public error-model payloads pass the independent series checks. | `dry.json` (refreshed by the final provenance run below) |
| Short check | Exit 0; 65 tests passed in 2.12 s. Includes all nine preregistered properties (150 deterministic examples each), reference shapes, checker-corruption tests and the new no-upper-bound regressions. | `short_check.txt` |
| Full regression | Exit 0; 250 tests passed in 3.60 s, including the existing 185 implementation tests. | `regression_check.txt` |
| Static/graph checks | Ruff, `git diff --check`, and `tools/graph.py --check` pass. | Local command output |
| Dry 5 | Final repeat after updating method/status documentation, to record current source hashes; same revised scientific contract. | `dry.json` |

Raw inspection confirmed that each of the three previously flagged curves has
three stored coordinates above the former limit with ordinate zero. Regression
fixtures explicitly cover both zero and nonzero tails, so the removed bound is
not replaced by a positive-density-only upper-bound check. Large scalar and
representative sizes are accepted too; nonfinite/nonpositive sizes still fail.
The snapshot checksum remains the one pinned in METHOD §3.

No resampling, comparison pipeline, deliberate-bug branch, tags or commits were
created. This is a verifier-code/test result, not a scientific stability verdict
or a complete HW2 submission. The unchanged general `checks/check.py` readiness
gate still requires committing the new `results/` artifacts; no commit has been
authorized. Original failure evidence remains separate and unchanged.

## Resampling stage authorized by “good, go next”

After the revised verifier passed, Anton requested the next stage. Implemented
METHOD §6's smoke → full sequence; no commit/tag or planted-error branch is
included in this authorization. The earlier no-resampling notes above describe
the previous checkpoint, not this new stage.

Before the first real resampling run, recorded the execution conventions in
METHOD §9: fixed original errors; untruncated normal draws paired across both
models and baseline; inverse-primary-variance baseline; five-seed t intervals;
explicit zero-variance test convention; signed Δ. Corrected the purely
mathematical range typo for Δ in §2 without changing its ≥0.20 threshold.

`test_resampling.py` checks the noise pairing, fixed errors, negative draws,
comparison with the ORIGINAL target shape, deterministic streams/order,
public payload agreement, independent paired-t reference, Holm adjustment,
signed differences, degenerate variance, exact practical boundary, incomplete
runs, full's matching-smoke gate, failed-preflight stop and CSV encoding.
These tests use synthetic data, not real snapshot resampling. The first test
pass had 80 tests; the added practical-boundary regression is included in the
final preflight/full regression below.

| Resampling stage | Result | Evidence |
|---|---|---|
| Final full regression | 266 passed in 3.65 s. | `resampling_regression.txt` |
| Smoke preflight | 81 verifier tests pass; raw and both-model series contract pass. | `smoke_preflight.txt`, `smoke.json` |
| Smoke sweep | All 10 series × 2 models; seed 0, 100 draws; 20 rows; total 2.369716 s. Pure sampling about 0.011 s; projected full total about 2.90 s. | `smoke_runs.csv`, `smoke.json` |
| Full gate/preflight | Exact matching snapshot/source fingerprints and smoke CSV verified; 81 tests pass again. | `full_preflight.txt`, `full.json` |
| Full sweep | 10 series × 2 models × 5 seeds × 1000 draws; 100 rows; 2.848431 s including preflight; all cases evaluated. | `full_runs.csv`, `summary.csv`, `full.json` |
| Artifact verification | Current source hashes match full manifest; every artifact hash matches; combined log has 120 rows. | Local checksum assertions |

All sweeps completed without contract/property/reference failure. This is a
successful execution, not a verdict that all scientific shapes are supported.
Results and limitations are interpreted in `RESULTS.md`; no threshold or noise
convention was changed after seeing the resampling results. No commit, tag,
planted-error branch or claim-comparison output was created.

### Artifact-bookkeeping correction and exact repeat

Final review found that the smoke manifest also hashed combined `runs.csv`,
which full subsequently rewrites. Smoke now hashes only its stage-specific
CSV and preflight log; full additionally hashes the final combined log.
Added a regression for this mutable-artifact issue. This is bookkeeping, not a
change to simulation or inference. Preserved initial manifests/CSVs/preflights,
the original runner/test source and regression output in `initial_resampling/`.
Its smoke manifest describes the historical combined-log version, not today's
combined file; use its stage-specific smoke CSV as the retained evidence.

Reran all tests and both fixed-seed stages after the correction:

- Full regression: **267 pass / 3.68 s** (`resampling_regression.txt`).
- Each sweep preflight: **82 pass**.
- Smoke: **20 rows / 2.361628 s**; full: **100 rows / 2.895960 s**.
- Every source and artifact hash in BOTH current manifests matches the files.
- Per-seed scientific rows reproduce the initial runs exactly (excluding wall
  times), and `summary.csv` is byte-for-byte identical. No additional seeds or
  draws entered the estimates, and no run was selected for a better outcome.

The current manifests/logs supersede the initial timing/test counts above.
No scientific thresholds, inputs or noise conventions changed between runs.
