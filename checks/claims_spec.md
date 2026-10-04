# Claims specification

Defines `results/claims.csv`: the claims an article's text makes about how
the size of gold nanoparticles depends on the laser pulse fluence, energy,
power or intensity. `checks/check.py` enforces it. Change this file and
`check.py` together, never one alone.

## 1. Input

- `data/corpus.csv` — `article_id, doi, title, year`: the articles to read.
- `data/articles/<article_id>/<file>.pdf` — the article's PDFs: the main
  text and any supplements.
- `data/files.csv` — `article_id, file, role, sha256`, one row per PDF;
  `role` is `main` or `supplement`. The PDFs are not in git; the hash
  identifies them.

A page is the 1-based page index within one PDF file, as `pdf_read` labels
it, not the page number printed by the journal.

## 2. What is a claim

A claim is a statement in the text that nanoparticle size changes, or does
not change, when the laser pulse fluence, energy, power or intensity changes.

- Include claims about gold or gold-containing particles (e.g. Au, AuSi, Au-Ag, ...).
- Exclude claims about other materials; explanations of a mechanism that
  state no dependence ("this indicates a stronger interaction"). Figure axis
  labels, captions alone and the reference list.
- One claim per article for each distinct `(material, medium_class,
  variable, direction, basis)`. A dependence restated in the abstract, the
  results and the conclusions is one claim; quote the results section if it
  states it, otherwise the first occurrence.

## 3. Columns

| Column | Type | Rule |
|---|---|---|
| `claim_id` | str | `<article_id>-c<k>`, `k` from 1 in order of the quote's position: main PDF before supplements, then page, then place on the page |
| `article_id` | int | from `data/corpus.csv` |
| `file` | str | the PDF holding the quote, as in `data/files.csv` |
| `page` | int ≥ 1 | the page of `file` holding the quote (§1) |
| `quote` | str | the claim's sentence copied verbatim (§4) |
| `variable_written` | str | the words the text uses, e.g. `laser fluence` |
| `variable` | str | §5 |
| `direction` | str | `increase`, `decrease`, `no_effect`, `non_monotonic`, `affects` |
| `basis` | str | `own_data`, `cited`, `general` (§6) |
| `material` | str | as written, e.g. `Au`, `AuSi`; |
| `medium_class` | str | as in `results_spec.md` §2, or `unspecified` |
| `conditions` | str | other stated conditions, e.g. `fs pulses`; may be empty |

`affects` is a claim of dependence with no direction ("size depends on
fluence"). A size "always around 5–8 nm" across the range is `no_effect`.

## 4. Quote

The quote is one sentence, or the shortest run of consecutive sentences that
states the claim, copied from the page's text.
It must be found in text after this normalization of both
strings, in order:

1. Unicode NFKD, then drop combining marks (as `pdf_search` does; this also
   splits ligatures such as "ﬁ");
2. case folding;
3. remove a hyphen followed by a line break;
4. replace every run of whitespace with one space.

Nothing else may differ: no paraphrase, no ellipsis, no corrected typos.

## 5. Variable

Decide `variable` by the unit of the quantity the text varies, not by its
name: authors often call pulse energy "fluence".

| Unit | `variable` |
|---|---|
| J/cm², mJ/cm² | `fluence` |
| J, mJ, µJ, µJ/pulse | `energy` |
| W, mW | `power` |
| W/cm², GW/cm² | `intensity` |
| no unit stated | the name used, mapped to the four above; `unspecified` if none fits |

## 6. Basis

| `basis` | When |
|---|---|
| `own_data` | The article reports this dependence from its own experiments. |
| `cited` | The sentence attributes it to other work, with a citation. |
| `general` | Stated as common knowledge, with no citation and no own data. |

## 7. Blindness

Claims are extracted from the text alone. Do not consult the database, the
series, or the figures' data while extracting: the claims must be recorded
before they can be compared with the data.
