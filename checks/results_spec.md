# Results specification

Defines the database tools' output, `results/comparison.csv` and
`results/summary.json`, and what `checks/check.py` verifies. Claims are
defined in `claims_spec.md`. Change this file, `check.py` and
`ontology.yaml` together, never one alone; `check.py` fails when a value
list here differs from `ontology.yaml`.

## 1. Format

- CSV: UTF-8, comma separator, header row, `.` as decimal point, no index
  column, empty field for a missing value, every line ending with a
  newline (the last one too). Fields containing a comma, quote or newline
  are double-quoted (RFC 4180); every row has as many fields as the header.
- JSON: UTF-8, `null` for a missing value.
- `series_id` is `<article_id>-s<k>`, series of one article numbered from 1
  in order of their smallest `experiment_id`, then quantity, technique,
  statistic, weighting and component (missing labels sort as empty strings),
  then the canonical candidate profiles to break remaining ties.
  IDs describe this snapshot and grouping rules, not a permanent identity.

## 2. Series (produced by `tools/`)

A series contains experiments of one article with a gold-only ablation
target and pairwise-compatible fixed conditions. The profile includes every
exported experiment condition except its ids, product colloids, pulse fluence,
pulse energy, average power and spot diameter. In particular it keeps
scanning, duration, beam path, target, medium, feedstock identity and
fractions, gas, and the full ordered post-processing protocol. Shared
objects are compared by their exported contents, not their surrogate ids;
feedstock colloid ids are retained as identities. Constituent, additive and
feedstock list order is immaterial. The product's liquid medium is also
part of the profile. Compare known scalar values exactly in snapshot units;
missing/null scalar values and optional condition subobjects are wildcards,
including missing details inside listed records. Absent/null/empty condition
collections mean none, not unknown: an absent feedstock, additive, beam-path
or post-processing list cannot match a nonempty one. Collections must have
the same length; unordered lists need a compatible one-to-one matching.

Compatibility is symmetric but not transitive. Within an article and exact
measurement kind/statistic, construct all maximal pairwise-compatible
candidate groups, then apply storage, representation and x selection below.
Do not use connected components: a missing wavelength can join both a
532 nm group and a 1064 nm group but cannot bridge those conflicting values.
**Overlapping series are allowed**, even for the same experiment/kind/statistic;
an experiment occurs at most once within each series. Deduplicate identical
selected series after exclusions. Mark surviving series sharing an
experiment/kind/statistic with `overlapping_series` in `notes`.
`condition_key` is only a canonical profile fingerprint, not an equality
key for wildcard grouping. See also METHOD.md §3, Series key.

Size measurement kinds are separated by quantity, technique, weighting,
component and normalized location statistic. After the statistic normalization
below, these labels are exact, not wildcard conditions: an absent label does
not match a stated one. Whole-particle and component sizes never mix, nor do
number- and intensity-weighted sizes. Supported
size quantities are geometric diameter, hydrodynamic diameter and particle
size; unrelated spectra/properties are not size measurements.

**Statistic selection.** Within each article and measurement kind (before
adding statistic to the key), request all scalar location statistics:
`mean`, `mode` (also called `peak`) and `median`. If none occur, request
`mean`. Widths such as SD and FWHM do not request another series. By the
curator's project assumptions, scalar `z_average` is normalized to `mean`,
and a missing scalar statistic is treated as `mean`; original labels and
these assumptions remain on the points. The snapshot schema normally
requires a statistic. Other scalar size statistics get an explicit
unsupported-statistic diagnostic, not a fabricated conversion.

All members use the shortest storage duration available in every member
for this kind/statistic. Null is a distinct duration, not zero, and is
chosen only if no common numeric duration exists. Do not split or salvage
a group with no common duration. At that duration, prefer a matching
scalar, then a histogram, then a curve. Multiple candidates at the same
priority are ambiguous and that experiment is excluded with a diagnostic.

