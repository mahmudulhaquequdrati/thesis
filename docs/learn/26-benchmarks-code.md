# Lesson 26 — LiveCodeBench: the hard tier and its two shapes

*Part 3 · about 1 hour · `carr/benchmarks/livecodebench.py`, `carr/execute/_lcb_runner.py`*

---

## In one sentence

> The benchmark that makes the thesis answerable shares **nothing** with
> evalplus — two execution styles, no canonical solutions, and no contamination
> control — so it needed its own loader, its own grading path and its own
> subprocess runner.

---

## `livecodebench.py` — the loader (187 lines)

### Why it exists, in the file's own words

> HumanEval+ and MBPP+ saturate. The first real grid cell had all 10
> configurations solve `HumanEval/0`, including every no-reasoning one. If every
> problem is solved by the cheapest configuration, "which configuration should I
> use" has the answer "the cheapest" and **there is nothing to decide**.

Releases **v5 + v6 together** give **342 problems — 154 hard, 104 medium, 84
easy** — so the usable tier is **258** rather than the 132 that v6 alone
provided. Loading v5 doubled the hard tier for **$0**, because problems are free
to download; only *running* them costs money.

That is a good instinct to generalise: **when data is free and compute is not,
take all the data.**

### The contamination warning, in the source

The loader carries a block headed `READ THIS BEFORE CITING LCB AS
CONTAMINATION-FREE — it is not, for us`:

> LCB's whole design is release-date filtering: evaluate only on problems
> published after a model's training cutoff. **That works when the benchmark
> keeps updating. It stopped.** Newest release v6, last modified 2025-06-05,
> newest problem 2025-04-06. Every model on our roster is a 2026 release.

`contest_date` is stored per problem so the exposure can be **quantified and
reported** rather than assumed away.

Putting that warning **in the code**, at the point where someone would misuse
it, is better than putting it only in a document. Documents get skimmed; the
loader gets read by whoever next touches LCB.

### Two problem styles

| Style | Count | What the model must write |
|---|---|---|
| **stdin → stdout** (AtCoder) | 217 of 342 | A complete program: read from standard input, print the answer |
| **functional** (LeetCode) | 125 of 342 | A method on a `Solution` class, using supplied `starter_code` |

They need genuinely different execution, which is why `verify.py` branches
rather than abstracting.

`build_prompt()` is where the one documented prompt deviation lives: stdin
problems get an added sentence explaining that input arrives on standard input,
because the statement alone does not say so and the task would not be
well-posed. **A constant string, identical across every configuration** — so it
cannot confound the effort axis, but it is a deviation from "send the prompt
unmodified" and is recorded as one.

### No canonical solutions

evalplus ships reference implementations — which is what
`test_canonical_solutions_pass` uses to prove the harness works. **LCB ships
none.** The tests it ships are inputs and expected outputs, nothing more.

So the check that saved the project on evalplus was unavailable here. The
replacement: **hand-written reference solutions** for both styles in
`tests/test_verify_lcb.py`, scoring 43/43 and 34/34.

Without them, an LCB harness bug would have read as *"all models fail hard
problems"* — and hard problems are exactly where your thesis lives. That is the
most expensive possible place for a silent bug, and it is why writing those
references was worth the effort.

---

## The second grading path in `verify.py`

```python
if dataset == "livecodebench":
    return _grade_lcb(task_id, code)
```

A **branch**, not an abstraction over both. From the decisions log:

> Nothing is shared with the evalplus path — no canonical solutions, no `atol`,
> no special oracles, and two execution styles — so it is a branch in `grade()`
> rather than an abstraction over both.

Resisting a premature abstraction over two things that share nothing is a real
engineering judgement, and it matches `CLAUDE.md`'s "no speculative abstraction
layers".

### Comparison is normalised string equality

```python
def _normalise_stdout(text):
    return "\n".join(line.rstrip() for line in text.strip().split("\n")).strip()
```

Trailing whitespace per line and trailing blank lines are not answers — the same
rule the judges these problems came from apply.

For functional problems it compares **parsed JSON**, so `[1,2]` and `[1, 2]`
agree, falling back to string comparison if the answer is not JSON.

⚠️ And a limitation stated in the source: *there is no float tolerance, because
these problems are integer/string answers — if a future release adds
floating-point answers this will need an `atol` equivalent and will silently
mark correct solutions wrong until it gets one.*

**That is a comment describing a bug that does not exist yet.** Writing those is
one of the highest-value habits in research code.

### One subprocess per problem, not per test

```python
def _run_lcb(problem, code, tests):
    """One subprocess for the whole test set."""
```

> 175 problems × ~43 tests × 10 configurations would otherwise be **75,000
> interpreter startups**. The cost of batching is that a single non-terminating
> test times out the whole problem — which is the same behaviour evalplus's
> per-task timeout already has.

A clean trade: a large constant-factor win, at a cost that matches the existing
behaviour of the other path.

