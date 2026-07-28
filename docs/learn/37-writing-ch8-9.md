# Lesson 37 — Writing Chapters 8 and 9

*Part 4 · about 2 hours of writing · after lesson 36*

---

## In one sentence

> Chapter 8 draws the boundary of your claims without apologising; Chapter 9
> tells a reader what to do differently on Monday.

---

## Chapter 8 — Limitations

### The opening two sentences

Put the framing before the list:

> The absolute numbers in this thesis are contaminated, censored and
> under-powered. **The comparisons are not** — every comparison holds the problem
> set, the grading and the pricing constant, and the biases that remain act
> against the direction claimed rather than for it.

That paragraph concedes everything a hostile reader would raise, explains why the
conclusions still stand, and demonstrates you understand the difference between a
biased *measurement* and a biased *comparison*.

### The seven entries, each as fact / damage / survival

Written out, each is three or four sentences. Here is one in full, as a model:

> **Contamination is uncontrolled.** LiveCodeBench's newest problem dates from
> 2025-04-06 and the dataset stopped updating on 2025-06-05, while every model in
> the roster is a 2026 release; every problem therefore predates every model by at
> least nine months. **This inflates absolute pass rates on LiveCodeBench, and a
> high score on a hard problem should be read as possible memorisation.** Each
> problem's contest date is stored so the exposure can be quantified. **The
> comparative findings survive**, because contamination inflates all
> configurations on a given problem roughly equally and therefore cannot generate
> the 29-point gap observed between effort arms on hard problems.

Do that seven times: not a routing algorithm; not novel on overthinking;
contamination; not fully powered; censoring; unbalanced grid; RQ5 under-powered.
Plus the two small ones — single sample at temperature 0, and three model
families.

### Three rules

**1. No limitation appears here for the first time** if it affected a result.
Censoring belongs in Chapter 7 where it did its damage. Chapter 8 *collects*.

**2. Never write "future work will address this"** without saying what the work
is. Compare:

| Weak | Strong |
|---|---|
| "Further research is needed." | "A cost-aware objective — predicting expected cost per configuration and minimising, rather than classifying the modal cheapest-passing label — is the concrete next step, and the decomposition indicates it is the binding constraint." |

**3. Be explicit about resource decisions.** Balancing the thinking arm would
have cost ~$1.50 and required raising the $6.00 cap. **Say that.** A defensible
resource decision, stated, is far better than a limitation that looks like an
oversight.

---

## Chapter 9 — Conclusion

### What a conclusion is for

Not a summary. A reader who reached Chapter 9 does not need to be told what
Chapter 5 said. The conclusion answers: **so what?**

### The five moves

**1. The question and its answer, in one paragraph.**

> This thesis asked when the invisible, billed thinking of reasoning models is
> worth paying for. The answer is that its value is **conditional on difficulty
> and sharply so**: on hard competitive-programming problems, enabling reasoning
> more than doubles the pass rate, while on the standard benchmarks used
> throughout this literature it changes almost nothing — because those benchmarks
> are saturated.

**2. Guidance for practitioners.** Concrete and actionable:

- Enable reasoning for hard problems; leave it off for anything resembling
  standard benchmark tasks — you pay roughly an order of magnitude more tokens
  for one to six points.
- Expect **~15% of spend** to buy nothing at all, concentrated in long
  non-terminating traces.
- If you will trade **12% of solved problems for roughly half the cost**, abort
  at 16,000 reasoning tokens. **There is no free threshold.**
- Do not assume a cheaper model is worse: here the cheap model with reasoning
  enabled dominated the frontier model with reasoning enabled at one sixth the
  price.

**3. Guidance for researchers.** This is where your validity chapter pays off:

- Pin the provider **and** the quantization, or you are not comparing models.
- Report your truncation rate next to any result about long outputs.
- State which subset of your benchmark carries signal — in this study, fewer than
  half the problems could distinguish any configuration from any other.
- Verify that reasoning-budget parameters bind. Here they did not.

**4. Future work, named.** Two or three items, each specific:

