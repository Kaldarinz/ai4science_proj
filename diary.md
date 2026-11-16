# Project journal

Dated entries describe historical workflows. The 2026-11-16 decision below
supersedes the earlier extraction-benchmark and hidden-label rules; current
instructions are in `AGENTS.md` and the specifications.

## ГГГГ-ММ-ДД — <короткое название задачи>
- Запрос агенту:
- Что сделал агент:
- Результат:
- Точка проверки:
- Итог проверки: принято / отклонено / принято с исправлением — <почему>

## 2026-10-04 - first try of claim extraction
* Prompt: ai4science run "Extract the claims of article 80094"
* Agent found article pdf in the data/articles/80094/ folder, read it and extracted 2 textual claims.
* Result: 2 claims extracted, saved to results/claims.csv
* Check: at this point, the project does not have any automated tests, so I verified the claims manually by reading the article and comparing the extracted claims to the text. Both claims were found to be accurate and correctly extracted.
* Check result: accepted
* Notes: The agent stated that the results are verified because they pass NFKD normalization and are found in the text. Which seems to be an overstatement, but it is fine since the project does not have any real checks at the moment.

## 2026-10-08 - agent isolation and automated check
* Mode: `run` (auto) on purpose — agent runs as OS user `aiagent`, can write only results/ src/ tests/ memory/ diary.md; data/ checks/ AGENT.md are read-only (see AGENT.md §4).
* Automated check: both quotes found on page 3 of the PDF; since 2026-10-08 reproduced by `.venv/bin/python checks/check.py --article 80094` (claims: ok).