**x.** Prefer fluence (J/cm²) when every member has it; otherwise use pulse
energy (µJ) when every member has it. Spot diameter is excluded and imposes
no additional condition, whether stated, missing or varying, for either
x choice. Never derive fluence. Missing x is not a condition wildcard. A
series needs at least two distinct x values; repeated x values are
excluded as an ambiguous series rather than averaged or ordered
arbitrarily. Unusable groups and points are returned by `list_exclusions`.

**size.** Use the matching scalar when present. For histograms, mean is
`Σ nᵢ·cᵢ / Σ nᵢ`, with cᵢ the stored bar centre; median interpolates within
the bar containing half of the counts. Mode MUST come from a fitted
zero-location lognormal, not the tallest bin: fit amplitude, log-scale
and log-width by least squares against the integrated mass in each stored
bar extent, then take its global density maximum `exp(mu - sigma²)`.
Require at least three positive bars; report failed/degenerate fits.
The fit residual is retained on the point. Stored bar extents can differ
from true bin boundaries; this is a fitting limitation.

For curves, sort a descending x array into ascending order, require
strictly monotone nonnegative x, finite nonnegative y and positive area. Mean and SD
use trapezoidal integration; median is the half-area point of the
piecewise-linear curve; mode is the smallest x attaining the global y
maximum. Treat ALL size-curve y values, including DLS, as ordinary
densities over the stored diameter d: mean = `∫d*y dd / ∫y dd`.
No logarithmic integration, Jacobian or exponentiation of x is used.
This deliberate toy-project approximation overrides the snapshot schema's
DLS y convention; it does not change the snapshot or database.

**size_err** is a fixed relative tolerance on every selected particle size,
not a measured standard error: `size_err = f × size` with `err_source` =
`fixed_relative` (§3). Reported SE, SD and particle counts do not override it.
Preserve source, colloid id, original statistic, SD, explicitly reported N,
error source and assumptions as metadata. Never infer N from digitized counts.

**medium_class**, the first that applies: `colloid` (contains a feedstock
colloid), `water` (one water constituent and no additives), `aqueous`
(water with additives), `organic` (one non-water liquid), `other`. Use stated
synthesis-medium information across selected members, not just the first
member if its condition details are missing.

**pulse_duration_class.** `fs` below 1e3 fs, `ps` below 1e6 fs, else `ns`.
Series wavelength and pulse duration use the stated value among selected
members; null only if all members lack it. These scalar fields cannot have
conflicting stated values in one compatible series. Original point/snapshot
values are not imputed.

## 3. Shape

Two tolerance models apply to every point: `primary` uses
0.10 × `size`, `lenient` uses 0.20 × `size`. Each series gets a shape under
each model.

Take the points in order of increasing `x`; the anchor is the first point.
For each next point, a change is counted when
`|size − anchor_size| > √(size_err² + anchor_err²)`; its sign is recorded if
it differs from the last recorded sign, and the point becomes the anchor.

| Recorded signs | Shape |
|---|---|
| none | `flat` |
| + | `increasing` |
| − | `decreasing` |
| +, − | `peak` |
| −, + | `valley` |
| three or more | `irregular` |

## 4. Tool contract

`tools/ablation_db.py` reads only the committed
`data/ablation_snapshot.json`, never a database or credentials, and returns
plain JSON-ready Python data. Its pure calculations live in `tools/series.py`.

| Function | Returns |
|---|---|
| `find_articles(material="Au")` | list of `{article_id, doi, title, year, n_experiments}`, including articles with no usable series; missing DOI/year are null |
| `list_series(article_id)` | list of series rows, columns below; `[]` for an article absent from the snapshot |
| `get_series(series_id, model="primary")` | `{"series": <row>, "points": [...]}` with point errors under the requested model |
| `list_exclusions(article_id)` | list of `{article_id, experiment_ids, reason, detail}`, including unusable measurements/groups |

