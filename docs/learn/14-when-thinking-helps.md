# Lesson 14 — Finding 2: thinking works, conditionally

*Part 2 · about 45 minutes · after lesson 13*

**This is the headline answer to the thesis question.**

---

## In one sentence

> The value of reasoning is a property of the **(model, difficulty) pair**, not
> of difficulty alone: on hard problems it takes one model from 29.2% to 82.1%
> and another from 22.1% down to 3.8%. The aggregate "+29.3 points" is the
> average of those opposite effects, and should not be quoted bare.

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

### 🔴 First, the bigger problem: that table is an average over opposite effects

Every row above pools all five models together. Split by model and the hard-tier
row does not just shrink — **it changes sign**:

| tier | model | off | high | delta | censored |
|---|---|---|---|---|---|
| hard | `deepseek-v4-flash` | 29.2% (154) | **82.1%** (28) | **+52.9** | 11% |
| hard | `qwen3.6-35b-a3b` | 22.1% (154) | 27.6% (29) | +5.5 | 17% |
| **hard** | **`qwen3.5-9b`** | 22.1% (145) | **3.8%** (26) | **−18.2** | **81%** |
| medium | `deepseek-v4-flash` | 62.5% (104) | **94.4%** (36) | **+31.9** | 0% |
| medium | `qwen3.6-35b-a3b` | 52.9% (104) | 72.2% (36) | +19.3 | 6% |
| medium | `qwen3.5-9b` | 43.6% (101) | 38.7% (31) | −4.9 | 52% |
| **MBPP+** | **`qwen3.5-9b`** | 80.0% (20) | **55.6%** (18) | **−24.4** | **0%** |
| HumanEval+ | `qwen3.5-9b` | 90.5% (21) | 94.7% (19) | +4.3 | 0% |

> **"+29.3 on hard" is the average of +52.9 and −18.2.**

That is not a small correction. It means **reasoning is not a property of the
difficulty tier at all** — it is a property of the **(model, tier) pair**. One
model gains 53 points from thinking on hard problems; another loses 18 on the
same problems.

#### The `censored` column is what makes this interpretable

Remember from lesson 09: a call stopped at the token ceiling **cannot** have
succeeded. So before reading any negative delta as "reasoning made the model
worse", check how much of the thinking arm was simply cut off. Two very
different things are hiding in that table:

**1. Non-termination — a measurement effect as much as a model effect.**

`qwen3.5-9b|high` on hard problems: **81% of its calls hit the 48,000-token
ceiling**, 77% returned no code at all, mean reasoning length **24,826 tokens**.
`deepseek-v4-flash|high` on the *same problems* censors at 11%.

So the small model's −18.2 is mostly *it never stopping thinking*. And note the
honest framing: a fixed ceiling censors a rambling model far harder than a
concise one, so part of that number is our ceiling, not the model. Say both.

**2. Genuine degradation — and this is the cleanest result you have.**

On MBPP+, the same `qwen3.5-9b`:

- censoring: **0%**
- mean reasoning: **368 tokens** — it barely thought at all
- every call terminated normally, every failure produced extracted code and
  failed on **assertions** (wrong answers, not crashes, not truncation)
- and it fell from **16/20 to 10/18 on the same twenty problems**

**Truncation is ruled out. The model simply got easy problems wrong that it had
got right without thinking.** That is overthinking, observed directly, in a
paired within-model design. Nothing else in the thesis is this clean.

#### What to say, and what it buys you

The practitioner rule that comes out of this is better than the one the
aggregate gave you:

> Enable reasoning on a **capable** model for **hard** problems. On a small
> model it can cost you accuracy at *both* ends — it fails to terminate on hard
> problems and it talks itself out of correct answers on easy ones.

And when someone asks why you did not just report the tier averages:

> Because averaging +52.9 and −18.2 into +29.3 describes neither model, and a
> practitioner acting on +29.3 with the small model would lose accuracy.

Reproduce: `uv run python scripts/results.py`, section **⚠ THE EFFECT IS PER
MODEL**, or `carr.analysis.within_model_effect()`.

⚠️ One more thing about the aggregate table: its **easy-benchmark rows are
model-confounded**. The `high` arm on MBPP+ is 62% `qwen3.5-9b` and on
HumanEval+ 58%, while the `off` arm is roughly a quarter each of four models. So
"MBPP+ 72.3% → 73.3%" compares a four-model average against a mostly-one-model
average, and the flatness is partly composition.

