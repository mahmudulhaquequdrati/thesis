# The thesis as research — what it asks, what it found, what it contributes

Written 2026-07-27, after the grid. Every number here comes from
`uv run python scripts/results.py` and is reproducible from `data/carr.sqlite`.

This document exists because the code and the science drifted apart during the
build. It states the research plainly: the question, why it is a question, what
was measured, what was found, what the contribution honestly is, and what it is
not.

---

## 1. The question

> **Reasoning models can "think" before answering. That thinking is billed but
> invisible. When is it worth paying for?**

That is the whole thesis in one sentence.

### Why it is a real question and not a made-up one

**The cost is invisible.** A reasoning model emits *reasoning tokens* that never
appear in its answer but appear on the bill. Day 1 of this project measured a
trivial "reverse a string" prompt: **392 of 412 completion tokens were
reasoning.** The visible answer was three lines. Anyone pricing from the
response text would understate that call ~20×.

**The stakes are large.** Across this project's roster, cost per correct answer
spans **305×**, from $0.00021 to $0.06320. That is the difference between a
$50 and a $15,000 monthly bill for the same work.

**Nobody can tell you when to turn it on.** The practitioner question — *should
I enable thinking for this task?* — has no measured answer for code generation
with real prices attached.

---

## 2. What was measured

| | |
|---|---|
| Problems | 320 (of an 884 pool: HumanEval+, MBPP+, LiveCodeBench) |
| Configurations | 10 = 5 open-weight models × reasoning off/on |
| Generations | **1,373**, of which 1,280 graded |
| Cost | **$5.24**, every call priced from OpenRouter's actual bill |

Each cell is one API call: send the problem verbatim, extract the code, run it
against the benchmark's real test suite in a sandbox, record pass/fail, tokens,
reasoning tokens and dollars.

**The unit of analysis is the *problem*, not the call.** Two calls on the same
problem are not independent observations of difficulty, so every confidence
interval resamples problems.

---

## 3. What was found

### 3.1 Thinking works — decisively, and only where it is needed

Pass rate, reasoning off vs on:

| tier | off | on | n (off / on) |
|---|---|---|---|
| HumanEval+ | 92.9% | 97.0% | 85 / 33 |
| LiveCodeBench easy | 94.1% | 100% | 68 / 11 |
| MBPP+ | 72.3% | 73.3% | 83 / 30 |
| **LiveCodeBench medium** | **53.3%** | **76.4%** | 317 / 148 |
| **LiveCodeBench hard** | **24.9%** | **54.2%** | 462 / 118 |

**On hard problems, thinking more than doubles the pass rate.** On the easy
benchmarks it buys almost nothing, because those are already saturated.

This is the answer to the headline question, and it is not trivial: it says the
value of reasoning is *conditional on difficulty*, and the condition is sharp.

### 3.2 Most benchmark problems cannot answer the question at all

Of 320 problems: **81 are solved by every configuration, 98 by none, and only
141 discriminate.** A problem everything solves and a problem nothing solves are
equally uninformative — neither can distinguish a good decision from a bad one.

That is a finding about *benchmarks*, not models: **HumanEval+ and MBPP+ are
too easy to study this question with.** Anyone doing so should say which subset
carries their signal.

### 3.3 Reasoning length tracks difficulty, and predicts failure

Mean reasoning tokens rise monotonically with difficulty — 642 (MBPP+), 773
(HumanEval+), 2,693 (LCB easy), 10,183 (LCB medium), **17,547 (LCB hard)**.

And length predicts outcome:

| outcome | n | mean reasoning tokens | spend |
|---|---|---|---|
| passed | 242 | 7,567 | $2.52 |
| failed | 49 | 7,577 | $0.55 |
| **billed, no answer at all** | **49** | **29,584** | **$0.56** |

**49 calls burned an average of 29,584 reasoning tokens and returned nothing
usable, at a cost of $0.56 — about 15% of everything spent.** A model that
thinks for very long is not working harder; it is failing expensively.

### 3.4 Cost per correct answer spans 305×

Over the 107 problems where both effort arms were measured:

| config | CPC | 95% CI |
|---|---|---|
| deepseek-v4-flash \| off | **$0.00021** | [0.00015, 0.00028] |
| deepseek-v4-flash \| high | $0.00193 | [0.00150, 0.00238] |
| deepseek-v4-pro \| high | $0.01224 | [0.00930, 0.01581] |
| kimi-k2.6 \| high | **$0.06320** | [0.03940, 0.09324] |

**Five adjacent pairs have overlapping intervals**, so their ordering is *not*
established despite different point estimates. Reporting these bare — which is
the norm — would have manufactured a ranking that the data does not support.

### 3.5 The expensive model is not worth its price

On the 60 problems where six configurations were all measured, the cost-accuracy
hull has **only two vertices**: `flash|off` ($0.00016/problem, 65.0%) and
`flash|high` ($0.00177, 98.3%). Everything else is dominated — including

> **`deepseek-v4-pro | high`, which costs 6× more than `flash | high` for 3
> points *less* accuracy.**

The cheap model with thinking beats the expensive model with thinking. (Caveat:
the accuracy intervals overlap, [95,100] vs [88,100], so the *direction* is
suggestive rather than established.)

### 3.6 There is real headroom for routing — 13.8 points

An **oracle** that always picks the cheapest config solving each problem reaches
98.3% at $0.00111/problem. A **problem-blind mixture** with the same money
reaches only 84.5%.

**That 13.8-point gap is the measured value of knowing something about the
problem before choosing.** It is the honest ceiling for any router.