Series row: `article_id, series_id, n_points, x_quantity, size_quantity,
size_statistic, size_technique, size_weighting, size_component, size_source,
storage_duration_h, pulse_duration_fs, pulse_duration_class, wavelength_nm,
medium_class, shape_primary, shape_lenient, spearman_rho, notes`.
`size_source` is `scalar`, `histogram`, `curve` or `mixed`. Undefined
Spearman correlation (constant sizes) is null, never NaN.

Points are sorted by x and contain `experiment_id, colloid_id, x, size,
size_err, err_source, size_source, original_statistic, sd, particles_counted,
assumptions, fit_residual`. Derived points have null original statistic;
fit residual is null except for histogram mode. Optional metadata stays
null rather than being invented.

`SnapshotTools(path)` reads a particular snapshot once for callers/tests
that need a fixed view. Module-level convenience calls load the default
snapshot afresh: there is no stale global cache. Returned dictionaries are
independent, so mutating a response cannot corrupt subsequent calls.
Only `Au`/`gold` is supported by this gold-only snapshot. Unsupported
material/model or malformed IDs raise ValueError; an unknown well-formed
series ID raises KeyError. Missing/corrupt files and unsupported format or
units fail explicitly, never falling back to another source.

Tool tests: `.venv/bin/python -m pytest tools/tests -q`. These are unit and
adapter integration tests, not the HW2 verifier or resampling experiment.
For a fresh checkout, create a Python 3.12 virtual environment with
`python3.12 -m venv .venv`, then install the pinned tool/test dependencies
with `.venv/bin/python -m pip install -r requirements.txt`. Run commands
from the project root; the course agent cannot install packages itself.

## 5. Auditable claim–series comparison (working contract v1)

This is a provisional, curator-adopted contract, not a scientific result.
A later change must be disclosed in `diary.md`, increment the contract
version and regenerate affected outputs and matching approval. Never
reinterpret old outputs under new rules without rerunning the pipeline.
The generator in `src/comparison/` and its tests in `tests/` are supplied
infrastructure. AI4Science runs the code and supplies scientific matching
decisions, evidence and caveats; it does not write or modify the pipeline.
The protected checker independently verifies records and tallies; it cannot
judge a scientific exclusion, a caveat or whether reading was thorough.
The generator must not import/call the checker or reuse its tally oracle as
its own test oracle: its implementation and tests follow this specification.

### 5.1 Candidates and `results/matching_audit.csv`

After blind extraction is recorded, generate candidates for **every
`own_data` claim of a completely reviewed article**, including claims
with `variable=unspecified`. Candidates are all series of the same
article with the same medium; a claim medium of `unspecified` permits
every series of that article. Do not add variable, material, wavelength,
pulse-duration or measurement-statistic filters at candidate generation.
Pooling laser variables for prevalence is not physical equivalence and
does not justify a numerical proxy.

Include candidates by default. The agent may exclude a pair for a
substantive, evidence-backed reason, but must audit **every** candidate,
including inclusions, without seeing agreement as a selection criterion.
Explain scientific judgments, cited text/conditions, assumptions and
limitations in the audit; the human curator reviews them before final aggregation.

Header (exact order):
`claim_id,series_id,decision,assessment,reason,caveats`.

- Exactly one row per candidate pair, even excluded pairs. No duplicates.
- If a claim has no candidates, exactly one row with empty `series_id`,
  `decision=no_candidates`, empty `assessment`, and a reason.
- Every row has nonblank `reason` and `caveats`; write `none` explicitly
  for no identified caveat, not an unexplained empty field.
- An included pair has an assessment: `direct` (comparable on the
  stated terms), `qualified` (a defensible proxy/assumption, explicitly
  conditional), or `unassessable` (retain the candidate but no defensible
  agreement judgment). Qualified/unassessable pairs need substantive caveats.
