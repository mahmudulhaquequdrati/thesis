# Thesis re-positioning — one page for my advisor

**Mahmud Qudrati · 2026-07-25 · CARR (Cost-Aware Reasoning Routing)**

## Summary

While setting up the experimental harness I ran a fresh literature check and found
four papers, three of them from 2026, that sit much closer to my proposal than the
four works my Section 3 gap analysis is built on. My central novelty claim as
written is no longer defensible. **I am not proposing to change topic** — the
empirical contribution is unaffected — but the framing needs revising, and I would
rather do that in Week 1 than have it surface at the defence.

## What I claimed

> "No existing method performs pre-inference, feature-only, joint (model × effort)
> routing for code generation." — Proposal §3

Positioned against RouteLLM (ICLR 2025), Universal Routing (2025), Budget Guidance
(ACL 2026), AnytimeReasoner (NeurIPS 2025).

## What I found

| Work | Overlap with my claim |
|---|---|
| **Route-To-Reason** (arXiv 2505.19435) | "Dynamically allocates **both language models and reasoning strategies** according to task difficulty under budget constraints." This is the joint (model × effort) claim — and it predates my proposal |
| **DART** (arXiv 2606.23181, Jun 2026) | "**Training-free** adaptive thinking budgets", explicitly compatible with text-only API access. This is my training-free, provider-agnostic angle |
| **HRBench** (arXiv 2605.28398, May 2026) | Benchmarks thinking-mode switching across 6 models × 5 benchmarks **including code**, with released data. Covers much of my RQ1–RQ3 |
| **LLMRouterBench** (arXiv 2601.07206, Jan 2026) | 33 models, 21 datasets, 400k instances. **Explicitly excludes reasoning effort as a routing axis** — supports my framing rather than threatening it |

## What survives, and my proposed new claim

Every published router is treated as if it were free to run. None of them are:

| Router | Cost of one routing decision |
|---|---|
| DART | Generates draft answers — **real tokens on every query** |
| Route-To-Reason | Requires a training phase |
| Budget Guidance | Needs hidden-state access at every decoding step |
| **CARR (mine)** | A k-NN lookup over cached features — **microseconds, $0** |

So my proposed re-framing:

> **Routers occupy a spectrum from free to expensive. What do you give up by
> choosing the free end?**

Concretely, I would report **total cost = routing overhead + inference cost**, which
to my knowledge no routing paper currently does. This turns the apparent weakness of
my method (CARR is "just" a lookup table) into the actual finding: CARR can lose on
routing *accuracy* and still win on *total* cost. None of the papers above can make
this argument, because honest accounting works against them.

It is also methodologically continuous with the thesis's own theme — a Pareto
analysis, applied to the routers themselves rather than to the models.

## Two further corrections I intend to make

1. **The RQ4 baseline is too weak.** I compare CARR against "the strongest single
   configuration". If randomised routing is permitted, the achievable set is the
   *convex hull* of the configuration points, and the budget-constrained optimum is
   a mixture of at most two configurations — which beats any single config at most
   budgets. I will compare against the hull instead. (RouterBench already evaluates
   this way, so it is standard practice rather than an innovation on my part.)

2. **Benchmark saturation is a live risk.** If the cheapest configuration already
   passes ~90% of HumanEval+/MBPP, the routing target degenerates to "always route
   cheap". *When Routing Collapses* (arXiv 2602.03478, Feb 2026) names exactly this
   failure. I will weight the problem mix toward LiveCodeBench and report
   per-difficulty breakdowns, so the effect is a finding rather than an artefact.

## What is unchanged

The empirical contribution stands regardless of framing: **no published dataset
records per-problem reasoning-token cost across a (model × thinking-mode) grid on
code generation.** I still have to generate that table, and it is still mine. The
harness, the experiment grid, and the analysis plan are unaffected.

## What I would like from you

1. Agreement that re-positioning is the right call, rather than changing topic.
2. A view on the total-cost framing — is that a strong enough contribution for the
   thesis to rest on?
3. Whether Section 3 should be rewritten now or at the end of the empirical phase.

## Status

Harness scaffolding is done; model roster verified against live pricing; first API
calls made. Data collection can start immediately and does not depend on the
outcome of this conversation.
