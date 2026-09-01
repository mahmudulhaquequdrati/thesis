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
spans **305×**, from $0.00021 to $0.06320 — and **65×** even on the strictest
like-for-like set, where six configurations sat the identical 60-problem exam
(§3.4). That is the difference between a $50 and a $15,000 monthly bill for the
same work.

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
| Cost | **$5.24** — see the caveat below: only the 139 pilot calls were reconciled against OpenRouter's actual bill; the 1,224-call grid is priced from token counts × the pinned endpoint's contracted price |

Each cell is one API call: send the problem verbatim, extract the code, run it
against the benchmark's real test suite in a sandbox, record pass/fail, tokens,
reasoning tokens and dollars.

**⚠️ How the dollars were actually obtained — state this before it is asked.**
The schema stores two cost columns: `cost_computed_usd` (token counts × the
price table) and `cost_actual_usd` (`GET /generation`, OpenRouter's own bill).
Only **139 of 1,373 rows — 10.1% — have the actual figure, and all 139 are the
2026-07-25 pilot.** The **1,224-call grid was never reconciled**, so every
headline dollar figure is a computed one.

That is defensible, because the grid pinned one provider per model with
`allow_fallbacks: false`, which makes the endpoint's price contractual rather
than a routing lottery. But it is an **unverified assumption**, and the one
subset where verification was possible disagrees: on the 139 pilot rows,
**actual ran 1.354× computed overall**, and 2.16–2.51× on `deepseek-v4-pro`.

The honest reading is that the discrepancy is *evidence for the pinning finding*
rather than against the grid — the pilot ran **before** providers were pinned,
which is exactly why it was billed to whichever endpoint routing chose. But say
that as an argument, not as a verified fact.

**This is fixable for $0 and it is the highest-value remaining action.**
`runner.reconcile_costs()` exists, **1,207 of the 1,224 grid rows still carry an
`openrouter_gen_id`**, and `GET /generation` is free. The only risk is that
records five weeks old may have expired — in which case *that* becomes the
reportable limitation, and a stronger one than silence.

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

#### 🔴 And the aggregate hides a reversal — the effect is per *model*

Before the style confound below, a larger problem with the table above: it
averages over models whose responses to reasoning point in **opposite
directions**. Per (tier, model), on the arms with real coverage:

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

**"+29.3 points on hard" is an average over +52.9 on one model and −18.2 on
another.** Reasoning is not a property of the difficulty tier; it is a property
of the **(model, tier) pair**, and the correct headline says so.

The `censored` column separates two mechanisms that need different sentences:

1. **Non-termination.** `qwen3.5-9b|high` hits the 48,000-token ceiling on
   **81% of hard calls**, returns no code on 77%, and averages 24,826 reasoning
   tokens. Its −18.2 is mostly *the model failing to stop*, and partly a
   statement about our ceiling: `deepseek-v4-flash|high` censors at 11% on the
   same problems.
2. **Genuine degradation.** On MBPP+, `qwen3.5-9b|high` censors **0%**, reasons
   for a mean of **368** tokens, terminates normally — and still falls from
   16/20 to 10/18 on the **same 20 problems**. Every failure produced extracted
   code and failed on assertions. **That one is not measurement.** Enabling
   reasoning made easy problems harder for a small model.

The second is the cleaner result and the thesis had not isolated it: it is
overthinking observed directly, paired, with the truncation explanation ruled
out by the censoring column.

Reproduce: `scripts/results.py` (⚠ THE EFFECT IS PER MODEL) or
`analysis.within_model_effect()`.

⚠️ Note also that the easy-benchmark rows of the aggregate table are
**model-confounded**: the `high` arm on MBPP+ is 62% `qwen3.5-9b` and on
HumanEval+ 58%, against roughly 25% each in the `off` arm. So "MBPP+ 72.3% →
73.3%" is comparing a four-model average against a mostly-one-model average, and
should be replaced by the per-model rows.

#### ⚠️ But those two arms did not sit the same exam — the matched figures

LiveCodeBench ships two kinds of problem: **stdin→stdout** programs from AtCoder
and **`Solution`-class methods** from LeetCode. They are not equally hard, and
coverage of the two is wildly uneven between the effort arms. On the hard tier
the `off` arm is **348 stdin / 114 functional** and the `high` arm is
**8 / 110** — so the raw comparison above mixes a reasoning effect with a
composition effect.

**The cause is mechanical, not a design choice.** `runner.plan` orders cells by
`(expected_usd, problem_id)`. Within one configuration every cell has the same
expected cost, so the tiebreak is the problem id *as a string* — and
LiveCodeBench's LeetCode ids are numeric (`LiveCodeBench/3487`) while its
AtCoder ids begin with letters (`LiveCodeBench/abc374_a`). Digits sort before
letters, so **all 125 functional problems ran before any of the 217 stdin ones**,
and the expensive thinking arm stopped at the cost cap while still inside the
functional prefix.

Restricting to one style is the honest comparison, and it is free — a
re-analysis of rows already bought:

| tier | style | off | on | matched gap | raw gap |
|---|---|---|---|---|---|
| **hard** | functional | 31.6% (n=114) | **57.3%** (n=110) | **+25.7** | +29.3 |
| **medium** | functional | 49.1% (n=163) | **78.0%** (n=141) | **+28.9** | +23.0 |

**The finding survives, and the direction is unchanged on both tiers.** The raw
pair *overstates* the effect on hard by 3.6 points and *understates* it on
medium by 5.9. What must change is the wording: on hard function-style problems
reasoning raises the pass rate by a factor of **1.8**, not "more than doubles".
The stdin thinking arm is n=8 and n=7, which supports nothing at all — that gap
is the honest answer to "what does reasoning do on stdin problems?"

Reproduce with `scripts/results.py` (⚠ STYLE CONFOUND section) or
`analysis.style_matched_effect()`.

### 3.2 The easy benchmarks are saturated — but read the problem-level split carefully

The **per-tier** result is solid, because it is a pass rate: HumanEval+, MBPP+
and LiveCodeBench-easy sit at **72–100% whichever effort arm you read**. Those
benchmarks are too easy to study this question with, and anyone doing so should
say which subset of their benchmark carries the signal.

The **problem-level** split needs more care. Counted over all 320 problems:
81 solved by every configuration that ran, 98 by none, 141 discriminating.

**⚠️ But that split is largely a coverage artefact, and the honest version is
different.** Unanimity is trivially easier to reach with fewer voters, and
coverage here runs from 2 configurations per problem to 10: **206 of the 320
problems saw only two or three**, nearly always the three cheap `off` configs.

| coverage | n | all solved | none solved | discriminating |
|---|---|---|---|---|
| ≥ 1 configuration (as reported) | 320 | 81 (25%) | 98 (31%) | **141 (44%)** |
| ≥ 1 *reasoning-enabled* configuration | 108 | 33 (31%) | 4 (4%) | **71 (66%)** |
| ≥ 6 configurations | 73 | 11 (15%) | 2 (3%) | **60 (82%)** |

**Of the 98 problems "solved by nothing", 94 were never attempted by a single
reasoning-enabled configuration.** They saw only the cheap arm. Read at real
coverage the picture inverts: on problems actually measured across six or more
configurations, **82% discriminate**.

So the defensible claims are: *the easy benchmarks are saturated* (a pass rate,
unaffected), and *problems measured thinly look unanimous, which is a property
of the budget and not of the problems*. The claim that three quarters of the
pool carries no routing signal does **not** survive, and it should be dropped
rather than defended.

Reproduce with `scripts/results.py` or `analysis.discrimination_by_coverage()`.

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
usable, at a cost of $0.56 — 15% of everything spent on reasoning-enabled calls,
and 11% of all spend.** A model that thinks for very long is not working harder;
it is failing expensively.

**⚠️ And 76% of that waste is a single model.** Per model, share of thinking
calls that were billed and returned nothing:

| model | wasted / thinking calls | rate | mean reasoning | $ wasted |
|---|---|---|---|---|
| **`qwen3.5-9b`** | **37 / 99** | **37.4%** | 30,411 | $0.24 |
| `qwen3.6-35b-a3b` | 7 / 74 | 9.5% | 16,635 | $0.21 |
| `deepseek-v4-flash` | 3 / 73 | 4.1% | 48,000 | $0.03 |
| `deepseek-v4-pro` | 2 / 72 | 2.8% | 31,999 | $0.08 |
| `kimi-k2.6` | 0 / 22 | 0.0% | — | $0.00 |

So "expect 15% of your reasoning spend to buy nothing" is the wrong advice to
hand anyone. **Non-termination is a property of the small model, not of
reasoning:** about a third of `qwen3.5-9b`'s thinking calls returned nothing,
against roughly one in twenty-five of `deepseek-v4-flash`'s. That is the same
story `within_model_effect()` tells about the sign reversal, and it makes the
practitioner rule sharp instead of average.


### 3.4 Cost per correct answer spans two orders of magnitude

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

**⚠️ The 305× headline is not like-for-like, and must never be quoted without
its denominator.** `paired_problems` guarantees each *row* has both effort arms
graded; it does not guarantee two rows share the same problems. Coverage inside
the paired set runs from n=16 to n=107, and the tier mix moves with it —
`deepseek-v4-pro | off`, for instance, sits mostly on the easy benchmarks. So
the cheapest and dearest rows sat **different exams**, and their ratio mixes a
price difference with a difficulty difference. Three honest figures, all
printed by `scripts/results.py`:

| comparison | denominator | spread |
|---|---|---|
| cheapest vs dearest config | different problem sets, n=107 and n=22 | **305×** |
| the same two configs | the **22** problems they actually share | **228×** |
| all six frontier configs | the **same 60** problems | **65×** |

All three are large, so the claim *"cost per correct answer varies by orders of
magnitude"* is robust. The specific number is not interchangeable between them.

### 3.5 The expensive model is not worth its price

On the 60 problems where six configurations were all measured, the cost-accuracy
hull has **only two vertices**: `flash|off` ($0.00016/problem, 65.0%) and
`flash|high` ($0.00177, 98.3%). Everything else is dominated — including

> **`deepseek-v4-pro | high`, which costs 6× more than `flash | high` and shows
> no measurable accuracy advantage.**

On the frontier set it is 57/60 against `flash|high`'s 59/60. On the **68
problems the two actually share** it is an exact **tie, 64/68 each**. So do not
claim "3 points less" — claim the stronger and safer thing: *at roughly six
times the price, the frontier model was not measurably more accurate, and on
the problems both sat it was exactly as accurate.*

Reproduce the tie:

```python
from carr import analysis, db
c = db.connect()
names = {v: k for k, v in analysis._config_names(c).items()}
a = names[("deepseek/deepseek-v4-flash", "high")]
b = names[("deepseek/deepseek-v4-pro", "high")]
shared = analysis.common_problems(c, [a, b])          # 68 problems
per = analysis._per_problem_config(c, shared)
for cid in (a, b):
    rows = [r for r in per[cid] if r["problem_id"] in set(shared)]
    print(cid, sum(r["solved"] for r in rows), "/", len(rows))
```

The cheap model with thinking beats the expensive model with thinking. (Caveat:
the accuracy intervals overlap, [95,100] vs [88,100], so the *direction* is
suggestive rather than established.)

**⚠️ And those 60 problems inherit the style skew.** They are **51 functional
and 2 stdin** LiveCodeBench problems, plus 7 from the easy benchmarks — every
one of their 19 hard problems is function-style, against a pool hard tier that
is 117 stdin to 37 functional. So the frontier, the hull, the oracle and the
router below all describe **function-style problems**, not the hard tier at
large. `flash|high`'s 98.3% is an accuracy on LeetCode-style completions and
should be labelled that way.

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

### 3.7 A router cannot exploit that headroom — and we can say why

A k-NN router over the free features (difficulty, test count, prompt length),
evaluated leave-one-out, reaches **65.0%** — **exactly the convex hull**, adding
**nothing**. It collapsed to a single configuration.

The gap decomposition (§10.2) locates the fault:

| | |
|---|---|
| oracle, needs the answers | 98.3% |
| ceiling from these features alone | **98.3%** |
| k-NN actually achieves | **65.0%** |
| **feature insufficiency** | **0.0 points** |
| **estimation error** | **33.3 points** |

**The features are sufficient; the estimator is not.** The cheapest-solving
label is dominated by one configuration, so a nearest-neighbour vote predicts it
everywhere — the collapse is a property of the *objective*, not the inputs. The
fix is a cost-aware objective rather than modal-label classification, and that
is a concrete piece of future work rather than a shrug.

A negative result that says *which direction to fix* is worth more than a
marginal positive one. (Caveat: the feature ceiling is fitted over 12 buckets on
60 problems, so it is an optimistic bound.)

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
- **Not an observation of reasoning — only of its token count.** The harness
  stores `choice.message.content` as `raw_response`; `choice.message.reasoning`
  is never read and no column holds it. So `reasoning_tokens` is a **vendor
  annotation** that nothing in the pipeline can check, and the traces behind the
  headline numbers do not exist: the call that burned 73,037 reasoning tokens
  left an 18KB block of code and an integer. The overthinking finding therefore
  cannot be inspected, only counted — and unlike an extraction bug this is not
  fixable offline.
- **Not a tier-level story.** The effect of reasoning differs in *sign* between
  models on the same tier, so aggregate off-vs-on rows average opposite effects
  and should not be quoted as findings. The per-model table is the reportable
  one, and even it rests on 18–36 thinking calls per cell.
- **Not evenly covered.** Coverage runs from 2 configurations per problem to 10,
  and 206 of the 320 problems saw only two or three. Any statistic that counts
  *unanimity* across configurations — the 81/98/141 split — is therefore a
  statement about the budget as much as about the problems, and is reported at
  several coverage cuts rather than bare.
- **Not style-balanced.** LiveCodeBench's stdin and function-style problems are
  covered very unevenly by the thinking arm (n=8 vs n=110 on hard), because the
  runner's `problem_id` tiebreak ran every LeetCode problem before any AtCoder
  one. Every comparison is therefore reported *within* a style, and the frontier
  set is 51 functional to 2 stdin. Nothing here says what reasoning does on
  stdin-style problems.
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
> $5.24, this thesis measures when that expenditure is justified. The value of
> reasoning turns out to be a property of the (model, difficulty) pair rather than
> of difficulty alone: on hard problems it moves one model from 29.2% to 82.1%
> and another from 22.1% down to 3.8%, the latter because it fails to terminate
> on 81% of its calls. On easy problems a small model paired against itself over
> the same twenty problems falls from 80.0% to 55.6% with reasoning enabled and
> no truncation at all — overthinking, measured directly. The standard benchmarks
> are saturated at 72–100% whichever effort arm is read. Cost per correct answer
> spans 305×
> across the roster and 65× on an identical exam,
> and 15% of all spending on reasoning-enabled calls bought no answer at all after
> reasoning for an average of 29,584 tokens. A cheap model with reasoning enabled
> dominates a frontier model with reasoning enabled, at one sixth the price.
> Problem-level information is worth 13.8 accuracy points against a
> problem-blind mixture at equal budget. Along the way, three platform behaviours
> are documented that invalidate naive measurement: provider routing that varies
> price 4× and quantization silently, reasoning-budget parameters that are
> accepted and ignored, and token ceilings that do not bind — and one that
> enables a new control, since cancelling a reasoning stream is billed nothing.
