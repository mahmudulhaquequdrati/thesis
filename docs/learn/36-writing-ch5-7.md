# Lesson 36 — Writing Chapters 5, 6 and 7

*Part 4 · about 4 hours of writing · after lesson 35*

**These three chapters are where the thesis lives. The evidence is done — this
is transcription plus care.**

---

## In one sentence

> Every results paragraph is the same four moves: the claim, the number with its
> denominator, the interval or caveat, and what it means — and no paragraph
> contains a number you have not copied from `results.py`.

---

## The universal results paragraph

```
1. THE CLAIM        one sentence, in plain words
2. THE EVIDENCE     the number, with its denominator
3. THE UNCERTAINTY  the interval, or why the number is a floor
4. THE MEANING      what someone should conclude — and not conclude
```

Worked example:

> **Reasoning improves the pass rate far more on hard problems than on easy
> ones.** On LiveCodeBench hard, the pass rate rises from 24.9% with reasoning
> disabled to 54.2% with it enabled (n = 462 and 118 calls respectively, over the
> 107 problems where both arms were graded). **26.3% of hard thinking calls
> truncate at the 48,000-token ceiling and are scored as failures, so 54.2% is a
> lower bound.** The value of reasoning is therefore conditional on difficulty,
> and the condition is sharp: on MBPP+ the same manipulation moves the pass rate
> by 1.0 points.

Four moves. Roughly 90 words. **Write forty of these and you have a results
section.**

---

## Chapter 5 — Results

### 5.1 Saturation — and it must come first

Because it tells the reader how to read everything after it.

Structure: the risk named in advance (quote your own risk register) → the first
observation (`HumanEval/0`, 10/10, 58× cost spread) → the measurement (81 solved
by all, 98 by none, **141 discriminate** of 320) → the per-tier table → the
consequence (every later result is reported per tier) → the generalisation for
other researchers.

⚠️ **Frame it as a finding, not an apology.** The claim is about the field's
measurement practice, not about your budget.

### 5.2 When thinking helps

The headline table, with `n` on every row. Then the paired comparison over the
107 problems. Then the censoring caveat **in the same section**.

Figure: `01-effort-by-tier.png`.

### 5.3 Reasoning length and difficulty

642 → 773 → 2,693 → 10,183 → **17,547** mean reasoning tokens, monotonic across
tiers. Note it as a small validity check: the models' internal effort tracks the
benchmark's difficulty labels.

### 5.4 Expensive failure

The three-way outcome table. Lead with the near-identity of passed (7,567) and
failed (7,577) — that is what makes the third row (**29,584**, no answer)
surprising.

Then convert to money **immediately**: $0.56, about **15% of all spend**, bought
nothing.

Then scope the claim: non-termination is not novel (three citations); the
economic framing is the contribution. And state that your data cannot fully
separate genuine non-termination from truncation.

Figure: `02-reasoning-vs-outcome.png`.

### 5.5 Cost per correct answer

Define CPC = Σcost ÷ Σsolved. State it is a ratio estimator, therefore biased,
and bootstrapped over **problems, not calls**.

The table, with intervals. **$0.00021 to $0.06320 — 305×.**

Then the sentence that earns its keep:

> Five adjacent configuration pairs have overlapping intervals, so their ordering
> is not established despite distinct point estimates. Reporting these bare —
> which is the norm — would have manufactured a ranking the data does not
> support.

---

## Chapter 6 — The frontier

### 6.1 The denominator, first

6 configurations × 60 problems, because all ten share only 5. **The largest
valid set, not the largest set.** One sentence, and it prevents the obvious
question.

### 6.2 Frontier and dominance

Define dominance. Present the points. Note that 8 of 10 configurations are
dominated.

### 6.3 The dominated frontier model

> `deepseek-v4-pro | high` costs six times more than `deepseek-v4-flash | high`
> and scores three points lower (95.0% against 98.3%). **The accuracy intervals
> overlap ([95, 100] against [88, 100]), so the direction is suggestive rather
> than established; what the data does support is that the more expensive model
> shows no measurable advantage at six times the price.**

The caveat is in the same sentence as the claim. That is how to write a strong
result you cannot fully establish.

### 6.4 Why the hull is the baseline

The proposition, its two-line LP justification, and the honest attribution:
standard linear programming, not new mathematics. Then the payoff:

> A router's margin over the convex hull is the measured value of problem-level
> information.

### 6.5 The oracle and the 13.8 points

Oracle 98.3% at $0.00111/problem; problem-blind mixture at the same budget
84.5%; gap **13.8 points**. Name it as MCKP's integer optimum. Note the oracle
reaches 98.3% more cheaply than any single configuration that reaches it.

Figure: `03-frontier-and-hull.png`.

### 6.6 The router, and why it failed

**Do not apologise. Do not bury it.**

