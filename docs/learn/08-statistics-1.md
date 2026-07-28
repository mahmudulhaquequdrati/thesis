# Lesson 08 — Statistics I: samples, means, and the denominator

*Part 1 · about 1 hour · after lesson 07*

---

## In one sentence

> A percentage without its denominator is not a result — and in your data, two
> configurations' percentages are often computed over **different exams**.

---

## The idea, from zero

### Population and sample

The **population** is everything you care about: *all code problems a person
might ever ask a model to solve.* You cannot measure that. It is infinite and
partly not yet written.

So you take a **sample** — 320 problems — measure those, and hope they represent
the population.

Every statistical worry in your thesis is a version of one question:

> **How much of what I saw in the sample is real, and how much is the sample?**

### The mean, and its blind spot

The **mean** (average) is the sum divided by the count. It is the right summary
when values cluster around a middle.

It is a terrible summary when they do not. Consider reasoning-token counts on
hard problems:

```
280, 340, 410, 520, 640, 48000
```

Mean: **8,365**. But five of the six calls used under 700 tokens. The mean
describes none of them; it describes the one runaway.

The **median** is the middle value when sorted — here **465** — and it is
immune to the runaway.

This matters concretely for you. Your Day 2 prompt-size measurement is reported
as a **median** (99 tokens for HumanEval+), and your reasoning-token findings as
**means** (17,547 on LCB hard). Those choices are not interchangeable:

- Use the **mean** when you care about *totals* — cost is a sum, so mean tokens
  × price = total spend. That is why cost analysis uses means.
- Use the **median** when you care about *the typical case*, and a few extreme
  values would mislead.

An examiner may ask why. That paragraph is your answer.

### Pass rate is a mean too

If `passed` is 1 or 0, then the average of that column **is** the pass rate:

```
1, 0, 1, 1, 0   →  mean 0.6  →  60% pass rate
```

Which is why your SQL says `AVG(passed)`. It looks like a trick; it is just
arithmetic.

### ⚠️ The denominator is part of the number

*"Pass rate 54.2%."*

Out of how many? Five problems, or five hundred? Because:

| Passes / attempts | Rate | How much would you bet on it? |
|---|---|---|
| 3 of 5 | 60% | Almost nothing |
| 300 of 500 | 60% | Quite a lot |

Same number. Completely different claim. A rate without an *n* is not a finding;
it is a rumour.

This is why every line of your `scripts/results.py` prints its denominator, and
why your own findings are always written like this:

> On LCB hard, reasoning off scores **24.9%** and reasoning on **54.2%**
> (**n = 462 / 118**).

Note that even the two arms have different *n*. That is the next problem.

### ⚠️ The comparability trap — the most important idea in this lesson

Your grid is **unbalanced**. Not every configuration ran on every problem:

| Configuration group | Problems each |
|---|---|
| `off` configurations | 320 |
| `high` configurations | 51–104 |
| the held-out model (kimi) | 16–23 |

Why? Money. Thinking calls cost 10–100× more, so you bought fewer of them.
Entirely reasonable.

But now watch what happens if you are careless. Suppose you compute each
configuration's cost-per-correct **over its own problems**:

- `flash|off` ran all 320, including 164 easy HumanEval+ problems it aces
- `flash|high` ran 104, weighted heavily toward LCB hard

Then you compare the two numbers and announce which configuration is better.

**You have just compared two students who sat different exams.** One did the
easy paper. The other did the hard paper. The comparison is meaningless, and
nothing in the arithmetic will tell you so.

### The fix: the paired denominator

`analysis.paired_problems()` restricts every comparable statistic to the
problems where **both** effort arms were actually graded.

> **107 of 320.**

That is a painful number. Two thirds of your data cannot participate in a
head-to-head comparison. But 107 honest comparisons beat 320 dishonest ones, and
`scripts/results.py` prints that denominator next to every result so the
restriction is visible rather than buried.

The same logic drives the frontier analysis (lesson 17): it runs over **6
configurations × 60 problems**, because those 60 are the problems all six share.
All ten configurations share only **5** problems, which is useless — so the
analysis uses the largest *valid* set rather than the largest set.

Choosing the largest **valid** set rather than the largest set is a mark of a
careful thesis. Say it explicitly in Chapter 5.

### The unit of analysis: problems, not calls

You have 1,373 calls but only 320 problems. Which is your *n*?

**Problems.** And the reason is independence.

Statistics assumes your observations are independent — one does not tell you
about another. But ten calls on the same problem are **not** independent: if that
problem is brutally hard, all ten are likely to fail together. They are ten
measurements of *one* underlying difficulty, not ten separate facts about the
world.

So:

> **The unit of analysis is the problem. Every confidence interval resamples
> problems, never individual calls.**

