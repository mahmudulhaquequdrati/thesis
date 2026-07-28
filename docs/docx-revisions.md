# Revising the proposal `.docx` — what to change and why

Every number here is reproducible: `uv run python scripts/results.py`.
Supersedes the older list in THESIS.md §14, which predates the reframing and
several results that contradict it.

Work top-down. Edits **1–3 are structural** and change what the document is
about; the rest follow from them. If time is short, 1, 2, 3 and 12 are the ones
that would otherwise be actively wrong at submission.

---

## 1. ⚠️ The title and framing — the biggest edit

**Now:** *Cost-Aware Reasoning Routing (CARR) — a training-free router that
picks the cheapest (model, thinking-mode) pair that still solves the problem.*

**Change to something like:** *When is reasoning worth paying for? A cost
measurement of thinking modes in open-weight code generation.*

**Why.** The router does not work, and the data says so cleanly: a k-NN router
over free features reaches **65.0%**, which is *exactly* the convex hull — it
adds **+0.0 points** and collapses to one configuration. A thesis titled after
its method, where the method fails, spends its whole length apologising.

The measurement is what survives, and it is the stronger contribution anyway.
The router becomes one section reporting a negative-but-diagnostic result
(edit 9).

---

## 2. Research questions — rewrite the list

**Now:** RQ1–RQ5 built around building and evaluating a router.

**Change to:**

| | question | where answered |
|---|---|---|
| RQ1 | What predicts how long a model reasons? | difficulty, monotonically: 642 → 17,547 tokens |
| RQ2 | When is that reasoning wasted, and what does it cost? | 49 calls, 29,584 mean tokens, $0.56, no answer |
| RQ3 | Can waste be cut at runtime? | abort curve; no free threshold exists |
| RQ4 | Is there headroom for a router, and can one exploit it? | 13.8 points exist; a router captures 0 |

Keep RQ5 (held-out model) only if you report it as thin: kimi has 16–23
problems, which is not enough to conclude anything.

---

## 3. §3 Gap analysis — the most-owed rewrite

**Now:** positions the work as the first joint (model × effort) router, citing
RouteLLM, Universal Routing, Budget Guidance, AnytimeReasoner.

**Problem:** that analysis is ~12 months stale. Four closer works exist:

| work | what it already does |
|---|---|
| **Agent-as-a-Router / CodeRouterBench** (Jun 2026) | code routing, 8 backends, released 9,999-task × 8-model matrix with cost |
| **Route-To-Reason** (May 2025) | joint model *and* reasoning-strategy allocation under budget |
| **DART** (Jun 2026) | training-free adaptive thinking budgets, text-only API |
| **HRBench** (May 2026) | 6 models × 5 benchmarks incl. code, 12 switching settings |

**What to claim instead.** Do not claim a novel router. Claim the measurement
and the validity findings, and state the one concrete gap: **CodeRouterBench's
`model` column holds eight model names and nothing else — no effort axis, and
no reasoning-token column at all.** The quantity this thesis is about is the
quantity the nearest prior work does not record.

Also cite **When Routing Collapses** (Feb 2026) — it names the degenerate
outcome that this thesis then reproduces and diagnoses.

---

## 4. Add a new section: measurement validity

There is no equivalent section in the proposal, and this is arguably the most
transferable material in the thesis. Three platform behaviours that invalidate
naive measurement, all verified directly:

1. **Provider routing changes price *and* model.** One slug is served by 18
   providers at **$0.87–$3.48 per M output**. `GET /models` reports only the
   cheapest. Unpinned, one run was served by **nine different providers** and
   billed **1.54× the prediction**. Quantization varies fp4→bf16, so an unpinned
   evaluation compares *different models*.
2. **Advertised reasoning budgets are ignored.** `reasoning:{max_tokens:2000}`
   produced **13,731** reasoning tokens; `effort:"low"` produced 11,926. Both
   accepted without error, both listed in `supported_parameters`.
3. **`max_tokens` does not bind.** Observed 35,837 against a 16,000 ceiling and
   73,037 against 48,000.

Plus one that *enables* a method: **cancelling a stream mid-reasoning is billed
$0.00**, verified on two providers, with reasoning observable live via
`delta.reasoning`.

**The claim to make:** any evaluation of open-weight models through an
aggregator without provider pinning is confounded on both price and precision.

---

## 5. §6.1 Roster — five models, and say how they are pinned

- Remove GLM-5.1. State **five open-weight models across three families**, and
  acknowledge the within-family caveat (two DeepSeek, two Qwen).
- **Add the pinning method**: every model pins one provider *and* one
  quantization (fp8 or better) via `provider: {only: [tag]}`, with
  `allow_fallbacks: false`. Explain that this trades availability for
  reproducibility — a pinned provider that is down produces a failed call rather
  than a silently different, differently-priced result.
- Note prices are per-endpoint, not the `/models` headline.

## 6. §6.2 Problems — separate the pool from the run set

The current text conflates them. State:

- **Pool: 884** — HumanEval+ 164, MBPP+ 378, LiveCodeBench 342.
- **Run: 320 problems, 1,373 generations, $5.24.**
- Coverage is **uneven by design and by budget**: the no-reasoning arm covers
  320 problems, the thinking arm 51–104, the held-out model 16–23. Comparable
  statistics therefore use the **107-problem paired set**, and per-config `n` is
  reported on every row.
