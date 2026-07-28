# Lesson 25 — `verify.py`, the most important file

*Part 3 · about 1.5 hours · `carr/execute/verify.py` (280 lines)*

**Every number in your thesis is downstream of this file.** Read it twice.

---

## In one sentence

> It turns extracted code into `passed = 0 or 1`, in a guarded subprocess, by
> delegating to the benchmark's own checker — because pass/fail is not `==` and a
> mislabel corrupts everything.

---

## Why delegation is a *correctness* decision

The docstring opens with it:

> We delegate to evalplus's own checker rather than re-implementing it. **That is
> a correctness decision before it is a convenience one: pass/fail is not plain
> `==`.**
>
> Float results are compared with a per-problem `atol`, some MBPP tasks are
> graded by set-equality, and others only assert the output is not None.
> Hand-rolled grading would silently mislabel those, and a wrong label corrupts
> every number downstream — the Pareto frontier, CPC, and CARR's routing target
> all read from `results.passed`.

That last clause is the argument. It is not "evalplus is convenient". It is:
**a grading bug does not announce itself; it just makes every conclusion
slightly wrong in an unknowable direction.**

Three concrete cases a hand-rolled `==` gets wrong:

| Case | What naive `==` does |
|---|---|
| `0.3` vs `0.30000000000000004` | Marks a correct answer wrong |
| MBPP tasks with several valid outputs | Marks a correct answer wrong |
| MBPP tasks whose oracle is "output is not None" | Marks the wrong things right |

---

## The sandbox, and what it is not

Isolation comes from evalplus too: **each check runs in a subprocess** under an
adaptive timeout and `reliability_guard()`, which disables `os.system`,
`os.remove`, `os.fork`, `subprocess` and ~40 other calls.

And then the honesty, in the docstring:

> evalplus's own docstring for `reliability_guard` says it **"is NOT a security
> sandbox"**. It contains accidents and casual hostility, which is the threat
> model for benchmark solutions, not a determined adversary.

**Stating your threat model precisely is worth marks.** "It is safe" is a claim
an examiner can attack. "It contains accidents and casual hostility, which is the
threat model here, and it is not proof against a determined adversary" is a claim
that is simply true.

---

## ⚠️ The macOS bug — the most important comment in the repository

```python
os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")
```

One line, sixteen lines of comment above it. Here is the failure chain:

1. evalplus caps subprocess memory with `resource.setrlimit(RLIMIT_AS/RLIMIT_DATA)`.
2. **macOS refuses to lower either, at any value** — `getrlimit` reports an
   infinite hard limit, and every `setrlimit` call raises *"current limit exceeds
   maximum limit"*.
3. That exception fires as the **first statement** of `reliability_guard`, so the
   subprocess dies **before running a single test** *and* before the guard
   disables `os.system` and friends.
4. **evalplus reports the dead subprocess as a timeout.**

So the failure mode is **silent and total**: every solution "fails", including
evalplus's own canonical ones.

Note step 3's second half — the guard never finished, so the protections were
*also* not applied. The bug was simultaneously breaking your measurements and
your sandbox.

**How it was caught:** `tests/test_verify.py::test_canonical_solutions_pass`.
Run the benchmark's own known-correct solutions through your grader; if they
fail, the instrument is broken.

**What it would have cost:** the entire budget, spent producing a dataset in
which every model fails everything, with no money left to diagnose it.

**The trade-off, stated:** `-1` skips the `setrlimit` block, so there is **no
memory cap**. Runaway allocation is bounded only by the per-test timeout.
Accepted knowingly — *"a broken grader is far more dangerous than an unbounded
one."*

Note also **`os.environ.setdefault(...)` sits above the imports**, with a comment
saying `MUST be set before evalplus.eval is imported`. That is unusual Python
style, done on purpose, and flagged so nobody "tidies" it into the wrong place.

---

## What `grade()` returns

```python
@dataclass
class GradeResult:
    passed: bool           # survived BOTH base and plus tests
    base_passed: bool      # original benchmark tests only
    n_tests_passed: int    # diagnostic; pass@1 is binary, this is not the metric
    n_tests_total: int
    error_type: str | None  # None | "assertion" | "timeout" | "exception"
```

Three things to notice:

