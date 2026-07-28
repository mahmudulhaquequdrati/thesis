# Lesson 27 — `db.py`: the schema and never paying twice

*Part 3 · about 1 hour · `carr/db.py` (476 lines)*

---

## In one sentence

> The module that guards the one thing money bought — with a `UNIQUE` hash that
> makes a crashed run free to resume, a mock flag that cannot be forgotten, and a
> results schema that mirrors the grader exactly.

---

## The three guarantees

The docstring names them, and each one exists because of a specific failure:

> 1. **Never pay twice.** `generations.request_hash` is UNIQUE over (model,
>    effort, prompt, params). `insert_generation` checks it and returns `None`
>    rather than raising, so a crashed run can be restarted and the
>    already-bought rows cost $0 to skip.
> 2. **Non-purchased rows can never be mistaken for real ones.** `is_mock` is a
>    real column and every analysis query filters on it. There is no mock provider
>    in the tree today, **but the column stays**: the moment anything writes a row
>    it did not buy, an unflagged one is indistinguishable from a $0.0006
>    purchased one, and by then the mistake is invisible.
> 3. **The grader's output shape is the results schema.** Columns mirror
>    `GradeResult` exactly, so there is no translation layer that could silently
>    drop or rename a field.

Guarantee 2 is the most interesting, because the thing it defends against
**cannot currently happen**. The mock provider was deleted. The column stays
anyway, because the cost of keeping it is one column and the cost of not having
it — should anything ever write an unpurchased row — is a corrupted scientific
asset with no way to tell which rows are real.

**Defending against a failure that is currently impossible, because it would be
undetectable if it became possible, is a genuinely mature engineering call.**

---

## `request_hash` — resumability, in one column

```python
payload = "\x00".join([model_slug, effort_label, prompt,
                       json.dumps(params, sort_keys=True, separators=(",", ":")),
                       problem_id])
```

Two details, each with a reason:

**`sort_keys=True`** — so dictionary ordering cannot produce two different hashes
for the same request. Without it, `{"a":1,"b":2}` and `{"b":2,"a":1}` hash
differently, and **you buy the same generation twice.**

**`\x00` as the separator** — a byte that cannot appear in any of the fields, so
`"ab" + "c"` and `"a" + "bc"` cannot collide.

### ⚠️ The latent bug: `problem_id` was missing

Read the docstring's own account:

> `problem_id` is in here even though it does not change what the API returns
> (the prompt already determines that). **Without it, two problems that happen to
> share a prompt collide**: the second one silently gets no generation row, no
> result, and therefore **no routing label** — and CARR's target is "cheapest
> config that passes THIS problem", which needs every problem to have been run
> through every configuration. **That hole would be invisible.**

Follow the failure: problem B shares a prompt with problem A. B's request hashes
to A's hash. `has_generation` says "already bought". B is skipped. B has no row,
no grade, no label — and nothing anywhere reports a missing problem, because
skipping is the *normal* path.

The trade is stated too: you now pay twice for genuinely identical prompts.
**Across the 717-problem pool there are zero duplicate prompts**, so it costs
nothing today and closes a failure that could not be detected later.

That is the ideal shape of a bug fix: name the failure, name the cost of the
fix, show the cost is currently zero, and take it.

And when it was fixed, the existing rows were **migrated in place, not
re-bought** (`migrate_request_hashes`). Fixing a hash function must not cost
$5.24.

### Why it returns `None` instead of raising

```python
except sqlite3.IntegrityError as exc:
    if "request_hash" in str(exc):
        return None
    raise
```

> Returning `None` instead of raising is the point: the caller's loop treats a
> duplicate as **"already bought, skip"** rather than as an error to abort on.

Note it re-raises anything *else*. A duplicate hash is expected; a foreign-key
violation is not, and must not be swallowed.

There are **two** layers of this protection: `has_generation()` is a cheap
pre-flight check *"so we never even build a paid request twice"*, and the
`UNIQUE` constraint is the backstop if the check is somehow bypassed. Cheap check
in front, hard guarantee behind.

---

## `backup()` — because `generations` cannot be rebuilt

```python
source = sqlite3.connect(src)
target = sqlite3.connect(dest)
with target:
    source.backup(target)
```

Three decisions:

- **sqlite3's own backup API, not a file copy** — safe while other connections
  are open. A `cp` of a live SQLite file can produce a corrupt snapshot.
- **Timestamped filenames**, keeping the newest 10.
- **Called before anything destructive.** `scripts/studio.py` snapshots before
  its first write of each session, and its SQL console runs on a **read-only**
  connection.

