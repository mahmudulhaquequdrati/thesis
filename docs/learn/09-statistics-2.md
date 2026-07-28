# Lesson 09 — Statistics II: uncertainty and the bootstrap

*Part 1 · about 1.5 hours · after lesson 08*

---

## In one sentence

> A confidence interval says *"the truth is probably in this range"* — and the
> bootstrap gets you one by re-running your own experiment thousands of times,
> using only the data you already have.

---

## The idea, from zero

### The problem: your number is not the truth

You measured 54.2% on LCB hard. Is the *true* rate 54.2%?

No. It is the rate **of your sample**. Draw a different 118 problems and you get
a different number — 51%, or 58%. Your measurement contains real signal plus
sampling luck, and nothing in the number itself tells you how much of each.

So reporting `54.2%` is over-claiming. It implies a precision you do not have.

### What you want to say instead

> "The true rate is probably somewhere between **45% and 63%**."

That range is a **confidence interval** (CI). "95% CI" means: if you repeated
this whole experiment many times, about 95% of the intervals you constructed
this way would contain the true value.

*(That is the technically correct phrasing. In practice everyone reads it as
"probably in here", which is close enough for a thesis so long as you never
write something stronger.)*

An interval does two jobs:

1. It stops you over-claiming.
2. **It tells you when two numbers are not actually different.** This is the job
   that earns its keep, and it earned it in your data.

### The classical approach, and why it fails you

Traditional statistics has formulas — the standard error of a proportion, the
*t*-distribution, and so on. They are fast and they assume things: a known
distribution shape, independence, a simple statistic like a mean.

Your headline statistic is **cost per correct answer**:

```
CPC = total dollars spent ÷ number of problems solved
```

That is a **ratio of two sums**, both of which are random. There is no clean
textbook formula for its interval, and ratio estimators are additionally
**biased** — the average of many CPC estimates is not the true CPC.

So you need something that does not care what shape your statistic is.

### The bootstrap: the trick

Here is the idea, and it feels like cheating the first time you meet it.

You wish you could re-run the experiment 1,000 times to see how much the answer
wobbles. You cannot — that would cost $5,000.

**But you can re-run it *inside* your sample.**

> Treat your 107 problems as if they were the whole world. Draw 107 problems
> from them **with replacement** — meaning the same problem can be drawn twice,
> and some are not drawn at all. Compute your statistic on that fake sample.
> Repeat 2,000 times.
>
> The spread of those 2,000 answers estimates the spread you would have seen by
> re-running the real experiment.

"With replacement" is the whole trick. It is what makes each resample *differ*.

```
Real sample:      [A B C D E]                → CPC = $0.0021

Resample 1:       [A A C D E]  (B missing)   → CPC = $0.0019
Resample 2:       [B C C C E]                → CPC = $0.0026
Resample 3:       [A B B D D]                → CPC = $0.0022
...
Resample 2000:    [A C D E E]                → CPC = $0.0020

Sort all 2,000. Take the 2.5th and 97.5th percentiles.
                  → 95% CI = [$0.0015, $0.0028]
```

That is the **percentile bootstrap**, and it is what
[`carr/stats.py`](../../carr/stats.py) implements — in the standard library,
with no scipy, in a couple of hundred lines.

### Three details that are easy to get wrong, and you got right

**1. Resample *problems*, not cells.**

Each draw takes a whole problem **with all its configurations attached**. Never
individual (problem, configuration) rows.

This is lesson 08's independence rule made operational. Two cells on the same
problem are not independent, so resampling them separately would pretend you had
far more information than you do, and your intervals would come out too narrow.

**2. The statistic must take the whole resample.**

For a ratio like CPC, you must compute:

```
sum(costs in the resample) ÷ sum(corrects in the resample)      ✅
```

**not**

```
average of the per-problem cost/correct ratios                   ❌
```

Those are different numbers, and the second is wrong. Your codebase records this
as "the §10.2 error, now pinned by a test" — meaning somebody (you) got it
wrong once, and a test now makes it impossible to get wrong again.

That is exactly the right response to a subtle bug: not "be careful next time",
but a test.

**3. Fix the seed.**

The bootstrap uses randomness. Random means a different answer every run, which
means your thesis's numbers change between drafts, which means nobody can
reproduce them.

So the random number generator is **seeded** — started from a fixed value — and
`CLAUDE.md` makes it a project-wide rule:

> **Fixed seeds everywhere** — sampling, splits, bootstrap. Reproducibility is a
> graded property of a thesis.

