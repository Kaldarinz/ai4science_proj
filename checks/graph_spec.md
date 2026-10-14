# Project graph specification

Defines the notes in `ontology/`, `notes/` and `tasks/`: who writes them,
their format and their links. The schema (classes, relations, attributes,
rules) is `ontology.yaml`. Change this file and `ontology.yaml` together;
both change only by the human.

## 1. Vault

The project root is an Obsidian vault: every file is a node, every `[[…]]`
link an edge. `.obsidian/app.json` and `.obsidian/graph.json` are set by the
human.

## 2. Generated notes

`src/graph_notes.py` writes all notes in `ontology/` and `notes/`, from
scratch on every run. Nobody writes or edits them by hand. Run it after any
of its sources changes:

```
.venv/bin/python -m src.graph_notes
```

| Note | Source |
|---|---|
| `ontology/<Class>.md` | `ontology.yaml` |
| `notes/Article <article_id>.md` | `data/corpus.csv`, `data/files.csv`, `results/no_claims.csv`, `checks/claims_gold.csv`, `checks/gold_articles.csv` |
| `notes/Claim <claim_id>.md` | `results/claims.csv`, `results/comparison.csv` |
| `notes/Series <series_id>.md` | `tools/ablation_db.py` (once it exists) |
| `notes/Check <claim_id> <reason>.md` | `checks/claim_checks.csv`; `checks/claims_gold.csv` (§2.4) |

The script exits with 1 if a note would break `ontology.yaml` (unknown class,
relation or attribute value; a link against domain or range) or if the
Claim notes and the `claim_id`s of `results/claims.csv` differ.

### 2.1. Class note

```
---
kind: class
---
# <Class>

<definition>

Relations from this class: <relations with the class in domain>.
Attributes: <attributes with the class in domain, with their values>.

## Links
```

All classes are top-level, so `## Links` is empty.

### 2.2. Object note

```
---
type: <Class>
<attribute>: <value>
---
# <name>

<1–3 lines from the source row>

## Links
- type: [[<Class>]]
- <relation>: [[<note name or path from the root>]]
```

One link per line; links are never in backticks. Files get no notes: a link
to a file is its path from the root, e.g. `[[results/claims.csv]]`.

| Class | Attributes | Links | Body |
|---|---|---|---|
| Article | – | `storedIn` each PDF; `noClaimReasonIn: [[results/no_claims.csv]]` if it has a row there | title, year, DOI; for a gold article, the number of gold claims and how many the agent found |
| Claim | `direction`, `basis`; `verdict` for `own_data` (§2.3) | `extractedFrom: [[Article <id>]]`; `comparedWith` each series of its `comparison.csv` rows; `storedIn: [[results/claims.csv]]` | `variable`, `material`, `medium_class`, `page`; never the quote |
| Series | `shape_primary`, `shape_lenient` | `reportedIn: [[Article <id>]]`; `computedBy: [[tools/ablation_db.py]]` | `n_points`, `x_quantity`, `medium_class` |
| Check | `reason` | `checks: [[Claim <claim_id>]]`; `storedIn` its source file | `outcome`, `wrong_fields`, `curator`, `date` |

### 2.3. Verdict

From the claim's rows of `results/comparison.csv`; no rows (file not yet
written) → no `verdict`.

| Rows | `verdict` |
|---|---|
| none with a `series_id` | `unmatched` |
| every row `agree_primary` and `agree_lenient` true | `agrees` |
| every row both false | `disagrees` |
| anything else | `model_dependent` |

"Anything else" also covers two series of one claim that disagree with each
other.

### 2.4. Gold checks

For an article in `checks/gold_articles.csv`, each agent claim gets a Check
with `reason: gold_sample`: `outcome: correct` if a gold row has the same
`(article_id, variable, direction, basis, medium_class)`, otherwise `wrong`
(the key of `results_spec.md` §7.6). Gold claims the agent missed have no
Claim note; the Article note states them (§2.2).

## 3. Tasks

The agent writes the notes in `tasks/`. A user message that needs work on
project files is a new top-level task, even if it continues an earlier one;
a question answered in words is not a task.

```
---
type: Task
status: open
---
# <action>

Request: "<the user's words, verbatim>"      (top-level task only)

Done when: <checkable: a file, a number, a command and its result>
Not included: <what not to do>

## Plan                                        (parent task only)
<subtask names, one per line, no links>

## Summary                                     (from status done or blocked)
<what was done, which files and notes appeared, how it was checked: command and result>

## Links
- type: [[Task]]
- subtaskOf: [[<parent task>]]                 (subtask only)
- resolvedBy: [[<note or file>]]               (from status done)
```

- The name is an action ("Extract the claims of article 534494"), unique in
  the project and without `/ \ : # | [ ]`.
- Record the task and its 2–5 subtasks with status `open` before any other
  work, and show the plan to the user, one line per subtask. A task is split
  only if it needs several closing objects.
- "Done when" never changes after work starts; if it cannot be met, the
  status is `blocked`.

| `status` | Set when |
|---|---|
| `open` | the task is recorded |
| `in progress` | before the subtask's first command |
| `done` | "Done when" is checked by a command and `## Summary` is written |
| `blocked` | "Done when" cannot be met: reason and question in `## Summary` |
| `accepted` | the user's words accept it |

- Change a status at the moment of the event, one subtask at a time.
- A parent task is `done` when all its subtasks are; its Summary sums them up.
- `accepted` only after the user's words ("accept" or equal in meaning); it
  covers the subtasks; add `Accepted by the user: "<their words>"` to each
  Summary. A request to redo returns the task to `in progress`.
- An accepted task is closed: new work is a new task.
- A message that both accepts and sets new work: accept first, then record
  the new task.

## 4. End of each user message

1. `.venv/bin/python -m src.graph_notes` exits with 0 (once the script exists).
2. Statuses and Summaries are up to date.
3. `diary.md` gets an entry: date, the message in short, tasks and every
   status change, what appeared in the graph, the check commands and their
   exit codes.
