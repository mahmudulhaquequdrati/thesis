# Thesis update for my advisor — 2026-07-26

**Original title:** *Cost-Aware Reasoning Routing (CARR): a training-free router
that picks the cheapest (model, thinking-mode) pair that still solves a problem.*

**What I am asking you:** whether to keep that framing, or adopt the reframing
in §4. I have pilot data that argues against the original and for the new one,
and I would rather change direction now than after spending the budget.

Total spent so far: **$0.58**. Remaining: $14.42.

---

## 1. What is built and working

A complete measurement harness, tested (77 tests):

* 884 problems loaded — HumanEval+ (164), MBPP+ (378), LiveCodeBench (342: 154 hard, 104 medium, 84 easy)
* 10 configurations — 5 open-weight models × reasoning off/on, via OpenRouter
* Sandboxed grading for both benchmark families (LiveCodeBench needed a second
  execution path: stdin/stdout programs and `Solution`-class methods)
* A cost cap that aborts before spending, dedup so nothing is ever bought
  twice, and a local database browser

## 2. Why the original framing is in trouble

**Routing collapses.** Across the pilot, **13 of 16 problems share the same
cheapest-passing configuration** (`deepseek-v4-flash`, reasoning off). A router
that always answered that would score 81%. This is the degenerate outcome
described in *When Routing Collapses* (Feb 2026).

**The benchmarks are saturated.** Pass rates, reasoning off / on:

| tier | off | on | usable? |
|---|---|---|---|
| HumanEval+ | 90% | 100% | no signal |
| MBPP+ | 93% | 100% | no signal |
| LiveCodeBench easy | 100% | 100% | no signal |
| LiveCodeBench medium | 60% | 50% | yes |
| LiveCodeBench hard | 50% | 31% | yes |

**76% of the problem pool produces no routing signal at all.**

**The prior art closed in.** Agent-as-a-Router / CodeRouterBench (Jun 2026)
released a 9,999-task × 8-model result matrix for code routing. DART does
training-free thinking budgets. Route-To-Reason does joint model-and-effort
allocation. My remaining niche was narrow.

## 3. Four findings the pilot produced anyway

These are measurement results that hold regardless of framing.

**(a) Reasoning length scales with difficulty, monotonically.**
963 → 2,955 → 7,009 → 9,449 mean reasoning tokens across easy benchmarks →
LCB easy → medium → hard.

**(b) Reasoning length predicts failure.** Calls that *pass* average **2,333**
reasoning tokens. Calls that return **nothing** average **11,878**. All 11
billed non-answers produced zero usable code while being charged in full —
**17% of total spend bought nothing**.

**(c) The platform advertises controls it does not enforce.** Two instances:

* *Provider routing.* One model slug is served by 18 providers at $0.87–$3.48
  per M output. `GET /models` reports only the cheapest. Unpinned, one pilot
  run was served by nine different providers and billed **1.54× my prediction**.
  Quantization also varies silently, fp4 to bf16 — so an unpinned evaluation
  compares models of differing fidelity.
* *Reasoning budgets.* `reasoning: {max_tokens: 2000}` produced **13,731**
  reasoning tokens (6.9× over); `effort: "low"` produced 11,926. Both accepted
  without error, both listed in `supported_parameters`. Silent non-compliance.

**(d) Aborting a reasoning stream is billed $0.00.** Verified on two providers.
`delta.reasoning` is observable live, so the abort can be triggered on a token
threshold mid-generation. The same cell run to completion cost $0.011.

## 4. Proposed reframing

> **When is reasoning worth paying for, and can you tell before you have paid?**

| | question | evidence |
|---|---|---|
| RQ1 | What predicts how long a model reasons? | (a) — difficulty, monotonic |
| RQ2 | When is that reasoning wasted? | (b) — length predicts failure |
| RQ3 | Can waste be cut at runtime? | (d) — abort works, costs $0 |
| RQ4 | Can a cheap router beat the frontier? | demoted to one section |

Simulated on pilot data, aborting at **10,000 reasoning tokens keeps 42 of 42
solved problems and cuts spend 44%**. At 6,000: 78% saved for 10% fewer solved.
**The tradeoff curve is the deliverable, and it exists whether or not any
router works** — which is the main reason I prefer this framing.

Note (c) forecloses the obvious objection: you cannot simply instruct these
models to think less, so runtime monitoring is not a redundant mechanism.

## 5. Honest limitations

* **Sample size: 15 problems, 59 thinking calls.** Everything above is
  direction, not estimate. The full grid — 318 problems, 2,744 cells, priced
  at **$4.59** — fixes this and fits the remaining budget.
* **The 10,000-token threshold held because nothing above it succeeded here.**
  That is exactly the kind of result that regresses with more data, and it is
  the main scientific risk.
* **LiveCodeBench is not contamination-controlled for us.** Its newest problem
  is 2025-04-06, it stopped updating 2025-06-05, and every model on the roster
  is a 2026 release. There is no post-cutoff window available, so LCB enters as
  a difficulty tier and contamination is reported rather than eliminated.
* **The effort axis is binary in practice**, not graded — see (c).
* **RQ2 overlaps existing work** on overthinking (ThoughtTerminator,
  SelfBudgeter, RecurGuard). RQ3's economic framing and the $0-abort mechanism
  are the parts I believe are less covered, but I have not verified that
  exhaustively.

## 6. Questions for you

1. Is the reframing in §4 acceptable, or should I stay with routing?
2. Is the overlap in §5 a problem at undergraduate level, or is careful
   measurement with honest limitations sufficient?
3. Finding (c) is arguably a methodology contribution in its own right —
   published open-weight evaluations that route through an aggregator without
   pinning are comparing different quantizations at different prices. Worth a
   section, or a footnote?
4. Should I spend the remaining budget widening the problem set further (more
   LiveCodeBench releases are free to download) before running the full grid?

---

*Reproduce any number above with `uv run python scripts/results.py` (free,
read-only). The harness, data and this document are version-controlled.*
