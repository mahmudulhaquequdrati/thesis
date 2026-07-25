# Codebase tour — everything, in order

A teaching walkthrough of every file in this repository: what it is, why it
exists, and what is inside it. Read top to bottom the first time.

**Current size:** ~460 lines of Python, ~1,000 lines of documentation, 20 files.
Small on purpose. This is a research codebase, not a framework.

---

# Part 0 — The mental model

Before any file makes sense, hold this shape in your head:

```
        A PROBLEM                    A CONFIG
   "write a function that      "deepseek-v4-flash,
    reverses a string"          thinking = high"
            |                          |
            +------------+-------------+
                         |
                         v
                  send to the API
                         |
                         v
              model returns markdown text
                         |
                         v
              extract the code from it
                         |
                         v
           run it against the problem's tests
                         |
                         v
        ONE ROW:  passed? tokens? cost?
```

Do that ~2,700 times (300 problems × 9 configs) and you have **the table**.
The table is the thesis. Everything in this repository either **fills** the
table, **protects** it, or **reads** it.

**How many tests is "the problem's tests"?** It varies a lot, and the figure
1,006 that appears throughout this tour is `HumanEval/0` specifically — the
worked example — not a general number. Measured across the actual files:

| | HumanEval+ | MBPP+ |
|---|---|---|
| Problems | 164 | 378 |
| Test inputs, total | 124,253 | 41,015 |
| Per problem: min / **median** / max | 12 / **982** / 1,100 | 3 / **108** / 150 |

Only 9 of the 164 HumanEval+ problems have exactly 1,006.

Three jobs, and every file belongs to exactly one:

| Job | Files |
|---|---|
| **Fill** the table | `scripts/day1_hello.py`, and the runner (not built yet) |
| **Protect** the table | `carr/execute/verify.py`, `tests/`, `config/models.yaml`, `estimate_cost.py` |
| **Explain** the work | `THESIS.md`, `CLAUDE.md`, `docs/` |

---

# Part 1 — The dataset

This is the part to understand first, because everything else serves it.

There are **two different things** both called "dataset". Do not confuse them.

## 1.1 The INPUT dataset — problems we download, free

We do not write coding problems. We download standard ones so our results are
comparable to published work.

### HumanEval+ — 164 problems

Written by OpenAI (HumanEval, 2021), then extended by the evalplus team who added
far more tests because the originals were too weak — a wrong solution could pass.
The "+" is those extra tests.

**One problem is a Python dictionary with these fields:**

| Field | What it is | Do we send it? |
|---|---|---|
| `task_id` | `"HumanEval/0"` — unique name | no |
| `prompt` | Function signature + docstring | **YES, verbatim** |
| `entry_point` | `"has_close_elements"` — the function name the tests call | no |
| `canonical_solution` | The official correct answer | **NEVER** |
| `base_input` | Original test inputs (7 for problem 0) | **NEVER** |
| `plus_input` | evalplus's extra test inputs (999 for problem 0) | **NEVER** |
| `atol` | Float tolerance for comparing answers | no |

Here is the **complete** `prompt` for `HumanEval/0` — this exact text is the
entire message we send:

```python
from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
```

That is it. An unfinished function. The model's job is to write the body.

**The tests are inputs, not assert statements.** `base_input[0]` is
`[[1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3]` — the arguments. evalplus runs the
*canonical* solution on every input to learn the right answers, then runs the
*model's* code on the same inputs and compares. That is why the tests never need
to be sent, and why sending them would be cheating.

### MBPP+ — 378 problems

"Mostly Basic Python Problems", from Google. Easier and shorter than HumanEval.
Prompts are plain English with one example assertion:

```python
"""
Write a function to find the shared elements from the given two lists.
assert set(similar_elements((3, 4, 5, 6),(5, 7, 4, 10))) == set((4, 5))
"""
```

> **Note:** the proposal says "MBPP, 500 sampled". **378 is all that exists** —
> evalplus removes problems whose tests are broken. The 500 was never available.