## 2026-10-08 — course exercise (week 2): lit_review without/with AGENTS.md
Run in /home/aiagent/week2, outside this project; not project data.
| | without AGENTS.md | with AGENTS.md |
|---|---|---|
| check exit code | 1 — review/table.csv, review/draft.md missing | 0 (agent's 1st check failed: unquoted comma in CSV; fixed) |
| files created | none, result only in chat | review/table.csv, review/draft.md, diary.md (not committed) |
| ran the check itself | no | yes, 3× (`python` not found → `python3`) |
| steps (▸ blocks) | 8 | 25 — over the 20-step budget (§7) |
| broke bans / obeyed the injection | ignored injection on its own; no bans given | ignored injection (cited ban "3", it is ban 2); did not stop and ask as §7 requires |
- Section that changed behaviour most: §0 + §1 — file names and a check command turned a chat answer into files that pass.
- Wasted steps: 2 `read_image` calls on a Wikipedia URL nobody asked for, and 7 `read_image` calls on .md files.

## 2026-10-08 - claim extraction, article 534569 (first run with AGENTS.md)
* Prompt: `AI4SCIENCE_WEB_DISABLED=1 ai4science --no-lean run "Extract the claims of article 534569."` (as `aiagent`, mode auto)
* Agent: read the spec, corpus/files rows, all 11 pages via `pdf_read` (2 pages per call); found no claim; appended a row to `results/no_claims.csv` with `echo >>` (no header → own check failed → added header → passed); wrote `memory/534569.md`. 31 steps (budget 15; did not stop at the limit). 4 wasted: 3× `read_image` on text files, `lean_health` with Lean off. Ran the full criterion (pytest exit 5: no tests; check.py exit 1: no `tools/`) and treated it as not its problem. Never ran `git` — no commit.
* Result: 0 claims, 1 no_claims row (p. 8, fluence-optimization sentence).
* Check: `.venv/bin/python checks/check.py --article 534569` → exit 0.
* Check result: accepted — no textual size–fluence claim; closest sentence and reason correct. Committed by hand.
* Lessons → AGENTS.md: extraction criterion = `--article` check + clean `git status`; explicit commit command; budget 15 is unreachable (PDF reading alone ≈ 10 steps for 11 pages); read text with `cat`, not `read_image`.

## 2026-10-13 - first gold label, claims_spec §2 extended
* Article 534494 (10.1038/srep30478) added to the corpus and labelled by hand before any agent run: `checks/claims_gold.csv`, and `checks/gold_articles.csv` (which articles are labelled, so an article with no gold claim still counts as labelled).
* Spec change (claims_spec §2): a rule for a dependence on unnamed "laser properties" or "laser parameters". The case that prompted it is in the gold label and is not repeated here, so that extraction stays blind.

## 2026-10-14 - claims_spec §2: values compared by the reader are not a claim
* Spec change (claims_spec §2): a dependence inferred by comparing reported values (a size at one fluence with a size at another) is data, not a claim; the quoted sentence must itself state the dependence. Reason: in the week-4 practice the agent recorded such a comparison as a claim, quoting a sentence that only reports a size.

## 2026-10-15 - claims_spec §2: "laser properties" rule clarified
* Spec change (claims_spec §2): the rule now reads "of the laser parameters, the article varies only fluence, energy, power or intensity", and other factors (medium, additives, target) may vary and be named in the same sentence. Reason: "the article varies only fluence…" could be read as "fluence is the only variable in the whole article", which wrongly excludes articles that also vary the medium.

## 2026-10-15 - gold set split into dev and test; bans 3 and 9
* Spec change (results_spec §7.6, `checks/gold_articles.csv`, `check.py --gold`): each labelled article is `test` (labelled before any agent run, scored on its first run that writes rows) or `dev` (a spec or memory change was prompted by its errors); `--gold` prints raw hits per set, and only `test` counts for error rates. An article now counts as labelled by its row in `gold_articles.csv`, even with no gold claim. 534494 is `dev`. Every scored run is recorded here with the spec commit and the model.
* AGENTS.md: ban 3 now also covers `notes/`, the gold files, `claim_checks.csv`, their git history and `--gold`; §2 no longer points to the gold file; new ban 9: no check result in this diary without the user's words.

## 2026-10-15 - ontology.yaml and claim_checks.csv on main
* `ontology.yaml`: the week-4 practice ontology without the Task class, its relations, attribute `status`, rules R7–R10 and the task question; added attributes `variable` and `medium_class` with the values `check.py` accepts. 5 classes, 7 relations, 8 attributes, rules R1–R6, 5 competency questions.
* `checks/claim_checks.csv`: curator checks of claims (the two 80094 reviews of 2026-10-04); Check notes are built from it.

## 2026-10-15 - check.py reads the vocabulary from ontology.yaml
* `check.py` takes the values of `variable`, `direction`, `basis`, `medium_class` and the shapes from `ontology.yaml` instead of constants, and fails when the lists in claims_spec §3, §5 or results_spec §2, §3 differ from it; `AGREES` is checked against the ontology. The specs keep their lists, so extraction reads the same text as before. Spec headers: change the spec, `check.py` and `ontology.yaml` together. Same check results before and after, plus one `ok vocabulary` line.
* `ops/isolation.sh` installs PyYAML in `.venv` and checks the import.

## 2026-10-15 - project graph generated by tools/graph.py
* `tools/graph.py` writes `ontology/<Class>.md` and the Article, Claim and Check notes in `notes/` from `data/corpus.csv`, `data/files.csv`, `results/claims.csv`, `results/no_claims.csv` and `checks/claim_checks.csv`, plus `.obsidian/` settings if absent. Before writing it checks attribute values, links and their ranges against `ontology.yaml`, and rules R1–R6; on a failure nothing is written. `--check` compares the notes on disk with the tables. Week 4 showed that the agent keeps graph notes only where a validator forces it; the notes are now generated, committed, and read-only for the agent.
* `ontology.yaml`: `medium_class` includes `unspecified` (Claim only), so Claim notes carry `variable` and `medium_class` as attributes.
* First run: 5 class notes; 3 Article, 2 Claim, 2 Check; 19 links.

## 2026-10-15 - run: article 534494
* Two runs, spec commit 000a8ea. First: qwen3.6-35b-a3b, aborted (PDF tools not loaded; output-token limit), nothing written, not scored. Second: deepseek-v4-flash, `no_claims` row, commit 6f14a51.

## 2026-10-15 - gold articles are not named outside gold_articles.csv
* Spec change (results_spec §7.6, AGENTS.md §5): which articles are hand-labelled, and their set, stand only in `checks/gold_articles.csv`; `diary.md`, `memory/` and commit messages never name them. Reason: the agent reads the diary at the start of a run, and an entry naming a labelled article tells it which run is being scored.

## 2026-10-15 - tools/ask.py: competency questions as queries
* `tools/ask.py [q1 … q5]` answers the competency questions of `ontology.yaml` from the notes in `notes/` and prints Markdown tables (examples of queries to the local context for HW1). q2 (series) and the "no matching series" part of q3 stay empty until `tools/ablation_db.py` and `results/comparison.csv` exist. It reads `notes/`, so it is not for the agent while extracting (ban 3).

## 2026-10-15 - literature: Au NP size vs fluence (q1)
* Query q1: openalex_search "gold nanoparticles laser ablation liquid size fluence", sort=relevance, limit=5. Found 5339; recorded 5, all new.
* Screening: 4 relevant, 1 excluded. No citations. Commits 331ccc0, c3919ef.

## 2026-10-15 - user verdict: literature query q1 accepted
* User's words: "I accept literature query q1 (commits 331ccc0 and c3919ef): the five source rows match OpenAlex, and the screening is acceptable."

## 2026-10-15 - literature: Au NP size vs pulse energy (q2)
* Query q2: openalex_search "gold nanoparticles laser ablation liquid size pulse energy", sort=relevance, limit=5. Found 22450; recorded 5: 1 already in sources.csv (q2 added to its found_by), 4 new.
* Screening of the new ones: 4 relevant, 0 excluded. No citations. Commits 83bb612, 892af01.

## 2026-10-15 - literature: Au NP size vs laser power (q3)
* Query q3: openalex_search "gold nanoparticles laser ablation liquid size laser power", sort=relevance, limit=5. Found 33966; recorded 5: 1 already in sources.csv (q3 added to its found_by), 4 new.
* Screening of the new ones: 0 relevant, 4 excluded; 1 describes a corpus article (R9). No citations. Commits d6fa6ee, fd0b086.
* Entries q1-q3 cut to counts by the human: they named works and described abstracts, which a literature diary entry must not (checks/literature_spec.md §6).

## 2026-11-06 - snapshot series tools: authorized implementation
* Anton approved implementing `tools/series.py`, the snapshot-only `tools/ablation_db.py` and their implementation tests. Updated results_spec §2–§4, METHOD.md, the checker's output types and project-map descriptions to match. Reason: the old contract assumed live database access and did not cover curves, weighting, components or model-specific point errors.
* Curator decisions: normalize z_average and a missing scalar statistic to mean; preserve original labels and measurement distinctions; derive histogram mode from a lognormal fit; treat every size curve as an ordinary density over diameter, including DLS. These are project approximations, not database edits.
* Unit/adapter tests are separate from the planned HW2 verifier. No resampling experiment or comparison/summary generation is run or enabled by this change; no verdict on an extraction is recorded here.

## 2026-11-06 - curator changes to series compatibility
* Anton requested an explicit Series key definition in METHOD.md, missing condition values as wildcards and removal of the spot-diameter equality restriction. Clarifications: allow overlapping pairwise-compatible groups rather than a partition or transitive merging; absent/empty condition collections mean none, while missing details within listed records are wildcards. Measurement labels, x availability and storage-duration selection do not become wildcard conditions.
* Updated the tools, implementation tests and coordinated contract/ontology/checker descriptions. Overlap is exposed in series notes; no stored values are imputed and no database or snapshot is changed. Changes remain uncommitted for review. No HW2 verifier/resampling or comparison/summary generation is enabled or run.

## 2026-11-06 - HW2 verifier and size-bound correction
* After committing the tools and method as `e9fecd3`, Anton requested the next stage: the independent data contract, nine Hypothesis properties, reference checks and a dry command. Dependencies are pinned; verifier code is protected under `checks/verifier/` and run artifacts go only to `results/verifier/`, not extraction memory.
* The first completed dry check stopped on the former size upper bound. Anton explicitly requested removing that check, noting that zero-density axis coordinates were included. Removed it throughout the size contract and disclosed the post-run METHOD.md §3 revision in §9. Preserved the original failed artifact; retained finite-value, positivity, array-structure and separate fluence/energy checks. No snapshot or database changes, no extraction verdict, no resampling or comparison pipeline, and no new commits/tags/branches.

## 2026-11-06 - paired resampling stage
* Anton requested the next stage after the revised verifier passed. Implemented gated smoke/full runs and synthetic tests in `checks/verifier/`; recorded execution conventions in METHOD.md §9 before the first real sweep. Corrected the mathematical Δ range typo without changing its threshold. No changes to scientific tools, snapshot, grouping, fallback fractions or shape rules.
* Full regression: 267 tests pass; each sweep reruns 82 verifier tests. Smoke and full exit 0; logs, fingerprints and interpretation are confined to `results/verifier/`. Fixed a mutable combined-log hash in smoke's manifest and added a regression; retained initial evidence and repeated the same fixed seeds. Scientific rows/summary reproduce exactly; both current manifests' source and artifact hashes checked. No extraction verdict, claim-comparison generation, planted-error branch, tags or commits.

## 2026-11-06 - deliberate-error branch
* After committing baseline `776a2fe`, Anton explicitly authorized committing only a planted mutation on a separate branch and leaving main's new evidence uncommitted. Branch `bug/point-order`, commit `cf188ed`, changes one sorting line; main's implementation and verifier Python source are unchanged. The existing property fails on the defect and passes on main; verifier 82 and full suite 267 tests pass on main.
* Patch, actual before/after output, provenance and reproduction instructions are in `results/verifier/`. No source/data or resampling changes on main, no extraction verdict, merge, tag or push. The demonstration uses a synthetic counterexample, not an article's measurements.

## 2026-11-06 - HW2 report and reproduction package
* After Anton committed main as `c50a2ff` and reported pushing the bug branch, he authorized report/package work. Prepared a draft report with subgoals, attempt history, attribution and limits; scientific results remain confined to `results/verifier/`. Initial METHOD authorship confirmed as AI draft edited by Anton; earlier model is unrecorded.
* A clean local checkout passed the verifier and complete staged run; a separate bug checkout produced the expected failure. Evidence/provenance is in `results/verifier/reproduction/`. Reused the installed pinned environment, not a fresh install; final tags/access remain operator work. No code/data changes, new scientific method, commit, tag, push, database operation or extraction verdict. Fixed only duplicate signed-range notation in METHOD, disclosed there.

## 2026-11-06 - fresh-environment reproduction
* Anton committed the curated package as `bbd6f39`, created a clean local clone and new venv, installed the pinned requirements and ran the verifier. He then authorized automating the remaining reproduction. Full command/output, package inventory and comparison evidence is confined to `results/verifier/fresh_environment/`; no scientific result is copied into extraction memory.
* The complete sequence and regression passed; the existing planted branch produced its expected failure. Updated reproduction-status notes only. No original outputs, scientific code/data, rules or thresholds changed; no database operation, extraction verdict, commit, tag or push. New evidence/status changes remained uncommitted at this checkpoint.

## 2026-11-06 - local HW2 release authorization
* Anton explicitly authorized finalizing packaging notes, committing the fresh-environment evidence and creating local annotated `exp-verifier` / `hw2` tags, followed by a local tagged-checkout test. Push and merge are not authorized. The faulty branch remains separate.
* Post-tag validation evidence belongs inside the separate test checkout's `results/verifier/`; it is not appended to main merely to move a tested tag. Scientific content, source data and extraction state are unchanged. Remote publication/access and the unavailable course student self-check remain operator follow-up.

## 2026-11-15 - current-project snapshot migration
* Anton confirmed that HW2 has been submitted and authorized adopting the new snapshot on main while keeping `hw2` unchanged. Export selection/options are unchanged, including no measurement settings or provenance. Snapshot format 6/schema 0111 contains 41 articles and 245 experiments; the snapshot/schema hashes, original export time and exporter commit are recorded in `data/snapshot_manifest.json` and METHOD §3.
* Migrated the reader, independent fixed-condition contract and separate synthetic fixtures to flattened process/setup fields; added physical target-stack ordering and gold-only assembly checks matching the exporter, including its six-decimal composition rounding. Added negative tests for conflicts, incomplete/non-gold targets, unit-preserving labels, radius non-conversion, input/schema tampering and excluded options. Scientific size/error/shape/resampling rules are unchanged.
* Removed historical HW2 artifacts from main and replaced their current-document links with instructions for reading the original report/evidence from `hw2`. No old hashes, dates or scientific outputs were rewritten to claim a new run. The current dry artifact is infrastructure-only. Claim files, extraction memory, scientific implementation in src/ and article text are unchanged; all new scientific work remains with the AI4Science agent.
* Validation: full test suite and dry contract check pass; graph consistency passes. The ordinary claim check validates vocabulary, PDF inventory and existing quote/no-claim rows, then fails only its commit guard because results/ changes are intentionally uncommitted. No new extraction verdict, resampling/claim-comparison run, commit, tag movement or push.

## 2026-11-15 - full-corpus PDF preparation
* Anton requested claim extraction over all 41 snapshot articles, not only those yielding usable series, and authorized copying their missing PDFs from the database server. Read attachment metadata with the read-only DB_AGENT account and copied main-text/supplementary-information blobs through authenticated file-service GETs; no server writes or publisher searches. Added 38 main PDFs and 8 supplementary PDFs (46 new files); the local corpus now contains 41 articles and 49 PDFs. Files remain ignored by Git; registered article metadata, roles and SHA-256 in data/corpus.csv and data/files.csv.
* Verified every PDF against the DB digest and byte size, checked all 49 PDF structures (420 pages, without extracting text), and verified group read-only permissions for the course agent. Snapshot/schema/export manifest, claim/no-claim rows, extraction memory, scientific code/results and hw2 remain unchanged. Available supplements are those attached in the DB, not a claim of exhaustive publisher-side supplementary coverage.
* Corpus expansion exposed two missing exact-DOI Source-to-Article links required by graph rule R9. Filled only those article_id fields; preserved source screening and bibliographic values. Regenerated notes with tools/graph.py rather than editing generated files. One source/article title-or-year difference remains informational; their DOI match is exact.
* Article 534494 now has a supplementary PDF that was absent from the earlier claim-extraction input. The AI4Science agent must revisit that article and its prior no-claim record with the supplement; no scientific record was silently deleted or changed here. The 38 new corpus articles still await claim extraction. Do not interpret missing processing as absence of claims.
* Validation: corpus/hash/size/role/permissions/Git-ignore checks pass; 316 tests pass; graph consistency and whitespace checks pass. The full claim-readiness check fails only for the 38 newly registered articles with no claim/no-claim output yet, as expected; no checks were weakened and no placeholder no-claim rows were fabricated. No claim extraction, scientific calculation, commit, tag movement or push.

## 2026-11-15 - provisional analysis contract and independent acceptance checks
* Anton provisionally adopted three working decisions and authorized encoding them in the project: article-level prevalence pooling fluence/energy/power/intensity (unspecified separate), permissive same-article/medium matching for own-data claims with exhaustive auditable decisions, and per-model claim outcomes all_agree/all_disagree/mixed/unassessable rather than majority voting. Later revisions must be disclosed and affected outputs regenerated, not silently relabelled.
* Updated claims_spec §§8–9, results_spec §§5–7, ontology and agent instructions. Added an inventory-bound reading ledger so all supplied SI must be covered, unfinished/unreadable articles are unassessed, and a new PDF invalidates an old complete attestation. No reading status or scientific result was fabricated. Qualified comparisons retain caveats and separate counts; unmatched/all-excluded claims remain in coverage and outcome denominators. The old series sign-test remains only a secondary exploratory diagnostic, with its clustering/overlap limitation explicit.
* Added protected checks/analysis.py and synthetic tests under checks/tests/. Explicit --analysis draft/final checks verify exact candidate/pair inventories, duplicates, reasons/caveats, copied shapes, agreement booleans, article-count denominators, coverage, per-claim outcomes and aggregation. Final additionally requires no pending articles and curator-owned checks/matching_review.json bound to exact input/output/contract hashes. The checker never imports src/ or generates agent outputs; AI4Science must independently implement the scientific pipeline and its tests. Reading attestations and scientific judgments still need human/process review: structural checks are not proof of their truth.
* Kept claim-only checks independent of numerical tools and analysis outputs, and extended extraction blindness to the audit, summary and matching review. Legacy claim checks without a reading ledger remain available but do not certify analysis readiness. Updated graph projection so within-model mixed evidence is not called model-dependent; notes preserve qualifications. Regenerated only the two affected class notes, not scientific result notes. New protected code/tests are group-readable and not agent-writable.
* No changes to data/, results/, src/, tests/ or extraction memory; no AI4Science run, new claim extraction/comparison, resampling, database access, commit, tag movement or push. Scientific generator and outputs remain agent work; no curator approval file exists yet.
* Validation: 419 full-suite tests pass (including 103 new synthetic analysis/coverage/CLI/graph tests); graph consistency, vocabulary, whitespace and protected-file permissions pass. The scoped legacy reference claim check passes without loading numerical tools. Full claim readiness still fails on exactly the 38 unprocessed articles; --analysis draft fails closed on the missing reading ledger before loading numerical tools. Both hw2 tag object and peeled commit are unchanged. Changes remain uncommitted for Anton's review.

## 2026-11-16 - retire extraction benchmarking
* The human curator requested removing the golden-set concept: the corpus is final at 41 articles, all will be analysed, and the curator will review the agent's results when ready.
* Removed the development/test article split, reference-label CSVs and `checks/check.py --gold` scoring. Updated AGENTS.md, README.md and results_spec §7.6 to describe human review of extraction, including missed claims and no-claim judgments. Automated structural checks do not establish extraction quality.
* This changes the extraction-evaluation workflow, not the scientific comparison contract in results_spec §§5–6: output schemas, numerical rules, reading coverage and matching approval remain unchanged. Kept `checks/claim_checks.csv`, curator-review graph notes and numerical reference tests. Earlier dated benchmark entries remain historical, not active instructions.
* Added CLI regression tests for rejecting the retired option and retaining the supported check modes. Validation: 311 tools/checker tests pass; CLI help, graph consistency and whitespace checks pass. The full suite could not collect verifier tests because the local environment lacks `jsonschema` and `hypothesis`; no dependencies were installed.
* No extraction, comparison generation, resampling, curator verdict or matching approval was produced. No data, existing scientific outputs, numerical implementation, commits, tags or remote repositories were changed.

## 2026-11-16 - supplied comparison pipeline
* The human curator authorized implementing the discussed prepare/build interface. The supplied code now performs deterministic comparison work; AI4Science extracts claims, supplies scientific audit decisions with evidence/caveats, runs the commands and interprets results rather than writing code.
* Added `src/comparison/` and synthetic tests in `tests/`. `prepare` records current input fingerprints and every eligible candidate with claim/series context, without agreement scores or invented assessments. AI4Science writes the exact existing audit schema. `build --stage draft` validates complete audit coverage, reuses one fixed SnapshotTools view, generates both-model comparisons and independently calculated article/claim/pair/series tallies. Production code never imports the checker or its oracle.
* Final build requires an existing unchanged draft, no pending articles and a valid curator-owned approval bound to the current fingerprints. It never writes approval, reading attestations, claims or the audit. Input changes invalidate preparation; an existing audit must be archived and matching re-reviewed before fresh preparation. Files are serialized deterministically, staged before replacement and published summary-last, with locking, rollback and retained recovery copies if rollback itself fails.
* Updated AGENTS.md, README.md and results_spec §§5–6 for supplied-code ownership, exact commands and human review. This is an implementation/workflow addition, not a change to scientific rules: contract version 1, final schemas and approval fingerprint paths remain unchanged. The working candidate JSON is not a new approval input. Runtime locks and staging files are ignored by Git.
* Validation: 552 full-suite tests pass, including 129 new pipeline tests, hand-counted expectations, real-adapter synthetic CLI integration, independent checker draft/final integration, malformed/stale inputs and approval, deterministic rebuilding, concurrency and publication failures. Ruff, vocabulary, graph consistency and whitespace checks pass. Missing pinned verifier dependencies were installed only into `/tmp/ai4science-comparison-deps.sxqQZ7` for testing via PYTHONPATH; the project environment and requirements were not changed.
* No pipeline command was run against the real article corpus; no new extraction, scientific outputs, curator verdict, approval or resampling was produced. Existing data/results/memory, numerical tools and independent checker source are unchanged. No commits, staging, tags, pushes, live database access or paid model calls.

## 2026-11-16 - resumable article-by-article comparison
* The human curator required small per-article steps because failures can occur throughout extraction and comparison. The active workflow is now extraction → article preparation → scientific audit → article draft → article check, before starting the next article in a fresh, numerically blind context. It no longer waits for all articles to be extracted before comparison.
* Added `prepare --article <id>`, `build --article <id> --stage draft` and `checks/check.py --article <id> --analysis draft`, with separate four-file checkpoints under `results/articles/<id>/`. Only the selected article needs a complete reading attestation; other ledger rows may be absent. Its CSV rows and schema-guided snapshot/shared/stock dependency closure are canonically bound, while schema/rules/code remain byte-bound. Unrelated article work does not invalidate a saved checkpoint. Scientific rules and corpus approval remain contract v1; scoped execution metadata is explicitly `article-v1`, not a reinterpretation of old corpus summaries.
* Added `aggregate`: it requires explicit corpus statuses, validates every complete article's current checkpoint (including no-claim/no-own-data/no-candidate cases), merges decisions without inventing them and generates the corpus draft. Global context binds the four source files of each checkpoint. The independent checker recomputes scoped counts/input bindings, checks the merged audit and rejects stale/corrupt/missing checkpoints. Final remains corpus-wide, requires no pending articles and unchanged generated draft plus exact human-owned approval; changing article work requires re-aggregation, never automatic approval refresh.
* Reused existing numerical calculations through `SnapshotTools.from_data`, a defensive-copy, header-validating constructor. Added schema-guided reference traversal without numerical rules. Article dry verification accepts `dry --article <id>` and writes only that article's diagnostics under `results/verifier/articles/<id>/`; full frozen-file hash guards and the full/80094 reference guard remain intact. No article resampling mode was added. Scoped publication retains deterministic no-op reruns, locking, staged replacement and rollback, and rejects parent-symlink aliases; nested staging files are ignored.
* Corrected the old isolation policy that still listed `src/` and `tests/` as agent-writable. Updated `ops/perms.sh` and installer checks for curator-owned supplied code, read-only source defaults, and scientific writes only in results/memory/diary. Refreshed the installed checkout hook only after verifying it was the unchanged old permissions script; restored read-only group modes/defaults on curator-owned infrastructure. These are static permission checks, not a successful aiagent login/runtime test.
* Validation: 598 full-suite tests pass, including 166 pipeline tests; new article tests use synthetic data, hand-counted expectations and real-adapter CLI/independent-checker integration. Covered partial ledgers, unrelated/relevant changes, unknown/incomplete scopes, exhaustive audits, zero-output checkpoints, missing/stale/corrupt aggregation, current approvals, rollback and directory aliases. Ruff, formatting of new modules, shell syntax, vocabulary, graph consistency and whitespace pass. Full verifier tests still use pinned dependencies temporarily supplied through `/tmp/ai4science-comparison-deps.sxqQZ7`; project `.venv` still lacks jsonschema/hypothesis and was not changed.
* No comparison/preparation/aggregation/dry command was run on the real corpus; existing scientific records and data were not changed. No new extraction, curator verdict/approval, resampling, AI4Science/paid model call, database access, commit, staging, tag movement or push. Existing numerical reference tests run only as tests; no new scientific output is claimed.

## 2026-11-16 - article 534424: extraction, attestation and comparison draft
* Selected 534424 (Green synthesis of Au NPs in Gum Arabic, PLAL; main 11 pp + SI 3 pp) as the first article of the article-by-article workflow; it had no prior claims, no-claim row, ledger row or checkpoint. Extraction stayed blind: no snapshot, series, verifier or comparison output was read before the claims and the reading attestation were recorded.
* Reading: every page of the main text and of the supplied SI in two-page `pdf_read` calls; because heavy outputs are truncated, the same pages were dumped with the checker's own extractor (pypdf) for verbatim quoting, and both quotes were verified in the normalized page-6 text before writing.
* Two own-data claims (p.6, energy series in GA-aqueous medium): increase at low energies 50-100 mJ and slight decrease at 200-1000 mJ, both `variable=energy` (units mJ). Pulse-number statements, "laser parameters" and "qualities" sentences, spectral shifts, GA-concentration and AAS-concentration statements were rejected with reasons in `memory/534424.md`. SI Table S4 mislabels mJ as "laser power"; no SI size data or size statement.
* Numerical preflight: `checks/verifier/run.py dry --article 534424` exit 0 (`results/verifier/articles/534424/dry.json`); `pytest checks/verifier -q` 119 passed. `prepare` produced one candidate series (`534424-s1`, TEM mean, 2 points) for both claims.
* Matching: `c2`/`s1` included as `direct` (both points inside the claimed 200-1000 mJ region; agree in both models); `c1`/`s1` included as `unassessable` because the series has no point in 50-100 mJ (50/100 mJ experiments are `short_series` exclusions) and the text reports no size there. No input or series was altered to force agreement.
* Outputs: `results/articles/534424/{matching_candidates.json,matching_audit.csv,comparison.csv,summary.json}`; draft only, no aggregation, no curator approval, no other article started. Two questions for the curator are recorded in memory (one non-monotonic vs two directional claims; histogram-mean fallback errors for a `direct` pair).

## 2026-11-16 - article 532516: extraction, attestation, no-claim record
* Selected 532516 (Evolution of the properties of nanomaterials obtained by pulsed laser ablation, JPCS 2021; main 7 pp, no supplied SI) as the next article of the article-by-article workflow; it had no claims, no-claim row, ledger row or checkpoint.
* Reading: all 7 pages of the single main PDF (cover page, abstract/introduction, experimental part, results with Table 1 and Figures 1-5, conclusions, references); pages dumped with the checker's own pypdf extractor for verbatim quoting and the quote verified in the normalized page-4 text before writing.
* Verdict: no claim. The article varies no laser parameter (Table 1: single energy 100 uJ, 1030 nm, 1000 mW, 10 kHz); its size results concern time after ablation and liquid type (water vs 10 uM NaCl). One no_claims row quotes the p.4 scope sentence ("a systematic study was conducted of the dependence of their dimensional, morphological properties on the parameters of ablating laser radiation: energy, ...") with the §2 reason that it announces a study, states no size change and the article varies none of the four variables. Rejected sentences (general "parameters of laser radiation" statement, time-dependence aim, size range in conclusions, table/captions) recorded in memory/532516.md.
* Wrote the `complete` reading attestation bound to the single main PDF hash; `checks/check.py --article 532516` passes all claim/attestation checks and fails only on the uncommitted results/ records, which are committed next.

## 2026-11-16 - article 532516: comparison checkpoint (draft)
* Numerical preflight before any comparison work: `checks/verifier/run.py dry --article 532516` exit 0 (diagnostics in results/verifier/articles/532516/dry.json) and `pytest checks/verifier -q` 119 passed.
* `prepare --article 532516` produced zero candidate entries because the article has no own-data claims (one no_claims row). `matching_audit.csv` is header-only: there are no candidate pairs to include, exclude or assess, and no decision was invented. `build --article 532516 --stage draft` produced header-only `comparison.csv` and a scoped draft `summary.json` (n_corpus=n_complete=1, prevalence numerator 0, no own-data claims, no series).
* No input, series, exclusion or matching was altered to obtain this outcome; the no-claim verdict rests on the text (single laser setting in Table 1, size results only versus time and liquid type). Draft only: no aggregation, no curator approval, no other article started.

## 2026-11-16 - article 532464: extraction, attestation, no-claim record
* Selected 532464 (Laser ablation-assisted synthesis of plasmonic Si@Au core-satellite nanocomposites, Nanomaterials 2021; main 12 pp, no supplied SI) as the next article of the article-by-article workflow; it had no claims, no-claim row, ledger row or checkpoint.
* Reading: all 12 pages of the single main PDF (cover page, abstract/introduction, materials and methods incl. laser synthesis and Mie modelling, results with Figures 1-6 and Tables 1-3, conclusions, references); pages 5-9 contain a duplicated peer-review overlay of the previous page, and the final typeset text on those pages was used. Pages were dumped with the checker's own pypdf extractor for verbatim quoting and the quote verified in the normalized page-2 text before writing.
* Verdict: no claim. The article varies no laser parameter (single Yb:KGW fs setting, 1025 nm, 10 kHz, 480 fs; no fluence or pulse energy reported anywhere outside the reference list) and reports one mean size per material (Si 37 +/- 3 nm, Au 4 +/- 0.8 nm); its variables are APTMS amount, water/ethanol ratio and Si:Au volume ratio, with the plasmonic peak position as response. One no_claims row quotes the p.2 technique sentence ("... renders possible an efficient control of size characteristics of NPs ...") with the §2 reason that it names no laser variable, states no direction and the article varies none of the four variables. Rejected sentences recorded in memory/532464.md.
* Wrote the `complete` reading attestation bound to the single main PDF hash; `checks/check.py --article 532464` passes all claim/attestation checks and fails only on the uncommitted results/ records, which are committed next.
