# Results

Every number in this chapter is copied from the output of `scripts/results.py` run on 2026-09-11 against the database snapshot of 2026-07-26, and every paragraph follows the same four moves: the claim, the number with its denominator, the uncertainty or caveat, and what may and may not be concluded.

**Scale.** 1,373 generations, 1,280 graded, 320 problems, 10 configurations, $5.2402 in the database. Coverage per configuration is uneven (Figure 1): the run was cheapest-first and stopped at the cap, so the `off` arm covers 318–320 problems for three of the five models (`pro|off` 51, `kimi|off` 16) while the `high` arm covers 73–104 (`kimi|high` 23). Every comparison below is therefore restricted to a shared problem set and states which one.

![Figure 1. Coverage per configuration. The cheap `off` arm is complete; the expensive arms are partial. This picture is why every comparison in the thesis is restricted to shared problems.](../../data/figures/07-coverage.png)

## Saturation: most standard-benchmark problems cannot answer the question

**Claim.** The standard code benchmarks are saturated for 2026-class models: they pass at a high rate whether or not reasoning is enabled, so they carry little signal about which configuration to use.

**Evidence.** Pass rate per difficulty tier, reasoning off against on, over every billed call:

| Tier | Off | On | n (off / on) |
|---|---|---|---|
| LiveCodeBench hard | 24.9% | 54.2% | 462 / 118 |
| LiveCodeBench medium | 53.3% | 76.4% | 317 / 148 |
| MBPP+ | 72.3% | 73.3% | 83 / 30 |
| HumanEval+ | 92.9% | 97.0% | 85 / 33 |
| LiveCodeBench easy | 94.1% | 100.0% | 68 / 11 |

HumanEval+, MBPP+ and LCB-easy sit at 72–100% whichever arm is read. This was visible on the very first purchase: `HumanEval/0` was solved by all ten configurations at costs from $0.000106 to $0.004630, a 44× spread for an identical outcome.

**The problem-level split, and why it must be read at several coverages.** Counted over all 320 problems: 81 were solved by every configuration that ran on them, 98 by none, and 141 discriminate. But unanimity is trivially easier to reach with fewer voters, and 206 of the 320 problems saw only two or three configurations, nearly always the three cheap `off` ones. Recomputed at increasing coverage:

| Coverage | n | All solved | None solved | Discriminating |
|---|---|---|---|---|
| ≥ 1 configuration (as counted) | 320 | 81 (25%) | 98 (31%) | 141 (44%) |
| ≥ 1 reasoning-enabled configuration | 108 | 33 (31%) | 4 (4%) | 71 (66%) |
| ≥ 4 configurations | 114 | 38 (33%) | 4 (4%) | 72 (63%) |
| ≥ 6 configurations | 73 | 11 (15%) | 2 (3%) | 60 (82%) |

Of the 98 problems "solved by nothing", 94 were never attempted by a single reasoning-enabled configuration.

**What may be concluded.** The per-tier saturation finding stands, because it is a pass rate: the easy benchmarks are too easy to study this question with, and any study of reasoning value should say which subset of its benchmark carries signal. The claim that three quarters of the pool carries no routing signal does *not* stand; it measured the budget, not the problems. At real coverage, 82% of problems discriminate. Both statements are reported so the dependence is visible rather than chosen.

## When thinking helps: the per-tier aggregate, and why it is not the finding

**Claim.** Enabling reasoning raises the pass rate on the two discriminating tiers and does almost nothing on the saturated ones.

**Evidence.** From the table above: LCB hard 24.9% → 54.2%, LCB medium 53.3% → 76.4%, MBPP+ +1.0 point. Figure 2 shows the widening gap from easy to hard.

![Figure 2. Pass rate with reasoning off and on, per tier, easy to hard. Reasoning buys almost nothing on saturated benchmarks and a large gain on hard problems; the hard-tier thinking arm is a floor because 26.3% of its calls truncate.](../../data/figures/01-effort-by-tier.png)

