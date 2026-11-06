# Deliberate point-order defect: before / after

This is an intentional mutation, not a naturally discovered production error.
The existing property test was written and committed before planting it.

- Correct baseline / main HEAD: `776a2fe60c70a2225231511555302c4ca44e7e4a`.
- Faulty branch: `bug/point-order`, commit
  `cf188ed7f3618b3334af263eb67a7ad54783b5e0`, direct child of the baseline.
- That commit changes **only** `tools/series.py`: `points = sorted(...)`
  becomes `points = list(...)` at line 298. See `caught_error.patch`.
- Verifier Python source is identical on both commits and current main;
  SHA-256 checks are recorded in `caught_error_manifest.json`.
- The bug was tested in a separate worktree. Main's implementation never
  contained the defect; only the mutation was committed, not this evidence.
  No merge, tag, push, database operation or resampling run occurred here.

## What the existing property caught

METHOD §5 property 1 says that reordering corresponding `(x, size, error)`
triples cannot change their shape. The correct implementation sorts by x.
The mutation walks the input order instead.

Hypothesis reduced the failing generated input to:

```python
x = [1, 2]
sizes = [0.125, 0.25]
errors = [0.0, 0.0]
order = [1, 0]
```

The faulty implementation says `increasing` in the original order but
`decreasing` after the permutation. Main says `increasing` for both.
These are synthetic numbers, not values from any article.

The same unchanged targeted command was run for baseline, failure and after:

```sh
python -m pytest checks/verifier/test_properties.py::test_point_order_does_not_matter -q --tb=short --color=no
```

| Execution | Exit | Output |
|---|---:|---|
| Correct baseline in the new worktree, before mutation | 0 | `caught_error_baseline.txt`: 1 passed |
| Planted defect, subsequently committed unchanged | 1 | `caught_error_before.txt`: 1 failed, with the reduced example |
| Original correct implementation on main (“after”) | 0 | `caught_error_after.txt`: 1 passed |
| Complete HW2 verifier on main | 0 | `caught_error_verifier_after.txt`: 82 passed |
| Complete regression suite on main | 0 | `caught_error_regression_after.txt`: 267 passed |

“After” means the original correct parent implementation, not an additional
repair commit. The deliberately faulty branch is kept for reproduction.

## Reproduce without changing main

From the project root on main, with the project venv installed and the bug
branch present locally. The new worktree path must not already exist.

```sh
ROOT="$PWD"
PYTHON="$ROOT/.venv/bin/python"
CHECK=checks/verifier/test_properties.py::test_point_order_does_not_matter
umask 077
git worktree add --detach "$ROOT/../hw2-point-order-repro" bug/point-order
status=0
(cd "$ROOT/../hw2-point-order-repro" && "$PYTHON" -m pytest "$CHECK" -q --tb=short --color=no) || status=$?
test "$status" -eq 1  # expected assertion failure, not a setup/import failure
"$PYTHON" -m pytest "$CHECK" -q --tb=short --color=no
```

Inspect the failing output for the `decreasing`/`increasing` assertion and
shrunk counterexample, not just exit code 1. Python must retain its absolute
venv path: resolving its symlink to a system interpreter would lose the venv.
The committed branch is local; it has not been pushed to a remote.

## Evidence coverage and limits

| Claim | Code/evidence | Result |
|---|---|---|
| Correct function sorts input | `tools/series.py:298` at the baseline; `caught_error.patch` | verified |
| Existing verifier checks joint point permutations | `checks/verifier/test_properties.py:33–37` | verified |
| The one-line mutation is detected | `caught_error_before.txt`, reduced two-point example | verified |
| Same property passes on original main | `caught_error_after.txt` | verified |
| Test/checker code did not change between implementations | committed object hashes and working-file hashes in `caught_error_manifest.json` | verified |
| Main remains correct on existing suites | 82/267-test logs above | verified within those suites |

This establishes detection of one input-order defect, not all defects.
`build_series` itself sorts its selected pairs (`tools/series.py:635–640`)
before calling `classify_shape` (`:669`), so the demonstration does not claim
that this mutation changes any particular snapshot-derived series. It tests
the pure function's specified order-invariance contract. No claim extraction,
noise assumption or scientific database value is validated by the mutation.
