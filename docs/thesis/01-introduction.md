# Introduction

## The hook

On the first day of this project, a single request was sent to a small open-weight reasoning model through a commercial API: *"Write a Python function that reverses a string. Return only the code."* The visible answer was three lines. The bill said the model had produced 412 completion tokens. Of those, 392 were *reasoning tokens*: an internal monologue the model wrote before answering, which the API charged for and never showed.

That one measurement is the whole motivation. A token is the unit in which language models read, write and bill, roughly three quarters of an English word. If 95% of a call's billed output is invisible, then nobody can price a reasoning model from what it returns, and nobody who has not measured it can say when the extra spending is justified.

## The problem

Modern open-weight models such as DeepSeek V4, Qwen 3.5/3.6 and Kimi K2.6 expose a switch: reasoning off, or reasoning on at some "effort". With reasoning on, the model writes a long private scratchpad, trying approaches and checking itself, and only then writes the answer. The scratchpad is billed as output. Providers typically hide or summarise it.

For a practitioner running code generation at scale, the question is therefore practical and unanswered: *for this kind of task, should I turn thinking on?* Turning it on costs, in this study, 4.3× the output tokens on average (13,604 against 3,134 mean completion tokens over all billed calls). Whether that buys anything depends on the task, on the model, and, as it turns out, on how the model fails when it fails.

## The stakes

Across the ten configurations in this study, the cost of one correct answer ranges from $0.00021 to $0.06320, a factor of 305 across the roster and a factor of 65 even between six configurations that sat an identical 60-problem exam. At the scale of a coding assistant, that is the difference between a bill of tens of dollars and a bill of thousands for the same work. The wrong default is expensive in either direction: reasoning off loses hard problems that reasoning would have solved, and reasoning on wastes an order of magnitude on problems any configuration solves.

## The gap

The routing literature selects between *models*. The reasoning-control literature adjusts a single model's *thinking budget*. The nearest published dataset to this work, CodeRouterBench (June 2026), releases 9,999 coding tasks × 8 models with per-call cost, but its `model` column holds eight model names and nothing else: there is no thinking-mode axis and no reasoning-token column. The quantity that carries most of a thinking call's cost is the quantity the closest prior work does not record. Chapter 2 sets this out in detail.

## The question

> **Reasoning models can think before answering. That thinking is billed but invisible. When is it worth paying for, on code generation, with real prices attached, and can one tell before paying?**

## Research questions

The proposal for this thesis (Appendix E) framed the work around building a router. The pilot changed that, for reasons Chapter 3 gives. The questions the finished work answers are:

| | Question | Answered in |
|---|---|---|
| RQ0 | Which benchmark problems can distinguish one configuration from another at all? | Chapter 5.1 |
| RQ1 | What predicts how long a model reasons, and when does reasoning improve the pass rate? | Chapter 5.2–5.4 |
| RQ2 | When is that reasoning wasted, and what does the waste cost? | Chapter 5.5 |
| RQ3 | Can waste be cut at runtime by aborting on reasoning length, and at what price in lost solutions? | Chapter 7 |
| RQ4 | What is the cost-accuracy frontier, how much headroom does problem-level information offer over a problem-blind strategy, and can a training-free router capture it? | Chapter 6 |
| RQ5 | Do the findings transfer to a model held out of the analysis? | Chapter 5.7 (under-powered; reported as such) |

## Contributions

1. **A measured table** of 1,373 graded generations across 320 problems and 10 (model × thinking-mode) configurations, with reasoning tokens and cost per call, produced for $5.24 under a cost cap that was enforced in code and never breached. No published dataset records this combination for code generation.
2. **Evidence that the value of reasoning is conditional on the model as well as the difficulty.** On hard problems the effect ranges from +52.9 points to −18.2 points across models on the same tier; on easy problems a small model degrades by 24.4 points with truncation ruled out. The aggregate "+29.3 on hard" is an average over opposite effects.
3. **A quantification of benchmark saturation and of its dependence on coverage.** HumanEval+, MBPP+ and LiveCodeBench-easy pass at 72–100% whichever arm is read; and problems measured across six or more configurations discriminate 82% of the time, against 44% when thinly covered.
4. **Four measurement-validity findings** about commercial aggregators: silent provider and quantization substitution (one run billed 1.54× the prediction across nine providers), ignored reasoning-budget parameters (a 2,000-token budget produced 13,731 tokens), non-binding token ceilings (73,037 tokens against a 48,000 ceiling), and free mid-stream cancellation.
5. **A measurement of the value of problem-level information** (13.8 accuracy points at equal budget, against the convex-hull baseline rather than the best single configuration) and a **gap decomposition** showing that a free-feature nearest-neighbour router fails on estimation (33.3 points), not on information (0.0 points), together with the reason it collapses.
6. **A documented self-refutation.** The pilot's headline, a free abort threshold that saved 44%, was an artefact of the project's own 16,000-token ceiling. The mechanism (a truncation limit is a censoring mechanism) is stated as a general hazard.

## How the thesis changed from the proposal

The proposal promised a router, CARR, that would reach 90–95% of the best configuration's accuracy at 60–70% less cost. Two things happened. The first real problem sent through every configuration was solved by all ten of them at a 44× cost spread, and the pilot found 81% of problems shared the same cheapest solver. That is the degenerate outcome the routing literature calls collapse, and it was visible before the router was built. The thesis was therefore reframed in week two from *build a router* to *measure when reasoning is worth paying for*. The router was still built and evaluated; it added +0.0 points over the honest baseline, which confirms the reframing was right rather than convenient. Chapter 3.13 records every such change with its date and reason, and Appendix E lists the edits the proposal document itself owes.

## Roadmap

Chapter 2 gives the vocabulary and the prior work. Chapter 3 states the method in enough detail to reproduce the table. Chapter 4 reports what the measuring platform does that would invalidate a careless study. Chapter 5 gives the results. Chapter 6 gives the cost-accuracy frontier, the oracle, the router and its diagnosis. Chapter 7 is the runtime abort, told as the story of a refuted claim. Chapter 8 draws the boundary of the claims. Chapter 9 says what a practitioner and a researcher should do differently. The appendices hold the schema, the configuration files, the reproduction commands, the test inventory, the project timeline, a glossary, the full tables, and the record of the adversarial self-audit that was run on this draft.
