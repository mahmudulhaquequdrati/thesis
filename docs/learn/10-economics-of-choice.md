# Lesson 10 — The economics of choosing

*Part 1 · about 1.5 hours · after lesson 09 · **last foundations lesson***

---

## In one sentence

> When options differ in both cost and quality, "which is best" has no answer —
> but "which are *not worth considering*" always does, and that set is called
> the frontier.

---

## The idea, from zero

### The question that has no answer

Five configurations. Each has a price and an accuracy:

| config | cost per problem | accuracy |
|---|---|---|
| A | $0.0002 | 65% |
| B | $0.0018 | 98% |
| C | $0.0009 | 80% |
| D | $0.0110 | 95% |
| E | $0.0004 | 60% |

Which is best?

**The question is malformed.** A is best if you are poor. B is best if you need
accuracy. There is no "best" without saying what you are willing to pay.

But a question that *does* have an answer is: **which options are simply bad?**

### Dominance — the one idea everything else is built on

> Option X **dominates** option Y if X is *at least as good on every dimension*
> and *strictly better on at least one*.

Look at A versus E:

- A costs $0.0002; E costs $0.0004. A is **cheaper**.
- A scores 65%; E scores 60%. A is **more accurate**.

A dominates E. **E should never be chosen by anyone, at any budget, for any
purpose.** Not "usually worse" — *never rational*.

The **Pareto frontier** is what survives after deleting every dominated option:

```
accuracy
  100% ┤                    ● B (98%, $0.0018)
       │              ● D (95%, $0.0110)  ← dominated by B: dearer AND worse
   80% ┤        ● C
       │
   65% ┤  ● A
   60% ┤  ● E  ← dominated by A
       └────────────────────────────────→ cost
```

Frontier: **A, C, B**. Dominated: **D, E**.

D is the interesting one. D is *expensive and good* — a frontier model — but B is
**cheaper and better**. So D is not a "premium option"; it is simply a bad buy.

That is not a hypothetical. It is your finding:

> **`deepseek-v4-pro | high` costs 6× more than `deepseek-v4-flash | high` for 3
> points *less* accuracy.**

### Cost per correct answer (CPC)

A frontier tells you what is not stupid. It does not give you a single number to
rank things by. For that you need a metric, and yours is:

```
CPC = total dollars spent ÷ number of problems solved
```

*"How much does one working program cost me?"*

It is better than cost-per-call because it charges you for failures. A cheap
configuration that fails constantly has a *bad* CPC — you paid many times for
one success.

**TPC** (tokens per correct) is the same idea denominated in tokens. Useful
because it is price-independent, so it survives a price change.

Your measured spread:

| config | CPC |
|---|---|
| `deepseek-v4-flash \| off` | **$0.00021** |
| `deepseek-v4-flash \| high` | $0.00193 |
| `deepseek-v4-pro \| high` | $0.01224 |
| `kimi-k2.6 \| high` | **$0.06320** |

**305× from cheapest to dearest.** Or, as research-framing puts it: the
difference between a $50 and a $15,000 monthly bill for the same work.

⚠️ **But notice which problems each row sat.** The cheapest row is over 107
problems and the dearest over 22 — *different* problems, with a different
difficulty mix. So that 305× mixes a price difference with an exam difference.
On the 22 problems those two configurations actually share it is **228×**, and
across the six configurations that all sat the identical 60-problem exam the
full spread is **65×**. `scripts/results.py` prints all three. This is the
single most likely place for an examiner to catch a denominator error, so learn
the habit here: *a ratio between two rows is only a ratio if both rows sat the
same exam.*

### Mixing: why "the best single option" is a weak baseline

Here is the idea that makes your Chapter 6 sharp, and it is genuinely
counter-intuitive at first.

You have 100 problems and a budget. Nobody says you must send them all to the
same configuration. **Send 70 to A and 30 to B.** Then:

- your cost is `0.7 × cost(A) + 0.3 × cost(B)`
- your accuracy is `0.7 × acc(A) + 0.3 × acc(B)`

Both are *weighted averages*. Which means: on the cost-accuracy plot, you land
exactly on **the straight line between A and B** — and by changing the split you
can land anywhere on that line.

```
accuracy
       │            ● B
       │         ╱      ← every point on this line is achievable
       │      ╱            just by splitting traffic
       │   ╱
       │● A
       └──────────────→ cost
```

So the set of achievable strategies is not five dots. It is the whole shaded
region under the lines connecting them — the **convex hull**.

And the useful consequence:

> **A configuration can be on the Pareto frontier and still be worthless**, if it
> sits *below* the line between two others. You could get its accuracy more
> cheaply by mixing.

The **upper convex hull** is the set of configurations that survive *that*
stricter test. In your data it has **exactly two vertices**: `flash|off` and
`flash|high`. Every other configuration — all eight of them — is beaten by some
mixture of those two.

### Why this matters for judging a router

Your proposal promised the router would beat *"the strongest single
configuration"*.

That bar is **too low**, and here is the formal reason (THESIS.md §10.1):

> **Proposition.** The optimal non-adaptive budget-constrained routing strategy
> randomizes between at most **two** configurations, and lies on the upper
> convex hull.

Because a mixture already beats the best single configuration at almost every
budget, "beats the best single model" is nearly free and proves almost nothing.

The honest bar is: **beat the hull**. And the hull is a fair opponent to beat,
because it has one crippling weakness — **it is blind to the problem.** It splits
traffic by a fixed percentage without looking at what it was asked. A router
*reads the problem first*.

Which gives you a much sharper way to state what a router is even for:

> **A router's margin over the convex hull is the measured value of
> problem-level information.**

That sentence is one of the best things in your thesis. It converts a vague
engineering goal ("build a good router") into a *measured quantity*.