You can verify it in one command (it is in START-HERE for a reason):

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt      # must be identical
```

### Reading an interval: the part that changes conclusions

Two configurations:

```
config A:  CPC $0.00193   95% CI [0.00150, 0.00238]
config B:  CPC $0.00224   95% CI [0.00180, 0.00271]
```

A's point estimate is lower. Is A cheaper?

**You cannot say.** The intervals overlap heavily. The data is consistent with
either ordering. The honest sentence is: *"A's point estimate is lower, but the
intervals overlap, so the ordering is not established."*

This is not pedantry. It is the difference between a finding and a fabrication —
and it happened to you:

> **Five adjacent configuration pairs have overlapping CPC intervals.**

Reporting those bare — which is the norm in this literature — would have
manufactured a ranking your data does not support. You caught it because you
computed intervals at all.

⚠️ One caveat to have ready, because a sharp examiner may raise it: *overlapping
intervals* is a conservative test. Two intervals can overlap slightly while a
proper paired test still finds a difference. So "not established" is the correct
claim; "proven equal" is not. Never write the second.

### What an interval cannot save you from

An interval measures **sampling** uncertainty only. It says nothing about:

- **Bias** — your 320 problems being unrepresentative
- **Censoring** — the `max_tokens` ceiling truncating what you can observe
- **Contamination** — problems being in the training data

Those are *systematic* errors, and no amount of resampling touches them. They
belong in your Limitations chapter, not your error bars. A tight interval around
a biased number is a confident wrong answer.

---

## Why it is in *your* thesis

Every headline number carries an interval, and three of them changed what you
could claim:

| Finding | Point estimate | Interval | What the interval did |
|---|---|---|---|
| Abort at 16k keeps solutions | 88% | **[82, 92]%** | Made the claim honest rather than precise |
| …and saves | 49% | **[35, 61]%** | Very wide — the saving is real but poorly pinned down |
| CPC ordering | 5 adjacent pairs | overlapping | **Killed a ranking that looked solid** |
| `flash\|high` vs `pro\|high` accuracy | 98.3% vs 95.0% | [95,100] vs [88,100] | Direction is suggestive, **not established** |

That last row is worth dwelling on. Your finding "the cheap model beats the
expensive one" is one of your most quotable results — and you state it *with*
the caveat that the intervals overlap. You could have left the caveat out and
nobody would have known.

Writing the caveat is the thesis.

Your formal section (THESIS.md §10.2) names this as a deliberate contribution:

> **CPC needs confidence intervals.** Cost-per-correct is a ratio estimator,
> therefore biased, and almost always reported bare. Bootstrap it so you never
> claim a frontier difference that is within noise.

That sentence — "almost always reported bare" — is a small, specific,
defensible criticism of existing practice. Those are worth more than grand
claims.

---

## Do this

**1. Watch a bootstrap run.**

```bash
cd ~/thesis
uv run pytest tests/test_stats.py -v
```

Read the test names. One of them pins the ratio-of-sums rule from detail 2
above.

**2. See every interval in your thesis at once.**

```bash
uv run python scripts/results.py | grep -i "CI\|\[" | head -30
```

**3. Prove reproducibility yourself.**

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt && echo "IDENTICAL — seeds are fixed"
```

**4. Do one bootstrap by hand, on paper.**

Five problems. Costs `[1, 2, 2, 10, 3]`, solved `[1, 1, 0, 1, 1]`.

- True CPC = `(1+2+2+10+3) ÷ 4` = **4.5**
- Resample `[1, 1, 2, 10, 10]` with solved `[1, 1, 1, 1, 1]` → `24 ÷ 5` = 4.8
- Resample `[2, 2, 2, 3, 3]` with solved `[0, 0, 0, 1, 1]` → `12 ÷ 2` = 6.0
- Resample `[1, 2, 3, 3, 10]` with solved `[1, 1, 1, 1, 1]` → `19 ÷ 5` = 3.8

Look how far those wander — 3.8 to 6.0 — from five data points. **That wandering
is what the interval reports.** Now imagine 107 problems instead of 5, and you
have your real intervals.

---

## Check yourself

1. Why is reporting "54.2%" alone an over-claim?
2. Explain the bootstrap to someone who has never heard of it, in three
   sentences.
3. What does "with replacement" mean, and why is it essential?
4. Why must you resample problems rather than individual (problem, config)
   cells?
5. Why can't you average per-problem CPC ratios?
6. Two configurations have different point estimates and overlapping intervals.
   What may you claim? What may you *not* claim?
7. Name two sources of error a confidence interval does not protect you from.

<details>
<summary>Answers</summary>

1. Because it is the rate of your particular sample, and a different sample
   would give a different number. Stated bare, it implies precision you do not
   have.
2. Pretend your sample is the whole world. Draw a new sample of the same size
   from it, allowing repeats, and recompute your statistic. Do that thousands of
   times, and the spread of the answers estimates how much your real answer
   would wobble if you could re-run the experiment.
3. The same item can be drawn more than once and others not at all. It is what
   makes each resample differ from the original; without it every resample would
   be identical and you would learn nothing.
4. Because cells on the same problem are not independent — they share that
   problem's difficulty. Resampling cells would overstate how much independent
   information you have and produce intervals that are too narrow.
5. Because CPC is a ratio of sums, not a mean of ratios. The two are different
   quantities, and averaging ratios is the wrong one. A test now pins this.
6. You may say the point estimates differ and note the direction. You may **not**
   claim the ordering is established. You also may not claim they are equal —
   overlapping intervals are a conservative test, not proof of no difference.
7. Any two of: sampling bias (unrepresentative problems), censoring (the
   `max_tokens` ceiling), contamination (problems seen in training). All are
   systematic; resampling cannot detect them.

</details>

---

➡️ Next: [Lesson 10 — The economics of choosing](10-economics-of-choice.md)