- Excluded/no-candidate rows leave assessment empty.
- `cited` and `general` claims contribute to prevalence, not direct
  numerical comparison. They get neither audit nor comparison rows.

Controlled values (also in `ontology.yaml`):

| Attribute | Values |
|---|---|
| `matching_decision` | `include`, `exclude`, `no_candidates` |
| `assessment` | `direct`, `qualified`, `unassessable` |
| `claim_outcome` | `all_agree`, `all_disagree`, `mixed`, `unassessable` |

### 5.2 `results/comparison.csv`

Exactly one row per **included** audit pair, both models in the same row.
There are no unmatched or excluded placeholder rows here; those remain
visible in the audit and summary.

| Column | Type | Rule |
|---|---|---|
| `claim_id` | str | from `results/claims.csv`, `own_data` only |
| `series_id` | str | included audit pair, never empty |
| `direction` | str | the claim's |
| `shape_primary`, `shape_lenient` | str | the series' (§3), even if unassessable |
| `agree_primary`, `agree_lenient` | bool | lowercase `true`/`false` by the table below; both empty for unassessable |
| `assessment` | str | exactly the audit's assessment |
| `note` | str | explanation/caveat reference; `none` if genuinely none |

Header order is the table order, expanding paired columns left to right.

| `direction` | Agrees with shape |
|---|---|
| `increase` | `increasing` |
| `decrease` | `decreasing` |
| `no_effect` | `flat` |
| `non_monotonic` | `peak`, `valley`, `irregular` |
| `affects` | any shape but `flat` |

Agreement is directional concordance under the recorded comparison
assumptions, **not proof or unqualified verification/contradiction**.
Qualified results remain labelled and separately counted; uncertain
proxies must not acquire a boolean by silently treating unlike variables
as identical.

### 5.3 Claim-level outcomes (separately per model)

Aggregate all included pairs of each own-data claim, not a majority vote:

- Both true and false present → `mixed`, regardless of other unknowns.
- At least one included pair and **all** true → `all_agree`.
- At least one included pair and **all** false → `all_disagree`.
- Otherwise → `unassessable`: no included series, only unknowns, or a
  one-sided result with an unknown. Never call partial evidence “all”.

A claim with two agreeing series and one disagreeing series is mixed,
not “agreement by 2/3”. Keep qualifications and counts alongside the
claim outcome. Pair-level counts are secondary: more series in an
article must not silently give that article greater prevalence weight.
Claim-outcome counts are descriptive **claim-level** counts, not an
article-level agreement estimate or independent observations.

The legacy graph verdict projects these two outcomes: no included series →
`unmatched`; either model mixed → `mixed`; otherwise either unassessable →
`unassessable`; both all-agree → `agrees`; both all-disagree → `disagrees`;
remaining fully assessable differences → `model_dependent`. Graph notes retain
both model outcomes and the number of qualified pairs. No comparison file →
no verdict. Graph labels do not replace the full audit or curator gate.

### 5.4 Article-sized steps and checkpoints

Complete one article's blind extraction, comparison and checks before moving
to the next. Do not wait for the other articles to be extracted:

```sh
.venv/bin/python -m src.comparison prepare --article <id>
# AI4Science writes results/articles/<id>/matching_audit.csv.
.venv/bin/python -m src.comparison build --article <id> --stage draft
# Commit the records, then:
.venv/bin/python checks/check.py --article <id> --analysis draft
```

Only this article must have a current `complete` reading attestation and
claims XOR one no-claims record. Other articles need not have ledger rows
yet. Candidate, audit and comparison rules remain §§5.1–5.3. Every complete
article needs a checkpoint, including no-claim articles, cited/general-only
articles, and articles without usable numerical series. Empty audit and
comparison CSVs still have their exact headers.

The isolated directory `results/articles/<id>/` contains:

- `matching_candidates.json`: `format=1`, `scope`, `inputs` and `candidates`.
  Each candidate holds the full extracted `claim` and candidate `series`
  metadata (`null` if none). Shapes and Spearman correlation are omitted.
