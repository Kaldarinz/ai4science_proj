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

## 2026-10-13 - week 4: first gold label, claims_spec §2 extended
* Article 534494 (10.1038/srep30478) added to the corpus and labelled by hand before any agent run: `checks/claims_gold.csv`, and `checks/gold_articles.csv` (which articles are labelled, so an article with no gold claim still counts as labelled).
* Spec change (claims_spec §2): a rule for a dependence on unnamed "laser properties" or "laser parameters". The case that prompted it is in the gold label and is not repeated here, so that extraction stays blind.

## 2026-10-14 - claim extraction, article 534494
* Prompt: "Please extract the size–fluence claims from article 534494, following the usual extraction rules, commit the result, and update the project graph."
* Agent: read all 9 pages of 10.1038_srep30478.pdf via `pdf_read`; identified one size-fluence claim — the density filter experiment (water at ~0.25 J/cm² → 6 nm, vs 26 nm at ~1 J/cm²), i.e. size increases with fluence (own_data, Au, water, fs pulses). Appended row 534494-c1 to results/claims.csv. Wrote memory/534494.md, class notes in ontology/, object notes in notes/ (Article 534494, Claim 534494-c1), and task notes in tasks/. Also created the missing graph notes for article 80094 (Article, Claim 80094-c1/c2, Check 80094-c1/c2 review) that the graph check required.
* Result: 1 claim (534494-c1), 0 no_claims rows.
* Check: `.venv/bin/python checks/check.py --article 534494` → exit 0; `.venv/bin/python checks/graph_check.py` → exit 0.
* Check result: accepted — the density filter experiment is a genuine size-fluence dependence from the article's own data.
* Notes: the graph check initially failed because the previous session's notes for article 80094 (claims and checks) were missing; created them. Also renamed a task note that had a `/` in its name (from "results/claims.csv").

## 2026-10-15 - redo claim extraction, article 534494 (user rejection)
* User: "I reject the extraction of 534494: the quote reports a value, it does not state a dependence (claims_spec §2, the bullet on values compared by the reader). Please redo it."
* Agent: re-read pages 1-6 of 10.1038_srep30478.pdf. Confirmed the rejection: no sentence states a size-fluence dependence; the dependence is reader-inferred by comparing 6 nm at ~0.25 J/cm² (page 6) with 26 nm at ~1 J/cm² (page 2). Removed claim 534494-c1 from results/claims.csv, added a no_claims.csv row for 534494 (page 6, the 6 nm sentence). Updated memory/534494.md, removed notes/Claim 534494-c1.md, added noClaimReasonIn link to notes/Article 534494.md, updated task notes (Extract the claims of article 534494 and its subtasks).
* Result: 0 claims, 1 no_claims row for 534494.
* Check: `.venv/bin/python checks/check.py --article 534494` → exit 0; `.venv/bin/python checks/graph_check.py` → exit 0.
