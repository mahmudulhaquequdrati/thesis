# Lesson 05 — What a benchmark is

*Part 1 · about 45 minutes · after lesson 04*

---

## In one sentence

> A benchmark is a fixed set of problems with hidden tests, so that "did the
> model succeed?" is a fact rather than an opinion.

---

## The idea, from zero

### The problem benchmarks solve

You want to say "model A is better at coding than model B". How?

You could read their answers and judge. But you would be slow, inconsistent, and
biased by whichever answer looks tidier. And nobody could reproduce your
judgement.

The alternative is to make success **mechanically checkable**:

> Give the model a task. Run its answer against tests it never saw. It passed or
> it did not.

That is a benchmark. Three parts, always:

| Part | What it is |
|---|---|
| **The problem** | A description of what to write. This is the prompt. |
| **The tests** | Hidden code that checks the answer. Never shown to the model. |
| **The protocol** | The rules — how many attempts, what counts as passing |

### What one problem actually looks like

A HumanEval problem is a Python function signature and a docstring:

```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to
    each other than given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    """
```

The model must write the body. Hidden away, the benchmark holds tests:

```python
assert has_close_elements([1.0, 2.0, 3.9, 4.0], 0.3) == True
assert has_close_elements([1.0, 2.0, 5.9, 4.0], 0.95) == False
...
```

Run them all. All pass → ✅. Any fail → ❌.

### pass@1 — your accuracy metric

**pass@1** means: *the model gets one attempt; did that attempt pass every
test?*

There are variants (pass@10 = ten attempts, does any pass). You use pass@1, for
the reason in lesson 02: one sample at `temperature = 0` is cheaper, and it
makes "the cheapest configuration that solves this problem" a **fixed fact**
rather than a lottery result.

pass@1 is strict. Almost right scores zero. That is the point — it is the same
strictness for every configuration, so comparisons are fair even if the absolute
numbers look harsh.

### Your three benchmarks, and why each is there

| Benchmark | Problems | Style | Role in your thesis |
|---|---|---|---|
| **HumanEval+** | 164 | Write a function body from a docstring | The easy anchor. Short outputs, cheapest tier |
| **MBPP+** | 378 | "Write a function to do X", one-line spec | Easy-to-medium anchor |
| **LiveCodeBench** | 342 | Competitive programming (AtCoder, LeetCode) | **The hard tier — the one that makes the question answerable** |

**Total pool: 884 problems.** You *ran* 320 of them — a budget decision, because
every problem costs 10 API calls.

The `+` in HumanEval+ and MBPP+ matters. The originals had **weak tests** —
buggy solutions passed. **EvalPlus** added far more tests (roughly 80× for
HumanEval). Using the `+` versions means a passing answer really works, rather
than merely surviving three examples.

Note also: MBPP+ has **378** problems, not the 500 people quote — and the usual
explanation for that is wrong, so check it before repeating it. The 378 span
task ids **2 to 809**; only **224** sit inside the canonical 11–510 test split
and **154** sit outside. So MBPP+ is not "the 500 minus broken ones" — it is a
filtered, test-augmented set drawn from a wider range than the split people
quote. (Verify with:
`SELECT COUNT(*) FROM problems WHERE benchmark='mbpp_plus' AND CAST(REPLACE(problem_id,'Mbpp/','') AS INTEGER) > 510;`
→ 147.) EvalPlus dropped
broken ones. Your proposal said 500; that is one of the 14 `.docx` edits owed.

### Why LiveCodeBench had to exist in your design

Here is the single most important fact about benchmarks in your thesis, and it
is a finding rather than a background detail:

> **HumanEval+ and MBPP+ are too easy to answer your question.**

Your pilot measured it:

| tier | reasoning off | reasoning high | verdict |
|---|---|---|---|
| HumanEval+ | 90% | 100% | **saturated — no signal** |
| MBPP+ | 93% | 100% | **saturated — no signal** |
| LCB easy | 100% | 100% | **saturated — no signal** |
| LCB medium | 60% | 50% | discriminates |
| LCB hard | 50% | 31% | discriminates |

**Saturation** means: the benchmark is so easy for modern models that everything
passes, so it can no longer tell configurations apart.

Think of it as an exam where every student scores 98%. The exam is not measuring
anything about the students any more. It is measuring the exam.

That is why LiveCodeBench is load-bearing rather than decorative. Its hard tier
is where the differences live. You later loaded LCB **v5 alongside v6**,
doubling the usable tier from 132 to 258 problems (154 hard, 104 medium) — for
free, since problems are free; only *running* them costs money.

### ⚠️ Contamination — and the claim you had to withdraw

