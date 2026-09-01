# Everything, A to Z — the CARR thesis explained from zero

> **Who this is for.** Someone who does not know what a token is, what a
> benchmark is, what a confidence interval is, or what a thesis is supposed to
> look like — and who has to walk into a room in a few weeks and defend one.
>
> **What this is.** The whole thesis in one document, in order, assuming
> nothing. Every number here is real and reproducible with
> `uv run python scripts/results.py`, which costs nothing and touches no API.
>
> **How it relates to everything else.** [`docs/learn/`](../learn/00-index.md) is
> the same material as forty separate lessons with exercises. This is the single
> continuous read. [`01-question-bank.md`](01-question-bank.md) is the hostile
> examiner. [`02-cheatsheet.md`](02-cheatsheet.md) is the page you take into the
> room.

---

## Contents

- **[Part 0 — The whole thing in one page](#part-0)**
- **[Part A — The world you need to know first](#part-a)** — LLMs, tokens, money, benchmarks, grading, databases, statistics, economics
- **[Part B — Your thesis: question, machine, design](#part-b)**
- **[Part C — The eight findings](#part-c)**
- **[Part D — The code, module by module](#part-d)**
- **[Part E — What this is *not*](#part-e)**
- **[Part F — The story you tell](#part-f)**
- **[Part G — Turning it into the document](#part-g)**
- **[Part H — Glossary, A to Z](#part-h)**
- **[Part I — The numbers to know cold](#part-i)**

---

<a name="part-0"></a>

# Part 0 — The whole thing in one page

Modern AI models can **"think" before they answer**. The thinking is a long
internal monologue that you never see — but you are **billed for every word of
it**. On a trivial prompt ("write a function that reverses a string"), this
project measured **392 of 412 billed tokens were invisible thinking**. Pricing
that call from the visible answer would understate it about twentyfold.

So there is a practical question with no measured answer:

> **When is that thinking worth paying for?**

To answer it you need a table nobody had published: for each *coding problem*,
for each *model*, at each *thinking setting* — did it work, how many invisible
thinking tokens did it burn, and what did it cost in dollars?

This thesis built that table. **320 coding problems × 10 configurations
(5 open-weight models × thinking off/on) = 1,373 real API calls, 1,280 graded,
for $5.24.** Then it analysed it.

**What it found, in six lines:**

1. **Thinking works — but the effect belongs to the *model*, not the tier.** On
   hard problems it takes `deepseek-v4-flash` from **29.2% to 82.1%** and
   `qwen3.5-9b` from **22.1% down to 3.8%**. The aggregate "24.9% → 54.2%" is the
   average of those opposite effects. On easy problems a small model, paired
   against itself on the same 20 problems with **zero** truncation, falls from
   **80.0% to 55.6%** — overthinking, measured directly.
2. **The easy benchmarks are saturated** (72–100% whichever arm you read). The
   *problem-level* split — 81 all-solved, 98 none-solved, 141 discriminating —
   is largely a **coverage artefact**: at ≥6 configurations, **82% discriminate**.
3. **Long thinking means failure, not effort.** 49 calls averaged **29,584**
   thinking tokens and returned *nothing usable* — 15% of thinking-arm spend, and
   **76% of it one model** (`qwen3.5-9b`, 37 of its 99 thinking calls).
4. **Cost per correct answer spans 305×** ($0.00021 → $0.06320) across the
   roster — **65×** even on a strictly identical exam — and the *cheap* model
   with thinking beats the *expensive* model with thinking.
5. **Knowing something about a problem before you choose is worth 13.8
   accuracy points** — but the router built to exploit that captured **+0.0** of
   it, and the thesis diagnoses precisely why.
6. **The measurement platform itself lies in three ways** that would silently
   invalidate a careless study — and helps in one way that enables a new control.

And one thing more, which is the part examiners like most: **the project refuted
its own headline.** An early result claimed a free way to save 44% of the money.
Better data showed that result was an artefact of the project's own token limit.
It is reported, not buried.

---

<a name="part-a"></a>

# Part A — The world you need to know first

Nothing in this part is about your thesis yet. It is the vocabulary.

---

## A1. What a thesis actually is

A thesis is **not** a project report. A project report says *"here is what I
built."* A thesis says:

> **"Here is a claim about the world, here is the evidence I gathered for it,
> here is why the evidence supports it, and here is exactly how far it goes."**

Four things an examiner is checking, and none of them is "is this impressive":

| They check | What it means | Where yours lives |
|---|---|---|
| **Is there a question?** | Something answerable that was not already answered | "When is reasoning worth paying for?" |
| **Is the method sound?** | Could the method actually answer it, and could it be wrong? | The harness, the grader, the pinning, the caps |
| **Do the claims match the evidence?** | Nothing over-claimed. Denominators present. | Every headline carries its *n* and its interval |
| **Do you know the boundary?** | Where the work stops being true | The limitations chapter |

The single fastest way to fail a viva is to state something more strongly than
your data supports and be caught. The single fastest way to pass is to state a
limitation before the examiner does.

**Your thesis was originally proposed as a *method* thesis** (build a router).
The method failed. It is now a ***measurement* thesis** (measure the tradeoff,
and measure how much headroom any method would have). That is a legitimate and
common change — see [Part F](#part-f) for how to tell that story.

---

## A2. What a language model actually is, and what a token is

A large language model (LLM) is a program that does exactly one thing: **given
some text, predict the next chunk of text.** It does that over and over.

A **token** is that chunk. It is roughly ¾ of an English word. `"reverse"` might
be one token; `"reverseString"` might be three. Everything an LLM reads and
writes is counted in tokens, and — this is the part that matters — **you are
billed per token**.

Two counters exist on every API call:

- **prompt tokens** (also "input") — what you sent. Cheap.
- **completion tokens** (also "output") — what it generated. Expensive, usually
  2–10× the input price.

In this project, **input cost is essentially irrelevant**: measured prompt
medians are 99 tokens (HumanEval+) and 36 (MBPP+). Effectively 100% of the
budget is output.

---

## A3. Reasoning models, and the invisible bill

A **reasoning model** (also "thinking model") does something extra before
answering: it generates a long internal monologue — trying approaches, checking
itself, backtracking — and only then writes the answer you see.

Three facts about that monologue, and they are the foundation of your entire
thesis:

1. **You are billed for it.** It is part of `completion_tokens`.
2. **You usually cannot see it.** Providers often hide or summarise it. The
   answer you get back may be three lines while you paid for four thousand.
3. **It is broken out separately** in the usage object, as
   `completion_tokens_details.reasoning_tokens`.

> **Day 1 of this project:** the prompt *"write a Python function that reverses a
> string"* returned **412 completion tokens, of which 392 were reasoning.**
> The visible answer was three lines.

**The single arithmetic trap:** reasoning tokens are **a subset of**
completion tokens, not an addition to them. Adding the two would double-charge
every thinking configuration — that is, it would inflate exactly the
configurations the thesis is about. [`carr/cost.py`](../../carr/cost.py) exists
mostly to make that impossible.

**Effort / thinking mode.** Modern models expose a switch:
`reasoning: {enabled: false}` (no thinking at all) or
`reasoning: {effort: "high"}` (think hard). One (model, effort) pair is called a
**configuration**, or **config**. Your thesis compares **10** of them.

> ⚠️ **A finding, ahead of schedule.** Your project tested whether you can ask
> for *less* thinking — `reasoning: {max_tokens: 2000}`. The model produced
> **13,731** reasoning tokens: **6.9× the requested budget**, accepted without
> error. So the effort axis is **binary in practice** — off works, graded levels
> do not bind. See [C8](#c8).

---

## A4. How you buy tokens — and who you are actually buying from

You call an **API**: send JSON over HTTPS, get JSON back. This project uses
**OpenRouter**, an **aggregator** — one account, one API key, one request
format, hundreds of models.

The alternative would be six separate accounts, six billing relationships and
six client adapters, on a $15 budget. The aggregator is the right call — and it
turned into a whole chapter, because of the next three paragraphs.

**The thing beginners do not know: one model name is not one thing.**

An open-weight model is a file of numbers anyone can download and serve.
OpenRouter routes your request to whichever **provider** is serving that model.
For `deepseek-v4-pro` there are **18 of them**, charging **$0.87 to $3.48 per
million output tokens** — a 4× spread. `GET /models` shows you only the
cheapest one's price, but routing may send you to any of them.

**Quantization** is the second half of the problem. Serving a big model cheaply
means compressing its numbers — `bf16` (16 bits, full fidelity) down through
`fp8` to `fp4` (4 bits). A 4-bit version of a model is measurably *worse* than
the 16-bit version. The cheapest provider is usually the most quantized.

So an unpinned evaluation is **comparing different models at unpredictable
prices** and calling the result a benchmark.

**What your project did:** every model in
[`config/models.yaml`](../../config/models.yaml) pins **one provider tag**,
which pins provider *and* precision (`baidu/fp8`, `deepinfra/bf16`), sent as
`{"provider": {"only": [tag], "allow_fallbacks": false}}`. Policy: **fp8 or
better for every model**, so precision is held constant across the roster.

The price of that: if the pinned provider is down, the call fails instead of
silently succeeding elsewhere. That is the correct trade — a recorded failure is
resumable; a surprise 4× bill on a different model is not.

**Cost is measured, not estimated — but know exactly how far that goes.** The
database stores **both** the computed estimate (`cost_computed_usd` = tokens ×
the price table) and the billed truth from `GET /generation`
(`cost_actual_usd`), so price drift becomes visible instead of invisible.

> 🔴 **However: only 139 of 1,373 rows (10.1%) actually have the billed figure,
> and all 139 are the 2026-07-25 pilot.** The 1,224-call grid was never
> reconciled. Every headline dollar in this thesis is a *computed* figure.
>
> That is defensible — the grid pinned one provider per model with
> `allow_fallbacks: false`, so the endpoint's price is contractual rather than a
> routing lottery. But it is an assumption, not a verification, and on the 139
> rows where it *could* be checked, **billed cost ran 1.354× computed** (2.16–2.51×
> on `deepseek-v4-pro`). The best reading is that this is evidence *for* the
> pinning finding, because the pilot ran before pinning — but present it as an
> argument, not a fact.
>
> **It is fixable for $0**, and it is the highest-value action left:
> `runner.reconcile_costs()` exists and **1,207 of the 1,224 grid rows still
> carry an `openrouter_gen_id`**. If the records have expired after five weeks,
> report that instead — a stated limitation beats an unexamined assumption.

---

## A5. What a benchmark is

A **benchmark** is a pile of problems, each of which is exactly two things:

1. **a prompt** — the problem statement, and
2. **a set of tests** — assertions that a correct solution must pass.

That is all. There is no magic. Your project uses three:

| Benchmark | What it is | Pool size |
|---|---|---|
| **HumanEval+** | 164 hand-written Python function problems (the field's standard easy set), with EvalPlus's *extended* test suites | 164 |
| **MBPP+** | "Mostly Basic Python Problems", also with extended tests | 378 |
| **LiveCodeBench (LCB)** | Real competitive-programming problems from AtCoder / LeetCode contests, labelled easy/medium/hard | 342 |

**Pool = 884 problems. Run set = 320.** Those are different numbers and you must
never conflate them. The 320 is what the budget allowed, since every problem
costs 10 API calls.

⚠️ And the pool is **not** "everything available" — say it precisely. It is all
164 HumanEval+ problems, all 378 MBPP+ problems that EvalPlus ships, and
LiveCodeBench **releases v5 and v6 only** (342 problems). LCB ships
incrementally from v1, so several hundred earlier problems exist and were not
loaded. That was deliberate — older releases are *more* contamination-exposed,
since every roster model is a 2026 release and v6 already stops at 2025-04-06 —
but it is a choice, not an exhaustive sweep, and it should be stated as one.

**Why the "+" matters.** The original HumanEval ships very few tests per problem,
so wrong code passes surprisingly often. EvalPlus generates far more test inputs
and re-grades. Using the "+" variants means your pass/fail labels are much harder
to earn — which strengthens every claim you make.

**Why MBPP+ is 378 and not the famous 500** — and the usual answer is wrong, so
have the right one. It is *not* "the 500 minus the broken ones". The 378
problems span task ids **2 to 809**: only **224** fall inside the canonical
11–510 test split that "500" refers to, and **154** fall outside it. EvalPlus
filters *and* augments across a wider range than the split. So the proposal's
"500" is the wrong base as well as the wrong count. Check it yourself:
`SELECT COUNT(*) FROM problems WHERE benchmark='mbpp_plus' AND CAST(REPLACE(problem_id,'Mbpp/','') AS INTEGER) > 510;` → 147.

**Why LiveCodeBench:** because HumanEval+ and MBPP+ turned out to be **too
easy** — see [C1](#c1). LCB is where the signal is. It also brings two
complications your grader has to handle: **217 of its 342 problems are
stdin→stdout programs** (read input, print output — AtCoder style) and **125 are
methods on a `Solution` class** (LeetCode style). And **LCB ships no canonical
solutions at all**, which matters in [A6](#a6).

> ⚠️ **LCB is a difficulty tier, not a contamination control — say this before
> an examiner does.** LCB's newest problem is dated **2025-04-06**, the dataset
> stopped updating **2025-06-05**, and every model on your roster is a **2026**
> release. There is no post-cutoff window. Your proposal claims contamination
> resistance; that claim is now wrong and must be edited out.

---

<a name="a6"></a>

## A6. What it means to *grade* generated code

The model returns prose with code in it. Two steps turn that into a
pass or a fail.

**Step 1 — extraction.** [`carr/extract.py`](../../carr/extract.py) pulls the
program out of the response: prefer a ` ```python ` fence, then any fence, then
the whole response if it parses as Python. Among multiple fenced blocks it takes
**the longest**, because models often print a short usage example after the real
solution. It **returns `None` rather than raising** — an unparseable response is
a data point (a fail with no code), not a reason to crash a run that has already
spent money.

**Step 2 — execution.** [`carr/execute/verify.py`](../../carr/execute/verify.py)
runs the code against the tests. Three things make this harder than it sounds:

- **Never run generated code unguarded.** A model will eventually emit something
  destructive. Grading happens in a subprocess under EvalPlus's
  `reliability_guard`, which disables `os.system`, `os.fork`, `subprocess` and
  ~40 other calls, under a timeout. *(EvalPlus's own docstring says this is "NOT
  a security sandbox" — it stops accidents and casual hostility, which is the
  real threat model for benchmark solutions, not a determined attacker. Say that
  out loud rather than claiming a sandbox you do not have.)*
- **Pass/fail is not `==`.** Floating-point answers need a tolerance (`atol`);
  some MBPP tasks are graded by set-equality; others only assert the output is
  not `None`. A hand-rolled checker silently mislabels those — and a wrong label
  corrupts every number downstream, invisibly. This is why grading **delegates
  to EvalPlus's own checker** rather than reimplementing it.
- **LiveCodeBench needs an entirely separate path**, because nothing is shared:
  no canonical solutions, no `atol`, no special oracles, and two execution
  styles neither of which is "call a function and compare the return value".

**pass@1** is your accuracy metric: *did the model's single attempt pass every
test?* One attempt, no retries, temperature 0.

> ### 🔴 The bug that would have destroyed the thesis
> EvalPlus caps subprocess memory with `setrlimit(RLIMIT_AS)`. **macOS refuses
> to lower that limit at any value.** The exception fires as the *first
> statement* of `reliability_guard`, killing the subprocess before a single test
> runs — and EvalPlus reports the dead subprocess as a **timeout**.
>
> So *every* solution silently "failed", including EvalPlus's own known-correct
> canonical ones. Undiagnosed, the entire budget would have bought a table of
> garbage that looked plausible.
>
> It was caught by a test that grades the benchmarks' **canonical solutions** and
> asserts they pass. ⚠️ **Be precise about the size of that check.** The
> standing test, `test_canonical_solutions_pass`, is parametrized over **three**
> HumanEval tasks — run `pytest` and you see 3. A **210-solution sweep across
> both benchmarks** ran once, all passing, and its fixture was then retired.
> Quote both: *"three in the suite today, 210 in a one-off sweep."* Claiming 210
> as a standing check is checkable in one command, and false. Since LCB ships none, `tests/test_verify_lcb.py` uses
> **hand-written reference implementations** instead (43/43 and 34/34).
>
> The rule this generalises to: *a reference solution that fails means the
> harness is broken, not the model.*

---

## A7. The table: databases, rows, and what one row is

Everything the thesis knows lives in one file: `data/carr.sqlite`. **SQLite** is
a database that is just a file — no server, no setup, real SQL.

Four tables:

| Table | One row is | Cost to rebuild |
|---|---|---|
| `problems` | one coding problem: prompt, tests, benchmark, difficulty, release date | free |
| `configs` | one (model, effort) pair with its prices and pinned provider | free |
| `generations` | **one API call** — raw response, tokens, reasoning tokens, dollars, finish reason | **real money** |
| `results` | that call's grade: passed, n tests passed, error type | free (re-runnable) |

**`generations` is the scientific asset.** If the code were lost and this file
survived, the thesis survives. If this file were lost, you would have to pay
again.

Five design decisions in that schema that an examiner may ask about:

- **`request_hash UNIQUE`** over (model, effort, prompt, params, problem_id). It
  is checked before every call; if the hash exists, skip. Crash at row 3,000 and
  restarting costs **$0** for the first 3,000. *Never pay twice* is enforced by
  the database, not by discipline.
- **`raw_response` stored verbatim.** Extraction logic has bugs. Storing the raw
  text means you fix a bug and **re-grade offline for free**, rather than
  re-buying 1,373 generations.
- **`cost_actual_usd` beside `cost_computed_usd`** — ground truth beside
  estimate, so price drift is visible.
- **`is_mock`** — every analysis query filters `is_mock = 0`. During development
  the pipeline ran against a fake provider; without this flag a synthetic row and
  a $0.0006 purchased row are indistinguishable, and by the time that matters the
  mistake is invisible. *(The mock rows were later deleted entirely.)*
- **`effort_mechanism`** is a column, not a comment — because native thinking
  switches and prompt-level budget forcing are **not equivalent**, and results
  must be splittable by mechanism.

**Your results section is, literally, SQL.** `analysis.saturation()` is a
`GROUP BY tier, effort`. Nothing more mysterious than that.

---

## A8. The statistics you actually need

### A percentage without a denominator is not a number

"72%" means nothing. "72.3%, n=83" is a claim. Every table in this thesis prints
its *n*, and every comparison states which problem set it is over. That single
habit is what makes an unbalanced grid survivable — see [B3](#b3).

### Uncertainty, and the bootstrap

You measured 54.2% on 118 calls. If you had drawn a *different* 118 problems,
you would have got a different number. How different? That is what a **95%
confidence interval** answers: a range such that the procedure that produced it
captures the true value 95% of the time.

The **bootstrap** is a beautifully simple way to get one without any formula:

1. You have *n* problems.
2. Draw *n* of them **with replacement** (so some appear twice, some not at all).
3. Recompute your statistic on that fake sample.
4. Do that a few thousand times.
5. Take the 2.5th and 97.5th percentiles of the results.

[`carr/stats.py`](../../carr/stats.py) does exactly this, seeded, in pure
standard-library Python (no scipy). Two details that matter and that an examiner
may test:

- **You resample *problems*, not calls.** Ten calls on one problem are not ten
  independent observations of difficulty — they are one problem observed ten
  ways. Resampling calls would make every interval look far tighter than it is.
- **A ratio must be recomputed as a ratio on each resample.** Cost-per-correct
  is `Σcost ÷ Σsolved`. It is **not** the average of per-problem ratios — those
  are different quantities, and the second one is wrong. A test pins this.

**What the intervals bought you:** five adjacent pairs in the cost-per-correct
table have **overlapping** intervals. Their point estimates differ; their
ordering is *not established*. Reported bare — which is the norm in this
literature — that table would have manufactured a ranking the data does not
support.

### Censoring — the concept that overturned your own headline

If you stop a process before it finishes, you do not observe its true value; you
only observe that it exceeded your cutoff. That is **censoring**, and any
analysis of the censored quantity is biased by it.

Your `max_tokens` ceiling is a censoring mechanism. **A call cut off at the
ceiling cannot possibly have succeeded.** So a low ceiling makes long reasoning
look worse than it is — which is exactly how your pilot manufactured a finding
that better data destroyed. Full story in [C7](#c7).

Even now, **26.3% of hard thinking calls truncate at the 48,000 ceiling**, so
your 54.2% hard-tier pass rate is a **floor**, not an estimate. Say "floor".

---

## A9. The economics of choosing

### The two headline metrics

- **CPC — Cost Per Correct answer** = `Σ dollars ÷ Σ problems solved`. The
  economically meaningful number: what does one *working* solution cost?
- **TPC — Tokens Per Correct answer.** Same idea, token-denominated, and immune
  to price changes.

Accuracy alone is the wrong metric for this thesis, because a config that is 3
points better at 6× the price is not better.

### Pareto frontier and dominance

Plot each configuration as a point: cost on the x-axis, accuracy on the y-axis.

A point is **dominated** if some other point is at least as accurate *and* at
least as cheap. Nobody rational would ever choose a dominated config. The
**Pareto frontier** is what is left: the configs where buying more accuracy
genuinely costs more money.

### The convex hull — and why it is the *honest* baseline

Here is the idea that most improves this thesis, and it is worth being able to
draw on a whiteboard.

Suppose you are not forced to pick one config for everything. You may **split
your traffic**: send 70% of problems to the cheap config and 30% to the
expensive one. Your cost and accuracy are then the weighted averages — a point on
the straight **line between** those two configs.

So the set of things you can achieve without knowing anything about individual
problems is not the set of points; it is the **convex hull** of them — every
line between every pair.

> **Proposition.** Maximise `Σpᵢaᵢ` subject to `Σpᵢcᵢ ≤ B`, `Σpᵢ = 1`, `pᵢ ≥ 0`.
> That is a linear program with **two** constraints, so an optimal *basic*
> solution has at most **two** non-zero weights. Therefore the optimal
> problem-blind budget-constrained strategy **randomises between at most two
> configurations, and lies on the upper convex hull.**

Why this matters so much: your proposal said CARR must beat *"the strongest
single configuration."* But a fixed traffic split already beats that, for free.
**So that bar proves nothing.** The honest bar is the hull.

And it gives you a much sharper claim:

> **A router's margin over the hull *is* the measured value of problem-level
> information.**

The hull is blind to the problem. A router reads the problem. The gap between
them is exactly what "reading the problem" is worth. That is a real quantity, and
you measured it: **13.8 points**.

### The oracle, and MCKP

The **oracle** is a cheat: for each problem it picks the cheapest config that
actually solved it — using the answers, which you do not have at decision time.
It is an **upper bound**, not a method.

Formally, choosing one config per problem under a total budget is a
**Multiple-Choice Knapsack Problem** (MCKP): groups of items (one group per
problem), pick exactly one from each, maximise value subject to a cost budget.
Your oracle is its integer optimum. That framing is classical — say so; don't
dress it up as new mathematics.

### k-NN, and what a router is

A **router** reads an incoming problem and picks a config *before* calling any
model. **k-nearest-neighbours** is the simplest possible way to do that: find the
*k* most similar problems you have already measured, and copy whatever worked for
them. There is no training — it is a lookup. Cover & Hart (1967) bound k-NN's
error at twice the Bayes error, which is why it is the defensible choice at n=60
rather than something fancier.

**"Free features"** means features that cost nothing to compute: difficulty
tier, number of tests, prompt length. No forward pass, no draft answer, no
embeddings. That constraint is the point — *a router that must call a model to
decide whether to call a model has already spent the money it was trying to
save.*

---

<a name="part-b"></a>

# Part B — Your thesis: the question, the machine, the design

---

## B1. The question, and why it is a real one

> **Reasoning models can "think" before answering. That thinking is billed but
> invisible. When is it worth paying for?**

Three reasons this is not a made-up question. Have all three ready — the first
thing a strict examiner attacks is whether the question deserves a thesis.

**1. The cost is invisible, so nobody can price it by inspection.** 392 of 412
tokens on a trivial prompt. Anyone estimating cost from response length is wrong
by ~20×.

**2. The stakes are enormous.** Across this roster, cost per correct answer spans
**305×** — $0.00021 to $0.06320. That is the difference between a $50 and a
$15,000 monthly bill *for the same work*.

**3. There is no measured answer.** The practitioner question — *should I turn
thinking on for this task?* — had no empirical answer for code generation with
real prices attached. The nearest prior work (CodeRouterBench, June 2026)
releases 9,999 tasks × 8 models with cost, but **its `model` column holds eight
model names and nothing else: no effort axis, and no reasoning-token column.**
The quantity this thesis is about is the quantity the closest prior work does not
record.

---

## B2. The machine: the life of one row

This is the whole system. If you can narrate this, you can explain the thesis.

```
   problems table                configs table
   ┌──────────────┐             ┌───────────────────────┐
   │ prompt       │             │ model + effort params │
   │ tests        │             │ pinned provider       │
   │ difficulty   │             │ prices per M tokens   │
   └──────┬───────┘             └───────────┬───────────┘
          │                                 │
          └──────────────┬──────────────────┘
                         ▼
           ① request_hash — have we bought this already?  → if yes, SKIP, $0
                         ▼
           ② cost cap — would the WORST CASE breach the limit? → if yes, ABORT
                         ▼
           ③ OpenRouter call, provider pinned, temperature 0, n=1
                         ▼
           ④ store raw_response verbatim + tokens + reasoning_tokens + cost
                         ▼
           ⑤ extract.py: pull the Python out of the prose
                         ▼
           ⑥ verify.py: run it against the real tests, in a guarded subprocess
                         ▼
           ⑦ results row: passed / base_passed / n_tests / error_type
                         ▼
           ⑧ later, in one batch: GET /generation → cost_actual_usd
```

Points ① and ② are the money discipline. Point ④ before ⑤ is what makes
extraction bugs free to fix. Point ⑧ is separate because `/generation` needs
~10 seconds to settle — blocking on it per call would have added hours.

**The four cost controls**, all built and tested:

1. **A cap that aborts, not warns.** `carr/runner.py` refuses any call whose
   **worst case** would push **lifetime** spend past `abort_at_usd: 6.00`. An
   expected-case cap is not a cap. And the worst case is
   **2.5 × `max_tokens` × output price**, not 1× — because `max_tokens` is *not*
   a hard bound: `qwen3.5-9b` once returned **35,837** tokens against a 16,000
   ceiling, 2.24× over. `WORST_CASE_SAFETY = 2.5` exists so a single overrun
   cannot walk through a cap that looked satisfied. `tests/test_runner.py` holds
   **19** tests on that loop (THESIS.md's "16" is stale), three of them named
   directly on the cap abort.
2. **`max_tokens` per effort** — 16,000 for `off`, 48,000 for `high`. Also what
   the worst case is computed *from*.
3. **Cheapest configs first**, globally. If the cap fires, you lose the expensive
   tail, not the cheap foundation you would have to re-buy.
4. **`retries: 0`.** A retry loop is how a cost cap gets defeated. (The one
   exception: rate-limit 429s, which are billed $0, so retrying them cannot
   defeat anything.)

Result: **$5.24 spent, of $15.00 loaded, under a self-imposed $6.00 cap, never
breached.** $9 was left deliberately unspendable — a bigger balance is not a
bigger budget.

---

<a name="b3"></a>

## B3. The design, and the reason behind every choice

An examiner's favourite question is *"why did you do it that way?"* Here is every
answer, in one place.

| Choice | Why |
|---|---|
| **5 open-weight models** | Open weights mean the model is inspectable and re-servable — a closed model can be changed under you silently. It also makes the provider/quantization findings possible at all. |
| **Only 3 families** (2 DeepSeek, 2 Qwen, 1 Moonshot) | GLM was dropped; a within-family pair is not two independent models. **State this rather than letting it be raised.** |
| **Each model paired with *itself*** at off/high | Within a pair, the *only* thing that changes is the thinking mode. That is what keeps the effort axis unconfounded. |
| **Kimi held out entirely, on a subset** | It is the only non-DeepSeek/Qwen family, so it is the most genuinely out-of-distribution transfer test available. At $3.40/M output, full coverage would cost more than every other config combined. |
| **Both effort levels for Kimi** | `subset_only` cuts *problems*, never the effort axis. With one effort Kimi would be a single point with no measurable thinking delta — and the effort axis is what the thesis is about. |
| **OpenRouter** | One key, one schema, at a $15 budget. And it produced the measurement-validity chapter. |
| **Provider + quantization pinned, `allow_fallbacks: false`** | Otherwise you are comparing different models at unpredictable prices. Trades availability for reproducibility. |
| **temperature 0, n=1** | Halves cost *and* makes "cheapest config that passes" deterministic rather than a lottery. Cost: no within-cell variance measured — a stated limitation. |
| **320 problems, not 884** | Every problem is 10 API calls. Stratified, seeded (`20260726`). |
| **Grid re-weighted after the pilot** toward LCB medium+hard (20/20/20/104/154) | The pilot measured the easy tiers at 90–100% regardless of reasoning. Spending grid budget there buys rows that inform nothing. The easy tiers stay as **20-problem anchors** because the saturation rate is itself a reported finding and needs a measured denominator. |
| **Cut problems, never grid cells** | The routing label is "cheapest config that passes *this* problem", which is only computable if every problem ran through every config. A sparse grid destroys the ground truth. |
| **Grading in exactly one file** | `atol` and MBPP special oracles make pass/fail more than `==`; a second grader is a second chance to be silently wrong. |
| **Bootstrap over problems** | Two cells on one problem are not independent. |
| **Fixed seeds everywhere** | Reproducibility is a graded property of a thesis. Running the analysis twice produces byte-identical output. |

### The unbalanced grid — the design's biggest scar, and how it is handled

Coverage is **uneven**:

| config | problems run |
|---|---|
| `qwen3.6-35b\|off`, `flash\|off` | 320 |
| `qwen3.5-9b\|off` | 318 |
| `qwen3.5-9b\|high` | 104 |
| `qwen3.6-35b\|high`, `flash\|high` | 74 |
| `pro\|high` | 73 |
| `pro\|off` | 51 |
| `kimi\|high` | 23 |
| `kimi\|off` | 16 |

This happened because the run was ordered **cheapest-first** and stopped at the
cap. The cheap `off` arm finished; the expensive arms did not.

**Why it is not fatal:** a cost-accuracy number computed per config over *that
config's own* problems compares models on **different exams**. So every
comparable statistic is restricted to one shared set, and the denominator is
printed on every row:

- **107 problems** have *both* effort arms graded → the CPC/TPC table.
- **60 problems** are shared by **6 configs** → the frontier, hull, oracle and
  router. (All ten share only **5**, which is useless.)

**Concede the rest honestly:** balancing the thinking arm would have cost about
$1.50 and required raising the cap. It was recorded as a limitation instead. And
the missing cells are **not missing at random** — the expensive configs are
absent on the *later* problems in the run order. That is a real caveat and
belongs in the limitations chapter.

---

<a name="part-c"></a>

# Part C — The eight findings

Each one below is stated as: **the claim → the number → the caveat that must
travel with it → why it matters.** Never separate a claim from its caveat; that
is the habit that survives a viva.

---

<a name="c1"></a>

## C1. Most benchmark problems cannot answer the question at all

**Claim.** The standard code benchmarks are saturated for 2026-class models, and
most problems carry no signal about *which* configuration to use.

**The numbers.** Pass rate, reasoning off vs on:

| tier | off | on | n (off / on) |
|---|---|---|---|
| LiveCodeBench **hard** | **24.9%** | **54.2%** | 462 / 118 |
| LiveCodeBench **medium** | **53.3%** | **76.4%** | 317 / 148 |
| MBPP+ | 72.3% | 73.3% | 83 / 30 |
| HumanEval+ | 92.9% | 97.0% | 85 / 33 |
| LiveCodeBench easy | 94.1% | 100% | 68 / 11 |

And per problem, across all 320:

> **81 solved by every configuration. 98 solved by none. Only 141 discriminate.**

A problem everything solves and a problem nothing solves are **equally
uninformative** — neither can distinguish a good decision from a bad one.

### 🔴 But that second table is mostly a statement about your budget

**This is the most fragile number in the thesis. Know it before you are asked.**

Unanimity is trivially easier to reach with fewer voters, and coverage here runs
from **2 configurations per problem to 10**. **206 of the 320 problems saw only
two or three** — nearly always the three cheap `off` configs, because the run
was ordered cheapest-first and stopped at the cap.

| coverage | n | all solved | none solved | discriminating |
|---|---|---|---|---|
| ≥ 1 configuration *(as reported)* | 320 | 81 (25%) | 98 (31%) | **141 (44%)** |
| ≥ 1 *reasoning-enabled* config | 108 | 33 (31%) | 4 (4%) | **71 (66%)** |
| ≥ 6 configurations | 73 | 11 (15%) | 2 (3%) | **60 (82%)** |

> **Of the 98 problems "solved by nothing", 94 were never attempted by a single
> reasoning-enabled configuration.** They only ever saw the cheap arm.

Read at real coverage the picture **inverts**: on problems actually measured
across six or more configurations, **82% discriminate**.

**What survives, and what does not:**

- ✅ **The per-tier saturation result survives**, because it is a *pass rate*,
  not a unanimity count. HumanEval+, MBPP+ and LCB-easy sit at **72–100%
  whichever effort arm you read**. Those benchmarks really are too easy.
- ✅ **The methodological point survives**, and it is now sharper: *a problem
  measured thinly looks unanimous, and unanimity across few configurations is a
  property of the budget rather than of the problem.*
- ❌ **"76% of the pool produces no routing signal" does not survive.** Drop it
  rather than defend it.

Reproduce: `scripts/results.py` (the ⚠ COVERAGE-DEPENDENT block) or
`analysis.discrimination_by_coverage()`.

**Why it matters.** This is still a finding about **benchmarks**, not models. It
says HumanEval+ and MBPP+ are the wrong instruments for this question, and that
anyone studying it should state **which subset of their benchmark carries the
signal** — and now also *how many configurations each problem was actually
shown to* before calling it unanimous.

---

## C2. Thinking works — conditionally, and the condition is the *model*

**Claim.** The value of reasoning is conditional on difficulty **and on which
model you are asking**, and the second half is the part the aggregate hides.

**The aggregate numbers.** On LCB hard, **24.9% → 54.2%**. On LCB medium,
**53.3% → 76.4%**. On MBPP+, **+1.0 points**. *Read the caveat below before
quoting any of them* — the hard-tier figure averages a **+52.9** and a
**−18.2**.

### 🔴 The single most important caveat: this is *not* a per-tier finding

**The aggregate averages over models that respond in opposite directions.** Per
(tier, model), on the arms with real coverage:

| tier | model | off | high | delta | censored |
|---|---|---|---|---|---|
| hard | `deepseek-v4-flash` | 29.2% (154) | **82.1%** (28) | **+52.9** | 11% |
| hard | `qwen3.6-35b-a3b` | 22.1% (154) | 27.6% (29) | +5.5 | 17% |
| **hard** | **`qwen3.5-9b`** | 22.1% (145) | **3.8%** (26) | **−18.2** | **81%** |
| medium | `deepseek-v4-flash` | 62.5% (104) | **94.4%** (36) | **+31.9** | 0% |
| medium | `qwen3.6-35b-a3b` | 52.9% (104) | 72.2% (36) | +19.3 | 6% |
| medium | `qwen3.5-9b` | 43.6% (101) | 38.7% (31) | −4.9 | 52% |
| **MBPP+** | **`qwen3.5-9b`** | 80.0% (20) | **55.6%** (18) | **−24.4** | **0%** |
| HumanEval+ | `qwen3.5-9b` | 90.5% (21) | 94.7% (19) | +4.3 | 0% |

> **"+29.3 points on hard" is an average over +52.9 on one model and −18.2 on
> another.** Reasoning is not a property of the difficulty tier. It is a
> property of the **(model, tier) pair**.

The `censored` column — the share of thinking calls stopped at the 48,000-token
ceiling, which therefore *cannot* have succeeded — separates two mechanisms that
need different sentences:

1. **Non-termination.** `qwen3.5-9b|high` hits the ceiling on **81% of hard
   calls**, returns no code at all on 77%, and averages **24,826** reasoning
   tokens. Its −18.2 is mostly *the model failing to stop*, and partly a
   statement about our ceiling: `deepseek-v4-flash|high` censors at only 11% on
   the same problems.
2. **Genuine degradation — the cleanest result in the thesis.** On MBPP+ the
   same model censors **0%**, reasons for a mean of **368** tokens, terminates
   normally, and *still* falls from 16/20 to 10/18 **on the same twenty
   problems**. Every failure produced extracted code and failed on assertions.
   **That is not measurement.** Enabling reasoning made easy problems harder for
   a small model — overthinking, observed directly, with truncation ruled out.

**Why this is good news for you.** It is a richer finding than the aggregate,
it was free to obtain (a re-analysis, not a re-purchase), and it gives the
practitioner a real rule: *enable reasoning on a capable model for hard
problems; on a small model it may cost you accuracy at both ends of the
difficulty range.*

Reproduce: `scripts/results.py`, section ⚠ THE EFFECT IS PER MODEL.

⚠️ And note the easy-benchmark rows of the aggregate are **model-confounded**:
the `high` arm is 62% `qwen3.5-9b` on MBPP+ and 58% on HumanEval+, against ~25%
each in the `off` arm. So "MBPP+ 72.3% → 73.3%" compares a four-model average
against a mostly-one-model average.

**Further caveats, all of which you volunteer:**

- **🔴 The two arms did not sit the same exam.** LiveCodeBench ships
  stdin→stdout (AtCoder) problems and `Solution`-class (LeetCode) problems, and
  coverage is wildly uneven: on the hard tier the `off` arm is **348 stdin / 114
  functional**, the `high` arm is **8 / 110**. So the raw gap mixes a reasoning
  effect with a composition effect.

  **The cause is mechanical, not a design choice.** `runner.plan` sorts cells by
  `(expected_usd, problem_id)`; ties inside a config break on the id *as a
  string*; LeetCode ids are numeric (`LiveCodeBench/3487`) and AtCoder ids start
  with letters (`LiveCodeBench/abc374_a`); digits sort first. So all 125
  functional problems ran before any of the 217 stdin ones, and the expensive
  thinking arm hit the cost cap inside that prefix.

  **The matched comparison** — free, a re-analysis of rows already bought:

  | tier | style | off | on | matched | raw |
  |---|---|---|---|---|---|
  | hard | functional | 31.6% (n=114) | **57.3%** (n=110) | **+25.7** | +29.3 |
  | medium | functional | 49.1% (n=163) | **78.0%** (n=141) | **+28.9** | +23.0 |

  **The finding survives on both tiers** — and the medium effect is *larger*
  under matching, not smaller. What changes is the wording: on hard
  function-style problems reasoning multiplies the pass rate by **1.8**, not
  "more than doubles". And nothing is claimed about stdin problems: that arm is
  **n=8**. Reproduce with `scripts/results.py`, section ⚠ STYLE CONFOUND.
- **54.2% is a floor, not an estimate**, because **26.3% of hard thinking calls
  still truncate** at the 48,000-token ceiling, and a truncated call cannot
  succeed.
- The arms have different *n* (462 vs 118) and are compared on the paired
  problem set, not on each arm's own problems.

**Why it matters.** It is the direct answer to the thesis question, and it is not
the trivial answer. It is *not* "thinking helps"; it is **"thinking helps
enormously in one place and is essentially free money for the vendor
everywhere else"** — with the boundary measured.

**And note:** your own 15-problem pilot claimed the *opposite* direction on hard
problems (31% vs 50%). That was truncation, not capability. Which is a very good
story about why pilots are gates and not results.

---

## C3. Reasoning length rises monotonically with difficulty

**Claim.** Models reason longer on harder problems, without being told the
difficulty.

**The numbers.** Mean reasoning tokens: MBPP+ **642** (n=30) → HumanEval+ **773**
(33) → LCB easy **2,693** (11) → LCB medium **10,183** (148) → LCB hard
**17,547** (118).

**Caveat.** The easy-tier *n*s are small (11–33), and the tiers differ in more
than difficulty (different sources, different prompt styles).

**Why it matters.** Two reasons. First, it is a **validity check**: a measure
that tracks an independently-assigned difficulty label the model never saw is
behaving sensibly. Second, it is the mechanism behind C4 — length is the signal a
runtime intervention could act on.

---

## C4. Long reasoning is failure, not effort — and it is expensive

**Claim.** A model that thinks for a very long time is not working harder. It is
failing, at maximum cost.

**The numbers.** Among reasoning-enabled calls:

| outcome | n | mean reasoning tokens | spend |
|---|---|---|---|
| passed | 242 | 7,567 | $2.52 |
| failed (ran, wrong answer) | 49 | 7,577 | $0.55 |
| **billed, no usable answer at all** | **49** | **29,584** | **$0.56** |

> **49 calls burned an average of 29,584 reasoning tokens and returned nothing.
> That is 15% of everything spent on reasoning-enabled calls ($0.56 of $3.62),
> and 11% of total spend ($5.24).**

**⚠️ Carry the denominator.** An examiner will divide $0.56 by $5.24 and get 11%.
If you say "15% of spend" without saying "of reasoning spend", you look like you
do not know your own numbers.

**Caveats — two, and both matter:**

- Passing and failing calls have **nearly identical** mean reasoning length
  (7,567 vs 7,577) — so length does **not** separate right from wrong. It only
  separates *finished* from *never finished*. Do not overstate this as
  "reasoning length predicts correctness".
- **🔴 76% of the waste is one model.** Share of each model's thinking calls
  that were billed and returned nothing:

  | model | wasted / calls | rate | mean reasoning |
  |---|---|---|---|
  | **`qwen3.5-9b`** | **37 / 99** | **37.4%** | 30,411 |
  | `qwen3.6-35b-a3b` | 7 / 74 | 9.5% | 16,635 |
  | `deepseek-v4-flash` | 3 / 73 | 4.1% | 48,000 |
  | `deepseek-v4-pro` | 2 / 72 | 2.8% | 31,999 |
  | `kimi-k2.6` | 0 / 22 | 0.0% | — |

  So "expect 15% of your reasoning spend to buy nothing" is the wrong advice to
  give anyone. **Non-termination is a property of the small model**, not of
  reasoning — about a third of `qwen3.5-9b`'s thinking calls returned nothing,
  against one in twenty-five of `flash`'s.

**Why it matters.** It converts an abstract worry ("overthinking") into money,
and it is what makes a runtime abort worth studying at all.

---

## C5. The frontier: the expensive model is not worth its price

**Claim.** On the shared problem set, the cost-accuracy frontier has only two
vertices, and the frontier model is dominated.

**The numbers** (6 configs × 60 shared problems; cost is dollars per *problem*):

| config | cost/problem | accuracy | 95% CI | |
|---|---|---|---|---|
| `flash\|off` | $0.00016 | 65.0% | [52, 77] | **hull vertex** |
| `qwen3.5-9b\|off` | $0.00034 | 33.3% | [22, 45] | dominated |
| `qwen3.6-35b\|off` | $0.00170 | 41.7% | [30, 55] | dominated |
| `flash\|high` | $0.00177 | **98.3%** | [95, 100] | **hull vertex** |
| `pro\|high` | $0.01088 | 95.0% | [88, 100] | dominated |
| `qwen3.6-35b\|high` | $0.01093 | 68.3% | [57, 80] | dominated |

> **`deepseek-v4-pro | high` costs 6× more than `flash | high` and shows no
> measurable accuracy advantage.**

On the frontier set that is 57/60 against 59/60. But on the **68 problems the
two actually share it is an exact tie — 64/68 each.** Claim the tie, not the
3-point gap: it is stronger *and* it does not depend on overlapping intervals.

And the cost-per-correct table over the 107 paired problems spans **305×**:
`flash|off` at **$0.00021** to `kimi|high` at **$0.06320**.

**Caveats — all four essential:**

- **The accuracy intervals overlap** ([95,100] vs [88,100]). So the *direction*
  is suggestive, not established. What the data supports is: *the more expensive
  model shows no measurable advantage at six times the price.*
- **Five adjacent CPC pairs have overlapping intervals**, so their ordering is
  not established either.
- **⚠️ The 305× is not like-for-like.** The paired set guarantees each *row* has
  both effort arms; it does **not** guarantee two rows sat the same exam.
  Coverage runs n=16 to n=107 and the tier mix moves with it. Three figures,
  all printed by `scripts/results.py` — quote whichever you can name the
  denominator for:

  | comparison | denominator | spread |
  |---|---|---|
  | cheapest vs dearest config | different sets, n=107 and n=22 | **305×** |
  | those same two configs | the **22** problems they share | **228×** |
  | all six frontier configs | the **same 60** problems | **65×** |

  All three are large, so *"CPC varies by orders of magnitude"* is robust. The
  specific number is not interchangeable between them. Related: `pro|off` looks
  cheap per correct answer ($0.00080, third-best) partly because **35 of its 45
  paired problems are HumanEval+/MBPP+** — it sat an easier exam.
- **The 60 problems inherit the style skew**: they are **51 functional and 2
  stdin** LCB problems plus 7 from the easy benchmarks, and **all 19 of their
  hard problems are function-style** against a pool hard tier that is 117 stdin
  to 37 functional. So the frontier, the hull, the oracle, the 13.8-point
  headroom and the router result all describe **function-style** problems.
  `flash|high`'s 98.3% is an accuracy on LeetCode-style completions; label it
  that way.
- 60 problems, and prices from one week in July 2026.

**Why it matters.** It is the practitioner's answer, and it is
counter-intuitive: buying the frontier model is not buying accuracy here. It also
demonstrates the discipline of *not* claiming a ranking your intervals do not
support.

---

## C6. There is 13.8 points of headroom — and the router captured none of it

**Claim (positive half).** Knowing something about a problem before choosing a
configuration is worth 13.8 accuracy points at equal budget.

**The numbers.**
- **Oracle** (cheapest config that solves each problem): **98.3% at
  $0.00111/problem.**
- **Convex hull** (problem-blind mixing) at that same budget: **84.5%.**
- **Value of problem-level information: +13.8 percentage points.**

**Have this ready, because it looks like a bug and is not.** The oracle's 98.3%
is *exactly* `flash|high`'s, because `flash|high` solved 59 of 60 and the one it
missed was solved by nothing — so no per-problem choice could beat it on
accuracy. **What the oracle buys is price, not accuracy:** the same 98.3% at
$0.00111 instead of $0.00177, by routing 37 problems to `flash|off`, 3 to
`qwen3.5-9b|off`, 1 to `qwen3.6-35b|off`, and only **18 of 59** to the thinking
config. So state the 13.8 points precisely — it measures *how much cheaper you
can reach this accuracy if you know the problem*, not *how much more accurate
you can get*.

**Claim (negative half).** A k-NN router over free features captures **zero** of
it and **collapses to a single configuration**.

| strategy | accuracy | cost/problem | configs used |
|---|---|---|---|
| always cheapest | 65.0% | $0.00016 | 1 |
| always dearest | 68.3% | $0.01093 | 1 |
| rule: "think if hard" | 66.7% | $0.01027 | 2 |
| **k-NN (k=5), leave-one-out** | **65.0%** | $0.00016 | **1** |

65.0% is *exactly* the convex hull. **Router minus hull: +0.0 points.**

**The decomposition — and this is the genuinely original piece:**

| | |
|---|---|
| oracle (needs the answers) | 98.3% |
| **ceiling from these free features alone** | **98.3%** |
| k-NN actually achieves | 65.0% |
| **feature insufficiency** | **0.0 points** → better features are *not* the fix |
| **estimation error** | **33.3 points** → the *estimator* is the fix |

**Why it collapsed, mechanically:** the label being predicted is "the cheapest
config that solved this problem", and that label is **dominated by one config**.
A nearest-neighbour *vote* returns the modal label, so it returns that one config
everywhere. The collapse is a property of the **objective**, not of the inputs.

**The named fix:** predict per-config *success probability* and solve the
per-problem knapsack — a **cost-aware objective** — rather than classifying the
modal label.

### 🔴 And the harder question underneath: are those features even *available*?

This is the criticism that hurts most, because it is true whether or not the
router worked. The three "free features" are:

| feature | where it comes from | available for a new problem? |
|---|---|---|
| difficulty tier | **LiveCodeBench's own hardness label** (`problems.difficulty`); for HE+/MBPP+ it degrades to the benchmark name | **No** — it is benchmark metadata |
| number of tests | `problems.n_tests` = base + plus, i.e. **the size of the hidden grading suite** | **No** — not knowable before grading |
| prompt length | the prompt text | **Yes** |

**Two of the three are metadata a deployment would not have.** The proposal
positions CARR as routing "using only cheap, non-LLM structural and lexical
features" of the *arriving prompt*; that is not what was built.

Two consequences, and you should state both before an examiner does:

1. **The positioning claim is falsified independently of the result.** Even a
   router that had worked would not have demonstrated what the proposal said it
   would.
2. **It weakens the decomposition's good news.** "Feature insufficiency 0.0 —
   the features are sufficient to reach the oracle" really means *these
   features, two thirds of which are labels you would not have, are sufficient*.
   That is a much smaller claim, and the ceiling is fitted besides.

**What survives.** The measurement of *headroom* is untouched: the oracle, the
hull and the 13.8 points never use these features. And the honest future-work
sentence gets sharper: *a deployable router has one usable feature here (prompt
length) plus whatever else the prompt text yields — keyword presence, structure,
signature count — and none of that was measured.*

**Caveat you must volunteer.** The feature ceiling is **fitted on the same 60
problems it describes**, across 12 buckets — 5 problems per bucket. It is an
*optimistic upper bound*, not an achievable target. "The features are at least
this informative" is the honest reading.

**Why it matters.** This is what turns a failed method into a contribution. A
negative result that says **which direction to fix** is worth more than a
marginal positive one. And note it fails against the *correct* baseline — against
the weaker "beat the best single config" bar, `always dearest` at 68.3% would
have looked like a success.

---

<a name="c7"></a>

## C7. The runtime abort — and the headline this project refuted

This is the best story in the thesis. Tell it in this order.

**Step 1 — the mechanism is real, and it is free.** Reasoning is observable
*live* in the stream via `delta.reasoning`. And **cancelling a stream
mid-reasoning is billed $0.00** — verified on two providers, against **$0.010978**
for the same cell run to completion. So an abort saves the **whole** call, not a
pro-rata part. That makes "stop a call once it has thought too long" a real
intervention rather than a thought experiment.

**Step 2 — the pilot found a free lunch.** Over 15 problems: *abort at 10,000
reasoning tokens, keep **every** solved problem, save 44%.* A dominant
improvement. Wonderful.

**Step 3 — the full grid destroyed it.** The pilot ran under a **16,000-token
ceiling**. A truncated call **cannot succeed**. So the ceiling itself guaranteed
that nothing above ~10,000 reasoning tokens ever passed — **the ceiling
manufactured the cliff the claim depended on.**

At the raised 48,000 ceiling, **56 calls above 10,000 reasoning tokens
succeeded.** Pass rate declines as a **gradient**, not a cliff: 83.8% under 10k,
55.2% at 10–20k, 39.3% above 20k. `best_threshold()` now correctly returns
`None`.

**Step 4 — what honestly survives** is a tradeoff curve with no free point:

| abort at | solutions kept | 95% CI | cost saved | 95% CI |
|---|---|---|---|---|
| 2,000 | 35% | [27, 44] | 98% | [96, 99] |
| 6,000 | 57% | [48, 66] | 90% | [86, 94] |
| 10,000 | 77% | [69, 83] | 72% | [62, 80] |
| **16,000** | **88%** | **[82, 92]** | **49%** | **[35, 61]** |

> **No threshold saves money without losing a solved problem.**

### 🔴 And the pool hides a free threshold that *does* exist

"No threshold saves money without losing a solved problem" is true of the
**pooled** roster. Per model it is **false for two of the five**:

| model | free threshold | saving | solutions kept |
|---|---|---|---|
| **`qwen3.5-9b`** | **10,000 tokens** | **88%** | **46 / 46** |
| **`qwen3.6-35b-a3b`** | **16,000 tokens** | **13%** | **43 / 43** |
| `deepseek-v4-flash` | none — every threshold costs a solution | | |
| `deepseek-v4-pro` | none | | |
| `kimi-k2.6` | none | | |

**And the pattern is coherent, not noise: the free threshold exists exactly
where reasoning was not earning its keep.** `qwen3.5-9b`'s reasoning delta is
negative on three tiers of four and 37% of its thinking calls return nothing —
so whatever it solved, it solved early, and everything long was already doomed.
`deepseek-v4-flash` gains **+52.9 points** on hard problems *by* thinking
longer, so cutting it off must cost solutions.

**This refines the refutation; it does not undo it.** The pilot claimed a free
threshold *for the roster*, and that remains false — the 16k ceiling really did
manufacture part of it. What survives is narrower and far more useful:

> **Whether a reasoning-length abort is free is a property of the model.** Where
> long reasoning rarely succeeds it is free money — 88% of `qwen3.5-9b`'s
> thinking spend, losing nothing. Where long reasoning genuinely solves hard
> problems, every threshold costs solutions.

Same caveats as the pooled curve: a simulation over completed calls, resting on
the measured $0.00 cancellation, and a threshold picked here is fitted unless it
is evaluated on data it was not chosen on. Reproduce with
`analysis.abort_by_model()` or `scripts/results.py`.

**Caveats.** It is a **simulation** over completed calls, not a deployed
intervention. And a threshold must be chosen on data it is not then evaluated
against, or it is fitted. The right-hand end is still softened by the 26.3%
censoring at 48k.

**Why it matters.** Two things. It gives a practitioner a real dial. And it
demonstrates the general hazard in one sentence:

> **A truncation limit is a censoring mechanism, and censored observations bias
> any analysis of the quantity being truncated.**

Catching and reporting your own refutation is better science than the original
claim would have been. Lead with it when asked *"tell me about a result you got
wrong."*

---

<a name="c8"></a>

## C8. Three ways the platform lies, and one way it helps

Arguably the strongest and most transferable chapter, because it generalises far
beyond this thesis.

**1. Provider routing silently changes both price and model.**
One model slug is served by **18 providers at $0.87–$3.48 per M output**.
`GET /models` reports only the cheapest. Unpinned, one run here was served by
**nine different providers** and billed **1.54× the prediction**. Quantization
varies **fp4 → bf16**, so an unpinned evaluation is comparing *different models*.

**2. Advertised reasoning budgets are accepted and ignored.**
On `qwen3.5-9b`: `reasoning: {max_tokens: 2000}` produced **13,731** reasoning
tokens — 6.9× the request. `reasoning: {effort: "low"}` produced **11,926**. Both
accepted without error; both listed in the endpoint's `supported_parameters`.
This is **silent non-compliance**, not an unsupported feature.
→ Consequence: the effort axis is **binary in practice**, and must be described
that way rather than as a budget dial. It also answers the obvious objection to
the whole thesis — *"why not just tell it to think less?"* **You can't.**

**3. `max_tokens` is not a hard bound.** Observed **35,837** tokens against a
16,000 ceiling, and **73,037** against 48,000.

**4. And one that helps:** cancelling a stream mid-reasoning is **billed
$0.00**, verified on two providers, with reasoning observable live.

**The claim to make:**

> **Any evaluation of open-weight models through an aggregator without provider
> pinning is confounded on both price and precision.**

**Caveats — be first to say these.** Finding 2 rests on a small number of
targeted calls on **one model**, so state it as *"demonstrated on qwen3.5-9b"*
rather than as a universal law. Finding 1's 1.54× is from **one run**. These are
existence proofs of a hazard, not a systematic survey — and an existence proof is
enough to justify the pinning methodology, which is what you use them for.

---

<a name="part-d"></a>

# Part D — The code, module by module

~2,000 lines. Every rule exists to stop a specific, previously-observed failure.

| File | What it does | The failure it prevents |
|---|---|---|
| [`config/models.yaml`](../../config/models.yaml) | The roster: slugs, pinned provider+quantization, prices, snapshot date | No model name is hardcoded anywhere; the landscape moves every 6–8 weeks |
| [`config/experiment.yaml`](../../config/experiment.yaml) | Caps, `max_tokens`, temperature, strata, seed | A cap that lives in code is a cap somebody edits by accident |
| [`carr/effort.py`](../../carr/effort.py) | roster → the 10 configs, cheapest first | — |
| [`carr/cost.py`](../../carr/cost.py) | tokens → dollars | Reasoning tokens double-counted (they are a *subset* of completion) |
| [`carr/providers/openrouter.py`](../../carr/providers/openrouter.py) | **The one file that spends money** | Unpinned providers; unbounded calls |
| [`carr/extract.py`](../../carr/extract.py) | raw response → runnable Python | Never raises; a truncated fence is graded as the broken code it is |
| [`carr/execute/verify.py`](../../carr/execute/verify.py) | **THE grader** — EvalPlus path + LiveCodeBench path | Hand-rolled grading mislabels `atol`/oracle problems; the macOS `setrlimit` bug |
| [`carr/benchmarks/livecodebench.py`](../../carr/benchmarks/livecodebench.py) | Download/cache/decode LCB v5+v6 | 217 stdin vs 125 functional problems need different execution |
| [`carr/db.py`](../../carr/db.py) | Schema, `request_hash`, backups | **Never pay twice**; never lose the asset |
| [`carr/experiment.py`](../../carr/experiment.py) | Config loading + stratified seeded sampling | A pilot over `HumanEval/0..9` would report 100% and teach nothing |
| [`carr/runner.py`](../../carr/runner.py) | **The paid loop** | The cap aborts on *worst case* against *lifetime* spend, before sending |
| [`carr/stats.py`](../../carr/stats.py) | Seeded percentile bootstrap, stdlib only | Ratios averaged instead of recomputed; cells resampled instead of problems |
| [`carr/analysis.py`](../../carr/analysis.py) | Every number in the thesis | Infra failures scored as model failures; unbalanced comparisons |
| [`carr/router.py`](../../carr/router.py) | Free features, k-NN, rules, the §10.2 decomposition | Training on the problem being predicted (leave-one-out) |
| [`carr/figures.py`](../../carr/figures.py) | The five PNGs | Charts without error bars implying precision the data lacks |
| [`scripts/results.py`](../../scripts/results.py) | Regenerates every headline number, free | — |
| [`tests/`](../../tests/) | **132 tests** | Largest groups: the cost cap (16) and never paying twice (13) |

**Three naming/plumbing traps worth knowing** (they are good viva anecdotes):

- `scripts/inspect.py` **shadowed the stdlib `inspect` module** and silently
  broke every script in that directory. The viewer is called `view.py` for this
  reason.
- `config_id` was once a config's **position in a price-sorted list**. Repricing
  a model swapped two entries and **8 already-bought generations were attributed
  to the wrong model.** It surfaced only as a `UNIQUE` failure during an
  unrelated migration. Identity is now alphabetical and price-independent; the
  repair used `request_hash` as ground truth and resolved all 149 rows exactly,
  guessing none.
- In `experiment.yaml`, `max_tokens` keys are **quoted**: YAML 1.1 parses a bare
  `off` as the boolean `False`, which silently made the key unreachable.

---

<a name="part-e"></a>

# Part E — What this is *not*

State every one of these before an examiner does. Volunteering a limitation is
strength; conceding it under pressure is damage control.

- **Not a new routing algorithm.** Route-To-Reason, DART and CodeRouterBench
  occupy that space. RQ4 here measures the *headroom* a router would have, and
  stops there.
- **Not novel on overthinking.** ThoughtTerminator, SelfBudgeter and RecurGuard
  already study reasoning that fails to terminate. The **economic framing** —
  dollars per correct answer across a price-varying roster — is the less-covered
  part.
- **Not contamination-controlled.** LCB stopped updating in 2025; every roster
  model is a 2026 release. LCB is a **difficulty tier**; the exposure is reported
  and `release_date` is stored so it can be quantified.
- **Not fully powered.** Comparable statistics rest on **60–107 problems**.
  Several intervals overlap. Directions are clear; individual orderings often are
  not, and the thesis marks which is which.
- **Not free of censoring.** 26.3% of hard thinking calls still truncate at
  48,000 tokens, so the long-reasoning tail is a **floor**, not an estimate.
- **Not a variance study, and not a verified-determinism one either.** One sample
  per cell at temperature 0, so within-config variance is not measured. And
  `temperature_sent` logs what was *sent* — 0.0 on all 1,373 rows, a constant —
  not what the endpoint applied. THESIS.md §9 says to "log the actual
  temperature" because thinking endpoints sometimes override it; that was never
  implemented. **If asked how you know temperature 0 was honoured: you don't.**
  With one sample per cell you cannot detect nondeterminism either. Determinism
  is an assumption, and given that reasoning budgets and `max_tokens` were both
  silently ignored (Finding C8), it is not a safe one.
- **Not balanced.** Coverage is uneven and the missing cells are not missing at
  random — the run order's `problem_id` tiebreak made the thinking arm almost
  entirely function-style. Every effort comparison is therefore reported *within*
  a style, and **nothing here says what reasoning does on stdin-style problems**
  (that arm is n=8).
- **Not multi-language, not repository-scale, not agentic.** Single-file Python
  functions and competition problems only.
- **🔴 Not an observation of reasoning at all — only of its token count.**
  `carr/providers/openrouter.py` stores `choice.message.content` as
  `raw_response`. `choice.message.reasoning`, which OpenRouter returns for these
  models, is **never read**, and no column holds it. So the quantity the whole
  thesis is about was never captured: the call that burned **73,037** reasoning
  tokens left behind an 18KB block of code and an integer.

  Three consequences, and you should give all three: **`reasoning_tokens` is a
  vendor annotation** with no independent check anywhere in the pipeline, and
  every cost, waste and abort number rests on it; **the overthinking finding
  cannot be inspected** — nobody can say what the 49 wasted calls were *doing*
  for 29,584 tokens; and **it is not recoverable offline**, unlike an extraction
  bug. This is the best answer to "what would you do differently": *capture
  `message.reasoning`, because it costs nothing extra and it is the only thing
  that would let anyone check the number the thesis is built on.*
- **Not declared, yet — and this one is not a limitation but an errand.** The
  repository has **no generative-AI declaration**, while 37 commits carry
  `Co-Authored-By: Claude` and `CLAUDE.md` is a standing instruction file for an
  AI assistant. An examiner opens `git log` and finds that in ten seconds.
  Disclosed use is normally fine; **undisclosed use is an integrity matter, not
  a methodological one.** Draft wording is in THESIS.md §16 — check it against
  your department's actual regulations. Say what you verified yourself (every
  number regenerates from `scripts/results.py` on a fixed seed, 132 tests, raw
  responses stored for free re-grading) and expect to be asked to explain any
  line of the code on demand, which is the fair test.
- **Not a fully-read literature review — yet.** Route-To-Reason,
  Agent-as-a-Router and HRBench claims currently rest on **summaries and PDF
  extraction, not full reads**. That is the highest-value $0 task remaining, and
  the most likely thing a well-read examiner catches.

---

<a name="part-f"></a>

# Part F — The story you tell

A viva goes well when you have a *narrative*, not a pile of facts. Here is yours,
in five beats. Practise telling it in three minutes.

**Beat 1 — The question came from a measurement, not an idea.** On day one, a
trivial prompt burned 392 invisible tokens out of 412. That is the moment the
thesis existed: the cost is real, invisible, and unmeasured.

**Beat 2 — The first cell of the grid showed the design was wrong.** `HumanEval/0`
× all 10 configs came back **10/10 PASS**, with a **58× cost spread** at the
prices of the day — 44× as the database stands now, after providers were pinned
and re-priced — for an identical outcome. That is saturation, visible on the very first purchase — and
it is what moved LiveCodeBench from "nice to have" to load-bearing.

**Beat 3 — The pilot changed the thesis.** 81% of pilot problems shared the same
cheapest-passing config. Routing was collapsing before the router was built. So
the thesis was **reframed in week 2** from *"build a router"* to *"measure when
reasoning is worth paying for"* — deliberately, because the measurement yields a
result either way. The router was built anyway, and it added +0.0, which
confirms the reframe was right rather than convenient.

**Beat 4 — The harness caught two things that would have been invisible.** The
macOS `setrlimit` bug, which was silently failing *every* solution including
known-correct ones. And the `config_id` bug, which attributed 8 purchased
generations to the wrong model. Neither was found by looking; both were found by
a check that had been built for exactly that purpose.

**Beat 5 — And then the data refuted my own headline.** The free abort threshold
was an artefact of my own token ceiling. I report it, because a truncation limit
is a censoring mechanism, and that lesson is worth more than the claim was.

**Closing line, if you need one:**

> The thesis is not the code and it is not the document. **It is the table** —
> and the fact that every rule in the repository exists to stop that table being
> quietly wrong. Twice it *was* quietly wrong. Both times, the checks caught it.

---

<a name="part-g"></a>

# Part G — Turning it into the document

**Nine chapters.** Chapters 3–7 are already *built* — the analysis exists and is
reproducible. What remains is prose.

| ch | Content | Status |
|---|---|---|
| 1 Introduction | The invisible cost of thinking; the 392-of-412 example; the question | write |
| 2 Background | Reasoning models, token pricing, code benchmarks, routing prior art | write |
| 3 Method | Harness, roster, pinning, grading, cost reconciliation, caps | built |
| 4 **Measurement validity** | The three platform findings — arguably the strongest chapter | built |
| 5 Results | Saturation, when thinking helps, waste, CPC | built |
| 6 The frontier | Hull, oracle, value of problem-level information | built |
| 7 Runtime abort | The refuted claim and the honest tradeoff curve | built |
| 8 Limitations | [Part E](#part-e), stated plainly | write |
| 9 Conclusion | When to pay for thinking; what to measure before trusting a benchmark | write |

**Start with Chapter 5, §1 (saturation).** It is the finding with the cleanest
evidence and the least ambiguity, so it is the cheapest chapter to write first,
and writing it teaches you the house style for the rest.

**Three writing rules, non-negotiable:**

1. **The caveat travels in the same paragraph as the finding.** Never headline
   first and qualify in a later section. Examiners read that as concealment.
2. **Every number carries its denominator**, in the sentence, not in a footnote.
3. **Figures get error bars** wherever an interval exists. A bare chart of these
   numbers implies precision the data does not have. The five PNGs in
   `data/figures/` already do this and are regenerated, never hand-edited.

**Fourteen edits are owed to the proposal `.docx`** — the full ordered list is in
[`docs/docx-revisions.md`](../docx-revisions.md). Four of them would be *actively
wrong* if left:

1. **The title and framing** — the router adds +0.0 points, so the thesis is a
   measurement study, not a router.
2. **The §3 gap analysis** — four closer works landed after the proposal.
3. **Every LiveCodeBench contamination claim** — the property does not hold.
4. **Add a measurement-validity section** — nothing equivalent exists in the
   proposal, and it is the most transferable material you have.

---

<a name="part-h"></a>

# Part H — Glossary, A to Z

| Term | Meaning |
|---|---|
| **Abort (runtime)** | Cancelling a call mid-stream once reasoning exceeds a threshold. Billed **$0.00** here, verified on two providers. |
| **Aggregator** | A service reselling many providers' models behind one API. OpenRouter. |
| **`atol`** | Absolute tolerance for comparing floating-point answers. Why grading is not `==`. |
| **Bootstrap** | Estimating uncertainty by resampling your own data with replacement, thousands of times. |
| **Budget forcing** | Faking an effort level by capping reasoning tokens. **Does not work here** — the parameter is ignored. |
| **Censoring** | Observing only that a value exceeded a cutoff, not the value. Your `max_tokens` ceiling censors reasoning length. |
| **Configuration / config** | One (model, thinking-setting) pair. You have 10. |
| **Contamination** | A benchmark problem was in the model's training data, so it recalls rather than solves. |
| **Convex hull** | The cost-accuracy frontier achievable by *mixing* configurations. The honest baseline for a router. |
| **CPC** | Cost Per Correct answer = Σ dollars ÷ Σ solved. Headline economic metric. |
| **Discriminating problem** | One that some configs solve and others do not. Only these carry signal — **141 of 320**. |
| **Dominated** | A config another config beats on *both* cost and accuracy. No rational strategy picks it. |
| **Effort / thinking mode** | How hard the model reasons. Binary in practice here: off / high. |
| **EvalPlus** | The library providing HumanEval+/MBPP+ problems, extended tests **and** the checker. |
| **Feature ceiling** | The best any router using only your features could do. **Fitted**, so optimistic. |
| **`finish_reason`** | Why generation stopped. `length` means it hit the ceiling — i.e. censored. |
| **Free features** | Features costing no API call: difficulty tier, test count, prompt length. |
| **Gap decomposition** | Splitting router→oracle into *feature insufficiency* (0.0) + *estimation error* (33.3). Your most original piece. |
| **Held-out model** | Kimi — never in the router's build set, so RQ5 tests transfer to an unseen model. |
| **k-NN** | Copy what worked for the *k* most similar known problems. No training. Cover & Hart (1967). |
| **LCB** | LiveCodeBench. Contest problems, easy/medium/hard, two execution styles. |
| **Leave-one-out CV** | Train on all problems but one, predict that one, repeat. Chosen because at n=60 a single split measures the split. |
| **MCKP** | Multiple-Choice Knapsack Problem. Pick one config per problem under a budget. The oracle is its integer optimum. |
| **Oracle** | A cheat that always picks the cheapest config that solves each problem. Upper bound, not a method. |
| **Paired problems** | The **107** problems with both effort arms graded. The only honest denominator for effort comparisons. |
| **Pareto frontier** | The non-dominated configs. |
| **pass@1** | Did one attempt pass all tests? Your accuracy metric. |
| **Provider** | The company actually serving the model. 18 of them serve one slug here. |
| **Quantization** | Compressing model weights (bf16 → fp8 → fp4). Cheaper and measurably worse. Held at **fp8 or better**. |
| **Reasoning tokens** | The invisible thinking, billed, a **subset of** completion tokens. |
| **`request_hash`** | UNIQUE fingerprint of a call. Makes a crashed run free to resume. |
| **Router** | Picks a config for an incoming problem *before* calling any model. |
| **Saturation** | A benchmark too easy to distinguish configs. HumanEval+, MBPP+ and LCB-easy are saturated. |
| **Token** | ~¾ of a word. The unit of everything, including the bill. |
| **TPC** | Tokens Per Correct answer. Price-independent twin of CPC. |
| **Value of problem-level information** | Oracle − hull at equal budget = **+13.8 points**. The headroom any router plays for. |
| **Wasted call** | Billed, but returned no usable answer. 49 of them, mean 29,584 reasoning tokens. |

---

<a name="part-i"></a>

# Part I — The numbers to know cold

If you memorise one page, this is it. (There is a printable version in
[`02-cheatsheet.md`](02-cheatsheet.md).)

| | |
|---|---|
| **The question** | Reasoning is billed but invisible. When is it worth paying for? |
| **Scale** | 320 problems × 10 configs = **1,373 generations**, 1,280 graded, **$5.24** |
| **Pool** | **884** problems: HumanEval+ 164, MBPP+ 378, LCB 342 (84/104/154 easy/med/hard) |
| **Headline (per model — lead with this)** | hard: `flash` **29.2%→82.1%** (+52.9) · `qwen3.6-35b` +5.5 · `qwen3.5-9b` **22.1%→3.8%** (−18.2, **81% censored**). MBPP+ `qwen3.5-9b` **80.0%→55.6%** (−24.4, **0% censored**) |
| **Headline (aggregate — qualify it)** | LCB hard **24.9% → 54.2%** (n=462/118) raw; **31.6% → 57.3%** (n=114/110) style-matched. Both average over opposite per-model effects |
| **Style confound** | hard `off` is 348 stdin/114 functional, `high` is 8/110. Matched gaps **+25.7** (hard), **+28.9** (medium). Frontier set is **51 functional / 2 stdin** |
| **Saturation (per tier)** | HumanEval+/MBPP+/LCB-easy at **72–100%** either arm — solid |
| **Saturation (per problem)** | **141/320 (44%)** discriminate as reported — but **coverage-dependent**: 66% at ≥1 thinking config, **82% at ≥6 configs**. 94 of the 98 "none solved" were never shown a thinking config |
| **Reasoning length** | 642 → 773 → 2,693 → 10,183 → **17,547** by tier |
| **Waste** | **49 calls, mean 29,584 tokens, $0.56** = 15% of reasoning spend, 11% of total |
| **Censoring** | **26.3%** of hard thinking calls truncate at 48k → 54.2% is a **floor** |
| **CPC spread** | **305×** across the roster · **228×** on the 22 shared problems · **65×** on the identical 60-problem exam. 5 adjacent pairs overlap |
| **Frontier** | `flash\|high` **98.3% at $0.00177**; `pro\|high` 95.0% at **6×** the cost — and an exact **tie, 64/68 each**, on the problems both sat |
| **Thinking token cost** | measured **4.3×** (3,166 → 13,604 mean completion tokens), not the ~10× estimated pre-data |
| **Oracle / hull** | **98.3% at $0.00111** vs **84.5%** → **+13.8 points** of headroom |
| **Router** | k-NN **65.0%** = the hull exactly. **+0.0.** Collapsed to 1 config. |
| **Decomposition** | feature insufficiency **0.0**, estimation error **33.3** |
| **Abort at 16k** | keeps **88%** [82,92] of solutions for **49%** [35,61] saving. No free threshold. |
| **The invisible bill** | **392 of 412** tokens on "reverse a string" |
| **Platform** | 18 providers, **$0.87–$3.48**/M; 9 providers in one run, **1.54×** the prediction |
| **Ignored budgets** | `max_tokens: 2000` → **13,731** reasoning tokens (6.9×) |
| **Free cancellation** | Aborted mid-reasoning: **$0.000000** vs **$0.010978** completed |
| **Denominators** | **107** paired problems · **60** problems × **6** configs · only **5** have all ten |
| **Tests** | **132** passing; **210** canonical solutions validate the grader |
| **$5.24 vs $5.25** | **$5.240216** is the database (1,373 stored generations) — use it for anything computed from the table. **$5.25** is total account spend, including exploratory calls never stored as rows. Both are correct; know which you are quoting. |

---

**Next:** the hostile examiner — [`01-question-bank.md`](01-question-bank.md).
