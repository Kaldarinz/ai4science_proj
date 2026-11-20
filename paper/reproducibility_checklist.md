# Reproducibility checklist — Results Tables 1 and 2

Scope: verify the approved final analysis and regenerate the two Results
tables from saved results. This checklist does **not** rerun extraction or
rebuild the analysis.

Table order in `paper/paper.tex` (lines 215–216): Table 1 =
`tables/trend_directions.tex` (`tab:trend-directions`), Table 2 =
`tables/main_results.tex` (`tab:main-results`). No other floats precede them.

## 1. Frozen inputs and provenance

### Snapshot

| Item | Value |
|---|---|
| File | `data/ablation_snapshot.json` |
| SHA-256 | `0de0f35107c00c31adb096e4a974fdb18844bd9b505c05e3174543688879c637` |
| Bytes | 2 197 289 |
| Format | 6 (`checkout_schema_change` 0111) |
| Exported | 2026-11-15T09:30:40Z, from live read-only `DB_AGENT` |
| Exporter commit | `55e09d7251739f4ee7cbe17aa539ac93256d0862` |
| Inventory | 41 articles, 245 experiments |
| Schema | `data/ablation_snapshot.schema.json`, SHA-256 `76ecbba667009c0dc12356bb11090d998144090d46bc0fc2687cc1fddc9f0046` |

Manifest: `data/snapshot_manifest.json`.

### Approved final analysis commit

| Item | Value |
|---|---|
| Commit | `45e677a8e1e51c7994899dae49ffe715ca148c39` |
| Subject | "Approve and finalize the fixed-tolerance analysis" |
| Author / date | Anton Popov, 2026-11-20 |
| Contains | `results/summary.json` with `"stage": "final"`; `checks/matching_review.json` with `"decision": "accepted"` |

The approval record was first added at `176e714` and updated at `45e677a`;
`45e677a` is the commit that carries the final-stage summary and the current
approval. `results/` is clean at this commit.

### Table generators (uncommitted — identified by path + SHA-256)

Both generators are **untracked** in Git (`git status` shows `??`); they are
not part of `45e677a`. Do not attribute them to a commit.

| Table | Generator path | SHA-256 |
|---|---|---|
| Table 1 | `paper/generate_trend_table.py` | `db1ce2d5238fb6dd3aeb814de29d0c69c5d5d266d1b52cff488e9828082872f4` |
| Table 2 | `paper/generate_results_table.py` | `509b2cd97813363975855b972316c942a6abba28be42a598aca401434f93f60d` |

### Current table outputs

| Table | File | SHA-256 |
|---|---|---|
| Table 1 | `paper/tables/trend_directions.tex` | `ac2c9600e707add63bd48b48c5f935a299a9be99c18b5acbf80319e11c4aae96` |
| Table 2 | `paper/tables/main_results.tex` | `279abf97a9bc5935505d38970883a971d4f9a3f604c96f2a00bd7e8d3459b4b1` |

### Approved input hashes (from `checks/matching_review.json` / `results/summary.json`)

| File | SHA-256 |
|---|---|
| `results/claims.csv` | `7e309158fb4750cbdf659c1e75311c077f462cc29e30a841623d8c0ed8895ee9` |
| `results/comparison.csv` | `02f18827360446c412e253dac16957011827f27ef430d8d7921c3aa57572b4d9` |
| `results/extraction_status.csv` | `00cee96acaf91cc97d915117f6b173068f050e620631936b6b599c138fc0a4c8` |
| `results/matching_audit.csv` | `7c2b6c617d49c809eda3f82f37800ff4009765fb7e8ca4b71f02577c431ad4ec` |
| `results/no_claims.csv` | `11c0c61192ad3c9e652698064b53f600ea961d05155d0f4c355af15a631cec8f` |
| `results/summary.json` | `51084a9967e872f37773c50410e693e52e6eb6c17057dd8b08b773b2f44e0727` |
| `data/corpus.csv` | `0879d3619b4668c000ac48b55ab217e06ea54a013a50c62a743598db59c72a53` |
| `data/files.csv` | `94904b3adeab9049f6a9d1422f8019a74dc40540a764a5186f165bb5f671b31c` |
| `ontology.yaml` | `5d3e93ba0d96e1718b12a7bf6576deea084e5823b5ec76f016e5268e817265b2` |
| `checks/analysis.py` | `e6b1d05f0bf350a28bccb56d74b0395a9b6ead3a502bf71ed72bc02af0143de1` |
| `checks/check.py` | `a3dd19d120241cff91151150d3192ddde679a52cad4cfa23ecf9886cfd985ff7` |
| `checks/claims_spec.md` | `0075adf951f4bd13093ffdc9ea6a7f9bf27d293fc1dcc3ddd55953ba259a1d92` |
| `checks/results_spec.md` | `b6e48b953a26ae5ad95a137b05d0f47c95d0fa07861c59bf4b4c628d0394f89a` |
| `tools/ablation_db.py` | `8a5be3bbf946bbda12ded47affb0eb08e29aeb57bac319eaee63db7d50402cda` |
| `tools/series.py` | `bfa16b0a18cd866653c75f622f551fcb712929e28081cf86fe472236c84f60c5` |

## 2. Environment actually needed

