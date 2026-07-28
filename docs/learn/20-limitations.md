# Lesson 20 — What this is *not*

*Part 2 · about 45 minutes · after lesson 19 · **last science lesson***

---

## In one sentence

> Every limitation below is one an examiner would find in ten minutes — so you
> name each one first, quantify it, and say what it does and does not damage.

---

## The principle

A limitations chapter is not an apology. It is a demonstration that **you know
the boundary of your own claim**.

Every limitation should be written in three parts:

1. **The fact** — precisely, with a number.
2. **What it damages** — which specific claims weaken, and by how much.
3. **What survives** — the part that stands regardless.

Part 3 is what most students omit, and it is the part that keeps the thesis
standing. A limitation without it reads as a retraction.

---

## The seven limitations

### 1. Not a new routing algorithm

Route-To-Reason, DART and CodeRouterBench already occupy that space.

- **Damages:** any claim to a novel routing method. The proposal's title.
- **Survives:** RQ4 measures the *headroom* a router would have (13.8 points)
  and stops there. That measurement is not in the prior work.

### 2. Not novel on overthinking

ThoughtTerminator, SelfBudgeter and RecurGuard already study reasoning that
fails to terminate.

- **Damages:** any claim to discovering non-termination.
- **Survives:** the **economic** framing — dollars per correct answer across a
  price-varying roster, and the finding that 15% of spend buys nothing.

### 3. Not contamination-controlled

LiveCodeBench stopped updating in 2025 (newest problem **2025-04-06**, last
release **2025-06-05**); every roster model is a **2026** release. There is no
post-cutoff window; every problem predates every model by at least nine months.

- **Damages:** absolute pass rates on LiveCodeBench. A suspiciously high score on
  a hard problem may be memorisation.
- **Survives:** LCB enters as a **difficulty tier**, and every comparison is
  *between configurations on the same problems*. Contamination inflates all
  configurations on a given problem roughly equally, so the *relative* finding —
  thinking helps more on hard problems — is far more robust than the absolute
  numbers. `problems.release_date` is stored so exposure can be quantified.

That "relative comparisons survive" argument is the strongest sentence in this
section. Make it explicitly.

### 4. Not fully powered

60–107 problems underpin the comparable statistics. Several intervals overlap —
including 5 adjacent CPC pairs, and the `flash|high` vs `pro|high` accuracy
comparison ([95,100] vs [88,100]).

- **Damages:** individual orderings between adjacent configurations.
- **Survives:** the large effects. A 29-point pass-rate gap on hard problems and
  a 305× CPC spread are not fragile to sample size. **Directions are clear;
  fine-grained orderings often are not** — and you say which is which, rather
  than letting the reader guess.

### 5. Not free of censoring

**26.3%** of hard thinking calls still truncate at the 48,000-token ceiling.

- **Damages:** the long-reasoning tail. The ">20k tokens" band's 39.3% pass rate
  is a **floor, not an estimate**, and 54.2% on hard is likewise a floor.
- **Survives:** the direction. Censoring biases the thinking arm *downward*, so
  your central finding (thinking helps on hard problems) is understated rather
  than overstated. **A bias that works against your own claim is the safest kind
  to have**, and saying so is both honest and persuasive.

### 6. The grid is unbalanced

`off` configurations ran 320 problems; `high` 51–104; the held-out model 16–23.
Cost, not design.

- **Damages:** any per-configuration statistic computed over that
  configuration's own problems — configurations effectively sat different exams.
- **Survives:** `paired_problems()` restricts every comparable statistic to the
  **107 problems with both effort arms graded**, and `scripts/results.py` prints
  that denominator on every row. The restriction is visible, not buried.
- **The honest note:** balancing the thinking arm would have cost about $1.50 and
  required raising the $6.00 cap. **It was recorded as a limitation instead.**
  Say that plainly — it is a defensible resource decision, and pretending
  otherwise would be worse than the limitation.

### 7. RQ5 is under-powered

The held-out model (Kimi) ran on **16–23 problems**.

- **Damages:** any strong claim about transfer to an unseen model.
- **Survives:** honestly, very little. **Report RQ5 as under-powered rather than
  reporting a number from 16 problems as though it meant something.** That is
  the right call, and stating it costs you less than an examiner extracting it.

### And two smaller ones worth naming

- **One sample per cell, temperature 0.** No within-configuration variance
  estimate; a lucky pass is indistinguishable from a reliable one. Bought you
  half the cost and deterministic routing labels.
- **Three model families, five models.** The abstract's "five or more open-weight
  models" is true but spans only three families (qwen, deepseek, moonshot) after
  GLM was dropped. **Say so explicitly rather than letting an examiner raise it.**

