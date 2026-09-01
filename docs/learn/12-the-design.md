# Lesson 12 — The experimental design

*Part 2 · about 1 hour · after lesson 11*

---

## In one sentence

> One row = one problem × one configuration = one paid API call — and every
> design decision in the project is about which rows to buy, in what order, and
> how to make sure you never buy one twice.

---

## The idea

### The unit: one row

```
   A PROBLEM        +      A CONFIG
   (LiveCodeBench)        (flash, thinking on)
                    |
                    v          ← ONE PAID API CALL
              raw response
                    |
                    v
           extract the code
                    |
                    v          ← FREE, runs the benchmark's real tests
              run the tests
                    |
                    v
   ONE ROW:  passed? tokens? reasoning tokens? dollars?
```

Do that 1,373 times and you have **the table**. The table is the thesis.

### The two axes

A **configuration** is a (model, thinking-mode) pair. Not a model. This is the
distinction the whole thesis rests on, so it deserves emphasis:

`flash|off` and `flash|high` are **the same model**. The only thing that differs
is whether reasoning is enabled.

**5 models × 2 effort levels = 10 configurations.**

| Model | Family | Role | out $/M (pinned) |
|---|---|---|---|
| `qwen/qwen3.5-9b` | qwen | cheapest tier, the frontier floor | 0.150 |
| `deepseek/deepseek-v4-flash` | deepseek | cost-efficient reasoner | 0.182 |
| `qwen/qwen3.6-35b-a3b` | qwen | mid tier | 1.000 |
| `deepseek/deepseek-v4-pro` | deepseek | frontier open-weight reasoner | 1.251 |
| `moonshotai/kimi-k2.6` | moonshot | **held out** for RQ5, subset only | 3.400 |

**Output prices span 22×.** Combine that with thinking's token multiplier —
**measured at 4.3×**, mean completion 3,166 tokens with reasoning off against
13,604 with it on, over 1,355 graded calls; the ~10× you will see quoted in
older notes was an estimate made before any data
and the most expensive configuration costs roughly **200×** the cheapest for the
same problem. *That spread is the thesis.*

### Design decision 1 — pair each model with *itself*

Why `qwen3.5-9b` off **and** `qwen3.5-9b` high, rather than two different small
models?

**Because within a pair, only the thinking mode changes.** If you compared
"small model without thinking" against "different model with thinking", any
difference could be the thinking *or* the model, and you could never separate
them. The word for that is **confounding**, and it is the thing experimental
design exists to prevent.

Holding the model constant across the effort axis is the single most important
structural choice in your experiment. One sentence in Chapter 3.

### Design decision 2 — cut *problems*, never cells

Budget got tight. Two ways to spend less:

| Option | Effect |
|---|---|
| Run fewer problems, all configurations each | Fewer rows, **grid stays complete** |
| Run all problems, skip some configurations | Same row count, **grid full of holes** |

You chose the first, and the reason is precise:

> The routing label is *"the cheapest configuration that passes this problem"*.
> That is only computable if **every** problem has been run through **every**
> configuration. A sparse grid destroys the ground truth.

⚠️ **And then reality intervened.** The grid ended up unbalanced anyway — `off`
configurations have 320 problems for three of five models (`pro|off` 51,
`kimi|off` 16), `high` 73–104, kimi 16–23 — because thinking
calls cost far more than projected and buying stopped at $5.25. So the principle
was right and the execution was partial, which is why `paired_problems()` (107
of 320) exists at all.

**Say this plainly in Chapter 3 and again in Chapter 8.** "We intended a
complete grid; cost forced an unbalanced one; here is the restriction that makes
comparisons valid anyway" is a strong paragraph. Pretending the grid is complete
is a hole an examiner will find in five minutes.

### Design decision 3 — one sample, temperature 0

One attempt per (problem, configuration). No repeats, no averaging.

- **Halves cost** — the biggest single lever available.
- **Makes the routing label deterministic** — "cheapest configuration that
  passes" becomes a fact rather than a coin flip.

Cost: you cannot measure *within-configuration variance*. If a configuration
gets a problem right by luck, you will not know. Honest limitation, stated in
Chapter 8.

⚠️ And log `temperature_sent`, because some thinking endpoints silently override
it. Record what you asked for, not just what you got.

### Design decision 4 — cheapest configurations first

The run is ordered by ascending **expected** cost, globally across all problems
— not problem by problem.

Why: **if the cost cap fires, you want a complete cheap foundation, not a random
half of every problem.** The cheap rows are the ones every analysis needs; the
expensive tail is the part you can most afford to lose.

Note a subtlety in your decisions log: run *order* is by **expected** cost, but
`config_id` is a stable identity that must never move. They are different things
and they live in different columns (`tier_index` vs `config_id`) — the bug in
lesson 07 happened because they were once the same thing.

### Design decision 5 — the pilot as a gate

Before the full grid you ran a **pilot**: 15 difficulty-spread problems × 10
configurations, $0.578.

Its job was not to produce results. It was to **measure the one number the whole
budget depended on** — mean thinking tokens on hard problems — because the grid's
cost estimate swung from $3.55 to $8.69 depending on that number alone.

It also found three things that changed the design:

