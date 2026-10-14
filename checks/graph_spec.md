# Project graph specification

Defines the notes in `ontology/`, `notes/` and `tasks/`: who writes them,
their format and their links. The schema (classes, relations, attributes,
rules) is `ontology.yaml`. Change this file and `ontology.yaml` together;
both change only by the human.

## 1. Vault

The project root is an Obsidian vault: every file is a node, every `[[…]]`
link an edge. `.obsidian/app.json` and `.obsidian/graph.json` are set by the
human.

## 2. Notes and their check

The agent writes all notes in `ontology/`, `notes/` and `tasks/` by the
rules below. `checks/graph_check.py` checks them against `ontology.yaml` and
the result tables; it is the readiness criterion of the graph:

```
.venv/bin/python checks/graph_check.py
```

| Note | Must match |
|---|---|
| `ontology/<Class>.md` | one per class of `ontology.yaml` |
| `notes/Article <article_id>.md` | an `article_id` of `data/corpus.csv` |
| `notes/Claim <claim_id>.md` | a `claim_id` of `results/claims.csv`, one to one; its `direction` and `basis` |
| `notes/Series <series_id>.md` | the output of `tools/ablation_db.py` (none until it exists) |
| `notes/Check <claim_id> <reason>.md` | a row of `checks/claim_checks.csv`, one to one; its `outcome` |

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
| Article | – | `storedIn` each PDF; `noClaimReasonIn: [[results/no_claims.csv]]` if it has a row there | title, year, DOI |
| Claim | `direction`, `basis`; `verdict` for `own_data` (§2.3) | `extractedFrom: [[Article <id>]]`; `comparedWith` each series of its `comparison.csv` rows; `storedIn: [[results/claims.csv]]` | `variable`, `material`, `medium_class`, `page`; never the quote |
| Series | `shape_primary`, `shape_lenient` | `reportedIn: [[Article <id>]]`; `computedBy: [[tools/ablation_db.py]]` | `n_points`, `x_quantity`, `medium_class` |
| Check | `reason` | `checks: [[Claim <claim_id>]]`; `storedIn: [[checks/claim_checks.csv]]` | `Outcome: <outcome>` on its own line; `wrong_fields`, curator, date |

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

The curator compares the agent's claims of a gold article with the hand
labels after the agent's run and records each verdict in
`checks/claim_checks.csv` with `reason: gold_sample`; the agent then writes
the Check note like any other. Neither the agent nor `graph_check.py` reads
the hand labels (`AGENTS.md` ban 3).

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
- "Done when" names a command and the result it must give. The top-level
  task's "Done when" also includes `checks/graph_check.py` exiting with 0.
  Running a check is part of every subtask, not a subtask of its own.
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

1. `.venv/bin/python checks/graph_check.py` exits with 0.
2. Statuses and Summaries are up to date.
3. `diary.md` gets an entry: date, the message in short, tasks and every
   status change, what appeared in the graph, the check commands and their
   exit codes.
