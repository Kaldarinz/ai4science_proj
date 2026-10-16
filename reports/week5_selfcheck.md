# Week 5 self-checks

`lectures/week_5/artefacts/practice.md`, «Артефакт недели 5», student self-checks 1–5, with the project's English names: `Источник` → `Source`, `ЗапросКГрафу` → `Query`, `найденЗапросом` → `foundBy`. Check 3 uses `xargs -d '\n'` instead of `$(…)`: note names contain a space (`Source W….md`), which `$(…)` splits, so the course's form checks no file at all. Run 2026-10-16 on branch `week-5` at commit `6cc8aa1`.

```
$ grep -c "^## " reports/my_search_report.md
5
$ grep -c "^\[написано\]" reports/my_search_report.md
6
$ grep -l "^type: Source" notes/*.md | wc -l
13
$ grep -l "^type: Source" notes/*.md | xargs -d '\n' grep -L "foundBy"
$ grep -l "^type: Source" notes/*.md | xargs -d '\n' grep -l "foundBy" | wc -l
13
$ grep -l "^type: Query" notes/*.md | wc -l
3
$ grep -c SELECT reports/my_search_report.md
1
$ git grep -c "OPENALEX_API_KEY=" ; git status --short
```
