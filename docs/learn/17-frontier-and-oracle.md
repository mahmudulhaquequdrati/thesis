# Lesson 17 — Finding 5: the frontier, the hull and the oracle

*Part 2 · about 1 hour · after lesson 16 · uses lesson 10 heavily*

---

## In one sentence

> The cost-accuracy hull has only **two** vertices, the expensive frontier model
> is a **bad buy**, and knowing something about the problem before choosing is
> worth **13.8 accuracy points**.

---

## The finding

### The denominator first, because it constrains everything

These results run over **6 configurations × 60 problems**.

Why not 10 × 320? Because a frontier comparison requires that every
configuration was measured on **the same problems** (lesson 08). And:

- all **ten** configurations share only **5** problems — useless
- **six** configurations share **60** — usable

So the analysis runs over **the largest valid set, not the largest set**. Say
that sentence in Chapter 6. It is a small thing that signals you understand what
you are doing.

⚠️ And be upfront: 60 problems is not many, and it is why several intervals here
overlap.

### Result 1 — the hull has two vertices

| configuration | cost/problem | accuracy | status |
|---|---|---|---|
| `deepseek-v4-flash \| off` | $0.00016 | 65.0% | **hull vertex** |
| `deepseek-v4-flash \| high` | $0.00177 | 98.3% | **hull vertex** |
| everything else (4 configs) | — | — | **dominated** |

Every other configuration is beaten by *some mixture* of those two (lesson 10).
Two points define the entire achievable frontier.

Practically: **your whole roster reduces to one model, with thinking off or on.**
That is a striking, quotable result, and it is only visible because you measured
cost and accuracy together.

### Result 2 — the expensive model is a bad buy

The single most quotable line in your thesis:

> **`deepseek-v4-pro | high` costs 6× more than `deepseek-v4-flash | high` for 3
> points *less* accuracy** — 95.0% vs 98.3%.

The frontier open-weight reasoner, the top of your roster, is **dominated**. Not
"less cost-effective" — strictly worse on both dimensions.

⚠️ **The caveat, which must travel with the claim:** the accuracy intervals
overlap — [95, 100] vs [88, 100]. So the *direction* is suggestive, not
established. What *is* solid is that the expensive model shows no measurable
advantage while costing 6× more. That is enough to be useful, and it is all you
may claim.

Write the caveat in the same sentence as the claim. It costs you nothing in
impact and buys you complete credibility.

### Result 3 — the oracle, and the 13.8 points

Three strategies, all at the same budget:

| strategy | accuracy | cost/problem | knows what? |
|---|---|---|---|
| **Oracle** | **98.3%** | $0.00111 | cheats — knows the answers |
| **Problem-blind mixture** | **84.5%** | $0.00111 | knows only the budget |
| **Gap** | **13.8 points** | | **the value of problem-level information** |

Read the middle row carefully. The blind mixture is not a strawman — it is the
*optimal* non-adaptive strategy, the best you can do by splitting traffic
without ever looking at what you were asked. Beating it requires actually
reading the problem.

So:

> **13.8 accuracy points is the measured value of knowing something about the
> problem before choosing.**

That is the sharp form of RQ4, and it is what THESIS.md §10.1 set out to
produce: *"CARR's margin over the convex hull is the measured value of
problem-level information."*

Note too: the oracle reaches 98.3% *more cheaply* ($0.00111) than the single
configuration that reaches 98.3% ($0.00177). Adaptivity buys you the same
accuracy at 63% of the price.

### Why the hull and not "the best single model"

Your proposal compared against *"the strongest single configuration"*. That bar
is too low, and the argument (THESIS.md §10.1) is:

> **Proposition.** The optimal non-adaptive budget-constrained routing strategy
> randomizes between at most **two** configurations, and lies on the upper convex
> hull of the cost-accuracy frontier.

Because a mixture already beats the best single configuration at most budgets,
clearing that bar proves almost nothing. Raising your own baseline — making your
result *harder* to achieve — is one of the strongest moves available in a
thesis, and an examiner will notice it.

The formalism is a two-constraint linear program (`Σpᵢcᵢ ≤ B`, `Σpᵢ = 1`), whose
optimal basic solution has at most two nonzero weights. Standard LP theory. **Say
that it is standard** — THESIS.md §10 is explicit that MCKP is classical, the
k-NN bound is Cover & Hart (1967), bootstrapping is standard, and what is yours
is the *framing* plus the gap decomposition.

