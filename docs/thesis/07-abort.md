# Runtime abort: a refuted headline and the honest curve

This chapter is told in the order it happened, because the reasoning is the contribution and the final number is modest.

## The mechanism is real, and it is free

Three measured facts (Chapter 4): reasoning is observable live in the stream; cancelling a stream mid-reasoning is billed $0.00 on both providers tested; and asking a model to think less does not work. Together they make "stop a call once it has thought too long" the only functioning control over reasoning spend, and a real intervention rather than a thought experiment.

## The claim, as it was believed

The pilot ran 16 problems (15 stratified, plus the first cell) × 10 configurations, 149 generations, under a 16,000-token ceiling. Simulating an abort at 10,000 reasoning tokens over its completed calls kept 42 of 42 passes and cut thinking-configuration spend by 44%. A dominant improvement: money saved, nothing lost. It was written into the project log as the headline of the reframed thesis.

## The doubt: censoring

At that ceiling, 43.8% of LCB-hard and 36.4% of LCB-medium thinking calls were cut off and returned nothing. The realisation that overturned the claim is one sentence: **a call truncated at the ceiling cannot have succeeded**, so the pilot could never have observed a success above roughly 10,000 reasoning tokens, whatever the models were capable of. A thermometer that stops at 40 °C can never disprove "it never gets hotter than 40 °C". In statistical terms, the ceiling is a **censoring** mechanism, and any analysis of the censored quantity, here reasoning length against success, is biased by it. The ceiling had manufactured the cliff the claim depended on.

## The refutation

The ceiling was raised to 48,000 for the grid. Over billed thinking calls, pass rate by reasoning length:

| Reasoning tokens | n | Passed | Pass rate |
|---|---|---|---|
| under 10,000 | 221 | 186 | 84.2% |
| 10,000–20,000 | 58 | 32 | 55.2% |
| 20,000 and above | 61 | 24 | 39.3% |

**Fifty-six calls above 10,000 reasoning tokens succeeded.** Pass rate declines as a gradient, not a cliff. The analysis function that searches for the cheapest threshold losing no solved problem correctly returns *none*.

## What honestly survives: a trade-off curve

The abort simulation over completed thinking calls: for a threshold $T$, a call with reasoning length $r_i \ge T$ is scored as costing nothing and solving nothing (valid because cancellation is billed nothing), and

$$
\text{kept}(T) = \frac{\sum_i s_i\,[r_i < T]}{\sum_i s_i}, \qquad
\text{saved}(T) = 1 - \frac{\sum_i c_i\,[r_i < T]}{\sum_i c_i},
$$

with intervals from a bootstrap over the 108 problems the thinking arm covers.

| Abort at | Solutions kept | 95% CI | Cost saved | 95% CI |
|---|---|---|---|---|
| 2,000 | 85/242 (35%) | [27, 44] | 98% | [96, 99] |
| 4,000 | 104/242 (43%) | [34, 52] | 96% | [94, 98] |
| 6,000 | 138/242 (57%) | [48, 66] | 90% | [86, 94] |
| 8,000 | 162/242 (67%) | [57, 75] | 83% | [76, 88] |
| 10,000 | 186/242 (77%) | [69, 83] | 72% | [62, 80] |
| 12,000 | 192/242 (79%) | [72, 86] | 64% | [52, 74] |
| **16,000** | **212/242 (88%)** | **[82, 92]** | **49%** | **[35, 61]** |

![Figure 8. The abort trade-off: solutions retained against cost saved, with 95% bootstrap bands. There is no point at which money is saved without losing a solved problem.](../../data/figures/04-abort-tradeoff.png)

> **Pooled over the roster, no threshold saves money without losing a solved problem.** Abort at 16,000 keeps 88% of solutions for roughly half the cost; that is a dial a practitioner can set, not a free lunch.

## The pool hides a free threshold that does exist, for two models

The pooled statement is true of the roster and false for two of its five models:

| Model | Thinking calls | Solved | Free threshold |
|---|---|---|---|
| qwen3.5-9b | 99 | 46 | **T = 10,000 keeps 46/46, saves 88%** |
| qwen3.6-35b-a3b | 74 | 43 | **T = 16,000 keeps 43/43, saves 13%** |
| deepseek-v4-flash | 73 | 66 | none: every threshold costs a solution |
| deepseek-v4-pro | 72 | 66 | none |
| kimi-k2.6 | 22 | 21 | none |

The pattern is coherent, not noise. The free threshold exists exactly where reasoning was not earning its keep: `qwen3.5-9b`'s reasoning delta is negative on three tiers of four and 37% of its thinking calls return nothing, so whatever it solved it solved early, and everything long was already doomed. `deepseek-v4-flash` gains 52.9 points on hard problems *by* thinking longer, so cutting it off must cost solutions.

> **Whether a reasoning-length abort is free is a property of the model.** Where long reasoning rarely succeeds it is free money, 88% of `qwen3.5-9b`'s thinking spend for no lost solution. Where long reasoning genuinely solves hard problems, every threshold costs solutions.

This refines the refutation without undoing it: the pilot claimed a free threshold *for the roster*, that remains false, and the 16,000 ceiling really did manufacture part of it.

## Residual censoring

26.3% of hard thinking calls still truncate at 48,000 tokens, so the right-hand end of the curve is a floor, and the "20,000 and above" band's 39.3% is a lower bound. The ceiling was raised rather than removed for a budget reason: without one the worst case of a single call is bounded only by the context window (262,144 tokens for Kimi, $0.89 for one call), and the cost cap computes its reservation from `max_tokens`, so removing it would leave the cap nothing to bound.

## Caveats

The curve is a simulation over completed calls, not a deployed intervention; it rests on the measured $0.00 cancellation. A threshold chosen from this curve is fitted to it and must be evaluated on data it was not chosen on before being called a result. And the thinking arm is 108 problems, almost all function-style.

## The general lesson

> **A truncation limit is a censoring mechanism, and censored observations bias any analysis of the quantity being truncated.**

Catching and reporting the refutation is better science than the original claim would have been, and it is the first thing to say when asked about a result that turned out wrong.
