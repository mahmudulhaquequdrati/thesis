# Lesson 32 — What an examiner is actually looking for

*Part 4 · about 45 minutes · after lesson 31*

---

## In one sentence

> An examiner is checking four things, and none of them is "was this
> impressive?" — they are: is the question real, is the method sound, do the
> conclusions follow, and do you know your own limits.

---

## The four things

### 1. Is the question real, and clearly stated?

They want to read one sentence and know what you asked.

**Your answer:** *Reasoning models bill for invisible thinking. When is it worth
paying for?* Backed by three tests (lesson 11): the cost is hidden (392 of 412
tokens), the stakes are large (305× CPC spread), and nobody has measured it (the
nearest work has no reasoning-token column).

**Where students lose marks:** a question that is really a task ("build a
router"), or one so broad that no finite experiment could answer it.

### 2. Is the method sound enough that the numbers mean something?

Not "is it sophisticated". **Is it sound.** Specifically:

| They will ask | Your answer |
|---|---|
| Could this be reproduced? | Fixed seeds throughout; `results.py` run twice diffs identical; roster pinned with snapshot dates |
| Are the labels trustworthy? | Grading in one file, wrapping the standard checker, validated against 210 canonical solutions |
| Are the comparisons fair? | Effort pairs hold the model constant; comparable statistics restricted to 107 paired problems |
| Do you know what it cost? | Costs from measured token counts × the pinned endpoint price; the 139 pilot calls also reconciled against the actual bill, both stored so drift is visible |

**Your strongest evidence here is not that nothing went wrong — it is that things
went wrong and your checks caught them.** The macOS grading bug and the censored
abort claim are assets, not embarrassments.

### 3. Do the conclusions follow from the evidence?

This is where over-claiming is punished. They read a claim and check the number
behind it supports exactly that much and no more.

**Your defences are already built in:**

- Every rate carries its denominator.
- Every headline carries a confidence interval.
- Where intervals overlap, you say the ordering is **not established** — five CPC
  pairs, and the `flash|high` vs `pro|high` accuracy comparison.
- Where a number is a floor rather than an estimate, you say so — 54.2% on hard,
  39.3% in the >20k band.

**One under-claim is worth ten over-claims.** A reader who catches you
over-claiming once re-reads everything suspiciously.

### 4. Do you know the limits of your own work?

The most reliable signal of a competent researcher, and the easiest to
demonstrate.

Your Chapter 8 (lesson 20) names seven limitations, each with what it damages
*and* what survives. The key move: **the absolute numbers are contaminated,
censored and under-powered; the comparisons are not, and the remaining biases act
against the direction claimed.**

---

## What they are *not* looking for

| Not looking for | Why |
|---|---|
| Novelty of technique | You use k-NN, a bootstrap, a convex hull. All standard. That is fine — THESIS.md §10 says so explicitly |
| Volume of work | 1,373 API calls is not impressive by itself. What they weigh is what the calls established |
| A positive result | A negative result, honestly measured and diagnosed, is a full contribution |
| Perfect execution | They have run experiments. A method chapter where nothing went wrong reads as fiction |
| A large budget | $5.25 for a complete measurement study is a point in your favour |

---

## The three failure modes that lose marks

**1. The project report.** Writing what you did, in the order you did it,
instead of what is true and why it should be believed. Symptom: chapters named
after weeks or components.

**2. The unmarked claim.** A sentence with no number behind it and no citation.
Symptom: "significantly", "dramatically", "much better" with nothing after.

**3. The unnamed hole.** Any weakness the examiner finds that you did not
mention. It converts an honest limitation into an apparent blind spot — the
single most expensive mistake available, and entirely avoidable.

---

## What is genuinely strong in your thesis

Say these out loud; they are real, and you should not be shy about them.

1. **A table nobody else has.** (model × thinking-mode → pass/fail, reasoning
   tokens, dollars) for code generation. The nearest work lacks the reasoning
   column entirely.
2. **A measurement-validity chapter that transfers.** Useful to anyone
   benchmarking through an aggregator, whether or not they care about reasoning
   costs.
3. **A self-refutation you found and reported.** The abort claim, killed by your
   own better data.
4. **A negative result with a diagnosis.** Not "the router didn't work" but
   "0.0 points of feature insufficiency, 33.3 of estimation error, and here is
   the fix."
5. **A deliberately strengthened baseline.** You compared against the convex
   hull rather than the best single configuration — and the harder comparison is
   why your result is negative. Say that explicitly.
6. **Cost discipline as method.** $5.25, a cap enforced on worst case before
   every call, never breached.

---

## What is genuinely weak, and how to hold it

| Weakness | How to present it |
|---|---|
| Small samples (60–107 problems) | State it early, report every denominator, distinguish established from suggestive |
| Contamination uncontrolled | Concede absolutes, defend comparisons (lesson 20) |
| The router failed | Reframe: RQ4 measures headroom; the negative is diagnosed |
| Novelty is narrow | Claim the measurement and the validity findings; cite the four closer works yourself |
| RQ5 under-powered | Report it as thin rather than reporting a number from 16 problems |

**Present each one before the examiner reaches it.** A limitation you volunteer
is evidence of judgement; the same limitation extracted from you is evidence of
a blind spot. Identical fact, opposite reading.

---

## Do this

**1. Write your one sentence, then a paragraph, then a page.**

- **One sentence:** the thesis question.
- **One paragraph:** question, what you measured, the headline finding, the
  honest contribution. (§7 of `research-framing.md` is a working draft.)
- **One page:** add the method sketch and the three biggest limitations.

Do it in that order, and do not let the sentence grow. If you cannot fit it in
one, you have two theses.

**2. Read your own abstract-in-waiting.**

```bash
cd ~/thesis
sed -n '/## 7. The one-paragraph version/,$p' docs/research-framing.md
```

Then rewrite it in your own words, without looking.

**3. Grade yourself on the four criteria.**

For each of the four, write two sentences: what your evidence is, and what your
weakest point is. If any criterion has no concrete evidence, that is what to work
on first.

---

## Check yourself

1. Name the four things an examiner checks.
2. Why is "nothing went wrong" a weakness in a method chapter?
3. What is the difference in how a limitation reads when you volunteer it versus
   when the examiner finds it?
4. Why is a negative result acceptable, and what makes yours strong rather than
   empty?
5. Name three genuinely strong things about your thesis.
6. Why does an over-claim cost more than one sentence's worth of credibility?

<details>
<summary>Answers</summary>

1. Is the question real and clearly stated; is the method sound; do the
   conclusions follow from the evidence; do you know your own limits.
2. Because anyone who has run an experiment knows things go wrong. A flawless
   account reads as either fiction or as insufficient checking. Your caught bugs
   are evidence that the checks work.
3. Volunteered, it demonstrates you understand the boundary of your claim.
   Discovered by the examiner, the same fact reads as a blind spot.
4. Because a thesis is a defended claim, not a successful product. Yours is
   strong because it is diagnosed — 0.0 points feature insufficiency, 33.3
   estimation error — and because it names the fix.
5. Any three of: a table nobody has published; a transferable measurement-validity
   chapter; a self-refutation you found and reported; a diagnosed negative
   result; a deliberately strengthened baseline; cost discipline as method.
6. Because it makes the reader re-read everything else suspiciously. Credibility
   is global, not per-sentence.

</details>

---

➡️ Next: [Lesson 33 — The structure, chapter by chapter](33-thesis-structure.md)
