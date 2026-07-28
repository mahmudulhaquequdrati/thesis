# Lesson 14 — Finding 2: thinking works, conditionally

*Part 2 · about 45 minutes · after lesson 13*

**This is the headline answer to the thesis question.**

---

## In one sentence

> On hard problems, enabling reasoning **more than doubles** the pass rate
> (24.9% → 54.2%). On the standard benchmarks it buys almost nothing — because
> they are already saturated.

---

## The finding

Pass rate with reasoning off versus on, per tier:

| tier | off | on | n (off / on) | gain |
|---|---|---|---|---|
| HumanEval+ | 92.9% | 97.0% | 85 / 33 | +4.1 |
| LiveCodeBench easy | 94.1% | 100% | 68 / 11 | +5.9 |
| MBPP+ | 72.3% | 73.3% | 83 / 30 | +1.0 |
| **LiveCodeBench medium** | **53.3%** | **76.4%** | 317 / 148 | **+23.1** |
| **LiveCodeBench hard** | **24.9%** | **54.2%** | 462 / 118 | **+29.3** |

Read the last two rows again. On hard problems, thinking takes you from **one in
four** to **more than half**.

### Why this is not trivially obvious

Three reasons, and you need all three ready, because "well, obviously" is the
first thing anyone says.

**1. The direction was not obvious — your own pilot said the opposite.**

The 16-problem pilot reported thinking scoring *worse* on hard problems: 31% vs
50%. If it had been obvious, the pilot would not have been believable enough to
worry about for a day. (It was truncation, not capability — lesson 16.)

**2. The *conditionality* is the result, not the direction.**

"Thinking helps" is a mood. **"Thinking is worth +29 points on hard problems and
+1.0 on MBPP+"** is a decision rule. The sharpness of the condition is the
finding: the benefit is not spread thinly across difficulty, it is concentrated
almost entirely at one end.

**3. Nobody had the price attached.**

Leaderboards report accuracy. Yours reports accuracy *and* what it cost. The
+1.0 points on MBPP+ is not free — it costs roughly 10× the tokens. Lesson 17
converts that into the economic statement.

### What the numbers do *not* say

Be exact here, because this is where over-claiming happens.

⚠️ **The two arms have different denominators** — 462 vs 118 on hard. They are
not the same problems in the same proportions. The comparable statistics run
over the **107 paired problems** (lesson 08), and `scripts/results.py` prints
the paired denominator next to every result. When you write this in Chapter 5,
report both: the per-tier rates *and* the paired comparison.

⚠️ **26.3% of hard thinking calls still truncate at the 48,000-token ceiling.**
A truncated call is scored as a failure. So **54.2% is a floor, not an
estimate** — the true capability of thinking on hard problems is somewhere above
it, and you cannot say how far above without paying for a higher ceiling.

That caveat is uncomfortable and you must state it anyway. It also strengthens
your headline rather than weakening it: your central claim is that thinking helps
on hard problems, and censoring biases that number *downward*.

⚠️ **This is pass@1 with one sample at temperature 0.** No variance estimate
within a configuration.

### The story of how this number changed — and why that is good

Track this finding across the project:

| Stage | What it said | Evidence |
|---|---|---|
| Pilot (2026-07-26) | Thinking is **worse** on hard: 31% vs 50% | 16 problems, 16k ceiling |
| Grid, first read | Thinking is **better**: 31.3% vs 24.9% | 320 problems, 48k ceiling |
| Grid, fully graded | Thinking **more than doubles**: 24.9% → 54.2% | grading completed |

The number moved a long way. **That movement is not embarrassing — it is the
scientific method visible in a log file.** What made it possible:

- The pilot's contradiction was **investigated**, not explained away.
- The cause was identified: the token ceiling was censoring the thinking arm.
- The ceiling was raised (16k → 32k → 48k) *before* the grid.
- The corrections were **recorded in the history on purpose**.

An examiner who reads your log sees a researcher who changed their mind when the
data changed. That is worth more than a project where nothing ever went wrong.

