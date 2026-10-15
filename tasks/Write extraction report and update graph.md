---
type: Task
status: done
---
# Write extraction report and update graph

Request: "Write a report of the claim extraction so far in results/extraction_report.md: one section per article of data/corpus.csv with its claims or its no-claims row and the checks recorded for them. Every article of the corpus must have its Article note."

Done when: `results/extraction_report.md` is correct, `diary.md` has an entry, and `checks/graph_check.py` exits with 0.

## Summary
Created `results/extraction_report.md` with one section per corpus article. Fixed page count for 80094 (6, not 9). Created missing `notes/Article 534569.md`. Ran `checks/graph_check.py` (exit 0). Committed.

## Links
- type: [[Task]]
- resolvedBy: [[results/extraction_report.md]]