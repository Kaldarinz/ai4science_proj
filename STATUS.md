# Paper status

- **Method adopted, draft ready for review (2026-11-20):** every size has a fixed
  10% primary or 20% lenient tolerance. All 41 article checkpoints and the corpus
  draft were rebuilt. Compared with the approved run at `8e23b26`, neither model
  changed a series shape, pair assessment or claim outcome. Extraction is unchanged.
- **Approval pending:** the previous `checks/matching_review.json` covers only
  the old inputs. Review the changes, commit the scientific records and rerun
  `.venv/bin/python checks/check.py --analysis draft`. After a passing check,
  the curator can renew approval for the hashes in `results/summary.json`, then
  build and check final. Do not use the draft as an approved result.
- **Writing:** preserve Anton's Introduction and curated Methods, including the
  stated random selection of 41 of 408 gold-only records. Verification and
  Limitations distinguish the fixed tolerances from measured uncertainty.
  After final approval, generate the main table and draft Results, Reproducibility,
  Conclusion and Abstract. Check anonymity and 4–8 pages of main text.
