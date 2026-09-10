# The frontier, the oracle, and the router

This chapter answers RQ4 in three steps: what the best problem-blind strategy achieves, how much a problem-aware strategy could add, and whether a training-free router adds any of it.

## The denominator, first

Six configurations × 60 shared problems. All ten configurations share only five problems, which is useless; six is the largest configuration set that still shares at least fifty problems. The 60 are 4 HumanEval+, 3 MBPP+, 2 LCB-easy (stdin), 32 LCB-medium (functional) and 19 LCB-hard (functional). Everything in this chapter describes those problems, and, for LiveCodeBench, function-style problems specifically.

## Definitions: points, dominance, the frontier

Each configuration $i$ is a point $(c_i, a_i)$: mean cost per problem and accuracy over the shared set. Configuration $i$ **dominates** $j$ if $c_i \le c_j$ and $a_i \ge a_j$ with at least one strict. No rational strategy ever chooses a dominated configuration. The **Pareto frontier** is the set of non-dominated points.

| Configuration | Cost / problem | Accuracy | 95% CI | Status |
|---|---|---|---|---|
| deepseek-v4-flash \| off | $0.00016 | 65.0% | [52, 77] | **hull vertex** |
| qwen3.5-9b \| off | $0.00034 | 33.3% | [22, 45] | dominated |
| qwen3.6-35b-a3b \| off | $0.00170 | 41.7% | [30, 55] | dominated |
| deepseek-v4-flash \| high | $0.00177 | **98.3%** | [95, 100] | **hull vertex** |
| deepseek-v4-pro \| high | $0.01088 | 95.0% | [88, 100] | dominated |
| qwen3.6-35b-a3b \| high | $0.01093 | 68.3% | [57, 80] | dominated |

![Figure 7. The cost-accuracy frontier over 6 configurations and 60 shared problems. The hull has two vertices; the oracle sits above it at the same budget.](../../data/figures/03-frontier-and-hull.png)

## The dominated frontier model

**Claim.** The most expensive full-grid model is not worth its price on these problems.

