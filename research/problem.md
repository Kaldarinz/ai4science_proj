# Research question and scope

## Overall narrative

Pulsed laser ablation in liquids is a versatile route to nanomaterials:
researchers can vary the target material, liquid medium, laser parameters and
focusing conditions. This flexibility also makes outcomes difficult to predict
across setups. The introduction should substantiate both points with literature,
including evidence on transient conditions (such as high temperatures and
pressures and steep gradients) and on what existing models can and cannot
predict. Do not assume an absence of theory or claim unrestricted versatility.

Use gold as a well-studied test case. Particle size and pulse fluence or energy
are basic quantities, so a straightforward trend might seem plausible. Yet
in the fixed corpus, articles report different directions and no single trend
direction describes the eligible numerical series. The apparent simplicity
of the question does not make the trend predictable from the named quantities
alone. Contrast the trends first; then ask whether individual claims agree
with the data used to assess them.

The diversity is evidence about this corpus, not evidence that no universal
physical relationship exists or that existing mechanisms fail. Different
conditions and size measurements can yield different trends. Use the literature
review to determine how strongly the paper can describe gaps in prediction.

## Working questions

1. **Reported trends:** How often do articles in the fixed corpus explicitly
   state that particle size changes or does not change with a laser quantity,
   and what directions do they report? Count frequency at the article level,
   including those with no qualifying claim in the denominator.
2. **Numerical trends:** What shapes occur across all eligible size-versus-fluence
   or size-versus-pulse-energy series, and how do the distributions change
   between the two error rules? Include eligible series regardless of whether
   they match a textual claim.
3. **Secondary comparison:** For own-data claims, what can be assessed against
   same-article series? Under each rule, which claims agree with all included
   series, disagree with all, have mixed results, or are unassessable?

The existing extraction rule also admits claims about power or intensity.
Retain those distinctions where applicable; do not treat these quantities as
interchangeable with fluence or pulse energy. This framing was chosen after
analysis and does not change the extraction or comparison contract.

## Scope and acceptance

**Inputs.** The frozen gold-target snapshot in `data/ablation_snapshot.json`
and its manifest; the PDF inventory in `data/files.csv`; curated textual
records and final comparisons in `results/`. The qualifying corpus is a
selection, not a representative sample of the literature. Gold-containing
products are in scope; gold-only describes the target selection, not the
composition of all products.

**Outputs.** Present article-level claim frequency and directions, followed by
shape counts across all eligible series under both error rules. Report
claim–series agreement secondarily, with all own-data claims in the
claim-outcome denominator. Keep direct and qualified pair counts distinct and
show examples where the outcome changes with the error rule. Agreement here
means concordance under the stated trend rule, not physical confirmation.

**Acceptance.** Use final records approved for the fixed-tolerance rule. The earlier
approved run (`8e23b26`) predates this change and is a comparison baseline only.
`.venv/bin/python checks/check.py --analysis final` must pass. Numeric tables
and macros must regenerate from those artifacts. A human checks whether text
and examples support the interpretation; `checks/check_paper.py` checks form,
not scientific validity.

**Limits to disclose before writing results.** Corpus selection; retained-claim
review not an independent extraction-accuracy/recall estimate; missing
measurement provenance/settings; proxy comparisons and wildcard conditions;
size-statistic and error assumptions; shared experiments across series.
See `METHOD.md` §10 and `checks/results_spec.md` §§5–6. No new predictive
hypothesis or representativeness claim: the analysis was already complete
when this paper scope was written.