Order: what was built (free features only, and why that constraint is the
claim) → how it was evaluated (leave-one-out, against the hull) → the result
(65.0%, **+0.0 points**, collapsed to one configuration) → **the decomposition**
(0.0 feature insufficiency, 33.3 estimation error) → the mechanism (the
cheapest-passing label is dominated by one configuration, so a modal vote returns
it everywhere) → the named fix (a cost-aware objective) → the caveat (the ceiling
is fitted over 12 buckets on 60 problems).

And one sentence you should not leave out:

> The baseline here is the convex hull rather than the best single configuration.
> Against the latter, this router would have appeared to succeed.

That is you telling the examiner you chose the harder test. Say it.

---

## Chapter 7 — Runtime abort

**Write this one as a narrative.** The reasoning is the contribution; the final
number is modest.

**7.1 The mechanism.** Three measured facts: reasoning visible live via
`delta.reasoning`; cancellation billed $0.00 on two providers; ex-ante control
does not work. Therefore a runtime abort is the only functioning control.

**7.2 The claim, as it was believed.** Abort at 10,000 reasoning tokens: keeps
42/42 passes, saves 44%. Present it as you presented it at the time.

**7.3 The doubt.** 43.8% of LCB-hard thinking calls truncated at the 16,000
ceiling. And then the insight: **a censored call cannot succeed**, so the pilot
could never have observed a success above its ceiling. Use the thermometer
analogy — a device that maxes at 40°C can never disprove "it never gets hotter
than 40°C".

**7.4 The refutation.** At 48,000: **56 calls above 10,000 reasoning tokens
succeeded.** The cliff becomes a gradient — 83.8% under 10k, 55.2% at 10–20k,
39.3% above 20k. `best_threshold()` returns None.

**7.5 What survives.** Abort at 16,000 keeps 212/242 solutions — **88% [82, 92]**
— for a **49% [35, 61]** saving. State that the curve is a **simulation** over
completed calls, valid because cancellation is billed nothing.

**7.6 Residual censoring.** 26.3% still truncate at 48,000, so the right-hand
band is a floor. Explain why the ceiling was raised rather than removed: without
one, the worst case is bounded only by context length, and the cost cap computes
its reservation from `max_tokens`.

**7.7 The general lesson.**

> A truncation limit is a censoring mechanism, and censored observations bias any
> analysis of the quantity being truncated.

Figure: `04-abort-tradeoff.png`.

---

## Rules for all three chapters

1. **Never write a number from memory.** Copy from `results.py` output every
   time. Memory introduces transcription errors that are invisible and fatal.
2. **Denominator on every rate.** No exceptions.
3. **Interval or caveat on every headline.**
4. **Caveats travel with claims**, in the same paragraph — never deferred to
   Chapter 8.
5. **State what may *not* be concluded.** "The ordering is not established" is a
   result.
6. **One figure per claim**, referenced in the text by number and interpreted in
   words. A figure nobody explains is decoration.

---

## Do this

**1. Freeze your numbers.**

```bash
cd ~/thesis
uv run python scripts/results.py > /tmp/thesis-numbers.txt
```

Write with that file open. Every number gets copied.

**2. Write §5.1 today.** 400–600 words, using the six-step structure. You know it
cold.

**3. Write the four-move paragraph for three findings** — thinking helps, waste,
CPC spread. Check each has: claim, number + denominator, uncertainty, meaning.

**4. Audit yourself.** After a session, search your draft for `%` and check every
one has an `n` nearby. Then search for "significant", "clearly", "dramatically" —
each must be either backed by a number or deleted.

---

## Check yourself

1. Give the four moves of a results paragraph.
2. Why must saturation be the first results section?
3. Why does the frontier chapter open with its denominator?
4. How do you write a strong claim whose intervals overlap?
5. Why is Chapter 7 written as a narrative rather than as a tidy summary?
6. Why should the sentence about choosing the hull baseline appear explicitly?
7. Why must numbers be copied rather than remembered?

<details>
<summary>Answers</summary>

1. The claim in plain words; the number with its denominator; the uncertainty
   (interval, or why it is a floor); the meaning, including what may not be
   concluded.
2. Because it determines how every later number must be read — 179 of 320
   problems cannot distinguish configurations, so any aggregate over all of them
   is diluted.
3. Because 6 × 60 is unusual and invites the question "why not 10 × 320?".
   Answering first — all ten share only 5 problems, so this is the largest valid
   set — prevents it.
4. Put the caveat in the same sentence: state the comparison, then state that the
   intervals overlap so the direction is suggestive, then state the weaker claim
   the data does support.
5. Because the contribution is the reasoning — how a token ceiling manufactured a
   finding — rather than the final number, which is a modest tradeoff.
6. Because it shows you chose the harder comparison; against the best single
   configuration the router would have looked successful. It is the clearest
   integrity signal available.
7. Because a mis-transcribed number is invisible to you and fatal to
   credibility, and because the analysis is reproducible so there is no reason to
   rely on memory.

</details>

---

➡️ Next: [Lesson 37 — Writing Chapters 8 and 9](37-writing-ch8-9.md)
