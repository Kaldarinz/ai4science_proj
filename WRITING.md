# Writing the paper in academic English

Write directly in clear, idiomatic English. Prefer precise claims and concrete
verbs to formal-sounding phrasing. Use one spelling convention throughout.

## Style from the selected papers

Use the shared style of the four approved coauthored papers, with the two
first-author papers as the strongest references. This is a writing model,
not a source of scientific evidence for this study.

- **Abstract and introduction:** move from the scientific context to a
  specific unresolved issue. Then state the contribution directly: “Here,
  we compare…” or “This study examines…”. In the abstract, follow the
  contribution with the principal quantified observations and a bounded
  implication. In the introduction, explain the gap before describing our
  approach; do not start with a general survey of applications.
- **Methods and results:** lead with a question or observation. Use first-person
  plural for decisions and actions (“To assess sensitivity to the error model,
  we classified each series under both rules”). Use passive voice when the
  specimen, measurement or operation matters more than the actor. Use past tense
  for what we did and observed, and present tense for definitions and figure or
  table contents.
- **Comparisons:** put the observation, numerical range or denominator, and
  figure or table reference together. Contrast conditions explicitly in a
  paired sentence (“under the primary rule …, whereas under the lenient
  rule …”). Use “however” or “in contrast” only when the next clause actually
  changes the interpretation. Give the observation before the explanation;
  use “suggests” or “may reflect” when the explanation is not established.
- **Conclusion:** briefly return to what we did, what we found, and what that
  means for the studied corpus. Do not introduce a new result or promise an
  application. Vary sentence openings; do not repeat “we show” as a template.

## Academic English conventions

- Replace vague lead-ins such as “it is important to note that” and promotional
  terms such as “novel” or “robust” with the observation itself. Do not use
  “significant” to mean large or interesting. State uncertainty where it matters.
- Use terms consistently and define symbols, abbreviations and units on first
  use. Follow `GLOSSARY.md` and `ontology.yaml`. Do not use *power* as shorthand
  for fluence or pulse energy. Preserve original wording in direct quotations.

## Evidence and scope

- Generate result numbers and tables from the approved final artifacts in
  `results/`, not agent reports or the historical `hw2` results. Report units and
  denominators; distinguish article-level frequency, claim-level outcomes and
  pair-level assessments. Point readers to the relevant table or figure.
- Describe what agreed **under the stated comparison rule**, not what the
  experiment “proved.” Keep unassessable claims and qualified comparisons
  visible. Do not infer a universal effect or treat overlapping series as
  independent observations.
- Cite sources with `\cite{key}`, backed by the same key in `lit/lit.md` and
  the bibliography. Distinguish full-text evidence from abstract-only evidence.
- Write limitations before the results. Explain which assumptions could change
  a comparison or limit generalization, including matching, size measurement
  and error assumptions. Label exploratory interpretations as such.

## Before handing off a section

- Check the English for clarity and verify each substantive claim, number and
  citation against its source. Use `\written`, `\generated` or `\sourced` to
  reflect a passage's actual provenance. In the AI-use table, state what was
  checked and how; do not claim checks that did not happen.
- Target 4–8 LaTeX pages of main text, excluding references and AI-use
  disclosure. Check the main-text span in the compiled PDF, not the total page
  count.