**Three caveats travel with this table.** First, 26.3% of hard thinking calls (31 of 118) and 12.2% of medium ones (18 of 148) were truncated at the 48,000-token ceiling, and a truncated call cannot pass, so 54.2% is a floor. Second, the two arms did not sit the same exam (§5.4). Third, and most important, the aggregate averages over models that respond in opposite directions (§5.3). The per-tier table is retained because it is the form this literature reports; it is not the headline.

## The effect is per model, and the aggregate hides a sign reversal

**Claim.** The value of reasoning is a property of the (model, difficulty) pair. On the same tier, one model gains 52.9 points and another loses 18.2.

**Evidence.** Per (tier, model), on the arms with at least 15 calls. `cens` is the share of thinking calls truncated at the ceiling; `rtok` the mean reasoning tokens of the thinking arm.

| Tier | Model | Off | High | Delta | cens | rtok |
|---|---|---|---|---|---|---|
| hard | deepseek-v4-flash | 29.2% (154) | **82.1%** (28) | **+52.9** | 11% | 17,703 |
| hard | qwen3.6-35b-a3b | 22.1% (154) | 27.6% (29) | +5.5 | 17% | 12,187 |
| hard | qwen3.5-9b | 22.1% (145) | **3.8%** (26) | **−18.2** | **81%** | 24,826 |
| medium | deepseek-v4-flash | 62.5% (104) | **94.4%** (36) | **+31.9** | 0% | 7,590 |
| medium | qwen3.6-35b-a3b | 52.9% (104) | 72.2% (36) | +19.3 | 6% | 7,296 |
| medium | qwen3.5-9b | 43.6% (101) | 38.7% (31) | −4.9 | 52% | 19,084 |
| MBPP+ | qwen3.5-9b | 80.0% (20) | **55.6%** (18) | **−24.4** | **0%** | 368 |
| HumanEval+ | qwen3.5-9b | 90.5% (21) | 94.7% (19) | +4.3 | 0% | 487 |

![Figure 3. Percentage points gained by enabling reasoning, per (tier, model). The sign depends on the model; the two negative hard/medium bars are mostly truncation, the negative MBPP+ bar is not.](../../data/figures/05-effect-by-model.png)

**Two mechanisms, which need separate sentences.**

*Non-termination.* `qwen3.5-9b|high` hits the ceiling on 81% of hard calls, returns no code at all on 77%, and averages 24,826 reasoning tokens. Its −18.2 is mostly the model failing to stop, and partly a statement about the ceiling: `deepseek-v4-flash|high` censors at 11% on the same problems.

*Genuine degradation.* On MBPP+ the same model censors 0%, reasons for a mean of 368 tokens, terminates normally, and still falls from 16/20 to 10/18 on the same twenty problems. Every failure produced extracted code that failed on assertions. That is overthinking observed directly, paired, with truncation ruled out. It is the cleanest result in the thesis.

**Uncertainty.** The per-model thinking arms are 18–36 calls each. Directions are clear; magnitudes are not precise. Note also that the easy-benchmark rows of the aggregate table are model-confounded: the `high` arm on MBPP+ is 62% `qwen3.5-9b` and on HumanEval+ 58%, against about 25% in the `off` arm, so "MBPP+ 72.3% → 73.3%" compares a four-model average with a mostly-one-model average.

**What may be concluded.** Not "thinking helps on hard problems". Rather: *enable reasoning on a capable model for hard problems; on a small model it may cost accuracy at both ends of the difficulty range.* The practitioner rule is per model.

## The style confound: the two arms did not sit the same exam

**Claim.** The raw tier-level gap mixes a reasoning effect with a composition effect, because the thinking arm is almost entirely function-style LiveCodeBench problems. Within a style, the effect survives on both tiers.

**Evidence.** On the hard tier the `off` arm is 348 stdin-style calls and 114 function-style; the `high` arm is 8 and 110. The cause is mechanical: the runner orders cells by `(expected cost, problem_id)`, ties inside one configuration break on the id as a string, LeetCode ids are numeric and AtCoder ids start with letters, so all 125 function-style problems ran before any of the 217 stdin ones and the thinking arm hit the cap inside that prefix.