| Component | Version |
|---|---|
| Python | 3.14.4 |
| PyYAML | 6.0.3 |
| pypdf | 6.19.0 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |

- `checks/check.py --analysis final`: stdlib + PyYAML + pypdf (quote
  verification) + numpy/scipy (imported via `tools/series.py`). `jsonschema`
  is **not** needed for this check (verifier only).
- Both table generators: **stdlib only** (`csv`, `json`, `sys`, `collections`,
  `pathlib`). No third-party imports.
- `requirements.txt` pins the full set; the subset above is sufficient for this
  checklist.

## 3. Commands, in order

Run from the project root with the project interpreter:

```sh
cd /srv/ai4science_proj

# 1. Verify the approved final analysis (exit 0 required)
.venv/bin/python checks/check.py --analysis final

# 2. Regenerate Table 1 (trend directions)
.venv/bin/python paper/generate_trend_table.py

# 3. Regenerate Table 2 (main results)
.venv/bin/python paper/generate_results_table.py

# 4. Confirm the regenerated tables match the recorded bytes
sha256sum paper/tables/trend_directions.tex paper/tables/main_results.tex
```

Expected: step 1 prints `PASSED: 0 failure(s)`; steps 2–3 exit 0 and abort
without writing if any recomputed count disagrees with `results/summary.json`;
step 4 reproduces the hashes in §1.

## 4. Table inputs and outputs

### Table 1 — `paper/generate_trend_table.py`

| | |
|---|---|
| Inputs | `results/summary.json`; `results/claims.csv`; `results/extraction_status.csv`; `results/articles/*/summary.json` (41 files) |
| Diagnostic only | `results/comparison.csv` (reports pair/series coverage; never used for shape counts) |
| Outputs | `paper/tables/trend_directions.tex`; `paper/tables/trend_directions_checks.txt` |

### Table 2 — `paper/generate_results_table.py`

| | |
|---|---|
| Inputs | `results/summary.json`; `results/comparison.csv`; `results/claims.csv` |
| Outputs | `paper/tables/main_results.tex`; `paper/tables/main_results_checks.txt` |

## 5. Check vs rerun vs rebuild

| Action | Command | Effect |
|---|---|---|
| **Check approved analysis** (this checklist) | `checks/check.py --analysis final` | Verifies hashes, coverage, audit, pairs and summary against the approval. Reads saved results only; does not recompute from PDFs or the snapshot. |
| **Regenerate tables** (this checklist) | the two `paper/generate_*.py` | Presentation only: recomputes displayed counts from saved results, cross-checks them against `results/summary.json`, writes LaTeX. |
| Rerun extraction (not done) | re-read PDFs, rewrite `results/claims.csv`, `no_claims.csv`, `extraction_status.csv` | Invalidates reading attestations; requires re-reading and re-approval. |
| Rebuild analysis (not done) | `src.comparison aggregate` / `build --stage final` | Recomputes comparison from claims + snapshot; changes `results/summary.json` and requires fresh curator approval. |

## 6. Test in a temporary copy — what passed

Method: `git clone` of `45e677a` into a temp dir; copied the two untracked
generators and the current `paper/tables/*.tex`; copied the gitignored
`data/articles/*.pdf`; ran the commands with the project `.venv` interpreter.

| Check | Result |
|---|---|
| `checks/check.py --analysis final` | exit 0, `PASSED: 0 failure(s)` |
| `generate_trend_table.py` | exit 0 |
| `generate_results_table.py` | exit 0 |
| `trend_directions.tex` vs current | byte-identical (`ac2c9600…`) |
| `main_results.tex` vs current | byte-identical (`279abf97…`) |
| `*_checks.txt` logs vs current | byte-identical |
| Two consecutive generator runs | byte-identical (deterministic) |

### Could not verify / caveats

- A **bare clone fails** `check.py --analysis final`: the publisher PDFs under
  `data/articles/*.pdf` are gitignored and absent, so quote verification raises
  `FileNotFoundError`. The check passed only after copying those PDFs from the
  working tree.
- The generators are **not in Git**; a fresh clone lacks them. Their identity
  is the path + SHA-256 above, not a commit.
- I did not rerun extraction or `aggregate`/`build`, so I cannot confirm that
  re-deriving the results reproduces the same `summary.json`.
- I did not compile the PDF or run `checks/check_paper.py` (not requested).
- I did not verify the frozen snapshot against the live database (no live DB
  access permitted).

## 7. Inputs a reader cannot obtain from the manuscript alone

- `data/articles/*.pdf` — 49 publisher PDFs, gitignored and not redistributed;
  required for `check.py` quote verification. Identified by SHA-256 in
  `data/files.csv`.
- `data/ablation_snapshot.json` — frozen DB export (2.2 MB); needed to rebuild
  the analysis. In the repo, but not derivable from the manuscript.
- `results/articles/*/summary.json` — 41 per-article series diagnostics; needed
  for Table 1 Panel B.
- `paper/generate_trend_table.py`, `paper/generate_results_table.py` — untracked;
  must be supplied separately (path + SHA-256 above).
- `checks/matching_review.json` — curator approval; in the repo at `45e677a`.
- The exact Python environment (`.venv`) — not in the repo; versions in §2.