### 🔴 Second: those two arms did not sit the same exam

This is the most important caveat in the lesson, and it was found late — after
the rest of this course was written. **Learn it properly, because an examiner
who finds it before you do will take the headline away from you.**

LiveCodeBench contains two kinds of problem:

- **stdin→stdout programs** from AtCoder — read input, print output. 217 of 342.
- **`Solution`-class methods** from LeetCode — fill in a method body. 125 of 342.

They are not equally hard, and the two effort arms are covered *very* unevenly:

| hard tier | stdin | functional |
|---|---|---|
| reasoning **off** | **348** | 114 |
| reasoning **high** | **8** | **110** |

So the `off` column above is mostly AtCoder and the `high` column is almost
entirely LeetCode. Some of that "+29.3 from reasoning" is really "+ from an
easier kind of problem".

**Why it happened — and it is mechanical, not a decision anyone made.**
`runner.plan` sorts the work list by `(expected_usd, problem_id)`. Inside one
configuration every cell costs the same in expectation, so the tiebreak is the
**problem id, compared as a string**. LeetCode ids look like
`LiveCodeBench/3487`; AtCoder ids look like `LiveCodeBench/abc374_a`. Digits
sort before letters. So **all 125 functional problems ran before any of the 217
stdin ones**, and the expensive thinking arm — which runs last under
cheapest-first — hit the cost cap while still inside the functional prefix.

**The fix is free**, because it is a re-analysis of rows already bought:

| tier | style | off | on | matched gap | raw gap |
|---|---|---|---|---|---|
| **hard** | functional | 31.6% (n=114) | **57.3%** (n=110) | **+25.7** | +29.3 |
| **medium** | functional | 49.1% (n=163) | **78.0%** (n=141) | **+28.9** | +23.0 |

**Three things to take from that table.**

1. **The finding survives.** The direction holds on both tiers and the effect is
   still very large.
2. **It is not uniformly flattering.** Matching *shrinks* the hard gap by 3.6
   points and *grows* the medium gap by 5.9. A confound that moved everything one
   way would be suspicious; this one behaves like a real composition effect.
3. **The wording has to change.** "More than doubles" is a property of the
   confounded pair. The defensible sentence is *"on hard function-style problems,
   reasoning multiplies the pass rate by 1.8, from 31.6% to 57.3%."*

And say the thing you cannot say: **nothing here tells you what reasoning does
on stdin-style problems.** That arm is n=8. Refusing to report a rate from eight
observations is a better answer than reporting one.

Reproduce it: `uv run python scripts/results.py`, section **⚠ STYLE CONFOUND**,
or `carr.analysis.style_matched_effect()`.

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
| Style-matched | Thinking **× 1.8**: 31.6% → 57.3% | comparing like with like |

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
3. Why is 57.3% a floor rather than an estimate?
2b. Why is "+29.3 points on hard" not a finding, and what replaces it?
2c. Which of the two negative deltas for `qwen3.5-9b` is a model property and
   which is partly an artefact of your token ceiling? How do you tell?
3b. Why did the two effort arms end up on different kinds of problem, and what
   is the matched figure?
4. Your pilot said thinking made hard problems *worse*. What happened, and why
   is it good that this is in your written history?
5. Why must the per-tier table be reported alongside a paired comparison?
6. Give the practitioner's answer, including the uncomfortable last sentence.

<details>
<summary>Answers</summary>

1. Per model, because the aggregate averages opposite effects: on hard,
   `deepseek-v4-flash` 29.2% → 82.1% (+52.9) while `qwen3.5-9b` goes 22.1% →
   3.8% (−18.2, but 81% of its thinking calls were truncated). The cleanest
   result is MBPP+, `qwen3.5-9b`, 80.0% → 55.6% on the same 20 problems with 0%
   truncation. The aggregate, if asked: reasoning off 24.9% vs on 54.2%
   (n = 462 / 118) — but
   quote the style-matched 31.6% vs 57.3% (n = 114 / 110), because the raw arms
   sat different exams; on
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
   problems (4.3× the tokens for 1–6 points, and negative for a small model);
   **and you cannot reliably tell in
   advance which you have.**

</details>

---

➡️ Next: [Lesson 15 — Finding 3: expensive failure](15-expensive-failure.md)