1. **Saturation confirmed and quantified** — the easy benchmarks give no signal.
2. **Routing collapse visible** — 81% of problems shared one cheapest-passing
   configuration.
3. ⚠️ **The effort axis was confounded by `max_tokens`** — 7 of 16 thinking calls
   on hard problems hit the 16,000-token ceiling and returned nothing, making
   thinking look *worse* than not-thinking. That was truncation, not capability.

Finding 3 is why the ceiling went 16k → 32k → 48k before the grid ran.

> **The general principle: spend a little to find out what the big spend will
> cost, and be willing to redesign when it tells you something you did not
> want.** A pilot that only confirmed your plan would have been a waste of $0.58.

### What actually got bought

| | |
|---|---|
| Problems in the pool | **884** (HumanEval+ 164, MBPP+ 378, LiveCodeBench 342) |
| Problems run | **320** |
| Configurations | **10** |
| Generations | **1,373** (1,025 no-reasoning, 348 thinking) |
| Graded | **1,280** |
| Spend | **$5.25** — against $15 loaded and a $6 abort threshold |

The 884-vs-320 gap is a budget decision, not a sampling one, and you should say
so: every problem costs 10 API calls.

### Sampling: stratified and seeded

The 320 were not the first 320. They were **stratified** — sampled deliberately
across benchmarks and difficulty tiers — with a **fixed seed**.

Why stratified: a pilot over `HumanEval/0..9` would have reported ~100% pass
everywhere and taught you nothing. The grid was re-weighted after the pilot so
that the easy benchmarks became 20-problem *anchors* (they measure the
saturation *finding*) and all 258 LCB medium+hard problems went in.

Why seeded: rerun it and you get the same 320. Reproducibility is graded.

---

## Why it matters for the writing

Chapter 3 (Method) is this lesson, expanded, in this order:

1. The unit of measurement (one row)
2. The roster, and provider/quantization pinning (lesson 04)
3. The effort axis, and why models are paired with themselves
4. Problem selection: pool, stratified sample, seed
5. The protocol: pass@1, temperature 0, one sample
6. Grading (lesson 06)
7. Cost measurement and reconciliation
8. Cost controls: the cap, the ordering, `request_hash`
9. **What went wrong and how it was handled** — the pilot's findings, the ceiling
   changes, the unbalanced grid

Item 9 is the one most students omit, and it is the one that makes a method
chapter credible. A method section describing a plan that went perfectly reads
as fiction to anyone who has run an experiment.

---

## Do this

**1. See the configurations.**

```bash
cd ~/thesis
uv run python scripts/view.py --list | head -20
```

**2. See one problem across all ten.**

```bash
uv run python scripts/view.py HumanEval/0
```

Ten configurations, ten passes, a **44× cost spread** as the database stands
today (**58×** as first observed, before providers were pinned re-priced the
roster — see lesson 04). The last line names the
cheapest configuration that solved it — that is the routing label.

**3. Look at the grid's real shape.**

In Studio (`uv run python scripts/studio.py`):

```sql
SELECT c.model_slug, c.effort_label, COUNT(DISTINCT g.problem_id) AS problems
FROM generations g JOIN configs c USING (config_id)
WHERE g.is_mock = 0
GROUP BY c.model_slug, c.effort_label
ORDER BY problems DESC;
```

Look at the imbalance. Then say out loud what `paired_problems()` does about it.

**4. Read the experiment's own configuration file.**

```bash
cat config/experiment.yaml
```

Note `"off"` is **quoted**. YAML parses bare `off` as the boolean `False` — an
hour-long bug waiting to happen, prevented by two characters.

---

## Check yourself

1. What is one row of your table?
2. Why pair each model with itself across the effort axis instead of comparing
   different models?
3. Why cut problems rather than grid cells — and did that plan survive?
4. Why one sample at temperature 0? What does it cost you?
5. Why run cheapest configurations first, globally rather than per problem?
6. What was the pilot *for*, and name two things it changed.
7. You ran 320 of 884 problems. Is that a sampling decision or a budget
   decision?

<details>
<summary>Answers</summary>

1. One problem × one configuration = one paid API call, with its pass/fail,
   token counts, reasoning tokens and cost.
2. So that within a pair only the thinking mode varies. Comparing different
   models would confound the effort effect with the model effect, with no way to
   separate them afterwards.
3. Because the routing label needs every problem run through every
   configuration; holes destroy the ground truth. It survived only partially —
   thinking calls cost more than projected, so the grid is unbalanced and
   `paired_problems()` (107 of 320) restores valid comparisons.
4. It halves cost and makes the cheapest-passing label deterministic. The cost
   is that you cannot measure within-configuration variance — a lucky pass is
   indistinguishable from a reliable one.
5. So that if the cap fires you are left with a complete cheap foundation rather
   than a random fraction of every problem.
6. To measure mean thinking tokens, the number the whole budget estimate hinged
   on. It confirmed saturation, revealed routing collapse, and exposed that
   `max_tokens` was confounding the effort axis — which forced the ceiling from
   16k to 48k before the grid ran.
7. A budget decision: every problem costs 10 API calls. Worth stating explicitly
   so nobody reads it as a filtered sample.

</details>

---

➡️ Next: [Lesson 13 — Finding 1: most benchmark problems are useless](13-saturation.md)