### LiveCodeBench — the hard tier, **not built yet**

Competitive-programming problems from LeetCode/AtCoder/CodeForces, tagged with a
release date. The release date matters: if a problem was published *after* a
model's training cutoff, the model cannot have memorised it. That is
**contamination filtering**.

This tier is the one that makes the thesis non-trivial — see the saturation risk
in `THESIS.md §11`. It is the biggest remaining gap in the harness.

### Measured sizes

| Benchmark | Problems | Median prompt | Difficulty |
|---|---|---|---|
| HumanEval+ | 164 | 99 tokens | easy–medium |
| MBPP+ | 378 | 36 tokens | easy |
| LiveCodeBench | ~150 planned | not measured | **hard** |

Those prompt sizes are why **~100% of the budget is output tokens**. Input is
almost free.

## 1.2 The OUTPUT dataset — the table we build, ~$3.60

This is the thesis's actual contribution. It does not exist anywhere on the
internet, which is why we have to generate it.

One SQLite file, `data/carr.sqlite`, with five tables:

```
problems     ~300 rows    what we asked           free
configs         9 rows    who we asked            free
generations  ~2,700 rows  what came back          $3.60  <-- the only costly one
results      ~2,700 rows  did it work             free (CPU only)
features     ~300 rows    numbers describing      free
                          each problem, for CARR
```

**`generations` is the money table.** Every row is one API call that was paid
for. It cannot be regenerated from anything else. Back it up outside git.

**`results` is free** because grading is pure CPU. If the grading logic has a
bug, we re-grade from stored `raw_response` at zero cost — which is exactly why
`raw_response` is stored verbatim.

Full column-by-column detail: [data-spec.md](data-spec.md).

## 1.3 What the table is FOR

Everything reduces to one query. For each problem, find the cheapest config that
still passed:

```sql
SELECT problem_id, MIN(cost) FROM generations
JOIN results USING (gen_id)
WHERE passed = 1
GROUP BY problem_id;
```

That answer is CARR's **routing target** — the thing the router tries to predict
without paying for any of it.

**This is why every problem must run through every config.** Skip cells to save
money and the target becomes uncomputable. Budget is cut by dropping *problems*,
never by dropping cells.

---

# Part 2 — Every file

## 2.1 Environment layer

### `pyproject.toml` (24 lines)

The project definition — dependencies and Python version.

```toml
requires-python = ">=3.12,<3.13"
```

**The single most important line in the file.** Your Mac's system Python is
3.14.3. `evalplus` and the ONNX embedding libraries have no wheels for it. Left
unpinned, everything installs fine today and explodes in Week 3.

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

Lets `import carr` work without installing the package. Research code runs in
place.

### `.python-version` (1 line)

Contains `3.12`. `uv` reads this to build the virtual environment.

### `.env` / `.env.example`

`.env` holds `OPENROUTER_API_KEY`. **It is gitignored and must stay that way** —
a leaked key is someone else spending your money. `.env.example` is the committed
template showing the shape without the secret.

### `.gitignore`

Excludes `.venv`, `.env`, and `data/*.sqlite`. That last one is deliberate: the
database is *too valuable* for git, not too worthless. It costs real money and
belongs in a backup, not a diff.

---

## 2.2 `config/models.yaml` (114 lines) — the roster

**Every model name and price in the project lives here and nowhere else.**

Why: the open-weight landscape moves every 6–8 weeks. Hardcode `deepseek-v4-pro`
in ten files and you have ten places to fix when it is renamed.

Structure of one entry:

```yaml
- slug: deepseek/deepseek-v4-flash    # the id OpenRouter expects
  family: deepseek                    # for within- vs cross-family analysis
  price_in_per_m: 0.094               # USD per million input tokens, VERIFIED
  price_out_per_m: 0.188              # USD per million output tokens, VERIFIED
  efforts:
    - label: "off"
      mechanism: native_toggle
      params: {reasoning: {enabled: false}}
    - label: "high"
      mechanism: native_toggle
      params: {reasoning: {effort: "high"}}
```