Timeout scales with test count: `15s + 0.4s per test`, capped at 90s.

And a small detail with a real failure behind it:

```python
stdin=subprocess.DEVNULL,
```

> *A solution that reads stdin outside the harness must not inherit ours and
> block forever.*

---

## `_lcb_runner.py` — the subprocess entry point (133 lines)

> **Never import this.** `verify.py` owns it and invokes it with `python -m`; it
> exists as a separate file only because untrusted code has to run in its own
> process.

### The order of operations is load-bearing

The docstring spells it out, and each step exists because of the step after it:

1. **Read the payload** — because `reliability_guard` sets `builtins.open` to
   `None`, so every file read must happen *first*.
2. **Capture the real stdout** — the stdin-style loop reassigns `sys.stdout` and
   needs a way back.
3. **`reliability_guard(None)`** — `None` skips the `setrlimit` block macOS
   refuses (the same fix as `verify.py`).
4. **Only then execute anything the model wrote.**

Get the order wrong and you get a confusing failure, not an obvious one. That is
why it is written down at the top of the file.

### The sentinel

```python
SENTINEL = "__CARR_LCB_RESULT__"
```

A stdin-style solution **prints to stdout as its normal output**. The runner also
needs to report results on stdout. So results are written after a unique marker,
and `verify.py` searches for the **last** occurrence:

```python
marker = proc.stdout.rfind(_SENTINEL)
```

`rfind`, not `find` — because the model's own output could contain anything,
including something resembling the sentinel. Taking the last occurrence means
the harness's own output wins.

### The prelude

```python
PRELUDE = """
import math, re, sys, string, bisect, heapq, itertools, functools, collections
from typing import List, Dict, Tuple, Optional, Set, Any, Union
...
"""
```

> LeetCode starter code says `def f(self, grid: List[List[int]])` without
> importing `List`, so the names have to be in scope before the model's code is
> compiled. **This mirrors what LiveCodeBench's own harness provides.**

Without it, valid solutions would fail with `NameError: List` — and you would
have measured your harness rather than the models. The last clause matters: the
prelude matches the official harness, so it is not an advantage you invented.

---

## Do this

**1. Read the contamination warning where it lives.**

```bash
cd ~/thesis
sed -n '1,40p' carr/benchmarks/livecodebench.py
```

**2. Run the LCB tests.**

```bash
uv run pytest tests/test_verify_lcb.py -v
```

Eleven tests. These are the hand-written references standing in for the
canonical solutions LCB does not ship.

**3. Look at both problem styles.**

```sql
SELECT benchmark, difficulty, COUNT(*) FROM problems
WHERE benchmark = 'livecodebench' GROUP BY difficulty;
```

Then open one LCB problem in Studio and read its `prompt`. Compare with a
HumanEval one. **The difference in length and shape is why two grading paths
exist.**

**4. Check the release dates.**

```sql
SELECT MIN(release_date), MAX(release_date) FROM problems
WHERE benchmark = 'livecodebench';
```

The maximum should be around 2025-04-06. **Every model on your roster is
newer.** That query is your contamination limitation, quantified.

---

## Check yourself

1. Why is LiveCodeBench load-bearing rather than optional?
2. Why was loading v5 alongside v6 free, and what did it buy?
3. Why can LCB not give you contamination control, and what do you do instead?
4. What are the two problem styles, and why do they need different execution?
5. LCB ships no canonical solutions. What replaced that check, and why did it
   matter specifically for your thesis?
6. Why one subprocess per problem rather than per test, and what does it cost?
7. What is the sentinel for, and why `rfind` rather than `find`?

<details>
<summary>Answers</summary>

1. Because HumanEval+ and MBPP+ saturate — every configuration solves them — so
   without a hard tier there is nothing to decide and the thesis has no signal.
2. Problems are free to download; only running them costs money. It doubled the
   usable medium+hard tier from 132 to 258 problems.
3. Its release-date filtering only works while the benchmark keeps updating, and
   it stopped in June 2025 while every roster model is a 2026 release. Instead,
   `contest_date` is stored per problem so the exposure is quantified and
   reported as a limitation.
4. stdin→stdout whole programs (AtCoder, 217 of 342) and methods on a `Solution`
   class (LeetCode, 125 of 342). One is run as a program with piped input; the
   other is called and its return value compared.
5. Hand-written reference solutions for both styles in `tests/test_verify_lcb.py`.
   It mattered because an LCB grading bug would have looked like "models fail
   hard problems", and hard problems are where the thesis's findings live.
6. Because per-test would mean ~75,000 interpreter startups. The cost is that one
   non-terminating test times out the whole problem — the same behaviour
   evalplus's per-task timeout already has.
7. Stdin-style solutions print to stdout as their normal output, so results need
   a unique marker to be separable. `rfind` takes the last occurrence, so the
   harness's own output wins even if the model's output contains the marker.

</details>

---

➡️ Next: [Lesson 27 — `db.py`: the schema and never paying twice](27-database-code.md)