### The oracle — a cheat with a purpose

An **oracle** is an imaginary strategy that already knows the answers. For each
problem it picks the cheapest configuration that *actually solves that problem*
— which you know, because you ran them all.

It is not a method. You could never deploy it. It is an **upper bound**: no
router can do better, because no router can know more.

Your three numbers, on the 60 problems shared by six configurations:

| strategy | accuracy | cost per problem |
|---|---|---|
| Oracle (cheats) | **98.3%** | $0.00111 |
| Problem-blind mixture, same budget | **84.5%** | $0.00111 |
| **Gap** | **13.8 points** | |

**13.8 points is the entire prize.** It is what problem-level information is
worth. Any router lives inside that gap, and lesson 18 is the story of one that
captured **none** of it.

Notice also that the oracle reaches 98.3% *more cheaply* than any single
configuration that reaches 98.3%. That is the value of adaptivity in one line.

### One more name: the knapsack

"Pick one configuration per problem, maximise total solved, stay under budget"
is a classic optimisation problem — the **multiple-choice knapsack problem
(MCKP)**. Each problem is an item; each configuration is a way of taking it, with
its own weight (cost) and value (does it solve it).

You do not need to *solve* an MCKP anywhere. Naming it matters for two reasons:

1. It tells the reader your oracle is the integer optimum of a known problem,
   not something ad hoc.
2. **Honesty.** THESIS.md §10 says so explicitly: MCKP is classical, the k-NN
   bound is Cover & Hart (1967), bootstrapping is standard. What is *yours* is
   the gap decomposition and applying the right frame to a literature that
   benchmarks loosely.

**Do not call it new mathematics.** Correctly applying known formalism is a real
contribution, and claiming more is the fastest way to lose an examiner's trust.

---

## Why it is in *your* thesis

This lesson *is* Chapter 6, in advance. Every term appears in your results:

| Term | Your number |
|---|---|
| Dominance | 8 of 10 configurations are dominated |
| Pareto frontier | computed by `analysis.pareto_front()` |
| Upper convex hull | **two vertices only**: `flash\|off` and `flash\|high` |
| CPC | 305× spread, $0.00021 → $0.06320 |
| Oracle | 98.3% at $0.00111/problem |
| Value of problem-level information | **13.8 points** |
| MCKP | the frame that makes the oracle principled |

And one implementation detail worth knowing before Part 3: the convex hull is
computed **without scipy**. A 2D upper hull is a twenty-line monotone chain, and
adding a heavyweight dependency for twenty lines would have been silly. That
kind of judgement — knowing when *not* to add a tool — is worth a sentence in
your Method chapter.

---

## Do this

**1. Do the dominance check by hand.**

Go back to the five-option table at the top. Cover the answer. Which options are
dominated, and by what? *(Answer: E by A; D by B.)*

**2. See your own frontier and hull.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ4/,/RQ3/p'
```

Find the hull's two vertices, the oracle's accuracy and cost, and the 13.8-point
gap.

**3. Look at the picture.**

```bash
uv run python scripts/make_figures.py && open data/figures/03-frontier-and-hull.png
```

Every configuration is a dot. Find the two hull vertices, then find
`deepseek-v4-pro | high` sitting up and to the right of `flash | high` —
expensive and worse. That single dot is a whole paragraph of your thesis.

**4. Convince yourself mixing works.**

`flash|off` is $0.00016 at 65.0%. `flash|high` is $0.00177 at 98.3%. Send half
your traffic to each:

- cost = `(0.00016 + 0.00177) ÷ 2` = **$0.000965**
- accuracy = `(65.0 + 98.3) ÷ 2` = **81.65%**

Now compare that to any *single* configuration costing about $0.000965. If none
of them reaches 81.65%, you have just shown by hand why the hull is the right
baseline and a single model is not.

---

## Check yourself

1. Define dominance. Why is a dominated option never rational to choose?
2. Why is "which configuration is best?" a malformed question?
3. What is CPC, and why is it better than cost per API call?
4. Explain why splitting traffic between two configurations puts you on the
   straight line between them.
5. Why is "beats the best single configuration" a weak bar for a router?
6. What is the oracle, and what is it for, given it can never be deployed?
7. What does the 13.8-point gap mean in plain words?
8. Why does your thesis name the MCKP even though it never solves one?

<details>
<summary>Answers</summary>

1. X dominates Y if X is at least as good on every dimension and strictly better
   on at least one. Choosing Y means paying more (or the same) for less — there
   is no budget or preference under which it makes sense.
2. Because the options differ on two dimensions with no fixed exchange rate
   between them. "Best" only exists once you state what you will pay for
   accuracy.
3. Total spend ÷ problems solved. It charges you for failures, so a cheap
   configuration that fails often is correctly penalised.
4. Because both total cost and total accuracy are weighted averages of the two
   configurations' values, and a weighted average of two points is a point on
   the segment joining them.
5. Because a fixed traffic split already beats the best single configuration at
   almost any budget, so clearing that bar demonstrates nothing about reading
   the problem.
6. A strategy that always picks the cheapest configuration that actually solves
   each problem. It is an upper bound — the ceiling any router is measured
   against.
7. Knowing something about the problem before choosing is worth 13.8 accuracy
   points, at the same budget, compared with a strategy that never looks.
8. To show the oracle is the integer optimum of a known formal problem rather
   than an ad-hoc construction — and to be explicit that the mathematics is
   borrowed, not invented.

</details>

---

**🎉 Part 1 complete.** You now have every concept the thesis is built from:
tokens, reasoning tokens, prices and providers, benchmarks and grading, SQL,
denominators and intervals, frontiers and oracles.

From here on, everything is *your data*.

➡️ Next: [Lesson 11 — The question, and why it is real](11-the-question.md)