| Tier | Style | Off | On | Matched gap | Raw gap |
|---|---|---|---|---|---|
| hard | functional | 31.6% (114) | **57.3%** (110) | **+25.7** | +29.3 |
| medium | functional | 49.1% (163) | **78.0%** (141) | **+28.9** | +23.0 |

Arms with fewer than 30 calls are dropped: hard/stdin thinking is n=8, medium/stdin thinking n=7.

**What may be concluded.** On hard function-style problems reasoning raises the pass rate by a factor of 1.8, not "more than doubles". The medium effect is *larger* under matching, which is what a genuine composition effect looks like rather than a convenient one. Nothing is claimed about stdin-style problems. The 60-problem frontier set of Chapter 6 inherits the skew (51 functional, 2 stdin; all 19 of its hard problems function-style), so the hull, oracle, headroom and router results describe function-style problems.

## Reasoning length rises with difficulty

**Claim.** Models reason longer on harder problems without being told the difficulty.

**Evidence.** Mean reasoning tokens per thinking call: MBPP+ 642 (n=30), HumanEval+ 773 (33), LCB easy 2,693 (11), LCB medium 10,183 (148), LCB hard 17,547 (118). Maximum observed: 73,037.

![Figure 4. Mean reasoning tokens per call by tier, with min–max whiskers. The rise is monotone across a difficulty label the model never saw.](../../data/figures/08-reasoning-by-tier.png)

