# HW2 report: verifying nanoparticle-size series and their shape sensitivity

[порождено: gpt-6.1-sol] Report reviewed and curated by Anton. No `hw2` or `exp-verifier` tag has been created at this checkpoint. This is not yet a submission-ready package.

[источник: course `lectures/hw_2/REPORT_TEMPLATE.md`, §§1–9] Report structure follows the course template. Submission requirements: `lectures/hw_2/ASSIGNMENT.md`, §§3, 6–7; assessment criteria: `lectures/hw_2/RUBRIC.md`. The submission checklist below is a **student self-check**.

| Field | Value |
|---|---|
| Direction | Computational; week 7 direction B |
| Verifier | Nine property tests, independent data/series contract, reference and checker-corruption tests |
| Project | <https://github.com/Kaldarinz/ai4science_proj> — private; instructor access must be arranged |
| Submission tag | `hw2` — planned, not yet created or tested |
| Experiment tag | `exp-verifier` — planned; original sweep source is exactly captured by `776a2fe` |
| One-command verdict | `.venv/bin/python -m pytest checks/verifier -q` — identical to `AGENTS.md` §1 |

## 1. Task and place of the verifier

[написано] The main idea of the future article is comparison of textual claims about dependence of gold nanoparticle size versus laser fluence (energy) with their actual numerical data using corpus of existing literature on this topic. This work verifies a narrow component of that broader endeavour: grouping numerical data, already extracted and kept in structured form in specialized curated database (ablation_db, which I'm developing) into compatible size-versus-fluence or pulse-energy series, and assigning an error-aware shape. Incorrect grouping could combine incompatible experiments, an incorrect classifier could reverse a trend or invent a peak.

The verifier checks conformity to the declared contract. A resampling experiment measures classification sensitivity of the found numerical series under an assumed noise model.

## 2. Methodology and chronology

[порождено: gpt-6.1-sol] The first METHOD commit is `1dfe8db50fcb44cb71ab6d9ee75ece55313c5062`, dated **2026-10-28**. The passport's 2026-10-27 date is the stated drafting date, not the git commit date. The tools and curated method were committed as `e9fecd3` before the first completed verifier run on 2026-11-06. The first HW2 result artifacts were committed in `776a2fe`. Earlier exploratory knowledge of the reference case is disclosed in METHOD §1.

The input is the committed snapshot of relevant numerical data from the articles `data/ablation_snapshot.json`: 19 articles, 118 experiments; SHA-256 `c5380620d896237ad655bfde0ce166d3f638b84a3e9b0b996cc09226f6b8303f`. It was exported on 2026-10-27, schema change `0095`, and committed in `9db97cf`. The contract yields 10 usable series in 6 articles, 45 points and 75 exclusion records; these are observations, not acceptance targets.

Fixed: snapshot, compatibility/selection rules and anchor-walk classifier. Varied: primary/lenient fallback error fractions (0.10/0.20) and normal-noise seeds. Original errors remain fixed. Each seed uses one RNG in stable series order; the same normal draws perturb the data and constant inverse-primary-variance baseline under both models. No clipping, refitting, regrouping or error recomputation occurs. Baseline hits are measured against the **original observed shape**, not the baseline's own shape.

Full inference uses five seeds, 0–4, with 1000 draws per seed. Stability is the share retaining the original shape; Δ is stability minus the baseline's share of that same shape. Across five per-seed estimates: 95% t intervals, df=4; one-sided paired t-test of Δ>0; Holm correction over all 20 series/model cases. Support requires adjusted p<0.05 **and** mean Δ≥0.20. Stability additionally means a stability-CI lower bound ≥0.80. No threshold was tuned after the resampling results.

**Disclosed post-run changes:** the first completed dry run rejected three stored size-axis tails under the former 1000 nm upper bound. Anton explicitly removed the bound for all sizes/support coordinates, not just zero-density tails. The failed artifact is retained; finite/positivity/structure and separate x bounds remain. Later corrections affected bookkeeping (smoke must not hash a combined CSV overwritten by full) and notation (Δ ranges from −1 to 1), not the noise model or decision thresholds. See METHOD §9 and `attempts.md`.

## 3. Verifier and strength of checks

[порождено: gpt-6.1-sol] The single pytest command includes a pinned-snapshot contract and both public error-model payloads, nine Hypothesis properties, known reference shapes, nonvacuous shape examples and tests that the checker rejects synthetic corruptions. All **82 tests** pass on the correct implementation. Property settings are `max_examples=150`, `derandomize=True`, `database=None`; these are bounded searches, not universal proofs.

Tests below are in `checks/verifier/test_properties.py`:

| # | Property | Reason | Test |
|---|---|---|---|
| 1 | Joint point permutation preserves shape | Walk must sort by x | `test_point_order_does_not_matter` |
| 2 | Scaling sizes/errors by 2^k preserves shape | Unit invariance | `test_size_unit_does_not_matter` |
| 3 | Mirroring sizes reverses directed shapes | Symmetric threshold rule | `test_mirror_swaps_direction` |
| 4 | Increasing x remapping preserves shape | Only x order is used | `test_only_order_of_x_matters` |
| 5 | Primary-flat implies lenient-flat | Larger errors cannot move a previously unmoving anchor | `test_lenient_flat_when_primary_flat` |
| 6 | Repeating the last point at a larger x preserves shape | It cannot introduce another significant step | `test_repeated_last_point_changes_nothing` |
| 7 | Histogram mean is bounded, analytically correct and count-scale invariant | Normalized weighted mean | `test_distribution_mean` |
| 8 | SE → mean SD/√N → fallback priority | Explicit uncertainty contract | `test_error_priority` |
| 9 | Exact identities, maximal compatible groups and reordering invariance | Unknowns may overlap but cannot bridge conflicts | `test_series_compatibility` |

| Contract component | Independent check / evidence |
|---|---|
| JSON schema, version/options/filter, references, units/routes | `contract.py:132–244`; schema validation and schema-driven reference expansion |
| Unique IDs, article membership, gold-only targets | Raw snapshot checks; corruptions in `test_contract.py:63–104` |
| Finite/ranged x, positive selected sizes, valid histogram/curve structure | Named fatal violations, no learned allowlist; no size upper bound |
| Exact measurement labels, scalar values, storage/x, point uniqueness | Raw-member matching in `contract.py:254–351`, both error models |
| Pairwise-compatible conditions and collection semantics | Separate positive field list and permutation-based matching, not production compatibility helpers |
| Correct maximal overlapping groups | Exhaustive subset oracle on generated inputs, not production clique code |
| Error inputs and values | Raw-matched SE/N and independently computed distribution SD; `test_error_priority` |
| Reference | `80094-s1`: increasing/increasing; `80094-s2`: peak/flat; `test_contract.py:33–45` |
| Simulation/inference/gates | Synthetic tests in `test_resampling.py`; paired noise, fixed errors, signed Δ, t/Holm, boundary/degenerate cases, complete smoke prerequisite |

This is not a complete independent raw-to-output oracle for every derived histogram/curve statistic. In particular, not every fitted mode or median is independently reconstructed by the contract. Implementation tests complement, but do not replace, independent verification.

## 4. Decomposition and attempts

[порождено: gpt-6.1-sol] The scientific verification goal has five subgoals:

```text
Verify the declared series/classification/sensitivity computation
├── Raw data satisfy the contract
│   ├── schema, units, identities, references — raw checker + corruption tests
│   └── revised range policy — retained failure + curator-authorized regressions
├── Public series and grouping satisfy the contract
│   ├── every member pair, labels, x/storage/errors — independent checker
│   └── maximal overlapping groups — exhaustive generated-subset oracle
├── Shape/statistic rules satisfy metamorphic properties
│   └── nine properties + reference/threshold examples — passing pytest suite
├── Sensitivity calculation follows the fixed experiment
│   └── synthetic sampling/inference tests + complete five-seed gated runs
└── Verifier distinguishes a deliberately wrong implementation
    └── unchanged property 1 fails on cf188ed, passes on correct parent/main
```

Attempt counts below describe **recorded runs**, not an invented count of every edit. Detailed chronological evidence is in `attempts.md`.

| Subgoal | Recorded attempts and outcome | Three-attempt rule |
|---|---|---|
| Raw contract | Dry 1: dict `.sort` error; dry 2: metadata traversal TypeError; dry 3: completed rejection of size tails. After curator-authorized revision, dry 4 passes; dry 5 refreshes provenance. | Stopped after three unsuccessful dry runs and asked Anton; separated traversal bugs from a scientific-policy decision. No silent allowlist. |
| Public contract/properties/reference | First recorded completed short suite after the raw gate: 65 pass; later complete verifier: 82 pass. No separate failed property run on correct main is recorded. | No sequence of three recorded property failures. |
| Sampling/inference | Initial smoke/full completed; bookkeeping issue found during review, regression added; same seeds repeated exactly. Initial artifacts retained. | Changed bookkeeping, not experiment; did not select a favorable run. |
| Mutation detection | One planted candidate, one targeted failing run, then passing correct-code checks; defect committed unchanged. | First candidate detected; no need for three candidates. |
| Reproduction | One clean local clone; verifier and all stages pass; separate bug worktree: 1 failed, 81 passed. | No failed reproduction retry. |

## 5. Execution results and uncertainty

[порождено: gpt-6.1-sol] Archived original execution:

| Depth step | Result | Recorded time | Gate |
|---|---|---:|---|
| Revised dry | 0 violations, 10 series / 45 points | 0.25 s | Raw and both-model public contracts pass |
| Short check / sweep preflight | 82 verifier tests pass | under 3 s | Properties/reference pass |
| Smoke | 20 rows, seed 0 ×100 draws | 2.36 s | All series/models complete |
| Full | 100 rows, seeds 0–4 ×1000 draws | 2.90 s | Matching smoke, same source/snapshot; inference complete |
| Regression after mutation demonstration | 267 tests pass | 3.66 s | Correct main implementation |

[источник: `full_runs.csv`, `summary.csv`, `report_metrics.csv`] All 20 model/series cases are retained: **14 meet joint support**, **12 meet stability**. These are not 20 independent series: there are 10 series, paired models and potentially shared experiments. No best-seed selection or pooling of 5000 draws as experimental replicates is used.

The preregistered reference case `80094-s2` illustrates sensitivity. SD below is sample SD across five per-seed estimates; CIs are the original t intervals. All cases, not only this example, are in `report_metrics.csv` (the original summary plus three between-seed SD columns).

| Model / metric | Mean | SD | 95% interval |
|---|---:|---:|---|
| primary / stability of peak | 0.3094 | 0.0182 | [0.2869, 0.3319] |
| primary / baseline share of peak | 0.1534 | 0.0038 | [0.1487, 0.1581] |
| primary / paired Δ | 0.1560 | 0.0192 | [0.1321, 0.1799] |
| lenient / stability of flat | 0.3132 | 0.0166 | [0.2926, 0.3338] |
| lenient / baseline share of flat | 0.8360 | 0.0106 | [0.8229, 0.8491] |
| lenient / paired Δ | −0.5228 | 0.0170 | [−0.5439, −0.5017] |

[порождено: gpt-6.1-sol] Primary peak: Holm p=0.0001631, but Δ=0.1560<0.20, so the joint support criterion fails. Lenient flat: Holm p=1, negative Δ; support also fails. Neither classification is stable by the ≥0.80 lower-CI rule. The canonical label “not distinguishable from no dependence” means the joint criterion failed; it is **not proof of no effect**, and need not mean p≥0.05.

The intervals quantify Monte Carlo variation under the specified noise model, not repeat-measurement uncertainty. A boundary estimate of 1 can yield a collapsed interval without proving probability one. The zero-between-seed Δ-variance convention is recorded and tested; no original full-run case triggered it.

## 6. Caught error

[порождено: gpt-6.1-sol]

| Defect | Origin | Detector | Before | After |
|---|---|---|---|---|
| `classify_shape`: replace `sorted(...)` with `list(...)` | Deliberately planted; only `tools/series.py` changed in `cf188ed7f3618b3334af263eb67a7ad54783b5e0`, branch `bug/point-order` | Existing property 1, written before planting | `caught_error_before.txt`: exit 1 | `caught_error_after.txt`: exit 0 |

Hypothesis shrank the input to x=[1,2], sizes=[0.125,0.25], errors=[0,0], permutation=[1,0]. Faulty code changes increasing to decreasing; correct code returns increasing for both orders. Verifier Python files are byte-identical on the two commits; hashes and patch are in `caught_error_manifest.json` / `caught_error.patch`.

Main never contained the defect. “After” is the original correct parent `776a2fe`, not a fabricated repair commit. `build_series` already sorts its inputs, so this establishes detection of the pure function's order-contract violation, **not** an incorrect shape for a particular real snapshot series. New clean-clone evidence also runs the **complete** verifier on the faulty commit: `reproduction/bug_verifier.txt` contains **1 failed, 81 passed**.

## 7. Reproduction

[порождено: gpt-6.1-sol] Once the submission tag is created/pushed and instructor access is arranged:

```sh
git clone git@github.com:Kaldarinz/ai4science_proj.git hw2-check
cd hw2-check
git checkout --detach hw2
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checks/verifier -q
```

Expected verdict: exit 0, 82 tests pass. Tested interpreter: Python 3.12.3; exact package versions are in `requirements.txt`. After setup, the verifier and experiment require no network, PDF files or database. The committed numeric snapshot/schema are sufficient. Article PDFs are not tracked or required for this command; the separate claim-extraction readiness checker is not the HW2 verifier.

To repeat the numerical experiment, use this separate clone: the runner overwrites its stage outputs and records fresh provenance. Always regenerate smoke before full; historical manifests need not match later METHOD documentation hashes.

```sh
cp results/verifier/summary.csv results/verifier/summary.expected.csv
.venv/bin/python checks/verifier/run.py dry
.venv/bin/python checks/verifier/run.py smoke
.venv/bin/python checks/verifier/run.py full
cmp results/verifier/summary.expected.csv results/verifier/summary.csv
```

To reproduce the defect without changing correct main, from the clone root:

```sh
PYTHON="$PWD/.venv/bin/python"
git worktree add --detach ../hw2-bug cf188ed7f3618b3334af263eb67a7ad54783b5e0
status=0
(cd ../hw2-bug && "$PYTHON" -m pytest checks/verifier -q) || status=$?
test "$status" -eq 1
```

Expected assertion: point-order property; **1 failed, 81 passed**, not an import/setup error. The full clone must include the bug commit (ordinary clone fetches the published bug branch). Do not merge the defect into main.

**Actually tested :** a clean local clone at `c50a2ff`, with the existing project venv. Tests passed in about 2.2 s; full invocation about 3.4 s. Its summary was byte-identical; every scientific per-seed field matched the original, excluding only git commit and elapsed time. Original sweep source fingerprints match git objects at `776a2fe` exactly. Fresh manifests/artifact hashes were also checked. Logs, commands, expected/actual exits and limitations: `reproduction/manifest.json` and accompanying text files. No network access or final-tag reproduction was certified.

## 8. Limitations and remaining submission checks

[порождено: gpt-6.1-sol]

- The specification can be scientifically wrong while the implementation passes. The ordinary-diameter-density approximation for DLS, scalar aliases, wildcard conditions and ignored spot diameter are deliberate toy-project choices, not validated physical equivalences.
- Missing provenance prevents distinguishing digitized values and curator assumptions from direct reports. Nothing checks data against papers or verifies textual claim extraction.
- The independent oracle covers grouping, identities and error inputs; it does not independently reproduce every derived distribution statistic. Generated domains are bounded and do not prove all inputs safe. One planted bug does not measure general defect-detection power.
- Fixed independent normal errors, 10%/20% fallbacks and practical thresholds are assumptions. N counts particles, not independent syntheses; SD/√N does not model synthesis scatter or fitted-mode uncertainty. Signed resampled sizes are intentional, not physical observations.
- Shared experiments and paired models are dependent. Five-seed intervals describe simulation variation, not population-level experimental confidence. Retaining all cases and Holm adjustment does not repair an incorrect physical noise model.
- The raw size upper bound was removed **after** a failed run; original evidence and curator authorization are disclosed rather than presenting the revised check as untouched preregistration.

Student submission checks still open:

- [ ] Fresh dependency installation is tested, or its untested status remains explicit; current reproduction reused an installed pinned venv.
- [ ] Report/package changes are committed; `hw2` and `exp-verifier` tags are explicitly authorized/created/pushed by the operator, then the final tag is checked.
- [ ] Instructor access and permission to share the numeric snapshot are confirmed. Private status is not, by itself, a license check. No PDF redistribution is needed.
- [ ] Course student self-check `check_week6.py --run` is run if the starter script is obtained; it was not found in the available course repository and was **not** run here.


## 9. AI use and authorship

[порождено: gpt-6.1-sol] The recorded model is `gpt-6.1-sol`; this attribution comes from session metadata, not writing style. Anton identified the initial METHOD draft's model as DeepSeek flash 4 and personally edited that draft. It is attributed separately from the current model. Anton has reviewed and curated this report; `[написано]` below credits human-written content and decisions, while generated content retains its model attribution.

| Fragment / file | Label | Model or author | Checked by |
|---|---|---|---|
| Initial `METHOD.md` draft | `[порождено]` | DeepSeek flash 4 | Historical commit `1dfe8db`; Anton confirms AI draft + personal edits |
| METHOD curation and scientific-policy decisions | `[написано]` | Anton | Explicit instructions/edits; subsequent implementation and disclosed revisions |
| `tools/series.py`, `tools/ablation_db.py` | `[порождено]` | gpt-6.1-sol | Implementation tests, independent contract/properties/reference, regression |
| `tools/tests/series_fixtures.py`, `test_series.py`, `test_series_conditions.py`, `test_ablation_db.py` | `[порождено]` | gpt-6.1-sol | Full regression; not represented as independent scientific validation |
| `checks/verifier/contract.py`, `fixtures.py`, `test_properties.py`, `test_contract.py` | `[порождено]` | gpt-6.1-sol | Corruption tests, raw/public checks, reference, planted-defect failure |
| `checks/verifier/resampling.py`, `test_resampling.py`, `run.py` | `[порождено]` | gpt-6.1-sol | Synthetic pairing/inference/gating tests and exact-seed clean-clone repeat |
| Later METHOD implementation/status notes, verifier README, attempt/evidence documentation, this report | `[порождено]` | gpt-6.1-sol; Anton's edits separate | Linked code/logs/git history; report reviewed and curated by Anton |
| Snapshot/schema | `[источник]` | ablation_db data curated by Anton, who is responsible for data quality; snapshot/schema export committed `9db97cf` | Pinned checksum/schema; not independent paper-level correctness or license certification |
| Original JSON/CSV/test logs | `[источник]` | Actual Python/pytest executions; recorded code/environment | Manifest hashes and preserved failing/successful outputs |
| `report_metrics.csv` | `[порождено]` (aggregation code, not invented observations) | gpt-6.1-sol; Python aggregation of original runs | Original summary fields preserved; sample SD across seeds, ddof=1; Δ SD/√5 matches original SE |
| `reproduction/` logs and manifest | `[источник]` | Actual local clone/test/runner executions | Expected exits, exact scientific CSV comparison, source/artifact hashes |

The database's physical correctness is not certified; no instructor verdict is claimed, and the operator's publication steps remain incomplete.