---

## The two sentences that hold it together

Put these at the top of Chapter 8, before the list:

> **The absolute numbers in this thesis are contaminated, censored and
> under-powered. The comparisons are not — because every comparison holds the
> problem set, the grading and the pricing constant, and the biases that remain
> act against the direction claimed rather than for it.**

That framing does three things at once: it concedes everything a hostile reader
would raise, it explains *why* the conclusions still stand, and it demonstrates
that you understand the difference between a biased measurement and a biased
comparison.

---

## Why it matters for the writing

**Chapter 8**, and it should be short, dense, and completely unapologetic in
tone. Each limitation as a three-line entry: fact, damage, survival.

Two rules:

1. **No limitation may appear for the first time in Chapter 8** if it affects a
   result. Censoring belongs in Chapter 7 where it did its damage; the unbalanced
   grid belongs in Chapter 3 where the design was set. Chapter 8 *collects* them
   for a reader who wants the whole boundary in one place.
2. **Never write "future work will address this"** unless you say what the work
   is. "A cost-aware objective rather than modal-label classification" is future
   work. "More data is needed" is a shrug.

---

## Do this

**1. Read the existing list.**

```bash
cd ~/thesis
sed -n '/## 5. What this is NOT/,/## 6/p' docs/research-framing.md
```

Compare against this lesson. This lesson adds the "what survives" half to each —
that is the part you will write.

**2. Quantify limitation 5 yourself.**

```sql
SELECT p.difficulty,
       ROUND(100.0 * SUM(g.finish_reason = 'length') / COUNT(*), 1) AS pct_truncated,
       COUNT(*) AS n
FROM generations g JOIN problems p USING (problem_id)
WHERE g.is_mock = 0 AND g.reasoning_tokens > 0
GROUP BY p.difficulty;
```

**3. Quantify limitation 6 yourself.**

```sql
SELECT c.effort_label, COUNT(DISTINCT g.problem_id) AS problems
FROM generations g JOIN configs c USING (config_id)
WHERE g.is_mock = 0 GROUP BY c.effort_label;
```

**4. Practise the hostile question.**

> *"Your benchmark is contaminated. Your models were released after every
> problem was published. How can any of your pass rates mean anything?"*

Your answer, out loud:

> *"The absolute pass rates are inflated and I report them as such — release
> dates are stored so the exposure can be quantified. But every claim I make is
> a comparison between configurations **on the same problems**. Contamination
> inflates all configurations on a given problem roughly equally, so it does not
> generate a 29-point gap between thinking and not-thinking on hard problems.
> The comparison survives; the absolute level does not, and I do not claim it."*

That is the single most valuable paragraph to have memorised before your
defence.

---

## Check yourself

1. What are the three parts of a well-written limitation, and which is most
   often omitted?
2. Why does contamination damage your absolute numbers but not your comparisons?
3. Why is censoring biasing your thinking arm *downward* actually helpful to
   you?
4. Why is the grid unbalanced, and what would fixing it have cost?
5. What should you say about RQ5?
6. What is wrong with "future work will address this"?
7. Give the two-sentence framing that opens Chapter 8.

<details>
<summary>Answers</summary>

1. The fact (with a number), what it damages, and what survives. "What survives"
   is the omitted one, and without it a limitation reads as a retraction.
2. Because every comparison is between configurations on the *same* problems, and
   contamination inflates all configurations on a problem roughly equally. It
   cannot manufacture a 29-point gap between effort arms.
3. Because it means the true effect of thinking on hard problems is *larger* than
   the 54.2% reported. The bias works against the claim being made, so the claim
   is conservative.
4. Cost — thinking calls were far dearer than projected and buying stopped at
   $5.25. Balancing would have cost about $1.50 and required raising the $6.00
   cap; it was recorded as a limitation instead.
5. That it is under-powered — the held-out model ran on 16–23 problems — and that
   no strong transfer claim is made. Better to say so than to report a number
   from 16 problems.
6. It names no work. A real future-work statement has a direction: "a cost-aware
   objective rather than modal-label classification".
7. The absolute numbers are contaminated, censored and under-powered; the
   comparisons are not, because every comparison holds the problem set, grading
   and pricing constant, and the remaining biases act against the direction
   claimed.

</details>

---

**🎉 Part 2 complete.** You now know every finding in your thesis, its numbers,
its caveats, and how to defend it.

If you can teach lessons 13 through 20 to someone else without notes, you can
defend this thesis.

➡️ Next: [Lesson 21 — Python, `uv`, and the shape of the repo](21-python-and-the-repo.md)