Four things worth understanding:

1. **Each model appears with two efforts.** That pairing is the experiment: within
   a pair, the *only* thing that changes is thinking. Comparing two different
   small models instead would confound model quality with effort.
2. **`mechanism` is recorded, not assumed.** `native_toggle` means the provider
   has a real thinking switch. `budget_forcing` would mean we fake it with a token
   cap. These are **not equivalent**, so results must be splittable by mechanism.
3. **`held_out:`** contains `kimi-k2.6`, deliberately excluded from CARR's build
   set. It is the only non-DeepSeek/Qwen family, making it the most genuinely
   unseen model available for RQ5. It runs on a *subset* — RQ5 asks about
   transfer, which does not need full coverage.
4. **`rejected:`** records what we did *not* pick and why — e.g. `kimi-k2.7-code`
   at $3.50/M would alone exceed the budget. Without this you re-litigate the
   same decision in a month.

Prices verified live on 2026-07-25. Output prices span **18×** across the roster.

---

## 2.3 `carr/execute/verify.py` (141 lines) — the grader

**The most important code in the repository.** It decides `passed: true/false`,
and that boolean feeds the Pareto frontier, the CPC metric, and CARR's routing
target alike. A grader that lies corrupts everything, invisibly.

### What it does

```python
grade("humaneval", "HumanEval/0", code) -> GradeResult(passed=True, ...)
```

### Why it wraps evalplus instead of doing its own thing

Because **pass/fail is not `==`**:

- Float results compare against a per-problem `atol` tolerance
- Some MBPP tasks are graded by **set equality**, order-independent
- Others only assert the output **is not None**

Hand-rolling that gets it subtly wrong, and subtly wrong labels are worse than
obviously broken ones.

### The block worth reading twice

```python
os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")
```

evalplus caps subprocess memory with `resource.setrlimit(RLIMIT_AS)`. **macOS
refuses to lower that limit at any value.** The resulting `ValueError` is the
*first statement* of `reliability_guard()`, so:

1. The subprocess dies before running a single test
2. `os.system` and ~40 other calls never get disabled
3. evalplus reports the dead process as a **timeout**

Result: every solution "fails", including evalplus's own reference solutions.
This would have spent the entire $4 recording that every model fails everything —
and the numbers would have looked believable.

`-1` skips the setrlimit block so the rest of the guard actually runs. The cost:
no memory ceiling, only the timeout. Documented in the file; do not remove it.

### `GradeResult`

```python
passed: bool          # survived BOTH base and plus tests -- the metric
base_passed: bool     # original tests only
n_tests_passed: int   # diagnostic. NOT the metric -- pass@1 is binary
n_tests_total: int
error_type: str|None  # None | "assertion" | "timeout"
```

`n_tests_passed` is for diagnosis only. A solution passing 846 of 1,006 tests is
**failed**, not 84% correct.

### `_CACHE`

Loading problems and computing ground truth is slow — evalplus runs every
canonical solution against every test input to learn the expected answers. Cached
in memory here, and on disk by evalplus.

---

## 2.4 `tests/test_verify.py` (113 lines)

Eight tests. The grader is the one component that **must** be right.

| Test | What it proves |
|---|---|
| `test_correct_code_passes` | A right answer scores 1006/1006 |
| `test_wrong_code_fails` | A **plausible near-miss** is caught — only compares adjacent elements, misses far-apart close pairs. Scores 846/1006 → FAIL |
| `test_infinite_loop_times_out_cleanly` | `while True: pass` terminates. If this hung, a 2,700-row run would hang |
| `test_syntax_error_fails_without_crashing` | Broken code fails gracefully |
| `test_hostile_code_is_contained` | `os.system("echo PWNED > /tmp/...")` does not create the file |
| `test_canonical_solutions_pass` ×3 | **The most valuable test in the repo** |

