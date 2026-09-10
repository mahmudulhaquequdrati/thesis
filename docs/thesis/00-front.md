---
title: "When Is Reasoning Worth Paying For?"
subtitle: "A Cost Measurement of Thinking Modes in Open-Weight Code Generation, and the Headroom Left for Cost-Aware Reasoning Routing (CARR)"
author: "Mahmud Qudrati"
date: "Draft assembled 2026-09-11 from data/carr.sqlite (snapshot of 2026-07-26)"
lang: en
---

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Front matter {.unnumbered}

## Declaration of originality {.unnumbered}

I declare that this thesis is my own work. The experimental design, the decisions recorded in the project log, the interpretation of the results and the claims made here are mine. Every number in this document regenerates from the project database with a single free command (`uv run python scripts/results.py`) under a fixed random seed, and the figures are produced by `scripts/make_figures.py` from the same database and are never edited by hand. Where a claim rests on a source I have not read in full, it is marked as such in Appendix I.

## Declaration on the use of generative AI {.unnumbered}

An AI coding assistant (Claude, by Anthropic) was used throughout this project for drafting and reviewing code, drafting and editing prose, summarising literature, and acting as a hostile reviewer of the draft. Its use is visible in the repository: the file `CLAUDE.md` records the working rules it was given, and 38 of the 39 commits at the time of writing carry a `Co-Authored-By: Claude` trailer. The research question, the budget and roster decisions, the choice to reframe the thesis after the pilot, and the interpretation of every result are my own. I verified the reported figures against the output of the analysis script rather than against any generated text. The analysis code is covered by 132 automated tests, and all raw model responses are stored so that any grading step can be re-run without new purchases. This declaration will be checked against the department's regulations before submission; some institutions require a specific form of words or an appendix of prompts.

## Abstract {.unnumbered}

Reasoning models can "think" before they answer. That thinking is billed as output tokens but is usually hidden from the user, so the cost of a call cannot be read from its answer: on the first call of this project, 392 of 412 billed tokens were invisible reasoning. No published dataset records, for code generation, whether enabling that reasoning was worth its price. This thesis builds and analyses that table. Five open-weight models were each run with reasoning off and on (ten configurations) over 320 problems from HumanEval+, MBPP+ and LiveCodeBench, producing 1,373 real API calls (1,280 graded) for $5.24, with every call graded by execution against the benchmarks' hidden tests, its reasoning-token count recorded, and its cost priced at a pinned provider's contracted rate.

Four results follow. First, the value of reasoning is a property of the (model, difficulty) pair, not of difficulty alone: on hard problems it lifts `deepseek-v4-flash` from 29.2% to 82.1% and drops `qwen3.5-9b` from 22.1% to 3.8%, and on easy problems the same small model, paired against itself on the same twenty problems with no truncation, falls from 80.0% to 55.6%. Second, long reasoning signals failure rather than effort: 49 calls averaged 29,584 reasoning tokens and returned nothing usable, 15% of the reasoning arm's spend, and three quarters of those calls came from one model. Third, cost per correct answer spans 65× even across six configurations on an identical 60-problem exam, and the cheap model with reasoning enabled ties the frontier model with reasoning enabled at one sixth of the price. Fourth, knowing the problem before choosing a configuration is worth 13.8 accuracy points at equal budget, but a training-free nearest-neighbour router over free features captures none of it, and a gap decomposition locates the failure in the estimator rather than the features.

Along the way the thesis documents three behaviours of commercial model aggregators that silently invalidate careless measurement (provider routing that changes price and quantization, reasoning-budget parameters that are accepted and ignored, and token ceilings that do not bind) and one that enables a new control (cancelling a stream mid-reasoning is billed nothing). It also reports the refutation of its own pilot headline: an apparently free reasoning-length abort turned out to be an artefact of the project's own token ceiling. The contribution is the measured table, the findings with their uncertainty, and the methodology.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