### An implementation note worth a sentence

The convex hull is computed **without scipy**. A 2D upper hull is a twenty-line
monotone chain, and pulling in a heavyweight dependency for twenty lines would
have been silly.

Small thing, but it belongs in Chapter 3 as a one-liner: it shows the dependency
list is a set of decisions rather than an accumulation. `matplotlib` is the only
dependency added after week 1, for figures.

---

## Why it matters for the writing

This is **Chapter 6**, and the order is:

1. **The denominator** — 6 × 60, and why not 10 × 320.
2. **The frontier plot** — all configurations as points.
3. **The hull** — two vertices, everything else dominated.
4. **The dominated frontier model** — the quotable result, with its caveat.
5. **The proposition** — why the hull is the right baseline.
6. **The oracle** — 98.3% at $0.00111.
7. **The 13.8-point gap** — the value of problem-level information.
8. **Forward pointer** — "and Chapter 6b asks whether a cheap router can capture
   any of it." (It cannot. Lesson 18.)

Item 5 is where you demonstrate that you strengthened your own evaluation rather
than choosing an easy comparison. Do not skip it, and do not oversell it as new
mathematics.

---

## Do this

**1. See the numbers.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ4/,/RQ4b/p'
```

**2. Look at the picture — this is your best figure.**

```bash
uv run python scripts/make_figures.py && open data/figures/03-frontier-and-hull.png
```

Find: the two hull vertices, the dominated points below the line, and
`deepseek-v4-pro | high` sitting up and to the right of `flash | high`.

**3. Verify the 6 × 60 denominator yourself.**

```sql
SELECT n_configs, COUNT(*) AS n_problems FROM (
  SELECT problem_id, COUNT(DISTINCT config_id) AS n_configs
  FROM generations g JOIN results USING (gen_id)
  WHERE g.is_mock = 0
  GROUP BY problem_id
) GROUP BY n_configs ORDER BY n_configs DESC;
```

You will see very few problems covered by all 10, and a usable cluster at 6.
**That distribution is why the analysis is 6 × 60.**

**4. Check dominance by hand.**

Write down each configuration's (cost, accuracy). For each, ask: *is there
another that is both cheaper and at least as accurate?* If yes, it is dominated.
You should end with two survivors.

---

## Check yourself

1. Why is the frontier computed over 6 configurations × 60 problems rather than
   10 × 320?
2. How many vertices does the hull have, and what does that mean about your
   roster?
3. State the dominated-frontier-model result *with* its caveat.
4. What is the problem-blind mixture, and why is it not a strawman?
5. What does the 13.8-point gap measure, in plain words?
6. Why is beating "the best single configuration" a weak result?
7. Which parts of the mathematics here are yours, and which are borrowed?

<details>
<summary>Answers</summary>

1. Because a frontier comparison needs every configuration measured on the same
   problems. All ten share only 5 problems; six share 60. The analysis uses the
   largest *valid* set.
2. Two: `flash|off` and `flash|high`. Every other configuration is beaten by a
   mixture of those two — the roster effectively reduces to one model with
   thinking off or on.
3. `deepseek-v4-pro | high` costs 6× more than `flash | high` for 3 points less
   accuracy (95.0% vs 98.3%) — **but the accuracy intervals overlap ([95,100] vs
   [88,100]), so the direction is suggestive rather than established.** What is
   solid: no measurable advantage at 6× the price.
4. The optimal *non-adaptive* strategy — the best achievable by splitting traffic
   between configurations without looking at the problem. It is not a strawman
   because it is provably optimal within its class.
5. Knowing something about the problem before choosing is worth 13.8 accuracy
   points at the same budget, compared with the best strategy that never looks.
6. Because a fixed traffic split already beats the best single configuration at
   almost any budget, so clearing that bar says nothing about the value of
   reading the problem.
7. Borrowed: the LP/convex-hull argument, MCKP, the k-NN bound (Cover & Hart
   1967), the bootstrap. Yours: the framing of hull-margin as the value of
   problem-level information, and the gap decomposition in lesson 18.

</details>

---

➡️ Next: [Lesson 18 — Finding 6: the router collapsed, and why](18-router-collapse.md)