- `matching_audit.csv`: the agent's scientific decisions, exactly §5.1.
- `comparison.csv`: generated included pairs, exactly §5.2.
- `summary.json`: the §6.2 counting rules applied to this article only,
  plus `"scope":{"article_id":<id>,"binding":"article-v1"}`.
  Stage is always `draft`; `n_corpus=n_complete=1`; secondary series
  diagnostics cover only this article. This is not a corpus result or approval.

The scope marker is identical in candidates and summary. `prepare` invents
no decisions, assessments, evidence, reading attestations or approval.
Do not edit generated context. Build recomputes it and requires it unchanged.
If this article's preparation inputs change while its audit exists, archive
only that audit, prepare again, and re-review the matching decisions. Do not
merely rebind old decisions. Other articles' checkpoints remain usable.

### 5.5 Article input binding (article-v1)

The scientific contract remains v1; this execution binding is separate from
the corpus raw-byte approval map in §6.2. Article checkpoints use the same
input paths except audit/comparison are located under `results/articles/<id>/`,
and additionally bind raw `tools/snapshot_scope.py` bytes.

For `data/corpus.csv`, `data/files.csv`, `results/claims.csv`,
`results/no_claims.csv` and `results/extraction_status.csv`, bind only rows
whose `article_id` is exactly the selected decimal ID. Sort full row objects
by their canonical JSON bytes, serialize the list canonically and SHA-256 it.
Row values remain strings. Unrelated rows, row order and CSV whitespace do
not stale this article; all shared CSV files must still be well formed.

For the snapshot, keep the selected article and the transitive closure of
shared records (`x-shared`) and referenced colloids (`x-document`) reached
through its JSON Schema. Stocks can reside in another article or in
`referenced_colloids`; include their own dependencies. Retain interpretation
headers and omit unrelated articles and unused shared records. Exclude only
`exported_at` from the binding, not from the schema-valid numerical view.
Canonical JSON means UTF-8, `ensure_ascii=True`, sorted object keys,
`separators=(",", ":")`, no nonfinite numbers. This projection is a read-only
view; it never changes the frozen snapshot or fabricates its provenance.

All other inputs, including schema, ontology, scientific specs and checker/
numerical code, retain raw-byte hashes. The two local audit/comparison files
are raw-byte hashed. Preparation excludes those two paths; summary includes
them. Relevant data, PDF inventory, attestation or shared rules/code changes
stale the checkpoint; unrelated article work does not. Numerical construction
and the checker use only the selected article's view, not all-corpus series.

### 5.6 Corpus assembly and failure recovery

After article work, run:

```sh
.venv/bin/python -m src.comparison aggregate
# Commit the derived corpus records, then:
.venv/bin/python checks/check.py --analysis draft
```

Aggregation requires an explicit status for every corpus article and a
current, generated checkpoint for every `complete` article. It rejects
missing, stale or edited contexts/comparisons/summaries; pending/unreadable
articles remain explicitly unassessed, never invented negatives. It merges
article audits without changing decisions, then generates the corpus audit,
comparison and §6.2 summary. Full-corpus numerical diagnostics run here, not
during article tasks. The corpus candidate context also records
`checkpoints`: raw SHA-256 bindings to the four files of every complete
article. The generator and independent checker validate these bindings and
the merged audit; changing a checkpoint requires re-aggregation. Article
outputs and curator approval are never overwritten by aggregation.

`build --stage final` is corpus-wide only. It requires the existing unchanged
generated corpus draft, current source checkpoints, no pending articles and
the exact curator approval in §6.3. Draft/final comparison bytes are identical;
only summary stage changes. An article checkpoint is not curator acceptance.
Corpus schema and approval input paths in §6.2 remain unchanged. Legacy
corpus-only preparation/build remains readable, but is not the agent's
article-by-article workflow.

