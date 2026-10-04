# AGENT.md — what the literature says about Au nanoparticle size versus fluence, and what its data show

## 0. Goal and expected result

A common claim in laser ablation in liquids is that nanoparticle size grows
with pulse fluence. The project compares, for gold, what articles **say**
about this dependence with what their **data** show.

Your tasks are of two kinds:
- **Claim extraction.** Read an article's text and record its claims about
  the dependence. Read `checks/claims_spec.md` before proceeding with 
  claim extraction.
- **Comparison.** Write and run the code that pairs `own_data` claims with
  the data series of the same article and summarizes the results. Read
  `checks/results_spec.md` proceeding with comparison.

At the end the project will contain:
- `results/claims.csv` — the claims of every article in `data/corpus.csv`;
- `results/comparison.csv` — each `own_data` claim against its series;
- `results/summary.json` — claim counts, agreement rates, series shapes;
- `src/` — the code producing the last two from `results/claims.csv` and
  the database tools.

## 1. Readiness criterion

```
python -m pytest tests/ -q && python checks/check.py
```

Both exit with 0. The check finds every quote on its page, recomputes the
comparison and summary, and checks reference article 80094: Au in water
`increase` agrees with its series; AuSi `no_effect` disagrees under the
primary error model and agrees under the lenient one. Run it yourself before
answering. For one article, `python checks/check.py --article <id>` checks
only its claims.

## 2. Project map and sources

- `data/corpus.csv` — the articles; `data/articles/<article_id>/` — their
  PDFs, main text and supplements, listed in `data/files.csv`.
- `tools/ablation_db.py` — the only access to the database: `find_articles`,
  `list_series`, `get_series`. Import them; do not write SQL.
- `checks/` — the specs, the check, the hand-labelled `claims_gold.csv`.

### Project-specific information

- When a claim and the data disagree, record it: that is a result, not an
  error to resolve. Curated data are correct even where the article's text
  disagrees with them.

## 3. Tools and limits

- Python 3.10+, numpy, scipy, pandas, pytest. Do not install anything else.
- Run from the project root: `python -m src.<module>`, then the check.
- Network and Lean are not needed:
  `AI4SCIENCE_WEB_DISABLED=1 ai4science --no-lean`.

## 4. Bans

1. Do not change any files in `data/`.
2. Do not change any files `checks/` or `tools/`.
3. While extracting claims, do not call the database tools or read
   `results/comparison.csv`.
4. Do not connect to a database except through `tools/`, and do not read
   `~/dev/ablation_db`, `~/.config/ai4science_proj` or `.env` files.
5. No `git push`, `rm -rf` or `sudo`.

## 5. Working protocol

- **Claim extraction:** pipeline, one article per run:
  `ai4science run "Extract the claims of article <id>."`. Read every PDF of
  the article with `pdf_read`, 2 pages per call; copy quotes from that output.
  Append the rows to `results/claims.csv`, run the check for that article, commit.
- **Code:** ReAct — each function in `src/` with a test in `tests/`; run the
  tests after each change. Commit before and after each task.
- The specs change only by the human, with a `diary.md` entry giving the
  reason.

## 6. Memory

Notes on articles for later sessions go to `memory/`.

## 7. Stopping and escalation

- Budget: 15 steps per article, 30 per code task.
- If the check fails twice in a row for the same reason, stop and report why.
- Ask the human when `pdf_read` returns no text for a page (a scanned PDF),
  when it is unclear whether a sentence is a claim, and when a claim's medium
  or material cannot be decided from the text.
