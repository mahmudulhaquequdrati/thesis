# Lesson 31 — `scripts/` and `tests/`

*Part 3 · about 1 hour · **last code lesson***

---

## In one sentence

> Fourteen scripts are the interface to the library, and 119 tests are the reason
> you can believe the numbers they print.

---

## The scripts, grouped by what they are for

### Free, and you will use these constantly

| Script | What it does |
|---|---|
| **`results.py`** | **Prints the entire thesis.** Every RQ, every number, every interval |
| `make_figures.py` | Four PNGs into `data/figures/` |
| `view.py` | Terminal view of one problem across every configuration |
| `studio.py` | Browser database explorer with a read-only SQL console |
| `grade.py` | Re-grade generations. Free — the generations are already bought |

### Free, and they exist to protect you

| Script | What it protects |
|---|---|
| `verify_roster.py` | Roster vs live `/models`. **Exits non-zero on drift** |
| `estimate_cost.py` | Prices a run *before* it happens |
| `init_db.py` | Builds the database from free sources. **Refuses `--reset` when paid rows exist** |

### The evidence scripts — kept because they produced findings

| Script | The finding it produced |
|---|---|
| `day1_hello.py` | **392 of 412 tokens were reasoning.** The origin story |
| `day2_inspect_problems.py` | Median prompt 99 tokens, not the assumed 600 |
| `probe_cost_endpoint.py` | `/generation` needs ~10s to settle |

**Keeping these is right.** A thesis claims numbers; the script that produced a
number should survive, because "reproduce this" then has an answer.

### ⚠️ These spend real money

| Script | |
|---|---|
| `run_one.py` | One problem through 1..N configurations |
| `pilot.py` | The pilot **and** the grid (`--set grid`) |

Both support `--dry-run`, and both compute a worst case before sending anything.

### Two design notes

**`studio.py` introspects the schema per request** rather than hardcoding your
tables — because *"the schema will change when `features` and `router_runs` land,
and a browser that needs editing every time the schema moves would simply not be
used."*

It is also a **local server, not a static page**: a `file://` page cannot write
to SQLite, and the requirement was to edit and delete rows. Stdlib
`http.server`, loopback only, no new dependency.

**Every write snapshots the database first**, and the SQL console runs on a
read-only connection. Verified by deleting two rows and confirming the snapshot
still held 542.

**`view.py` is not `inspect.py`** — lesson 21's naming trap.

---

## The tests — 119, and what each group buys

| File | Tests | What it makes impossible |
|---|---|---|
| `test_runner.py` | **16** | The cost cap failing to abort |
| `test_db.py` | **13** | Paying twice |
| `test_verify.py` | **8** | A silently broken grader |
| `test_verify_lcb.py` | **11** | A silently broken LCB grader |
| `test_extract.py` | **11** | Extraction raising, or inventing code |
| `test_router.py` | **10** | Evaluation dishonesty and mis-assigned blame |
| `test_stats.py` | — | The mean-of-ratios error |
| `test_analysis.py` | — | Wrong numbers in the results |

Look at the ranking. **The most-tested thing is the cost cap, and the second is
never paying twice.** For a project whose central risk was spending a student's
own money on an irreproducible dataset, that is exactly the right allocation.

### The four tests worth knowing by name

**1. `test_canonical_solutions_pass`** — run the benchmark's own known-correct
solutions through your grader. If they fail, the *instrument* is broken, not the
model.

> This is what caught the macOS `setrlimit` bug. It has also been run at scale —
> **210 canonical solutions, both benchmarks, all PASS** — before the fixture was
> retired.

That is the highest-value test in the project. It tests the measuring device
rather than the thing measured, which is a category of test most codebases never
write.

**2. The zero-headroom cap test** — a cap with no room buys **literally
nothing**. Not "nearly nothing".

**3. `test_ratio_is_not_the_mean_of_ratios`** — pins the statistical rule from
lesson 09, after that mistake had been made once.

