# Current verifier outputs and historical HW2

No resampling experiment has been run on the format-6 snapshot.
A new `dry.json` is contract-validation evidence only, not a numerical
sensitivity or claim-comparison result.

The submitted HW2 package remains unchanged at tag `hw2`, commit
`3abd29312aa89c7e6deb3211ecc0d66c47c61f5f`:

```sh
git show hw2:results/verifier/REPORT.md
git show hw2:results/verifier/RESULTS.md
git ls-tree -r --name-only hw2 -- results/verifier
```

That tag includes the old format-1 snapshot, original manifests/hashes/dates,
all numerical CSVs, failures, deliberate-bug evidence and reproduction logs.
Its 68 tracked verifier files were removed from main, not modified and not
replaced with new-snapshot results. Do not use them as current evidence.

New scientific runs must be performed by the AI4Science agent with explicit
authorization, using the current inputs and fresh smoke/full evidence.
See `checks/verifier/README.md` and METHOD.md. This directory and its git
history remain forbidden during claim extraction (AGENTS.md ban 3).