That last one deserves explanation. It runs *evalplus's own official solutions*
through our harness. They must score ~100%. If they do not, **our harness is
broken — it is not a finding about models.**

That distinction is everything. Without this test, the macOS bug would have shown
up as "all 2026 reasoning models fail all coding problems", which is absurd but
not obviously so in a spreadsheet. This test is what caught it.

---

## 2.5 `scripts/` — runnable entry points

### `day1_hello.py` (99 lines)

One API call. Its purpose is not the generated code — it is showing where every
cost number comes from.

```python
usage.prompt_tokens                              # 23
usage.completion_tokens                          # 412  <- billed
usage.completion_tokens_details.reasoning_tokens # 392  <- INVISIBLE in the text
```

The visible answer was three lines. **95% of the billed tokens were thinking you
never see.** Measuring cost from response length understates it by 20×.

Then it fetches `GET /generation?id=...` for what was *actually charged* — the
ground truth when your price table is stale.

### `probe_cost_endpoint.py` (58 lines)

Answers one question: is the ground-truth cost endpoint usable?

Result: **yes, but it needs ~10 seconds to settle** (404 before that). So the
runner must collect generation IDs and reconcile costs in a **batch afterwards**,
never blocking per call — otherwise 2,700 calls × 10s adds 7.5 hours.

### `day2_inspect_problems.py` (75 lines)

Prints a real problem: prompt, entry point, canonical solution, test counts. Free.

```bash
uv run python scripts/day2_inspect_problems.py --task HumanEval/23
```

Use it whenever you want to see what the model actually receives.

### `estimate_cost.py` (86 lines)

Prices the whole grid *before* spending anything. Pure arithmetic over
`config/models.yaml`.

```bash
uv run python scripts/estimate_cost.py --think-tokens 6000
```

It sorts configs **cheapest first** — the same order the runner must use, so a
budget breach costs the expensive tail rather than the cheap foundation.

Its current output is the project's central open question:

| Mean thinking tokens | Grid cost | |
|---|---|---|
| 3,500 | **$3.55** | fits $4 |
| 6,000 | **$5.89** | **over** — supports ~203 problems |
| 9,000 | **$8.69** | **over** — supports ~138 problems |

*(Corrected 2026-07-26. This table previously read $3.61/$5.94/$8.75, which was
not reproducible from the script; THESIS.md §9 separately read $3.82/$6.15/$8.96
using the pre-Day-2 guess of 600 prompt tokens. The default `--in-tokens` is now
the measured 100, so both documents derive from one number.)*

Nobody knows which is true yet. That is what the pilot measures, and why the
pilot is a gate rather than a formality.

---

## 2.6 Documentation

### `THESIS.md` (513 lines) — the master document

**The single source of truth.** 16 sections: status, what we are building,
research questions, the stack, progress tracker, day-by-day plan, repo layout, DB
schema, the experiment, the formal section, risks, decisions log, glossary, owed
`.docx` edits, prior art, and maintenance rules.

Read **§1 first every session** — stage, next action, spend, blockers.

§12 (decisions log) is **append-only**. Superseded choices stay, struck through,
so you never re-argue a settled question.

### `CLAUDE.md` (103 lines) — working rules

Instructions for any AI assistant in this repo. Six sections, but §1 is the point:
a table mapping *kind of change* → *which doc to update*. It exists because you
pick this project up days apart, and a stale status section costs more time than
the work saved.

Also encodes the budget discipline and the hard constraints — including the two
learned the hard way: never hand-roll grading, never remove
`EVALPLUS_MAX_MEMORY_BYTES=-1`.

### `docs/data-spec.md` (237 lines)

The precise contract: what a problem is, exactly what we send, exactly what comes
back, how extraction and grading work, every column of every table with its
source, and a worked end-to-end example. **This is what you write the program
from.**

### `docs/advisor-repositioning.md` (89 lines)

