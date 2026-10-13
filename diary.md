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