**`passed` requires base AND plus.** `base` is the benchmark's original tests;
`plus` is EvalPlus's much larger extended set. Requiring both is the strict
reading, and the right one — the whole point of the `+` benchmarks is that the
originals were too weak.

**`base_passed` is kept separately** because it is the signal the saturation
check needs: a solution passing base but failing plus is exactly the "looks
right, is not" case the extended tests exist to catch.

**`n_tests_passed` is explicitly labelled diagnostic.** The metric is binary.
Recording partial credit without letting it leak into the metric is a small
discipline worth noticing.

And the columns of the `results` table **mirror this dataclass exactly** — no
translation layer that could silently drop or rename a field.

### Honest error typing

```python
error_type = "timeout" if any("timeout" in str(s).lower() for s in statuses) else "assertion"
```

With the comment: *we cannot always tell those apart from the status alone, so
"assertion" is the honest default for a non-timeout failure.*

The database `CHECK` constraint narrows the domain to exactly `assertion` and
`timeout` — the only two values `grade()` can emit. From the decisions log: *"a
documented-but-impossible value is a trap."* The schema matches the code
exactly, rather than an aspiration.

---

## Do this

**1. Read the macOS comment.**

```bash
cd ~/thesis
sed -n '36,56p' carr/execute/verify.py
```

**2. Run the tests that guard the instrument.**

```bash
uv run pytest tests/test_verify.py -v
```

Eight tests. Note the names: canonical solutions, infinite loop, hostile
`os.system`.

**3. Grade something yourself.**

```bash
uv run python -c "
from carr.execute.verify import grade
good = 'def has_close_elements(numbers, threshold):\n    for i,a in enumerate(numbers):\n        for b in numbers[i+1:]:\n            if abs(a-b) < threshold: return True\n    return False'
print(grade('humaneval', 'HumanEval/0', good))
print(grade('humaneval', 'HumanEval/0', 'def has_close_elements(n, t):\n    return False'))
"
```

First should pass; second should fail. **You just ran the instrument that
produced every number in your thesis.**

**4. Check that base and plus disagree somewhere.**

```sql
SELECT COUNT(*) FROM results WHERE base_passed = 1 AND passed = 0;
```

Every one of those is a solution the *original* benchmark would have marked
correct and EvalPlus's extended tests caught. **That count is the value of the
`+` benchmarks, measured in your own data.**

---

## Check yourself

1. Why is delegating to evalplus a correctness decision rather than a
   convenience one? Give two concrete cases.
2. What exactly did the macOS `setrlimit` bug do, and what were its *two*
   effects?
3. How was it caught, and what would it have cost undiagnosed?
4. What trade-off did the fix accept?
5. Why does `passed` require both base and plus tests?
6. Why is `error_type` restricted to `assertion` and `timeout`?
7. Why is it important that the file states evalplus "is NOT a security
   sandbox"?

<details>
<summary>Answers</summary>

1. Because pass/fail is not `==`: floats need a per-problem tolerance, and some
   MBPP tasks are graded by set-equality or by "output is not None". Hand-rolled
   grading mislabels those silently, corrupting every downstream number.
2. `setrlimit` cannot lower memory limits on macOS, so it raised as the first
   statement of `reliability_guard`. The subprocess died before running any test
   **and** before the guard disabled dangerous functions — so it broke both the
   measurement and the sandbox. evalplus reported it as a timeout, making every
   solution silently fail.
3. By `test_canonical_solutions_pass`, which runs the benchmark's own known-good
   solutions through the grader. Undiagnosed it would have consumed the whole
   budget producing a dataset where every model fails everything.
4. No memory cap: runaway allocation is bounded only by the per-test timeout.
   Accepted because a broken grader is more dangerous than an unbounded one.
5. Because the original benchmark's tests are weak enough that buggy solutions
   pass them; the extended set is the reason the `+` versions exist.
6. Because those are the only two values `grade()` can produce, and a
   documented-but-impossible value is a trap. The `CHECK` constraint keeps the
   schema honest to the code.
7. Because a precise threat model is defensible and an overclaim is not. It
   protects against accidents and casual hostility, which is what benchmark
   solutions contain — not against a determined adversary.

</details>

---

➡️ Next: [Lesson 26 — LiveCodeBench: the hard tier and its two shapes](26-benchmarks-code.md)
