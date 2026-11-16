# Supplied comparison pipeline

## Finish one article, then start the next

Run from the project root **after this article's blind extraction** and
inventory-bound reading attestation are complete:

```sh
id=80094
.venv/bin/python checks/check.py --article "$id"
.venv/bin/python checks/verifier/run.py dry --article "$id"
.venv/bin/python -m pytest checks/verifier -q
.venv/bin/python -m src.comparison prepare --article "$id"
# Review results/articles/$id/matching_candidates.json.
# Write results/articles/$id/matching_audit.csv with scientific decisions.
.venv/bin/python -m src.comparison build --article "$id" --stage draft
# Commit scientific records before the readiness check.
.venv/bin/python checks/check.py --article "$id" --analysis draft
```

Do not wait for the rest of the corpus. Only this article needs a reading
status; missing statuses for other articles do not block it. Extraction of
the next article starts in a fresh run/context without earlier numerical
outputs or comparison logs. Never expose numerical results before extraction.
The article dry preflight writes `results/verifier/articles/<id>/dry.json`;
it does not report other articles' numerical diagnostics or resample.

Each `results/articles/<id>/` is a resumable checkpoint:

```text
matching_candidates.json   generated claim/series context, no shapes/scores
matching_audit.csv         agent-authored decisions, evidence and caveats
comparison.csv            generated included pairs, both models
summary.json              generated draft counts/outcomes for this article only
```

All complete articles need checkpoints, including those without claims,
without own-data claims, or without numerical candidates. Empty CSV outputs
still have their headers. An article checkpoint completes an agent task;
it does not constitute curator acceptance and has no `final` mode.

## Assemble the corpus and obtain approval

```sh
.venv/bin/python -m src.comparison aggregate
# Commit derived corpus records before checking readiness.
.venv/bin/python checks/check.py --analysis draft
# Human curator reviews extraction/matching and writes checks/matching_review.json.
.venv/bin/python -m src.comparison build --stage final
# Commit final records before checking readiness.
.venv/bin/python checks/check.py --analysis final
```

Aggregation requires a ledger row for every corpus article and a current
checkpoint for every `complete` article. Pending/unreadable articles remain
explicitly unassessed, never invented negatives. It validates each checkpoint,
merges the unchanged scientific decisions into `results/matching_audit.csv`,
and generates corpus `comparison.csv` and `summary.json`. Only here do
secondary numerical diagnostics cover the whole corpus. The corpus candidate
context records raw bindings to the four source files of each checkpoint.
The independent checker verifies current checkpoints and the merged audit too.

Final requires an unchanged corpus draft, current source checkpoints, no
pending articles and curator acceptance bound to the exact draft inputs.
No command grants or updates approval. Changing a source checkpoint requires
re-aggregation; approval must match the resulting corpus inputs. Scientific
rules, corpus schemas and approval fingerprint paths remain contract v1.

## Responsibilities and audit

- Supplied code enumerates candidates, applies recorded decisions, obtains
  shapes from `tools/`, and calculates comparison records and summary counts.
- AI4Science supplies scientific decisions, evidence, caveats and interpretation;
  it runs the supplied commands and does not modify code or tests.
- The independent checker does not import the generator or use its tally logic.
  Shared low-level snapshot reference traversal is not a scientific tally oracle.
- The human curator reviews extraction and matching. Tests cannot establish
  that reading was thorough or an exclusion scientifically justified.

No network, credentials, live database or resampling are used. The commands do
not extract quotes: ordinary extraction checks still validate PDF evidence.

Audit header, exactly as in `checks/results_spec.md` §5.1:

```csv
claim_id,series_id,decision,assessment,reason,caveats
```

Every same-article/medium candidate of an own-data claim needs one row,
including exclusions. No candidates requires an empty series ID,
`no_candidates`, empty assessment, a reason and explicit caveats. Include by
default, never select by agreement or invent evidence. Qualified/unassessable
inclusions require substantive caveats. Unknown agreement remains empty, not
false. Scientific rules and conservative claim outcomes are in §§5–6.

## Input isolation and recovery

- Article contexts and summaries carry
  `"scope":{"article_id":<id>,"binding":"article-v1"}`. Counts and series
  diagnostics are local; do not present them as corpus prevalence.
- Bind only this article's CSV rows and snapshot reference closure, with
  canonical JSON hashes. Ignore unused shared records, other articles and
  snapshot export time. Bind schema, rules and code as raw bytes. Full details:
  `checks/results_spec.md` §5.5. Shared CSVs must still be syntactically valid.
- Other articles' extraction does not invalidate a checkpoint. Relevant input
  changes stale this article; shared schema/rule/code changes can stale all.
  Archive only the affected article's audit, rerun its preparation and review
  its decisions anew. Do not rebind old scientific decisions mechanically.
- Corrected article decisions require another article build/check and corpus
  aggregation/check. Approval is never automatically refreshed.
- `prepare` and `build` never change an audit, claims or reading attestation.
  Only `aggregate` replaces the *derived corpus* audit; local audits stay intact.
- Unchanged reruns do not rewrite bytes or timestamps. A project lock serializes
  pipeline operations. Concurrent input edits cause failure and require retry.
- Validation/serialization finish before publication. Each rename is atomic,
  summary last; failures trigger rollback. If rollback also fails, original
  backups are retained and their paths reported. A machine/process crash is
  not a multi-file transaction: hashes/checks expose mixed generations.
- Resume the failed article/step, not the entire corpus. Report supplied-code
  failures to the curator; do not patch scientific inputs/code to force a pass.

Legacy corpus-only `prepare` / `build --stage draft` remains supported for
existing outputs, but is not the article-by-article scientific workflow.

## Development checks

```sh
.venv/bin/python -m pytest tests tools/tests checks/tests checks/verifier -q
```

Pipeline tests use synthetic inputs and hand-calculated expectations, including
real-adapter article/aggregation CLI tests, unrelated-input isolation, missing/
stale/corrupt checkpoints, independent checking, curator gates and rollback.
The verifier suite separately retains the pinned numerical reference case.