### The practitioner's answer

Your thesis exists to answer *"should I turn thinking on?"*. Here it is:

> **On hard problems, yes — it roughly doubles your success rate. On problems
> resembling standard benchmarks, almost certainly not — you pay about 10× the
> tokens for 1–6 points, and on many problems for nothing at all.**
>
> **And you cannot tell in advance which kind you have** — that is lesson 18, and
> it is the honest hard part.

That last sentence is what keeps the thesis from being a tidy story. Keep it in.

---

## Why it matters for the writing

This is the **centrepiece of Chapter 5**, and the table above is arguably the
single most important table in the thesis.

How to present it:

1. Lead with the **conditional** framing, not "thinking helps".
2. Show the per-tier table with denominators.
3. Immediately give the paired-problem comparison, so nobody has to ask.
4. State the censoring caveat *in the same section*, not buried in Chapter 8.
5. Point forward: the accuracy gain is only half the story — Chapter 6 prices it.

And in Chapter 1, this is the finding you promise. In Chapter 9, it is the
finding you convert into advice.

---

## Do this

**1. See the numbers.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ1/,/RQ2/p'
```

**2. Look at the picture.**

```bash
uv run python scripts/make_figures.py && open data/figures/01-effort-by-tier.png
```

Off vs on, per tier, **with error bars**. Note how wide the bars are on the
small-*n* tiers — that width is lesson 09 doing its job. A bare bar chart of
these numbers would imply a precision the data does not have.

**3. Derive it yourself in SQL.**

```sql
SELECT p.difficulty, c.effort_label,
       COUNT(*) AS n, ROUND(AVG(r.passed) * 100, 1) AS pass_rate
FROM generations g
JOIN results r USING (gen_id)
JOIN problems p USING (problem_id)
JOIN configs  c USING (config_id)
WHERE g.is_mock = 0
GROUP BY p.difficulty, c.effort_label
ORDER BY p.difficulty, c.effort_label;
```

**4. Find the censored calls.**

```sql
SELECT COUNT(*) FROM generations
WHERE is_mock = 0 AND finish_reason = 'length' AND reasoning_tokens > 0;
```

Every one of those is a call that was cut off. Every one is scored as a failure.
**That is why 54.2% is a floor.**

---

## Check yourself

1. State the headline finding with its numbers and denominators.
2. Give three reasons this is not "obviously true".
3. Why is 54.2% a floor rather than an estimate?
4. Your pilot said thinking made hard problems *worse*. What happened, and why
   is it good that this is in your written history?
5. Why must the per-tier table be reported alongside a paired comparison?
6. Give the practitioner's answer, including the uncomfortable last sentence.

<details>
<summary>Answers</summary>

1. On LiveCodeBench hard, reasoning off 24.9% vs on 54.2% (n = 462 / 118); on
   medium 53.3% → 76.4% (n = 317 / 148); on HumanEval+ 92.9% → 97.0% and MBPP+
   72.3% → 73.3%.
2. The direction was contradicted by your own pilot; the finding is the sharp
   *conditionality*, not the direction; and nobody else attaches the price to
   the accuracy.
3. Because 26.3% of hard thinking calls hit the 48,000-token ceiling and are
   scored as failures. Censoring biases the number downward, so the true value
   is somewhere above it.
4. The pilot's 16,000-token ceiling truncated thinking calls, which cannot
   succeed, so the thinking arm was measuring the ceiling. It is good because it
   shows the contradiction was investigated and the design fixed before the main
   spend, rather than a story where nothing went wrong.
5. Because the two arms ran on different problem sets (462 vs 118 calls), so the
   per-tier rates are not a like-for-like comparison on their own. The 107
   paired problems supply the honest denominator.
6. Yes on hard problems (roughly doubles success); no on standard-benchmark-like
   problems (~10× the tokens for 1–6 points); **and you cannot reliably tell in
   advance which you have.**

</details>

---

➡️ Next: [Lesson 15 — Finding 3: expensive failure](15-expensive-failure.md)
