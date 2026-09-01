# Lesson 07 — Databases and SQL from zero

*Part 1 · about 1.5 hours · after lesson 06*

**Take your time here. Your entire results section is SQL queries wearing a
Python coat.**

---

## In one sentence

> A database is a set of spreadsheets that know how to be joined together, and
> SQL is the sentence you say to ask them a question.

---

## The idea, from zero

### A table is a spreadsheet with rules

A **table** has named **columns** and any number of **rows**. Every row has a
value for every column, and every value in a column is the same *kind* of thing.

```
problems
┌──────────────┬────────────┬────────────┬─────────┐
│ problem_id   │ benchmark  │ difficulty │ n_tests │
├──────────────┼────────────┼────────────┼─────────┤
│ HumanEval/0  │ humaneval+ │ easy       │ 1006    │
│ HumanEval/1  │ humaneval+ │ easy       │ 934     │
│ lcb/abc123   │ lcb        │ hard       │ 43      │
└──────────────┴────────────┴────────────┴─────────┘
```

A **primary key** is the column that uniquely identifies a row — here,
`problem_id`. No two rows may share one.

**SQLite** is a database that is just a *file* — `data/carr.sqlite`. No server,
no installation, no configuration. Copy the file and you have copied the
database. For a thesis, that is exactly right: one portable, backup-able,
inspectable scientific asset.

### Your four tables, and what one row of each means

| Table | One row = | How many | Rebuildable? |
|---|---|---|---|
| `problems` | one benchmark problem | 884 | **yes**, free |
| `configs` | one (model × thinking-mode) pair | 10 | **yes**, free |
| `generations` | **one API call** | **1,373** | **NO — this cost $5.24** |
| `results` | one graded generation | 1,280 | **yes**, free — re-run the grader |

Read that table again, because the whole design of the repository follows from
the third row. **Only `generations` costs money.** That is why:

- it is gitignored and backed up separately
- `scripts/studio.py` snapshots the whole file before any write
- `request_hash` is `UNIQUE`, so a crashed run never re-buys anything

### Relationships: how tables connect

`generations` does not repeat the problem text. It stores a **foreign key** — a
pointer:

```
generations
┌────────┬──────────────┬───────────┬───────────────┬──────────────────┐
│ gen_id │ problem_id   │ config_id │ reasoning_tok │ cost_actual_usd  │
├────────┼──────────────┼───────────┼───────────────┼──────────────────┤
│ 1      │ HumanEval/0  │ 3         │ 0             │ 0.000106         │
│ 2      │ HumanEval/0  │ 4         │ 1240          │ 0.004630         │
└────────┴──────────────┴───────────┴───────────────┴──────────────────┘
              ↓ points at              ↓ points at
          problems.problem_id      configs.config_id
```

This is why databases beat one giant spreadsheet: the problem text is stored
**once**, not 1,373 times, and a correction to it is a correction everywhere.

### SQL, one clause at a time

SQL is a language for asking tables questions. It reads almost like English, and
you only need six pieces.

**1. `SELECT … FROM` — which columns, from which table**

```sql
SELECT problem_id, benchmark FROM problems;
```

`SELECT *` means "every column".

**2. `WHERE` — keep only some rows**

```sql
SELECT problem_id FROM problems WHERE difficulty = 'hard';
```

Combine with `AND` / `OR`:

```sql
SELECT * FROM problems WHERE benchmark = 'lcb' AND difficulty = 'hard';
```

**3. `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` — squash many rows into one number**

```sql
SELECT COUNT(*) FROM problems;              -- 884
SELECT SUM(cost_actual_usd) FROM generations;  -- your total spend
SELECT AVG(reasoning_tokens) FROM generations;
```

**4. `GROUP BY` — one answer per group instead of one overall**

This is the clause that turns a database into a results section.

```sql
SELECT benchmark, COUNT(*)
FROM problems
GROUP BY benchmark;
```

> "Give me the count — **but separately for each benchmark**."

```
humaneval+  164
mbpp+       378
lcb         342
```

The rule: everything in `SELECT` must either be in the `GROUP BY` or be wrapped
in an aggregate like `COUNT`/`AVG`.

**5. `JOIN` — use two tables at once**

`generations` knows the cost. `results` knows whether it passed. To ask about
both, stitch them by their shared column:

```sql
SELECT g.problem_id, g.cost_actual_usd, r.passed
FROM generations g
JOIN results r ON g.gen_id = r.gen_id;
```

`g` and `r` are nicknames (aliases). When the shared column has the same name in
both tables, there is a shorthand:

```sql
FROM generations JOIN results USING (gen_id)
```

**6. `ORDER BY` / `LIMIT` — sort, and stop early**

```sql
SELECT problem_id, cost_actual_usd
FROM generations
ORDER BY cost_actual_usd DESC
LIMIT 10;                     -- the ten most expensive calls you ever made
```

### The query your whole schema exists for

Now put it together. Your thesis's routing label is *"the cheapest configuration
that solved this problem"*. In SQL:

```sql
SELECT problem_id, MIN(cost_actual_usd)
FROM generations
JOIN results USING (gen_id)
WHERE passed = 1
GROUP BY problem_id;
```

Read it aloud, clause by clause:

- `FROM generations JOIN results` — every API call, with its grade attached
- `WHERE passed = 1` — throw away the ones that failed
- `GROUP BY problem_id` — handle each problem separately
- `MIN(cost_actual_usd)` — of the survivors, take the cheapest

Four lines. That is the ground truth the entire router chapter is judged
against.