All commands validate before publication and never change claims or reading
attestations. `build` never writes an audit or approval. Only `aggregate`
replaces the derived corpus audit. Rerunning unchanged operations leaves
bytes and timestamps unchanged. Input changes during an operation fail closed;
a local lock serializes pipeline commands. Each file is replaced atomically,
summary last. Publication errors trigger rollback; if rollback fails, original
backups are retained and reported. A process/machine crash is not a multi-file
transaction: fingerprints and fresh checking expose mixed generations.
Resume the failed article/step; do not reset successful articles.

## 6. `results/summary.json` and curator gate

### 6.1 Article-level frequency

Read `results/extraction_status.csv` (claims_spec §9). Only `complete`
articles enter the denominator: main text and **all supplied SI** reviewed.
Unread/unreadable is unassessed, never a negative. The corpus is selected
(completed, curated, gold-only articles), not representative of all literature.

The primary numerator counts each complete article at most once if it has
at least one claim for `fluence`, `energy`, `power` or `intensity`,
including no-effect claims and any basis. This pools categories only, not
physical quantities. Preserve original labels in claims.csv. Report
articles with unspecified-variable claims separately; those claims never
enter the primary numerator. No separate variable-specific significance tests.

Basis and direction breakdowns count **articles**, not sentences or claims,
using the same four specified variables. Categories may overlap; an
article can appear in several cells, but at most once in any cell.

### 6.2 Exact summary schema, version 1

This is the corpus schema; article checkpoints use the scoped variant in §5.4.
All keys below are required, no extra keys. Counts are nonnegative JSON
integers (not booleans), fractions/p-values are finite numbers or null.
Every enum-indexed object includes all allowed values, including zeros.
All own-data claims below are from complete articles; include unspecified
variables. Retain claims with no candidates and with all candidates excluded.

Top-level keys:

- `contract_version`: integer `1`.
- `stage`: `draft` or `final`.
- `inputs`: raw-byte SHA-256 map with exactly the relative paths below.
- `articles`:
  - `n_corpus, n_complete, n_pending, n_unreadable`.
  - `prevalence: {numerator, denominator, fraction}`; denominator =
    n_complete, fraction = numerator/denominator or null for zero denominator.
  - `n_with_unspecified_claim`: complete articles with ≥1 unspecified claim,
    overlapping the primary numerator if other claims qualify.
  - `by_basis`, `by_direction`: article counts by their respective enums.
  - `by_basis_and_direction`: basis → direction → article count.
- `comparison`:
  - `n_own_data_claims, n_with_candidates, n_without_candidates,
    n_with_included_series, n_all_candidates_excluded, n_candidate_pairs,
    n_included_pairs, n_excluded_pairs`. Candidate pairs exclude no-candidate
    placeholder rows; the three claim coverage groups (no candidates,
    all excluded, ≥1 included) partition own-data claims.
  - `claim_outcomes`: claim_id → `{primary, lenient, n_included,
    n_qualified, n_unassessable}`. Every own-data claim appears, including
    unmatched claims (unassessable in both models, zero counts).
  - `by_model`: primary/lenient → object with:
    - `claims: {denominator, all_agree, all_disagree, mixed, unassessable}`,
      denominator = all own-data claims, not only matched/assessable ones.
    - `pairs: {n_included, n_assessable, agree, disagree, unassessable}`;
      n_assessable = agree + disagree; n_included additionally includes unknowns.
    - `pairs_by_assessment`: direct/qualified/unassessable → the same
      pair-count object. These prevent proxy concordance masquerading as
      unconditional validation. Any displayed pair agreement fraction uses
      n_assessable as denominator and shows excluded/unassessable counts.
- `series`: primary/lenient → `{counts, n_test, p_value}`:
  all corpus series counted once per series_id, all six shapes including zeros.
  n_test = increasing + decreasing. Retain the previous secondary
  `binomtest(increasing, n_test, 0.5, alternative="greater")` definition,
  null for n_test=0. This is an exploratory series-level diagnostic, not the
  primary claim statistic. Overlapping series and article clustering violate
  independent-series sampling; do not present this p-value as independent
  article-level evidence. No additional inference is prescribed here.

