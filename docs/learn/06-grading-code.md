# Lesson 06 — What it means to *grade* generated code

*Part 1 · about 1 hour · after lesson 05*

---

## In one sentence

> To grade an answer you must **run** it — which means running code written by a
> machine, on your machine, and deciding "correct" in a way that is not simply
> `==`.

---

## The idea, from zero

### Grading is execution, and execution is dangerous

Marking an essay means reading it. Marking a program means **running it**.

And the program was written by a model that was given no instructions about
being safe, from a problem statement it may have misread. It can:

- loop forever (`while True:`)
- allocate memory until your Mac swaps to death
- write files, delete files
- call `os.system("rm -rf ~")` — not maliciously, but because it hallucinated a
  "clean up temporary files" step

Now multiply by 1,280 graded generations. Something *will* misbehave.

So a grader needs three properties:

| Property | Meaning |
|---|---|
| **Isolation** | Runs in a separate process, so a crash kills that process only |
| **Timeouts** | An infinite loop is stopped and recorded as a failure |
| **Restriction** | Dangerous functions are disabled before the code runs |

### The choice you made, and the one you reversed

Your first plan was **Docker** — a container, total isolation. On Day 3 you
reversed it, and the reason is worth understanding because it is a good example
of engineering judgement in a thesis:

> **EvalPlus already ships a grader** (`untrusted_check`) with subprocess
> isolation, timeouts, and a `reliability_guard` that disables `os.system`,
> `os.fork` and ~40 other functions.
>
> **And — the deciding reason — it gets the *grading* right**, which Docker does
> not help with at all.

That second point needs unpacking, because "grading" sounds trivial and is not.

### Why "correct" is not `==`

**Floating point.** A problem asks for an average. The reference answer is
`0.30000000000000004`; the model returns `0.3`. In Python, `0.3 ==
0.30000000000000004` is `False`. Marking that wrong would be wrong. EvalPlus
compares floats with a **tolerance** (`atol`).

**Multiple valid answers.** Some MBPP problems have more than one correct
output — any valid ordering, any of several factorisations. EvalPlus ships
**special oracles** for these: bespoke checking functions instead of equality.

**Types that compare oddly.** `True == 1` is `True` in Python. Sets versus
lists. `NaN != NaN`.

Get any of these wrong and you mislabel some problems — **silently**, and in a
way that corrupts every downstream number. A wrongly-failed problem changes its
pass rate, its cost-per-correct, its "cheapest passing configuration" label, and
the frontier.

Which is why your `CLAUDE.md` contains this rule:

> **Never grade generated code outside `carr/execute/verify.py`.**

One file. One place a grading bug can live. One place to fix it.

### The canonical-solution check — the trick that saves you

Here is the best idea in your entire test suite, and it is simple:

> **Take the benchmark's own known-correct solution. Run it through your grader.
> If it does not pass, your grader is broken.**

This is not testing the model. It is testing **the measuring instrument**. And
it caught a catastrophe.

### The macOS bug that would have destroyed the project

EvalPlus limits memory using `setrlimit(RLIMIT_AS)`. On macOS, Darwin **refuses
to lower that limit at any value**. The exception fires as the *first statement*
of `reliability_guard` — before any test runs, and before dangerous functions
are disabled.

EvalPlus reports the dead subprocess as a **timeout**.

So on your Mac, *every solution silently failed*, including EvalPlus's own
canonical ones.

Now imagine not having the canonical check. You run the grid. You spend the
budget. Every model fails almost everything. You conclude that 2026 reasoning
models cannot solve HumanEval — a result so wrong it is comic — and you have no
money left to find out why.

The fix is one environment variable, `EVALPLUS_MAX_MEMORY_BYTES=-1`, with a
comment above it explaining exactly this. Which is why `CLAUDE.md` says:

> **Never remove `EVALPLUS_MAX_MEMORY_BYTES=-1` from `verify.py` without reading
> the comment above it.**

The trade-off, stated honestly: no memory cap. Runaway allocation is now bounded
only by the timeout. That is a real cost, accepted knowingly.

### LiveCodeBench needs a completely different grader

EvalPlus problems are all "fill in this function". LiveCodeBench problems are
competitive programming, and come in two shapes:

| Style | Count | How it works |
|---|---|---|
| **stdin → stdout** (AtCoder) | 217 of 342 | A whole program: read input from standard input, print the answer |
| **`Solution` class method** (LeetCode) | 125 of 342 | Implement a method on a class, using supplied starter code |

