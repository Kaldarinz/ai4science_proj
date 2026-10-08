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