Exact `inputs` paths (same map in curator approval):

```text
data/corpus.csv
data/files.csv
data/ablation_snapshot.json
data/ablation_snapshot.schema.json
results/claims.csv
results/no_claims.csv
results/extraction_status.csv
results/matching_audit.csv
results/comparison.csv
checks/claims_spec.md
checks/results_spec.md
ontology.yaml
checks/analysis.py
checks/check.py
tools/ablation_db.py
tools/series.py
```

Hash bytes as stored, including whitespace. No self-hash of summary or review;
do not bind to a moving Git HEAD. Changes to inputs, comparison decisions
or the contract invalidate approval and require regenerated outputs.

### 6.3 Draft → review → final

1. AI4Science completes article checkpoints, then runs
   `.venv/bin/python -m src.comparison aggregate` to assemble the corpus draft.
   After records are committed, `checks/check.py --analysis draft` checks
   completeness, duplicate/missing pairs, shapes, booleans, fingerprints and tallies.
2. The human curator reviews every inclusion/exclusion, reason and caveat. Corrections
   require a new draft; no selecting only agreeing series.
3. Only the curator writes protected `checks/matching_review.json`:
   exactly `{"decision":"accepted","reviewer":"<name>",
   "date":"YYYY-MM-DD","inputs":{...}}`, using the checked draft's inputs map.
   An agent cannot grant itself approval.
4. The agent runs `.venv/bin/python -m src.comparison build --stage final`
   after approval, commits the generated records and runs
   `checks/check.py --analysis final`, which additionally requires no pending
   articles and an exact matching approval. Unreadable articles stay explicitly
   outside the prevalence denominator. An accepted draft is not a final result.

No approval file or scientific outputs are fabricated by infrastructure setup.
The checker does not import src/, extract claims, judge physical matching,
run resampling or produce comparison/summary files.

## 7. What `check.py` verifies

1. Every file parses and has exactly the columns, keys and allowed values
   of the specs.
2. Every PDF in `data/articles/` matches its SHA-256 in `data/files.csv`,
   and every claim's quote is found on its page of its file
   (`claims_spec.md` §4).
3. With `--analysis draft` or `--analysis final` only: the audit is exhaustive,
   comparison contains exactly its included pairs, and agreement follows §5.
   Claim-only checks never load numerical tools or analysis outputs.
4. In analysis mode, summary keys, fingerprints, denominators and all tallies
   follow §6. Final mode also requires the curator's matching approval.
   `--analysis draft --article <id>` checks only that complete article's
   checkpoint, including its projected input binding; no other article's
   attestation or numerical comparison is required. Final is corpus-wide only.
   Corpus checks also verify any source article checkpoints and their merge.
   Claim-only checks retain
   legacy behavior if no extraction ledger exists; this does not certify
   complete reading or analysis readiness. Once present, the ledger is checked.
5. Reference article 80094 (series reference verified separately in
   `checks/verifier/`; the table illustrates a direct comparison when included,
   not a compulsory extraction label or an exception to auditable matching):

| Claim | Series | Shape primary / lenient | Agrees primary / lenient |
|---|---|---|---|
| Au in water, `increase`, `own_data` | `80094-s1` | `increasing` / `increasing` | yes / yes |
| AuSi in Si colloid, `no_effect`, `own_data` | `80094-s2` | `peak` / `flat` | no / yes |

6. Extraction quality is reviewed by the human curator for the fixed corpus
   of 41 articles, including claims and no-claim judgments. The automated
   checks do not establish semantic correctness or that no claims were missed.
   Record the curator's actual review and any corrections; never fabricate
   a verdict. This review does not replace the matching approval in §6.3.