One page for your advisor: the four papers that eroded the novelty claim, the
proposed "cheapest possible router" reframing, two methodology corrections, and
three questions to ask. Written to be handed over as-is.

### `README.md` (28 lines)

Setup commands and a layout table. Points at `THESIS.md`.

---

# Part 3 — How it all connects

```
config/models.yaml ──> which models, what prices
        │
        v
   [runner.py]  <── NOT BUILT YET
        │
        ├── reads problems ──── evalplus (HumanEval+ 164, MBPP+ 378)
        │
        ├── sends prompt ────── OpenRouter API      $  costs money
        │
        ├── writes ──────────── generations table   $  the money table
        │
        ├── grades ──────────── carr/execute/verify.py    free
        │
        └── writes ──────────── results table             free
                                      │
                                      v
                            [analysis/]  <── NOT BUILT YET
                                      │
                            Pareto frontier, CPC, convex hull
                                      │
                                      v
                            [router/]    <── NOT BUILT YET
                                      │
                                 CARR: k-NN lookup
```

Built: the roster, the grader, the tests, the cost estimator, the inspection
scripts. Not built: the runner, the database, the analysis, the router.

---

# Part 4 — What does not exist yet

Honest gaps, in priority order:

Built since this tour was first written (2026-07-26): **`carr/db.py`**
(schema, `request_hash` dedup, read helpers), **`carr/extract.py`**,
**`carr/cost.py`**, **`carr/effort.py`**, **`carr/providers/base.py`**,
**`scripts/init_db.py`**, **`scripts/studio.py`** and **`scripts/view.py`**.

The chain was proven end to end against a mock provider, and then the mock was
deleted — it had done its job. `data/carr.sqlite` now holds only real, free
data: 542 problems and 9 configs. `generations` and `results` are **empty on
purpose**; the only way to fill them is to buy the rows.

Honest gaps, in priority order:

| Missing | Why it matters |
|---|---|
| **`carr/providers/openrouter.py`** | **The only thing between here and real data.** API calls still exist only inside `day1_hello.py`. Implement the `Provider` contract in `providers/base.py` and swap it for `echo` |
| **`carr/runner.py`** | The loop. Needs `request_hash` dedup (built, in `carr/db.py`), cheapest-first ordering (built, in `carr/effort.py`) and a cost cap that *aborts* (not built) |
| **LiveCodeBench loader** | **The hard tier.** RQ4 is at risk of a degenerate result without it. Largest scientific gap in the repo |
| **`config/experiment.yaml`** | The `$50` hard cap that THESIS.md §9 says lives here has no file to live in yet |
| **`carr/features.py`** | CARR's inputs. `problems.n_tests` and `prompt_chars` are already stored for it |
| **`carr/router/`** | CARR itself |
| **`carr/analysis/`** | Pareto, convex hull, bootstrap CIs |

Roughly half the code exists. It is the half that protects the rest from
producing wrong numbers — which is the right order to build in.

## How to look at the data right now

```bash
uv run python scripts/init_db.py    # 542 problems + 9 configs, free
uv run python scripts/studio.py     # browser, http://127.0.0.1:8787
uv run python scripts/view.py --list   # terminal
```

**Studio** reads the schema out of SQLite at request time — table list, column
names and types, primary keys, and which tables reference which — so it is not
tied to CARR's schema and will keep working when `features` and `router_runs`
are added. It does sort, search, pagination, a read-only SQL console, and row
editing and deletion.

It is a small stdlib server rather than a static page because a `file://` page
cannot write to SQLite. Two guards, since `generations` rows cost money:

* the whole database is snapshotted to `data/backups/` before the first write
  of each session, so nothing done in the UI is unrecoverable;
* the SQL console runs on a read-only connection and accepts one
  SELECT / WITH / EXPLAIN / PRAGMA at a time.

`scripts/view.py` stays for the CARR-specific question studio cannot express in
a grid: one problem across all nine configs, ending with the cheapest config
that solved it — the routing label itself.
