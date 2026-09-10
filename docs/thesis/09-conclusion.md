# Conclusion

## The question and its answer

This thesis asked when the invisible, billed thinking of reasoning models is worth paying for on code generation. The answer is that its value is conditional, and the condition is the model as much as the task. On hard function-style contest problems, enabling reasoning raised one capable, cheap model's pass rate by a factor of 1.8 and dropped a small model's to near zero because it failed to stop. On the standard benchmarks this literature reports, it changed almost nothing, because those benchmarks are saturated; and on one of them a small model got measurably worse with reasoning on, with truncation ruled out. Fifteen percent of the reasoning arm's spend bought nothing at all, and three quarters of those wasted calls came from one model. The cheap model with reasoning enabled tied the frontier model with reasoning enabled at one sixth of the price. Knowing the problem before choosing is worth 13.8 accuracy points at equal budget, and the simplest router captured none of it for a reason the decomposition names.

## Guidance for practitioners

1. **Decide per model, not per task.** Enable reasoning on a capable model for hard problems. On a small model, expect it to cost accuracy at both ends of the difficulty range and to return nothing on roughly a third of calls.
2. **Do not assume the expensive model is better.** Here `deepseek-v4-flash` with reasoning matched `deepseek-v4-pro` with reasoning exactly on the problems both sat, at one sixth the price.
3. **Budget for waste, per model.** About one in twenty-five of a capable model's thinking calls returned nothing; about one in three of a small model's did.
4. **Use a reasoning-length abort, but know whose it is.** For a model whose long reasoning rarely succeeds, a threshold near 10,000 tokens can save most of its thinking spend for free. For a model that solves hard problems by thinking long, every threshold costs solutions; at 16,000 tokens the roster-wide trade is 88% of solutions for half the cost.
5. **Cancel, do not budget.** Reasoning-budget parameters may be ignored; mid-stream cancellation is free and observable.

## Guidance for researchers

1. **Pin the provider and the quantization.** Otherwise you are comparing compressed variants at unrecorded prices.
2. **Store both a computed and a billed cost**, and report which one each number rests on.
3. **Report the truncation rate beside every result about long outputs**, and treat a ceiling as a censoring mechanism.
4. **State which subset of your benchmark carries signal**, and at what coverage. Unanimity across two configurations is a property of the budget.
5. **Report reasoning effects per model.** A tier-level average can hide a sign reversal.
6. **Check your run order.** A string tie-break decided which exam the expensive arm of this study sat.
7. **Store the reasoning text.** It costs nothing extra and it is the only thing that would let anyone check the number the whole study rests on.

## Future work, named

- **Reconcile the grid's costs** against the aggregator's billing records over the 1,217 rows that still carry a generation id. Free; if the records have expired, that is itself the reportable limitation.
- **A cost-aware routing objective:** predict per-configuration success probability and solve the per-problem knapsack, rather than classifying the modal cheapest-passing label. The decomposition locates the failure precisely there.
- **A balanced re-run of the thinking arm on stdin-style problems** (about 110 hard calls, roughly $1.50 at `flash|high` prices), so the effect of reasoning on that style is measured rather than unknown.
- **A held-out-model test with real power:** at least 100 problems on both arms of a model from a fourth family.
- **Capture the reasoning traces**, so non-termination can be inspected rather than counted.
- **A contamination-controlled hard tier**, which does not publicly exist; the frontier stopped updating in 2025.

## Closing

A trivial request for a three-line function spent 392 tokens thinking. This thesis has measured when that expenditure is justified. For most of the problems on which such models are routinely evaluated, it is not; for hard problems it depends on which model is doing the thinking; and the platform through which the thinking is bought will, unless pinned and checked, quietly change both the price and the model. The thesis is not the code and it is not this document. It is the table, and the fact that every rule in the repository exists to stop that table being quietly wrong. Twice it was. Both times the checks caught it.