`CLAUDE.md`: *never edit `data/carr.sqlite` without a snapshot.* A delete button
on a table that cost $5.24 needs an undo.

---

## Schema details worth defending

```sql
error_type TEXT CHECK (error_type IN ('assertion', 'timeout'))
```

> Constrained to what `grade()` actually emits. The specs also listed `'syntax'`
> and `'exception'`; **nothing produces those, so they are not allowed in until
> something does.**

A schema that documents impossible values is a schema that lies. When the code
and the spec disagreed, **the code won every time** — there is a four-row table
in THESIS.md §8 recording each conflict and its resolution.

```python
conn.execute("PRAGMA foreign_keys = ON")
```

SQLite does **not** enforce foreign keys by default. One line turns on the
guarantee that a `results` row cannot point at a generation that does not exist.

```python
conn.row_factory = sqlite3.Row
```

Lets you write `row["passed"]` instead of `row[3]`. Small, but it means a column
reorder cannot silently shift every read.

### Two repair functions, kept in the tree

```python
def migrate_request_hashes(conn) -> int:
def repair_config_ids(conn) -> tuple[int, int]:
```

These are the fixes for the two bugs in this lesson and lesson 22. They are
**kept, not deleted**, and that is right: they are the audit trail of what was
done to the scientific asset. If anyone asks "were the 8 misattributed rows
guessed or resolved?", the function is the answer.

---

## Do this

**1. Prove the dedup works.**

```bash
cd ~/thesis
uv run pytest tests/test_db.py -v
```

Thirteen tests. One of them is literally "never pay twice".

**2. See a hash.**

```bash
uv run python -c "
from carr.db import request_hash
h1 = request_hash('m', 'off', 'prompt', {'a':1,'b':2}, 'P1')
h2 = request_hash('m', 'off', 'prompt', {'b':2,'a':1}, 'P1')
h3 = request_hash('m', 'off', 'prompt', {'a':1,'b':2}, 'P2')
print('same params, different order  ->', h1 == h2, '(must be True)')
print('different problem_id          ->', h1 == h3, '(must be False)')
"
```

The first line is `sort_keys=True` working. The second is the latent bug closed.

**3. Look at the backups.**

```bash
ls -la data/backups/ | head
```

Each is a full copy of the asset.

**4. Confirm no duplicate prompts exist.**

```sql
SELECT COUNT(*) FROM (
  SELECT prompt FROM problems GROUP BY prompt HAVING COUNT(*) > 1
);
```

Zero. **That is the measurement showing the `problem_id` fix costs nothing
today.**

**5. Check the never-pay-twice property on real data.**

```sql
SELECT COUNT(*) AS rows_, COUNT(DISTINCT request_hash) AS hashes FROM generations;
```

Equal. Every purchased cell is unique.

---

## Check yourself

1. State the three guarantees `db.py` exists to provide.
2. Why does `is_mock` remain even though nothing can write a mock row?
3. Why is `sort_keys=True` essential in `request_hash`?
4. Explain the `problem_id` bug: what would have happened, and why would it have
   been invisible?
5. Why does `insert_generation` return `None` on a duplicate rather than
   raising — and what does it still re-raise?
6. Why use sqlite3's backup API rather than copying the file?
7. Why is `error_type` restricted to two values when the spec listed four?

<details>
<summary>Answers</summary>

1. Never pay twice (`request_hash UNIQUE`); non-purchased rows can never
   masquerade as real (`is_mock`); the results schema mirrors `GradeResult`
   exactly so nothing can be silently dropped or renamed.
2. Because if anything ever writes an unpurchased row without the flag, it is
   indistinguishable from a real purchase and the corruption is undetectable. The
   column costs nothing; its absence would cost the asset's integrity.
3. Without it, the same parameters in a different dictionary order hash
   differently, so the same generation is bought twice.
4. Two problems sharing a prompt would collide: the second gets no generation, no
   result, and no routing label. It is invisible because skipping an
   already-bought cell is the normal path, so nothing reports the missing
   problem.
5. So the caller's loop treats a duplicate as "already bought, skip" rather than
   an error. It still re-raises any other integrity error — a foreign-key
   violation must not be swallowed.
6. Because copying a live SQLite file can produce a corrupt snapshot; the backup
   API is safe with other connections open.
7. Because `grade()` only ever emits `assertion` and `timeout`. A
   documented-but-impossible value is a trap, and the schema should match the
   code rather than an aspiration.

</details>

---

➡️ Next: [Lesson 28 — The paid loop and the cost cap](28-runner.md)