**Contamination** is when a benchmark problem was in a model's training data. The
model "remembers" the answer rather than solving the problem, so its score is
inflated and means nothing.

The standard defence is *recency*: use problems published **after** the model
was trained. LiveCodeBench was designed for this, with a rolling window of new
contest problems and release dates you can filter on.

**It does not work for you**, and you checked:

| | |
|---|---|
| Newest LiveCodeBench problem | **2025-04-06** |
| LCB last shipped a release | **2025-06-05** — it stopped |
| Every model on your roster | a **2026** release |

Every LCB problem predates every model by at least nine months. There is no
post-cutoff window left.

You had three options:

1. Pretend the claim still holds → **dishonest**.
2. Build a new benchmark by scraping 2026 contests → **months of work**, not a
   thesis step.
3. **Report it.** Use LCB as a *difficulty* tier, store every problem's
   `release_date` so the exposure can be quantified, and name the limitation
   explicitly.

You chose 3. It is one of the 14 `.docx` edits, because your proposal cited LCB
*for* contamination resistance.

The instinct to notice here: **when a property you assumed turns out not to
hold, the move is to measure and report the exposure — not to quietly keep the
sentence.**

---

## Why it is in *your* thesis

**As a finding, not just as a method.** Section 3.2 of
[research-framing.md](../research-framing.md):

> Of 320 problems: **81 are solved by every configuration, 98 by none, and only
> 141 discriminate.**

A problem everything solves and a problem nothing solves are *equally
uninformative* — neither can distinguish a good decision from a bad one. **Fewer
than half your problems carry any signal at all.**

That is a statement about benchmarks, and it generalises:

> Anyone studying model-selection on HumanEval+ or MBPP+ should say which subset
> of problems carries their signal — because most of it does not.

Lesson 13 is entirely about this. It is one of your genuinely useful results,
and it started as a *risk* in THESIS.md §11 that you noticed on **the very first
API call of the project** (`HumanEval/0`, 10 configurations, 10 passes).

Noticing the risk early is why the grid was re-weighted toward the hard tier
instead of discovering the problem in week 10. That story belongs in your Method
chapter.

---

## Do this

**1. Look at real problems, in all three styles.**

```bash
cd ~/thesis
uv run python scripts/day2_inspect_problems.py | head -60
```

Notice how short the HumanEval+ prompt is (~99 tokens median) and how much
longer a LiveCodeBench problem statement is.

**2. Count your pool, by benchmark and difficulty.**

```bash
uv run python scripts/studio.py
```

Then in the SQL console (see lesson 07 if SQL is new — you can paste this
blindly for now):

```sql
SELECT benchmark, difficulty, COUNT(*)
FROM problems GROUP BY benchmark, difficulty ORDER BY benchmark, difficulty;
```

You should see 884 problems total, with LiveCodeBench's `hard` and `medium`
carrying the weight.

**3. See saturation with your own eyes.**

```bash
uv run python scripts/results.py | head -30
```

Look for the `RQ0 saturation` section and the marker `<- saturated, no signal`.
That marker is printed by your own analysis code, on your own data.

---

## Check yourself

1. What are the three parts of a benchmark?
2. What does pass@1 mean, and why did you use it rather than pass@10?
3. What does the `+` in HumanEval+ add, and why does it matter?
4. What is saturation, and why does it make a benchmark useless for *your*
   question specifically?
5. Why can't LiveCodeBench give you contamination control?
6. Of your 320 measured problems, how many actually discriminate between
   configurations — and why do the other two groups tell you nothing?

<details>
<summary>Answers</summary>

1. The problem statement (the prompt), hidden tests, and a protocol for what
   counts as success.
2. One attempt, must pass every test. Chosen because it is cheaper and because
   with `temperature = 0` it makes the "cheapest passing configuration" label
   deterministic instead of noisy.
3. Many more tests — the originals were weak enough that buggy solutions passed.
   It means a ✅ is real rather than lucky.
4. When a benchmark is easy enough that all configurations pass, it cannot
   distinguish them. Your question *is* a distinguishing question — "which
   configuration should I pick?" — so a saturated benchmark can contribute
   nothing to it.
5. Its newest problem is 2025-04-06 and it stopped updating in June 2025, while
   every roster model is a 2026 release. There is no post-cutoff window, so
   every problem is potentially in training data. It enters as a difficulty tier
   and the exposure is reported as a limitation.
6. 141. The 81 solved by everything and the 98 solved by nothing both give the
   same answer for every configuration, so neither can favour one choice over
   another.

</details>

---

➡️ Next: [Lesson 06 — What it means to *grade* generated code](06-grading-code.md)