Why the *hull* and not "the best single model": if you may split traffic between
two configurations, everything on the line between them is achievable. So
beating the best single config is nearly free and proves little — the real bar
is beating the mixture.

---

## 4. What the contribution honestly is

### 4.1 The table itself

Nobody has published *(model × thinking-mode → pass/fail, reasoning tokens,
dollars)* for code generation. The nearest work, **CodeRouterBench**
(Agent-as-a-Router, Jun 2026), releases 9,999 tasks × 8 models with cost — but
its `model` column holds eight model *names* and nothing else. **It has no
effort axis and no reasoning-token column at all.** The thing that makes this
question answerable is the thing it does not record.

### 4.2 Three ways the platform lies, and one way it helps

These are measurement-validity findings, and they generalise beyond this thesis:

1. **Provider routing silently changes both price and model.** One model slug is
   served by 18 providers at $0.87–$3.48 per M output. `GET /models` reports only
   the cheapest. Unpinned, one run here was served by **nine different
   providers** and billed **1.54× the prediction**. Quantization varies too —
   fp4 to bf16 — so an unpinned evaluation is comparing *different models*.
2. **Advertised reasoning budgets are ignored.** `reasoning: {max_tokens: 2000}`
   produced **13,731** reasoning tokens; `effort: "low"` produced 11,926. Both
   accepted without error, both listed in `supported_parameters`. You cannot
   simply ask these models to think less.
3. **`max_tokens` is not a hard bound.** Observed 35,837 tokens against a 16,000
   ceiling, and 73,037 against 48,000.
4. **Cancelling a stream mid-reasoning is billed $0.00** (verified on two
   providers). Reasoning is observable live via `delta.reasoning`, so a runtime
   abort is a real mechanism, not a thought experiment.

Any study benchmarking open-weight models through an aggregator without pinning
is confounded on both price and precision. That is worth saying out loud.

### 4.3 A refutation of my own headline

The pilot appeared to show a **free** abort threshold: stop at 10,000 reasoning
tokens, keep every solved problem, save 44%. The full grid destroyed it.

The pilot ran with a 16,000-token ceiling. Truncated calls *cannot* succeed, so
the ceiling manufactured the cliff the claim depended on. At 48,000, **56 calls
above 10,000 reasoning tokens succeeded**, and the analysis now correctly
reports *"no threshold saves money without losing a solved problem."*

Catching and reporting that is better science than the original claim would have
been. It is also a concrete instance of a general hazard: **a truncation limit
is a censoring mechanism, and censored observations bias any analysis of the
thing being truncated.**

---

## 5. What this is NOT — state these before an examiner does

- **Not a new routing algorithm.** Route-To-Reason, DART and CodeRouterBench
  already occupy that space. RQ4 here measures the *headroom* a router would
  have, and stops there.
- **Not novel on overthinking.** ThoughtTerminator, SelfBudgeter and RecurGuard
  already study reasoning that fails to terminate. The economic framing —
  dollars per correct answer, across a price-varying roster — is the part that
  is less covered.
- **Not contamination-controlled.** LiveCodeBench stopped updating in 2025 and
  every model on the roster is a 2026 release, so there is no post-cutoff
  window. LCB is used as a *difficulty* tier and the exposure is reported.
- **Not fully powered.** 60–107 problems underpin the comparable statistics, and
  several intervals overlap. Directions are clear; individual orderings often
  are not.
- **Not free of censoring.** 26.3% of hard thinking calls still truncate at
  48,000 tokens, so the long-reasoning tail is a floor, not an estimate.

---

## 6. How this becomes a thesis

| chapter | content | status |
|---|---|---|
| 1 Introduction | The invisible cost of thinking; the 392-of-412 example | write |
| 2 Background | Reasoning models, token pricing, code benchmarks, routing prior art | write |
| 3 Method | Harness, roster, grading, provider pinning, cost reconciliation | **built** |
| 4 Measurement validity | The three platform findings (§4.2) — arguably the strongest chapter | **built** |
| 5 Results | §3.1–3.4: when thinking helps, saturation, waste, CPC | **built** |
| 6 The frontier | §3.5–3.6: hull, oracle, value of information | **built** |
| 7 Runtime abort | §4.3: the refuted claim and the honest tradeoff curve | **built** |
| 8 Limitations | §5, stated plainly | write |
| 9 Conclusion | When to pay for thinking, and what to measure before trusting a benchmark | write |

**The analysis is done. What remains is prose, figures, and the `.docx` edits in
THESIS.md §14.**

---

## 7. The one-paragraph version

> Reasoning models bill for tokens the user never sees. Across 1,373 graded
> generations on 320 code problems and 10 model/thinking configurations, costing
> $5.24, this thesis measures when that expenditure is justified. Thinking more
> than doubles the pass rate on hard problems (24.9% → 54.2%) and buys almost
> nothing on standard benchmarks, which are saturated: only 141 of 320 problems
> distinguish one configuration from another. Cost per correct answer spans 305×,
> and 15% of all spending bought calls that returned no answer at all after
> reasoning for an average of 29,584 tokens. A cheap model with reasoning enabled
> dominates a frontier model with reasoning enabled, at one sixth the price.
> Problem-level information is worth 13.8 accuracy points against a
> problem-blind mixture at equal budget. Along the way, three platform behaviours
> are documented that invalidate naive measurement: provider routing that varies
> price 4× and quantization silently, reasoning-budget parameters that are
> accepted and ignored, and token ceilings that do not bind — and one that
> enables a new control, since cancelling a reasoning stream is billed nothing.
