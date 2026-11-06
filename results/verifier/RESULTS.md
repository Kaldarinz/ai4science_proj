# Paired resampling sensitivity experiment

## Reproduce

From the project root with `requirements.txt` installed:

```sh
.venv/bin/python checks/verifier/run.py dry
.venv/bin/python -m pytest checks/verifier -q
.venv/bin/python checks/verifier/run.py smoke
.venv/bin/python checks/verifier/run.py full
```

Stop on failure. Full requires smoke for the same snapshot and source hashes;
both resampling steps rerun the contract and property/reference preflight.
At execution, code was **uncommitted**, based on git HEAD `e9fecd3`; it was
subsequently committed as `776a2fe`. The manifests retain the actual execution
time's dirty status and exact source hashes, not retroactively rewritten git
metadata. HEAD alone does not identify the code that ran. No
submission/reproduction tag was made.

## Execution

- Fixed snapshot SHA-256: `c5380620d896237ad655bfde0ce166d3f638b84a3e9b0b996cc09226f6b8303f`.
- Full regression: **267 tests passed**; each sweep's verifier preflight:
  **82 tests passed** (properties, contracts, reference and resampling tests).
- Smoke: 10 series × 2 models, seed 0, 100 draws; 20 log rows; 2.36 s.
- Smoke-based full estimate: about 2.90 s including preflight overhead.
- Full: all 10 series, seeds 0–4, 1000 draws per seed, both models and
  baseline; 100 log rows; 2.90 s including preflight.
- `runs.csv` contains smoke + full (120 rows). `summary.csv` has 20
  series/model results. Scientific outcomes are not verifier pass/fail tests.

Each seed supplies one RNG; series are processed in stable order. Original
primary errors generate the noise; original primary/lenient errors classify
every perturbed series and baseline. The same z is reused for both models and
baseline. No negative draw is truncated or rejected, no errors recomputed,
and no distribution re-fitted or series regrouped during resampling.

## Outcome under METHOD §7

- **14/20** series/model cases meet both Holm-adjusted p < 0.05 and mean
  Δ ≥ 0.20.
- **12/20** have the lower stability-CI bound ≥ 0.80.
- These are counts of model/series cases, **not 20 independent series**.
  Models are paired, and series may share experiments.

Reference `80094-s2`:

| Model | Original shape | Stability | 95% interval | Mean Δ | Joint support criterion |
|---|---|---:|---|---:|---|
| primary | peak | 0.3094 | 0.2869–0.3319 | 0.1560 | not met: Δ < 0.20 |
| lenient | flat | 0.3132 | 0.2926–0.3338 | −0.5228 | not met |

The primary peak's one-sided test is statistically significant after Holm
adjustment, but its effect does not meet the separate practical threshold.
The method's canonical “not distinguishable from no dependence” label must
not be read as proof of zero effect or as a claim that every such case has
p ≥ 0.05. All signed differences and exact p values remain in `summary.csv`.

## Evidence and limitations

- `full.json` and `smoke.json`: fixed configurations, source/environment
  fingerprints, elapsed time, gates and artifact hashes.
- `smoke_runs.csv`, `full_runs.csv`, `runs.csv`: integer hit counts and
  per-seed probabilities/differences, baseline centres, nonpositive-draw
  counts, original target shapes, time and git HEAD.
- `summary.csv`: five-seed means/t intervals, one-sided paired t-test,
  Holm adjustment across all 20 cases and both decision criteria.
- `smoke_preflight.txt`, `full_preflight.txt`, `resampling_regression.txt`:
  actual test outputs; `attempts.md`: implementation and execution journal.
- Initial size-bound failure remains in `dry_before_size_bound_removal.json`;
  its curator-authorized removal is disclosed in METHOD §9, not concealed.

CIs describe between-seed Monte Carlo variation under the chosen fixed noise
model, not repeated experimental measurement. With finite draws, zero observed
failures can yield a boundary estimate and a collapsed t interval; an estimate
of 1.0 is not proof of probability one. The zero-between-seed-variance test
convention is explicit in METHOD §9 (no full-run Δ case triggered it).
Neither scientific specification, curated values, normal noise nor fallback
fractions are established as physically correct by these tests. Overlapping
series remain dependent. No claim-comparison pipeline, deliberate-bug branch,
HW2 report, tags or commits were produced in this stage.