Treating 1,373 calls as 1,373 independent observations would make your
uncertainty look about **twice as small as it is** — which is exactly the
direction that flatters you, and exactly the kind of error an examiner is
trained to look for.

### Two more traps, named

**Simpson's paradox.** A configuration can win on easy problems, win on hard
problems, and *lose overall* — if the two groups have different sizes and
different difficulty mixes. Defence: **always report per-difficulty
breakdowns.** THESIS.md §11 names this as a required mitigation, and it is why
every results table in your thesis is split by tier.

**Censoring.** If your instrument cannot record values above a limit, every
statistic about "large values" is biased by the limit rather than by the world.
Your `max_tokens` ceiling is exactly this, and it destroyed one of your
headlines. Lesson 16.

---

## Why it is in *your* thesis

Because your headline numbers are only defensible with their denominators
attached. Compare:

| Sloppy | Defensible |
|---|---|
| "Thinking doubles the pass rate" | "On LCB hard, 24.9% → 54.2% (n = 462 / 118 calls over 107 paired problems)" |
| "Cost per correct spans 305×" | "Over the 107 problems where both arms were measured, CPC spans $0.00021 to $0.06320" |
| "The oracle gains 13.8 points" | "Over the 60 problems shared by all six configurations, 98.3% vs 84.5%" |

The right-hand column is what gets marks. The left-hand column is what gets
questions.

And your saturation finding is *literally a denominator argument*:

> Of 320 problems, 81 are solved by everything and 98 by nothing. **Only 141
> discriminate.**

Which means: any statistic you compute over all 320 has 179 problems in it that
could not have come out differently no matter which configuration you chose.
They dilute every effect toward zero. Naming that is the finding.

---

## Do this

**1. See the denominators in your own output.**

```bash
cd ~/thesis
uv run python scripts/results.py | grep -i "n=" | head -20
```

Every result carries its *n*. Notice the ones where the two arms differ wildly.

**2. Feel the unbalanced grid.**

In Studio's SQL console:

```sql
SELECT config_id, COUNT(DISTINCT problem_id) AS problems
FROM generations WHERE is_mock = 0
GROUP BY config_id ORDER BY problems DESC;
```

You will see 320s at the top and small numbers at the bottom. **That spread is
the comparability trap made visible.**

**3. Find the paired set yourself.**

```sql
SELECT COUNT(*) FROM (
  SELECT g.problem_id
  FROM generations g JOIN results r USING (gen_id)
  JOIN configs c USING (config_id)
  WHERE g.is_mock = 0
  GROUP BY g.problem_id
  HAVING SUM(c.effort_label = 'off') > 0 AND SUM(c.effort_label = 'high') > 0
);
```

You are looking for a number near **107**. That is the honest denominator, and
you just derived it from raw rows.

**4. Mean versus median, on your own data.**

```sql
SELECT AVG(reasoning_tokens) FROM generations
WHERE is_mock = 0 AND reasoning_tokens > 0;
```

Now find the largest single value:

```sql
SELECT MAX(reasoning_tokens) FROM generations WHERE is_mock = 0;
```

Ask yourself how much of that mean is being carried by the tail. (Lesson 15 is
about exactly that tail.)

---

## Check yourself

1. What is the difference between a population and a sample, in your thesis?
2. When should you report a median instead of a mean? Which does cost analysis
   need, and why?
3. Why is "pass rate 54.2%" incomplete?
4. Explain the comparability trap in your own words, using the exam analogy.
5. Why is 107 the denominator for paired comparisons rather than 320?
6. Why is the unit of analysis the problem rather than the API call? What would
   go wrong otherwise?
7. Why must every results table be split by difficulty tier?

<details>
<summary>Answers</summary>

1. Population: all code problems anyone might ask a model to solve. Sample: the
   320 you measured. Everything statistical is about how far the sample can be
   trusted to speak for the population.
2. Median when a few extreme values would distort the typical case. Cost
   analysis needs the **mean**, because total cost is a sum and mean × count = total.
3. It has no denominator. 3 of 5 and 300 of 500 are both 60% and are not
   remotely the same claim.
4. Different configurations ran on different problem sets — one sat the easy
   paper, one the hard paper. Comparing their scores compares the papers, not
   the students, and the arithmetic gives no warning.
5. Because only 107 problems had **both** effort arms graded. Comparisons
   restricted to those are like-for-like; comparisons over all 320 are not.
6. Because multiple calls on one problem are not independent — they share that
   problem's difficulty. Treating 1,373 calls as independent would shrink the
   apparent uncertainty roughly twofold, in the flattering direction.
7. Simpson's paradox: with unequal group sizes and difficulty mixes, an overall
   average can reverse the direction seen in every subgroup. Per-tier breakdowns
   make that impossible to hide.

</details>

---

➡️ Next: [Lesson 09 — Statistics II: uncertainty and the bootstrap](09-statistics-2.md)
