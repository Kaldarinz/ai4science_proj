# HW2 verifier: contract and properties

The initial size-upper-bound failure is preserved in
`results/verifier/dry_before_size_bound_removal.json`. The curator then
explicitly removed that check; finite-value/positivity checks remain.
See METHOD.md §9 and `results/verifier/attempts.md` for the revision and runs.
The revised dry check and initial verifier tests passed. Resampling code,
its synthetic tests, and gated `smoke`/`full` commands are now implemented;
execution status is recorded in `results/verifier/attempts.md`.
Smoke and full completed; 82 verifier tests and 267 full-suite tests pass.
Results and interpretation are in `results/verifier/RESULTS.md` (ban 3).
HW2 report, subgoal tree, authorship and clean-checkout commands:
`results/verifier/REPORT.md`; actual local reproduction logs:
`results/verifier/reproduction/`. Anton has reviewed and curated the report;
release identifiers are `exp-verifier` at `776a2fe` and `hw2` at the submission
commit. Remote publication remains an operator step. Fresh dependency installation and the
complete experiment were verified on committed package `bbd6f39` using its own
new venv; evidence is in `results/verifier/fresh_environment/`. The original
`reproduction/` evidence records the earlier shared-environment check.

From the project root, with the dependencies in `requirements.txt`:

```sh
.venv/bin/python checks/verifier/run.py dry
.venv/bin/python -m pytest checks/verifier -q
```

Run in that order and stop on any failure (METHOD.md §6–§7).
The first command writes `results/verifier/dry.json` and exits 0 only if
all raw-snapshot and public-series checks pass. It prints IDs, point counts,
x kinds, exclusion diagnostics and provenance, **not shapes**. Exclusions
are reported, not silently converted into accepted contract violations.
There is no violation allowlist. The next commands are:

```sh
.venv/bin/python checks/verifier/run.py smoke
.venv/bin/python checks/verifier/run.py full
```

Each first checks the contract and reruns properties/reference tests. Full
requires a passing smoke manifest and CSV for the same snapshot and source.
Changing source hashes requires a fresh smoke run before full.

Smoke: seed 0, 100 draws, all series × both models. Full: seeds 0–4, 1000
draws per seed, all series × both models and baseline. Errors remain fixed;
original primary errors generate one noise matrix shared by both models and
baseline. Negative normal draws are not clipped. See METHOD §9 for execution
conventions fixed before this implementation's first resampling run.

Artifacts: `smoke_runs.csv`, `full_runs.csv`, combined `runs.csv`, full
`summary.csv`, `smoke.json`/`full.json` with source/configuration fingerprints,
and each step's captured preflight output. Summary CIs and tests use five
per-seed estimates, not pooled draws; Δ remains signed. Holm covers every
series/model. A passing execution is not the same as a supported scientific
shape; unsupported/unstable classifications are valid experiment outcomes.

The second command includes the pinned snapshot contract, both error models,
the reference shapes in `checks/results_spec.md` §7.5, nine Hypothesis properties
from METHOD.md §5 (150 deterministic examples each, no example database), and
tests that synthetic corruptions actually fail the contract. Synthetic failures
are checker self-tests, separate from the deliberate-bug-branch demonstration.
It does not depend on implementation-test fixtures in `tools/tests/`.

## Independent evidence

| METHOD claim | Evidence |
|---|---|
| Raw data contract, §3 | `contract.check_snapshot`: local exported JSON schema, pinned metadata/units, identities, gold targets, ranges and arrays |
| Fixed conditions and identity, §3 | `contract.check_series`: schema-driven reference expansion, positive fixed-field list, every member pair, exact labels and storage/x checks; never calls production `condition_key` or compatibility/clique helpers |
| Error priority, §5 #8 | Direct generated cases plus raw-matched SE/N and independently computed distribution SD on public API responses |
| Nine properties, §5 | `test_properties.py`, test names exactly as preregistered |
| Compatible overlapping groups, §5 #9 | Exhaustively enumerate subsets of generated experiments, retain maximal pairwise-compatible subsets; compare all memberships, both models and reordered inputs |
| Reference case, §5 | `test_snapshot_contract_and_reference` |
| Checker can reject errors | Synthetic raw/response corruptions, key conflict and collection-order/absence tests in `test_contract.py` |
| Frozen source, §3 | Exact snapshot SHA-256 guard; dry artifact records git HEAD/status, code/schema hashes and dependency versions |

The `schema_mismatch`, `broken_reference`, `bad_curve`, `value_mismatch`,
`duplicate_article`, `snapshot_hash_mismatch`, `build_failure` and
`reference_mismatch` diagnostics supplement the named METHOD §3 rules;
all are fatal, not new accepted exceptions. Zero histogram/curve support
boundaries are allowed; selected sizes must remain strictly positive.
Sizes and distribution support have no upper bound, including zero-density
tails. The separate fluence and pulse-energy bounds are unchanged.

The declared schema is structural evidence, not an oracle for scientific
meaning: in particular its DLS ordinate description is **not** used for
integration. Ordinary diameter-density moments are deliberate project policy.
Independent checks share the written specification with the implementation;
they do not prove the specification or curated values scientifically correct.
Hypothesis searches a bounded generated domain, not all possible inputs.
The resampling stage did not implement claim comparison, submission tags or
the later HW2 report. Resampling estimates sensitivity under a specified noise model, not
repeat-measurement stability. It does not make shared experiments or
overlapping series independent.

## Deliberate-error demonstration

Local branch `bug/point-order` (`cf188ed`, parent `776a2fe`) changes only the
shape function's sorting line. The existing point-order property fails on
the mutation and passes on the unchanged correct main implementation.
No verifier Python source was modified for the demonstration.
Before/after output, patch, provenance and safe-worktree reproduction commands:
`results/verifier/caught_error.md` (ban 3). The branch was not merged;
Anton subsequently reported pushing it, and local `origin/bug/point-order`
points to `cf188ed`. No live remote-access check was performed here.
