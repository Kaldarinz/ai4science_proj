# Literature spec: OpenAlex records as candidates for ablation_db

A literature task finds works in OpenAlex that may be added to ablation_db
and records them in three tables. `tools/graph.py --validate` checks every
rule below that a script can check; the human decides which candidates to
add to the database.

## 1. Tools

- `openalex_search`, `openalex_links`, `openalex_work` (extension
  `research`). Queries in English. `wikidata_*`: never.
- Do not load the `literature` skill: this spec replaces it.
- `openalex_links` needs a W id: a DOI is mangled. To follow a work known by
  its DOI, first `openalex_work` by DOI, then links by the returned
  `openalex_id`.
- Only `openalex_work` returns an abstract: one call per work to screen it.

## 2. `results/queries.csv`: one row per call that adds new Sources

| Column | Value |
|---|---|
| `query_id` | `q1`, `q2`, … in order, never reused |
| `database` | `openalex` |
| `tool` | `openalex_search`, `openalex_links`, or `openalex_work` |
| `work` | `openalex_work`: the identifier given; `openalex_links`: the W id; search: empty |
| `relation` | `openalex_links`: `references` or `cited_by`; otherwise empty |
| `request` | `provenance.request` of the response |
| `retrieved` | `provenance.retrieved` (YYYY-MM-DD) |
| `n_found` | `found` of the response; 1 for `openalex_work` |
| `n_kept` | Sources whose `found_by` names this query (≥ 1); for links also the `citations.csv` rows of this query |

`openalex_work` gets a row only for a work named in the user's message.
Screening look-ups of works already in `sources.csv` get none.

## 3. `results/sources.csv`: one row per OpenAlex work

| Column | Value |
|---|---|
| `source_id` | `openalex_id` (W…) |
| `found_by` | query ids, `;`-separated; a work found again gets the new id added, never a second row |
| `doi` | `doi` of the response, lower case, without `https://doi.org/`; empty if none |
| `title`, `year` | `title`, `year` of the response |
| `venue` | `source` of the response |
| `cited_by_count` | `cited_by` of the response |
| `screening` | `relevant` or `excluded` (§4) |
| `screening_reason` | one line; required for `excluded` |
| `article_id` | the `article_id` in `data/corpus.csv` with the same DOI (compared in lower case); otherwise empty |

Every value comes from a tool response: never from memory or from the
article PDFs. No line breaks and no `[[`/`]]` in any field.

## 4. Screening

`relevant` if the abstract reports the size of Au nanoparticles made by
pulsed laser ablation in liquid at more than one fluence, pulse energy,
laser power or intensity; otherwise `excluded`. Unsure, or no abstract:
`relevant`. Screen honestly also a work that is already a corpus article.
`screening_reason` never says which way size changes (no "increase",
"decrease", "grow", "larger", "smaller"): claim extraction must stay blind
to an earlier reading.

## 5. `results/citations.csv`: one row per citation link

`citing`, `cited` (both W ids in `sources.csv`), `query_id` (an
`openalex_links` query whose `work` is `citing` for `references`, `cited`
for `cited_by`). Only links returned by `openalex_links`.

## 6. Done

At most five new works per message: if asked for more, record the first
five and say what is left. Then commit `results/` and run
`.venv/bin/python tools/graph.py --validate`; it must exit with 0.
