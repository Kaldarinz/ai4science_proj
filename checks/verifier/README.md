# Current-snapshot verifier: contract and properties

```sh
.venv/bin/python -m pytest tools/tests checks/verifier -q
.venv/bin/python checks/verifier/run.py dry
```

Run from the project root with the pinned dependencies. Stop on any failure.
This verifies the current format-6 snapshot, not the submitted HW2 experiment.
The exact snapshot **and schema** SHA-256 values, schema metadata, export
selection/options and unit routes are pinned in `contract.py` and METHOD §3.

The dry command writes `results/verifier/dry.json`. Its output contains series
IDs, point counts, exclusion diagnostics and provenance, not shapes. It
constructs series only to validate the API; it does not resample, compare
claims or generate a scientific conclusion. There is no violation allowlist.

During article-by-article work, after that article's blind extraction, use:

```sh
.venv/bin/python checks/verifier/run.py dry --article 80094
.venv/bin/python -m pytest checks/verifier -q
```

The scoped dry command validates/builds only that article's schema-guided
snapshot view and writes `results/verifier/articles/80094/dry.json`; it does
not report other articles' diagnostics. Its whole frozen-snapshot/schema digest
guards remain intact, separate from comparison checkpoint bindings. The 80094
reference guard applies to full dry and to article 80094, not other article
preflights. `--article` is not supported for smoke/full; those still require
explicit curator authorization. Do not read preflight output during extraction.

## Independent evidence

| Claim | Evidence |
|---|---|
| Frozen inputs | Snapshot/schema digest guards; header/options/filter checks; dry records source hashes and versions |
| Structure and references | Exported JSON Schema and schema-driven shared-reference expansion |
| Format-6 conditions | Explicit independent fixed-field list covering every exported condition; flattened process/setup fields, target-position reference contents and physical stack layer order |
| Gold-only targets | Ordinary quantified singleton (fraction rounds to one at six places, half-up) not explicitly incomplete, or nonempty explicitly complete all-gold stack; particle materials resolved; no substrate-role exemption |
| Series membership | Every member pair checked independently; exact measurement identity, storage duration and x route; never calls production condition/grouping helpers |
| Numerical rules | Public values matched to raw sources; independently calculated sizes/errors; both models |
| Properties | Nine deterministic Hypothesis properties in METHOD §5, up to 150 examples each |
| Reference case | Existing article 80094 expectations in `test_contract.py` |
| Rejecting corruption | Synthetic raw/response corruption tests, schema tampering, flattened-field conflicts and incomplete/non-gold stacks |

The checker uses its own synthetic fixtures, not `tools/tests/` fixtures.
Property tests explore a bounded generated domain; schema validation is not
proof of scientific correctness. Supported size quantities remain diameters
and particle size; radius records are not silently converted.

## Future numerical runs — AI4Science work, not this migration

```sh
.venv/bin/python checks/verifier/run.py smoke
.venv/bin/python checks/verifier/run.py full
```

Only run with authorization for the new scientific experiment.
Both first rerun the contract and verifier tests. Full requires complete
passing smoke evidence for the same snapshot and source fingerprints.
An old HW2 manifest is not valid evidence for the new inputs.

Smoke uses seed 0 and 100 draws. Full uses seeds 0–4 and 1000 draws per seed,
both models and a constant baseline. Fixed original errors, shared primary
noise, signed delta, five-seed inference, Holm correction and thresholds
remain as specified in METHOD §§6–7, §9. Outputs stay in `results/verifier/`
and remain forbidden during claim extraction (AGENTS ban 3).

## Submitted HW2 history

HW2 has been submitted; the unchanged `hw2` tag preserves the old input,
report, actual failures, planted-error demonstration and reproduction evidence:

```sh
git show hw2:results/verifier/REPORT.md
git show hw2:results/verifier/attempts.md
```

There are no current-snapshot resampling results yet. Historical numerical
artifacts were removed from main rather than made to look current. See
`results/verifier/README.md` and the project README for access to the archive.