And — this is the hard part — **LiveCodeBench ships no canonical solutions at
all.** So the trick that saved you on EvalPlus is unavailable.

Your answer: **hand-write reference solutions yourself**, covering both styles,
in `tests/test_verify_lcb.py`. They score 43/43 and 34/34.

Without them, an LCB harness bug would have read as *"all models fail hard
problems"* — which, given that hard problems are exactly where your thesis lives,
would have been the most expensive possible place for a silent bug.

### One more subtlety: extraction

Before grading, you must get code *out* of the response. A model does not return
bare Python; it returns prose with code fences:

````
Here's my solution:

```python
def has_close_elements(numbers, threshold):
    ...
```

This works by comparing each pair.
````

[`carr/extract.py`](../../carr/extract.py) pulls the runnable part out. Its
design rule:

> **It never raises.** A response it cannot parse is not a crash — it is a data
> point (a failure), recorded with `extracted_code` empty.

And the safety net behind it: **`raw_response` is stored verbatim, always.**
Extraction logic has bugs. Storing the raw response means you can fix the bug
and **re-grade offline for free**, instead of re-buying 1,373 generations.

That single decision is worth more than it looks. Re-grading is free forever;
re-buying is not.

---

## Why it is in *your* thesis

**Chapter 3 (Method)** must convince the reader that your pass/fail labels are
trustworthy — because *every number in the thesis is built on them*. Pass rates,
cost-per-correct, the frontier, the oracle, the router labels: all of it is
downstream of `passed = 0 or 1`.

The argument you can make is strong, and it is concrete:

1. Grading is in exactly one file, wrapping the standard tool rather than
   hand-rolled.
2. The instrument is checked against known-correct solutions — **3 in the
   standing suite, and a retired one-off sweep of 210 canonical
   solutions across both EvalPlus benchmarks, all passing.**
3. That check **caught a real, silent, project-ending bug** (the macOS one).
4. For the benchmark with no canonical solutions, references were hand-written
   to restore the check.
5. **132 tests** cover this and the rest of the harness.

Point 3 is the one to lead with. Anyone can claim their harness is careful.
"Here is the bug my checks caught, and here is what it would have cost me" is
evidence.

---

## Do this

**1. Run the tests that guard the grader.**

```bash
cd ~/thesis
uv run pytest tests/test_verify.py tests/test_verify_lcb.py -v
```

Read the test *names* as you watch them pass. They are a list of the things that
can go wrong: canonical solutions, infinite loops, hostile `os.system` calls,
both LCB execution styles.

**2. Read the comment that saved the project.**

```bash
grep -n -B6 -A6 "EVALPLUS_MAX_MEMORY_BYTES" carr/execute/verify.py
```

**3. Watch a grade happen end to end.**

```bash
uv run python scripts/grade.py --help
```

Then grade something already in the database. Nothing here costs money —
grading is free, because the generations are already bought.

---

## Check yourself

1. Why is grading generated code more dangerous than marking an essay?
2. Give two reasons "correct" cannot just be `==`.
3. What is the canonical-solution check, and what is it testing?
4. Describe the macOS bug in one sentence, and say what it would have cost.
5. LiveCodeBench ships no canonical solutions. What did you do instead, and why
   did it matter *specifically* for your thesis?
6. Why is `raw_response` stored verbatim?

<details>
<summary>Answers</summary>

1. Because you must *execute* it. Machine-written code can loop forever, exhaust
   memory, or call destructive system functions — and you are running 1,280 of
   them.
2. Floating-point results need a tolerance (`0.3` vs `0.30000000000000004`);
   some problems have multiple valid answers and need bespoke oracles. Also
   Python quirks like `True == 1`.
3. Run the benchmark's own known-correct solutions through your grader. It tests
   **the grader**, not the model — a failure means the instrument is broken.
4. EvalPlus's memory limit cannot be lowered on macOS, so the guard threw before
   any test ran and every solution was reported as a timeout — meaning every
   model would have appeared to fail everything, after the entire budget had
   been spent.
5. Hand-wrote reference solutions for both execution styles. It mattered because
   an LCB grading bug would have looked like "models fail hard problems", and
   hard problems are precisely where the thesis's findings live.
6. Because extraction code has bugs. With the raw text stored, fixing one means
   re-grading for free; without it, it means re-buying every generation.

</details>

---

➡️ Next: [Lesson 07 — Databases and SQL from zero](07-databases-and-sql.md)