**Caveat.** The easy-tier samples are small (11–33) and the tiers differ in source and prompt style as well as difficulty. **Meaning.** It is a validity check (the models' effort tracks an independently assigned label) and the mechanism behind Chapter 7: length is a signal a runtime intervention can act on.

## Long reasoning is failure, not effort, and it is expensive

**Claim.** A call that reasons for a very long time is not working harder. It is failing, at maximum cost.

**Evidence.** Among billed reasoning-enabled calls:

| Outcome | n | Mean reasoning tokens | Spend |
|---|---|---|---|
| passed | 242 | 7,567 | $2.52 |
| failed (ran, wrong answer) | 49 | 7,577 | $0.55 |
| **billed, no usable answer** | **49** | **29,584** | **$0.56** |

![Figure 5. Mean reasoning tokens by outcome. Passing and failing calls reason for almost the same length; calls that return nothing reason four times longer.](../../data/figures/02-reasoning-vs-outcome.png)

Forty-nine calls burned an average of 29,584 reasoning tokens and returned nothing. That is $0.56 of the $3.62 spent on reasoning-enabled calls (15%), and 11% of the $5.24 total. Both denominators are given because a reader with a calculator will divide.

**Two caveats.** Passing and failing calls have nearly identical mean length (7,567 against 7,577), so length does *not* separate right from wrong; it separates finished from never finished. And the waste is not spread across the roster:

| Model | Wasted / thinking calls | Rate | Mean reasoning (wasted) | $ wasted |
|---|---|---|---|---|
| qwen3.5-9b | **37 / 99** | **37.4%** | 30,411 | $0.24 |
| qwen3.6-35b-a3b | 7 / 74 | 9.5% | 16,635 | $0.21 |
| deepseek-v4-flash | 3 / 73 | 4.1% | 48,000 | $0.03 |
| deepseek-v4-pro | 2 / 72 | 2.8% | 31,999 | $0.08 |
| kimi-k2.6 | 0 / 22 | 0.0% | — | $0.00 |

**What may be concluded.** Three quarters of the wasted calls (37 of 49) are one model. Non-termination is a property of the small model, not of reasoning: about a third of `qwen3.5-9b`'s thinking calls returned nothing, against one in twenty-five of `deepseek-v4-flash`'s. "Expect 15% of reasoning spend to buy nothing" is the wrong advice to give anyone; the per-model rate is the useful one. The phenomenon itself is not novel (Chapter 2.7); the economic framing is.

## Cost per correct answer spans orders of magnitude

**Claim.** The cost of one correct answer varies by two orders of magnitude across the roster, and several adjacent orderings are not established.

**Evidence.** Over the 107 paired problems, CPC = Σcost ÷ Σsolved and TPC = Σcompletion tokens ÷ Σsolved, with 95% bootstrap intervals over problems:

| Configuration | n | Solved | CPC ($) | 95% CI | TPC |
|---|---|---|---|---|---|
| deepseek-v4-flash \| off | 107 | 74 | **0.00021** | [0.00015, 0.00028] | 889 |
| qwen3.5-9b \| off | 102 | 52 | 0.00058 | [0.00040, 0.00081] | 3,386 |
| deepseek-v4-pro \| off | 45 | 33 | 0.00080 | [0.00061, 0.00109] | 385 |
| qwen3.5-9b \| high | 63 | 46 | 0.00094 | [0.00056, 0.00146] | 6,011 |
| deepseek-v4-flash \| high | 70 | 66 | 0.00193 | [0.00150, 0.00238] | 10,078 |
| qwen3.6-35b-a3b \| off | 107 | 59 | 0.00262 | [0.00180, 0.00388] | 2,514 |
| deepseek-v4-pro \| high | 70 | 66 | 0.01224 | [0.00930, 0.01581] | 8,734 |
| kimi-k2.6 \| off | 16 | 11 | 0.01626 | [0.00696, 0.03619] | 4,657 |
| qwen3.6-35b-a3b \| high | 67 | 43 | 0.01793 | [0.01422, 0.02356] | 17,820 |
| kimi-k2.6 \| high | 22 | 21 | **0.06320** | [0.03940, 0.09324] | 18,524 |

![Figure 6. Cost per correct answer per configuration with 95% intervals, log scale. Dark bars are reasoning on.](../../data/figures/06-cost-per-correct.png)

**The headline ratio depends on the denominator, and all three are reported.**

| Comparison | Denominator | Spread |
|---|---|---|
| cheapest vs dearest configuration | different sets, n=107 and n=22 | 305× |
| the same two configurations | the 22 problems they share | 228× |
| six configurations on an identical exam | the same 60 problems | 65× |

**Uncertainty.** Five adjacent pairs have overlapping intervals (`qwen3.5-9b|off` vs `pro|off`; `pro|off` vs `qwen3.5-9b|high`; `flash|high` vs `qwen3.6-35b|off`; `pro|high` vs `kimi|off`; `kimi|off` vs `qwen3.6-35b|high`), so their ordering is not established despite distinct point estimates. Reported bare, which is the norm in this literature, that table would have manufactured a ranking the data does not support. Also, `pro|off` looks cheap per correct answer partly because 35 of its 45 paired problems are HumanEval+ or MBPP+; it sat an easier exam.

**What may be concluded.** "Cost per correct answer varies by orders of magnitude" is robust to every denominator. The specific multiplier is not interchangeable between them, and any quotation of it must name the problem set.

## The held-out model (RQ5): under-powered, reported as such

Kimi K2.6 was held out of every design decision and run on a subset: `off` on 16 problems (11 solved), `high` on 23 (21 solved), at $0.18 and $1.33 respectively. Twenty-three problems cannot establish transfer of any finding, and no claim is made from them beyond what appears in the tables above (its `high` configuration has the highest cost per correct answer in the roster, and none of its 22 billed thinking calls was wasted). RQ5 is answered *not with this budget*. The concrete design that would answer it is stated in Chapter 9.

## Token multiplier and latency

Two operational numbers that a practitioner will want. Over all billed calls, mean completion tokens are 3,134 with reasoning off (n=1,014) and 13,604 with it on (n=340): a 4.3× multiplier, against the roughly 10× guessed before any data existed. Mean wall-clock latency was 64 seconds for `off` calls and 111 seconds for `high`, with a maximum of 21 minutes; LiveCodeBench problems make even non-reasoning models write thousands of tokens of answer.
