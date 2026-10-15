# Project journal

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