**Evidence.** `deepseek-v4-pro | high` costs 6.1× more per problem than `deepseek-v4-flash | high` ($0.01088 against $0.00177) and scores 57/60 against 59/60. On the **68 problems the two actually share** (a larger set than the frontier's 60), it is an exact tie: **64/68 each**.

**Uncertainty.** The accuracy intervals overlap ([95, 100] against [88, 100]), so the direction on the frontier set is suggestive, not established. The tie on the shared 68 does not depend on intervals. **What may be concluded:** at roughly six times the price, the frontier model was not measurably more accurate, and on the problems both sat it was exactly as accurate. The cheap model with reasoning enabled is the practitioner's answer here.

## Why the convex hull is the honest baseline

The proposal compared the router against "the strongest single configuration". That bar is too weak, and the reason is two lines of linear programming.

Suppose a strategy may **split traffic**: send fraction $p_i$ of problems to configuration $i$. Its cost and accuracy are the weighted averages, a point on the line between the configurations it mixes. The set of achievable (cost, accuracy) points without reading the problem is therefore the **convex hull** of the configuration points, and the best such strategy at budget $B$ solves

$$
\max_{p} \sum_i p_i a_i \quad \text{subject to} \quad \sum_i p_i c_i \le B, \qquad \sum_i p_i = 1, \qquad p_i \ge 0 .
$$

> **Proposition.** This linear program has two constraints besides non-negativity, so an optimal basic feasible solution has at most two non-zero components. Hence the optimal non-adaptive budget-constrained strategy randomises between at most two configurations, and its (cost, accuracy) point lies on the upper convex hull of the configuration points.

*Proof sketch.* A basic feasible solution of a linear program with $m$ equality/inequality constraints (after slack variables) has at most $m$ non-zero variables; here $m = 2$. Any point on the upper hull between two vertices is achieved by the mixture of those two vertices. $\square$

The mathematics is standard [@dantzig1963]; what matters is the consequence. A fixed traffic split already beats the best single configuration for free, so "beats the best single configuration" proves little. **The honest bar is the hull**, and a router's margin over it is exactly what reading the problem is worth:

$$
V = A_{\text{oracle}} - A_{\text{hull}}\!\left(B_{\text{oracle}}\right).
$$

On these data the hull has two vertices, `flash|off` and `flash|high`, and the line between them is the best any problem-blind strategy can do. RouterBench [@hu2024] uses the same baseline, which is evidence it is standard practice rather than an invention here.

## The oracle, MCKP, and the value of problem-level information

Choosing one configuration per problem under a total budget is a **multiple-choice knapsack problem** (MCKP) [@kellerer2004]: one group per problem $j$, items $(c_{ij}, s_{ij})$ per configuration $i$, choose exactly one item per group,

$$
\max_{x} \sum_j \sum_i x_{ij}\, s_{ij} \quad \text{s.t.} \quad \sum_j \sum_i x_{ij}\, c_{ij} \le B, \qquad \sum_i x_{ij} = 1 \;\; \forall j, \qquad x_{ij} \in \{0,1\}.
$$

The **oracle** is its integer optimum when the budget is not binding: for each problem, pick the cheapest configuration that solved it (and, for a problem nothing solved, the cheapest attempt, because the money was still spent). It is a cheat, not a method: it uses the answers.

**Result.** The oracle reaches **98.3% at $0.00111 per problem**. The convex hull at that same budget reaches **84.5%**. The value of problem-level information is therefore

$$
V = 98.3 - 84.5 = \mathbf{13.8 \text{ percentage points}}.
$$

Note what the oracle buys. Its 98.3% is exactly `flash|high`'s, because `flash|high` solved 59 of 60 and the one it missed was solved by nothing. The oracle reaches the same accuracy at 63% of the cost by routing 37 problems to `flash|off`, 3 to `qwen3.5-9b|off`, 1 to `qwen3.6-35b|off`, and only 18 of the 59 solved problems to a thinking configuration (17 to `flash|high`, 1 to `qwen3.5-9b|high`). So the 13.8 points measure *how much cheaper the same accuracy can be bought when the problem is known*, not how much more accurate one can get.

## The router

**What was built.** A k-nearest-neighbour router over three features that cost no API call: difficulty rank (MBPP+ 0, HumanEval+ 1, LCB easy 2, medium 3, hard 4, ordered by measured pass rate), number of hidden tests, and prompt length in characters. Features are scaled to $[0,1]$ so no one of them dominates the distance:

$$
\phi(j) = \left(\frac{\text{rank}_j}{4},\; \frac{\min(n^{\text{tests}}_j, 1200)}{1200},\; \frac{\min(\text{chars}_j, 4000)}{4000}\right),
\qquad d(j, j') = \lVert \phi(j) - \phi(j') \rVert_2^2 .
$$

The label to predict for a problem is the cheapest configuration that solved it. For a new problem the router takes the $k = 5$ nearest labelled problems and returns the majority label. Two rule baselines are included: always the cheapest configuration, always the dearest, and a two-line rule "think if the rank is at least 3".

**How it was evaluated.** Leave-one-out cross-validation over the 60 shared problems, because at that size a single split measures the split. The router never sees the problem it predicts (a test enforces this), and a router that declines to choose is charged the cheapest configuration so abstention cannot win.

**Result.**

| Strategy | Accuracy | Cost / problem | Configurations used |
|---|---|---|---|
| always cheapest | 65.0% | $0.00016 | 1 |
| always dearest | 68.3% | $0.01093 | 1 |
| rule: think if hard | 66.7% | $0.01027 | 2 |
| **k-NN (k=5), leave-one-out** | **65.0%** | $0.00016 | **1** |

65.0% is exactly the hull at that cost. **Router minus hull: +0.0 points.** The router collapsed to a single configuration, the degenerate outcome *When Routing Collapses* [@collapse2026] names, now measured in these data. Note that the baseline here is the hull; against the proposal's weaker bar, "always dearest" at 68.3% would have looked like a success.

## The gap decomposition

The part that is genuinely this thesis's own. Split the router-to-oracle gap into the part better features could close and the part a better estimator could close:

$$
\underbrace{A_{\text{oracle}} - A_{\text{ceiling}}}_{\text{feature insufficiency}}
\;+\;
\underbrace{A_{\text{ceiling}} - A_{\text{router}}}_{\text{estimation error}}
\;=\; A_{\text{oracle}} - A_{\text{router}},
$$

where the **feature ceiling** $A_{\text{ceiling}}$ is the best any router reading only these features could achieve: bucket the problems by coarsened feature values (12 buckets here) and give each bucket its single best configuration, chosen with full knowledge of the answers.

| | |
|---|---|
| oracle (needs the answers) | 98.3% |
| ceiling from these features alone | **98.3%** |
| k-NN actually achieves | 65.0% |
| **feature insufficiency** | **0.0 points** |
| **estimation error** | **33.3 points** |

**Why it collapsed, mechanically.** The label is dominated by one configuration (`flash|off` is the cheapest solver on most problems), so a nearest-neighbour *vote* returns that label almost everywhere. The collapse is a property of the objective (classify the modal cheapest-passing label), not of the inputs. **The named fix** is a cost-aware objective: predict each configuration's success probability for the problem and solve the per-problem knapsack, rather than classifying the modal label.

**Two caveats, both volunteered.** The feature ceiling is fitted on the same 60 problems it describes, five per bucket, so it is an optimistic upper bound, not an achievable target: read it as "the features are at least this informative". And two of the three features are benchmark metadata, not properties of an arriving prompt: the difficulty rank is LiveCodeBench's own label (degrading to the benchmark name for HumanEval+/MBPP+), and the test count is the size of the hidden grading suite, unknowable before grading. Only prompt length is computable from an incoming request. The proposal's positioning, routing on "cheap, non-LLM structural and lexical features" of the prompt, is therefore not what was implemented, and that holds whether or not the router worked. What survives untouched is the headroom measurement: the oracle, the hull and the 13.8 points use none of these features.

**What may be concluded.** A negative result that says which direction to fix is worth more than a marginal positive one. Problem-level information is worth 13.8 points on function-style problems at equal budget; a modal-label router captures none of it; the estimator, not the information, is the binding constraint; and a deployable router would have one usable feature here plus whatever the prompt text yields, none of which was measured.
