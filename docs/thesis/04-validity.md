# Measurement validity: what the platform does

This chapter is separate from the method for three reasons. Its findings are about the measuring apparatus, so they condition every number in Chapters 5–7. They transfer: they apply to anyone benchmarking open-weight models through an aggregator. And each one changed the method. The proposal contained no equivalent section.

## The setup and the assumption

The project bought every call through one aggregator with one key. The implicit assumption at the start was the one every such study makes: that a model name identifies a model, that a listed price is the price, that a parameter the API accepts is a parameter the model obeys, and that a token ceiling is a ceiling. Each of those was tested by accident before it was tested on purpose.

## Provider routing silently changes both price and model

One model slug was served by 18 providers at prices from $0.87 to $3.48 per million output tokens, a 4× spread. The aggregator's model listing reports only the cheapest provider's price; routing picks whichever provider it likes. Before pinning, a single pilot run of `deepseek-v4-pro` was served by **nine different providers** and billed **1.54× what the price table predicted**.

Quantization varies with the provider, from `fp4` to `bf16`, and the cheapest endpoint is usually the most compressed: `deepseek-v4-flash`'s cheapest endpoint was `fp4`, as was `kimi-k2.6`'s.

The consequence, stated sharply:

> An unpinned evaluation does not compare models. It compares an unknown mixture of compressed variants at unrecorded prices, and a failure cannot be attributed to the model rather than to the compression.

**Mitigation.** Every configuration pins one provider and one precision (`fp8` or better across the roster) with fallbacks disabled, and both the computed and the billed cost are stored so drift is visible. The finding is corroborated by *The Silent Hyperparameter* [@silent2026] and by the community audit that found 31 of 32 surveyed repositories using the aggregator without pinning [@lesswrong2026]. The measurement here is an existence proof from one run, not a survey; that is enough to justify the pinning methodology, which is what it is used for.

## Advertised reasoning budgets are accepted and ignored

On `qwen3.5-9b` (pinned `deepinfra/bf16`), against a hard AtCoder problem:

| Request | Reasoning tokens produced | Outcome |
|---|---|---|
| `reasoning: {max_tokens: 2000}` | **13,731** (6.9× the budget) | hit the 16,000 ceiling, returned nothing |
| `reasoning: {effort: "low"}` | **11,926** | hit the 16,000 ceiling, returned nothing |
| `reasoning: {enabled: false}` | 0 (on 1,023 of 1,025 `off` calls in the grid) | behaves as advertised |

Both graded requests were accepted without error, and `reasoning` is listed in the endpoint's supported parameters. This is silent non-compliance, not an unsupported feature.

Two consequences. The effort axis of this thesis is binary in practice and is described that way. And *ex-ante* budget control does not work here, which answers the obvious objection to Chapter 7 ("why not just tell it to think less?"): you cannot, so a runtime abort is the only control that functions, not a redundant one. The finding rests on a small number of targeted calls on one model and is stated as *demonstrated on qwen3.5-9b*, not as a universal law.

## `max_tokens` is not a hard bound

Observed: 35,837 completion tokens against a 16,000 ceiling (2.24×, with `finish_reason` set to `error` and 143 KB of prose containing no code), and 73,037 reasoning tokens against a 48,000 ceiling. A cost cap computed from `max_tokens` is therefore computed from an advisory number. **Mitigation:** the pre-call reservation multiplies the requested worst case by 2.5, and actual spend is re-read from the database before every dispatch so an overrun self-corrects for everything after it.

## One behaviour that enables a method

Reasoning is observable **live** in the response stream (`delta.reasoning`), and **cancelling a stream mid-reasoning is billed $0.00**. This was verified on two providers with no billing record appearing after more than ten minutes: a `deepseek-v4-pro | high` call aborted at about 2,002 reasoning tokens after 33.8 seconds was billed $0.000000. A completed `pro|high` call in the grid averages $0.012165 (n=73, maximum $0.060253) and a completed `kimi|high` call $0.057706 (n=23). An abort therefore saves the *whole* call, not a pro-rata share, which is what makes Chapter 7's simulation valid. (An earlier note in the project log quoted "$0.010978 for the same cell run to completion"; that figure is not reproducible from the database and is not used.)

## Mitigations, summarised

| Finding | What changed in the method |
|---|---|
| Provider routing varies price and precision | Provider + quantization pinned; fallbacks off; computed and billed cost both stored |
| Reasoning budgets ignored | Effort axis described as binary; runtime abort studied instead of budget forcing |
| `max_tokens` advisory | 2.5× safety factor on the cap; spend re-read before every dispatch; ceiling raised but never removed |
| Free cancellation | Abort curve simulated over completed calls (Chapter 7) |
| Run order is part of the method (§3.13) | Within-style reporting; frontier labelled by style |

## Recommendations

Written as advice a researcher can follow tomorrow:

1. **Pin the provider and the quantization**, or you are not comparing models.
2. **Record both a computed and a billed cost**, and treat their disagreement as a signal, not noise.
3. **Report the truncation rate next to any result about long outputs.** A ceiling is a censoring mechanism (Chapter 7).
4. **Do not assume a reasoning-budget parameter binds.** Verify it with a call whose reasoning-token count you read back.
5. **Check your run order.** A tie-break on a string id changed which problems the expensive arm of this study saw.

The scope is stated honestly: the general hazard of backend variance is partly documented elsewhere. The contribution of this chapter is the commercial-aggregator case, with reasoning modes, cost, and the specific behaviours measured.