- A cost-aware routing objective rather than modal-label classification — the
  decomposition locates the failure precisely there.
- Re-measurement without a binding token ceiling, to estimate rather than bound
  the long-reasoning tail.
- A contamination-controlled hard tier, which currently does not exist publicly
  — the frontier stopped updating in 2025.

**5. Close on the opening.** Return to the 392-of-412 example:

> A trivial request for a three-line function spent 392 tokens thinking. This
> thesis has measured when that expenditure is justified — and the answer, for
> most of the problems on which such models are routinely evaluated, is that it
> is not.

### What not to do

| Don't | Why |
|---|---|
| Introduce a new result | The conclusion must contain nothing unsupported by earlier chapters |
| Overstate the contribution | You have said it honestly for eight chapters; do not spoil it in the last two pages |
| Apologise | The limitations chapter has already done that work, properly |
| End on future work | End on what you established |

---

## The abstract — written last

Roughly 250 words, and §7 of `research-framing.md` is already close. Structure:

1. **Context** (1 sentence) — reasoning models bill for invisible tokens.
2. **Gap** (1 sentence) — nobody has measured when it is worth paying for.
3. **Method** (2 sentences) — 1,373 graded generations, 320 problems, 10
   configurations, $5.24, actual billed cost per call.
4. **Findings** (4–5 sentences) — the conditional effect, saturation, waste, the
   CPC spread, the 13.8-point headroom, the validity findings.
5. **Contribution** (1 sentence) — the table and the validity findings.

⚠️ **Every number in the abstract must be exactly right.** It is the most-read
and most-checked 250 words in the document. Copy them; do not type them.

---

## Do this

**1. Write the two-sentence framing** that opens Chapter 8. In your own words.
Then read it aloud — it should sound calm, not defensive.

**2. Write all seven limitations** in the fact/damage/survival form. Aim for
three sentences each. Half a page in total. Then check: **does every one have a
"survives" clause?** If any does not, it is written as a retraction.

**3. Write the practitioner guidance** as four bullets someone could act on
tomorrow. Then test each: could a working engineer do it, or is it advice about
research?

**4. Rewrite the abstract from memory, then diff against the numbers.**

```bash
cd ~/thesis
sed -n '/## 7. The one-paragraph version/,$p' docs/research-framing.md
```

Every number you got wrong from memory is a number to copy rather than recall.

---

## Check yourself

1. What are the three parts of a limitation entry, and which is most often
   missing?
2. Give the two-sentence framing that opens Chapter 8.
3. Why may a limitation not appear in Chapter 8 for the first time?
4. What is wrong with "further research is needed"?
5. What is a conclusion actually for?
6. Give two pieces of practitioner guidance and two of researcher guidance.
7. Why is the abstract written last, and what must be true of every number in
   it?

<details>
<summary>Answers</summary>

1. The fact with a number, what it damages, and what survives. "What survives" is
   most often missing, and without it a limitation reads as a retraction.
2. The absolute numbers are contaminated, censored and under-powered; the
   comparisons are not, because each holds the problem set, grading and pricing
   constant and the remaining biases act against the direction claimed.
3. Because a limitation that affected a result belongs where the result is, so
   the reader can weigh it in context. Chapter 8 collects them for someone who
   wants the whole boundary at once.
4. It names no work. A real future-work statement identifies the specific change
   — here, a cost-aware objective rather than modal-label classification.
5. To answer "so what?" — to convert findings into what a reader should do
   differently, not to summarise chapters they have just read.
6. Practitioner (any two): enable reasoning on hard problems only; expect ~15% of
   spend to buy nothing; abort at 16k if trading 12% of solutions for half the
   cost; do not assume the pricier model is better. Researcher (any two): pin
   provider and quantization; report truncation rates; state which subset of your
   benchmark carries signal; verify that budget parameters bind.
7. Because it must promise exactly what the finished document delivers. Every
   number must be copied from the analysis output rather than recalled — it is
   the most-read and most-checked passage in the thesis.

</details>

---

➡️ Next: [Lesson 38 — Figures, tables and citations](38-figures-tables-citations.md)