**4. The LCB reference solutions** — hand-written, because LiveCodeBench ships no
canonical ones. They score 43/43 and 34/34, restoring the check from test 1 for
the benchmark where a silent bug would have been most expensive.

### The pattern worth naming

Look at what caused each of these tests:

| Test | Written because |
|---|---|
| canonical solutions | a grader bug would be silent and total |
| zero-headroom cap | a warn-and-continue "cap" is not a cap |
| ratio-not-mean-of-ratios | **that exact mistake was made once** |
| LCB references | the canonical check was unavailable |
| `make_all` survives a panel failing | losing three good figures to one bad one |

> **Every one of these tests exists because of a specific, named failure — most
> of them observed.** That is what separates a test suite from test theatre, and
> it is worth a sentence in Chapter 3.

---

## Reproducibility, demonstrated

`CLAUDE.md`: *fixed seeds everywhere — sampling, splits, bootstrap.
Reproducibility is a graded property of a thesis.*

The proof is one command:

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt        # must be identical
```

Identical output from a pipeline containing 10,000 bootstrap resamples, a
stratified sample and a leave-one-out cross-validation. **Run this before you
submit, and say in Chapter 3 that it holds.**

---

## Do this

**1. Run everything.**

```bash
cd ~/thesis
uv run pytest -q          # expect 119 passed
```

**2. Read the test names as a list of hazards.**

```bash
uv run pytest --collect-only -q | head -60
```

Each name is a thing that would otherwise be able to go wrong silently.

**3. Prove reproducibility yourself.**

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt && echo "IDENTICAL"
```

**4. Check the roster has not drifted.**

```bash
uv run python scripts/verify_roster.py; echo "exit code: $?"
```

Non-zero means something moved. **Run this before you quote a price in the
thesis.**

**5. Read the whole of `results.py`.**

```bash
less scripts/results.py
```

219 lines. Every section corresponds to a lesson from Part 2. **This script is
the skeleton of your results chapters** — when you write Chapter 5, you will
essentially be turning its output into prose.

---

## Check yourself

1. Which two properties are the most heavily tested, and why is that the right
   allocation?
2. What does `test_canonical_solutions_pass` test — and what does it *not* test?
3. Why was a hand-written reference needed for LiveCodeBench?
4. Why is `studio.py` a local server rather than a static HTML page, and why does
   it introspect the schema?
5. Why keep `day1_hello.py` in the repository?
6. What single command demonstrates reproducibility, and what must it output?
7. What distinguishes this test suite from test theatre?

<details>
<summary>Answers</summary>

1. The cost cap (16 tests) and never paying twice (13). Correct because the
   central risks were spending real money and losing an irreproducible dataset.
2. It tests the **grader** — the measuring instrument — by running known-correct
   solutions through it. It says nothing about any model's ability; a failure
   means the harness is broken.
3. Because LiveCodeBench ships no canonical solutions, so the instrument check
   was unavailable. Without it, a harness bug would have read as "all models fail
   hard problems" — the most expensive possible place for a silent bug.
4. A `file://` page cannot write to SQLite and the requirement was to edit and
   delete rows. It introspects the schema so it keeps working when the schema
   changes, rather than needing an edit each time.
5. Because it produced a headline number (392 of 412 reasoning tokens), and the
   script that produced a claimed number should survive so the claim can be
   reproduced.
6. Running `scripts/results.py` twice and diffing — the output must be byte-for-byte
   identical despite 10,000 bootstrap resamples, stratified sampling and
   cross-validation.
7. Every test exists because of a specific named failure, most of them actually
   observed — including one (mean-of-ratios) written after making that exact
   mistake.

</details>

---

**🎉 Part 3 complete.** You have now read every module in the project and know
what bug each rule prevents.

➡️ Next: [Lesson 32 — What an examiner is actually looking for](32-what-examiners-want.md)