- Drop the old "MBPP 500 → 150, LCB 200 → 120" numbers entirely.

## 7. §6.2 / Methods — the second grading harness

LiveCodeBench needs execution the evalplus checker cannot do: **112 of its
problems are stdin→stdout programs and 63 are methods on a `Solution` class.**
And **LCB ships no canonical solutions**, so the harness is validated against
**hand-written reference implementations** rather than the benchmark's own.
Say both — a reader will otherwise assume one grader covers everything.

## 8. §6.3 Metrics — CPC and TPC with intervals

- Define CPC = Σcost ÷ Σsolved, TPC likewise in tokens.
- **Report bootstrapped 95% intervals.** CPC is a ratio estimator, therefore
  biased, and normally reported bare.
- Report the denominator with every figure.
- State that resampling is over **problems, not calls** — two calls on one
  problem are not independent.
- Say what the intervals revealed: **five adjacent config pairs overlap**, so
  their ordering is not established despite distinct point estimates.

## 9. §5.3 / results — the router section, rewritten as a negative result

- **CARR-oracle is the MCKP integer optimum**, not an ad-hoc ceiling.
- **The comparison baseline is the convex hull, not the best single config.**
  Include the proposition: an optimal non-adaptive budget-constrained strategy
  randomises between at most two configurations, so beating the best single
  config is nearly free.
- Report the result honestly: **oracle 98.3% at $0.00111/problem; hull at the
  same budget 84.5%; headroom 13.8 points; k-NN router captures 0.0 of it and
  collapses to one config.**
- Then the decomposition, which is the point: **feature insufficiency 0.0
  points, estimation error 33.3 points.** The free features are sufficient to
  reach the oracle; the estimator fails because the cheapest-solving label is
  dominated by one configuration. Name the fix — a cost-aware objective rather
  than modal-label classification.
- Caveat the ceiling: fitted over 12 buckets on 60 problems, so optimistic.

## 10. §8 Risks — three of them are no longer risks but results

- **Benchmark saturation: confirmed.** Only **141 of 320** problems
  discriminate; 81 are solved by everything and 98 by nothing. HumanEval+ and
  MBPP+ pass at 72–97% regardless of reasoning.
- **Routing collapse: confirmed.** Cite *When Routing Collapses*, then report
  reproducing it.
- **Budget: held.** $5.24 of a $15 balance, under a $6.00 self-imposed cap
  enforced in code on worst-case spend before each call.

## 11. Results to add — there were none before

- **Thinking more than doubles the pass rate on hard problems: 24.9% → 54.2%**
  (n=462/118); on medium 53.3% → 76.4%. On easy benchmarks it buys almost
  nothing. *The value of reasoning is conditional on difficulty.*
- **Cost per correct answer spans 305×**, $0.00021 to $0.06320.
- **The cheap model with thinking dominates the frontier model with thinking**:
  `flash|high` at 98.3% costs one sixth of `pro|high` at 95.0%. (Intervals
  overlap; report as suggestive.)
- **~15% of all spend bought calls that returned nothing.**

## 12. ⚠️ LiveCodeBench contamination — every mention must change

**The property does not hold.** LCB's newest problem is **2025-04-06**, the
dataset stopped updating **2025-06-05**, and every roster model is a **2026**
release. There is no post-cutoff window.

Rewrite every citation of LCB-as-contamination-control to LCB-as-difficulty-tier,
and state the exposure as a limitation, backed by the stored `release_date`
distribution. This is the edit most likely to be caught by an examiner if left.

## 13. Limitations — write this section properly

- Coverage uneven; comparable statistics rest on 60–107 problems.
- Several intervals overlap; directions are clearer than orderings.
- **Censoring: 26.3% of hard thinking calls still truncate at 48,000 tokens**,
  so the long-reasoning tail is a floor, not an estimate.
- Contamination uncontrolled (edit 12).
- **The effort axis is binary in practice**, not graded — `off` genuinely yields
  zero reasoning tokens, but graded effort levels do not bind (edit 4.2).
- One sample per problem at temperature 0; no within-cell variance measured.
- RQ2 overlaps existing overthinking work (ThoughtTerminator, SelfBudgeter,
  RecurGuard).

## 14. Include the self-refutation — do not quietly drop it

The pilot appeared to show a **free** abort threshold: stop at 10,000 reasoning
tokens, keep every solved problem, save 44%. **The full grid refuted it.** The
pilot ran under a 16,000-token ceiling; truncated calls cannot succeed, so the
ceiling manufactured the cliff. At 48,000, **56 calls above 10,000 reasoning
tokens succeeded**.

Report it. It demonstrates the general hazard — *a truncation limit is a
censoring mechanism, and censored observations bias any analysis of the
quantity being truncated* — and correcting your own headline is a strength.

What survives is an honest tradeoff: **abort at 16,000 keeps 88% of solutions
[82, 92] for 49% of the cost [35, 61]**.

---

## Figures to insert

Generated by `uv run python scripts/make_figures.py` into `data/figures/`:

| file | goes in |
|---|---|
| `01-effort-by-tier.png` | Results — the headline conditional finding |
| `02-reasoning-vs-outcome.png` | Results — long reasoning means failure |
| `03-frontier-and-hull.png` | The frontier section — hull, oracle, 13.8-point gap |
| `04-abort-tradeoff.png` | Runtime abort — the curve, with its CI band |