### ⚠️ The filter you must never forget

```sql
WHERE is_mock = 0
```

Early in the project you seeded **fake rows** to test the pipeline without
spending money. They are all deleted now, but the column stays, because the
failure it prevents is *invisible once it happens*: an unflagged synthetic row
is indistinguishable from a real $0.0006 purchase, and by the time it matters
you cannot tell which is which.

Your `CLAUDE.md` makes it a rule. `db.summary()` applies the filter itself, so
your reported spend can never be inflated by a non-purchase.

---

## Why it is in *your* thesis

**Because the table *is* the thesis.** From your own THESIS.md §2:

> The table is the real scientific asset — RQ1–RQ3 are literally SQL queries
> against it. If the code is lost but this file survives, the thesis survives.

Everything in `carr/analysis.py` — every headline number you will write into
Chapter 5 — is a SQL query plus arithmetic. When you read that file in lesson
29, you will recognise `GROUP BY` and `JOIN` doing the work.

And the schema itself contains decisions you must be able to defend:

| Design choice | Why |
|---|---|
| `request_hash UNIQUE` | Never pay twice. Crash at row 3,000, restart costs $0 |
| `raw_response` stored verbatim | Re-grade free forever instead of re-buying |
| `is_mock` as a real column | A fake row must never be able to masquerade as a purchase |
| `effort_mechanism` as a column, not a comment | Native toggles and prompt tricks are not equivalent; results must be splittable by mechanism |
| `cost_computed` **and** `cost_actual` | Their disagreement is the only detector of silent price drift |

⚠️ And one bug that lives in this lesson's territory, because it is a perfect
illustration of why identity matters:

> **`config_id` was originally a configuration's position in a price-sorted
> list.** Repricing `deepseek-v4-pro` swapped two entries — and **8
> already-purchased generations were recorded against the wrong model**.

It surfaced only by accident, during an unrelated migration. Every per-model
number would otherwise have been quietly wrong. The fix: identity is now
alphabetical and price-independent; run *order* is a separate column
(`tier_index`). All 149 affected rows were repaired using `request_hash` as
ground truth — **resolved exactly, none guessed.**

The lesson generalises far beyond databases: **an identifier must never encode
something that can change.**

---

## Do this

**1. Open the database in a browser.**

```bash
cd ~/thesis
uv run python scripts/studio.py     # then open 127.0.0.1:8787
```

Click through all four tables. Look at actual rows. Find a `generations` row and
look at its `raw_response` — that is a real model's real answer, stored forever.

**2. Run these queries in Studio's SQL console, in order.**

```sql
-- how many problems, by benchmark?
SELECT benchmark, COUNT(*) FROM problems GROUP BY benchmark;

-- what did you actually spend?
SELECT COUNT(*), SUM(cost_actual_usd) FROM generations WHERE is_mock = 0;

-- pass rate for each configuration
SELECT config_id, COUNT(*) AS n, AVG(passed) AS pass_rate
FROM generations JOIN results USING (gen_id)
WHERE is_mock = 0
GROUP BY config_id ORDER BY pass_rate DESC;

-- the ten most expensive calls you ever bought
SELECT problem_id, config_id, reasoning_tokens, cost_actual_usd
FROM generations ORDER BY cost_actual_usd DESC LIMIT 10;

-- THE routing label
SELECT problem_id, MIN(cost_actual_usd) AS cheapest_pass
FROM generations JOIN results USING (gen_id)
WHERE passed = 1 GROUP BY problem_id LIMIT 20;
```

**3. Write one query yourself.**

*"What is the average number of reasoning tokens, for each difficulty tier?"*

<details>
<summary>Answer</summary>

```sql
SELECT p.difficulty, COUNT(*) AS n, AVG(g.reasoning_tokens) AS mean_reasoning
FROM generations g
JOIN problems p USING (problem_id)
WHERE g.is_mock = 0 AND g.reasoning_tokens > 0
GROUP BY p.difficulty;
```

The `reasoning_tokens > 0` filter matters: including the `off` configurations
would average in a thousand zeros and understate every tier.

</details>

---

## Check yourself

1. What is a primary key? What is a foreign key?
2. Which of your four tables cannot be rebuilt for free, and what follows from
   that?
3. In one sentence each: what do `WHERE` and `GROUP BY` do?
4. Explain the four-line "cheapest passing configuration" query, clause by
   clause.
5. Why does `is_mock` exist even though no mock rows remain?
6. `config_id` used to be a position in a price-sorted list. What went wrong,
   and what is the general lesson?

<details>
<summary>Answers</summary>

1. A primary key uniquely identifies a row within its own table. A foreign key
   is a column pointing at another table's primary key.
2. `generations` — it cost $5.24 of real money. Hence gitignored, snapshotted
   before writes, and protected by `request_hash UNIQUE`.
3. `WHERE` discards rows before anything else happens. `GROUP BY` splits the
   surviving rows into groups and produces one answer per group.
4. Join calls to their grades; keep only passes; handle each problem separately;
   take the minimum cost among that problem's passes.
5. Because a synthetic row is indistinguishable from a purchased one once the
   flag is gone, and the resulting corruption is invisible. The column is a
   guard against a mistake that must remain impossible.
6. Repricing a model changed its position, so its id changed, and 8 purchased
   rows were attributed to the wrong model. **An identifier must never encode a
   mutable property.** Identity and ordering are different things and need
   different columns.

</details>

---

➡️ Next: [Lesson 08 — Statistics I: samples, means, denominators](08-statistics-1.md)
