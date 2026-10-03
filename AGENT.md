# AGENT.md — does Au nanoparticle size grow with laser pulse fluence?

## 0. Goal and expected result

A common claim in laser ablation in liquids is that the mean nanoparticle size
grows with pulse fluence. The project tests it on gold, using experiments
extracted from the literature, and asks whether the answer depends on pulse
duration and medium.

The unit of analysis is a **series**: experiments of one article that differ
only in fluence or pulse energy. Only shapes of change within series are
compared; sizes from different articles are never compared directly.

At the end the project contains, and nothing else:
- `results/points.csv` — every point of every series (the primary result);
- `results/series.csv` — one row per series with its shape;
- `results/sign_test.json` — shape counts and the sign test, overall and per
  stratum.

Read `checks/results_spec.md` before writing or changing any of them: it
defines the series, every column and every derivation.

## 1. Readiness criterion

```
python -m pytest tests/ -q && python checks/check.py
```

Both exit with 0. `checks/check.py` compares `results/series.csv` with a
hand-computed reference; for article 80094 it expects Au in water
`increasing` (ρ = +1.0) and Au in a Si colloid `peak` (ρ = −0.6). Run the
check yourself before answering.

## 2. Project map and sources

- `data/curated/<article_id>/` — experiments exported from ablation_db after
  the curator's review. This is the ground truth.
- `data/agent/<article_id>/` — the same experiments as the extraction agent
  wrote them, before review. Use them only to compare with `curated/`.

### What the agent cannot know by itself

- Units: pulse duration in fs (10 ns = 1e7), energy in µJ, fluence in J/cm²,
  sizes in nm.
- When an article gives a size distribution, its stated mean is not stored:
  a missing mean is not missing data.
- Curated values are correct even where they disagree with the article text:
  the curator fixed known errors in the papers. Do not "correct" them back.

## 3. Tools and limits

- Python 3.10+, numpy, scipy, pandas, pytest. Do not install anything else.
- Run from the project root: `python -m src.<module>`, then the check above.
- Network and Lean are not needed:
  `AI4SCIENCE_WEB_DISABLED=1 ai4science --no-lean`.

## 4. Bans

1. Do not change `data/`. `[среда]` — `chmod -R a-w data`.
2. Do not change `checks/`, including the spec. `[среда]` —
   `chmod -R a-w checks`.
3. Do not drop or edit points to make a trend cleaner; list every excluded
   experiment with its reason in `notes`. `[окно]`
4. Do not read `~/dev/ablation_db` or `.env` files, and do not connect to
   any database: all data comes from `data/`. `[окно]`
5. No `git push`, `rm -rf` or `sudo`. `[вызов]` — `--mode approve`.

## 5. Working protocol

Mode: ReAct — run the tests after each code change.

- Each calculation is a pure function in `src/` with a test in `tests/` on a
  synthetic series whose shape is known.
- The spec changes only by the human, with a `diary.md` entry giving the
  reason.
- Commit before and after each task.

## 6. Memory

Notes on articles for later sessions go to `memory/`.

## 7. Stopping and escalation

- Budget: 30 steps per task.
- If the check fails twice in a row for the same reason, stop and report why.
- Ask the human before excluding any experiment, when it is unclear which
  experiments form a series, and in every case where the spec says to stop.
