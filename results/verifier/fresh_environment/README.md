# Fresh-environment reproduction

Tested correct commit: `bbd6f39f580cadbc09f7197053048b825c1fdb96`.
Faulty commit: `cf188ed7f3618b3334af263eb67a7ad54783b5e0`.
Both checkouts are local; no final submission tag or live instructor access
was tested. Main's original numerical artifacts remain unchanged.

Anton created the clone and new Python 3.12.3 venv, installed requirements and
saved the first verifier output (`verifier_user.txt`: 82 passed / 2.15 s).
He then authorized completing the remaining steps automatically. Installation
stdout was not archived: installation success was reported by Anton, while
venv isolation, every requirement pin, package import paths, installed inventory
and `pip check` were verified directly. The original project venv was not reused.
`packages.txt` contains the complete installed inventory, including transitive
dependencies not individually pinned in `requirements.txt`.

| Check | Result | Evidence |
|---|---|---|
| Requirements / dependency consistency | All pins match; pip check passes | `packages.txt`, `pip_check.txt`, manifest |
| Dry contract | Pass; 0 violations, 10 series / 45 points | `dry.json`, `dry.txt` |
| Verifier after dry | 82 passed / 1.95 s | `verifier.txt` |
| Smoke / full | Pass, including both preflight gates and matching smoke prerequisite | Stage JSON, preflight text and CSV files |
| Complete regression | 267 passed / 3.76 s | `regression.txt` |
| Faulty commit, same fresh venv | Expected exit 1; order property fails; 81 others pass | `bug_verifier.txt` |
| Summary | Byte-identical to original | `summary.csv`, manifest |
| Per-seed scientific fields | All 20 smoke / 100 full / 120 combined rows identical | CSV files, manifest |

Only git commit and per-series elapsed time are excluded from row comparisons;
all scientific fields, original target shapes and diagnostic counts are retained.
Source/artifact hashes and the full run's exact smoke-manifest prerequisite were
verified. This repeat does not add seeds or draws to the original inference.

Pytest's failure output contains trailing whitespace on an empty diagnostic
line. The readable `bug_verifier.txt` removes trailing whitespace only to pass
git's whitespace check. The exact captured bytes are preserved in
`bug_verifier.raw.txt.gz`; the manifest records both artifact hashes and the
SHA-256 of the uncompressed original. No failure message or counterexample
was changed.

`manifest.json` records the actual commands, working directories, expected and
actual exits, wall times, installed-environment identity, comparison scope and
SHA-256 hashes of captured outputs. Stage manifests retain source hashes for
the tested committed checkout, including its historical METHOD text; subsequent
status edits on main do not retroactively change the tested source.

The clone was clean when created. Its initial status at automated continuation
contains only the user's saved verifier output; runtime outputs subsequently
modify result files in that clone. The correct and faulty code were tested in
separate worktrees. Main never received the intentional mutation.

The earlier `../reproduction/` directory is preserved: it documents the older
shared-venv test at `c50a2ff`, not this fresh-install test. See `../REPORT.md` §7
for reviewer setup and commands. No merge, commit, tag or push was performed
while completing this fresh-environment run.
