# Lesson 13 — Finding 1: most benchmark problems cannot answer the question

*Part 2 · about 45 minutes · after lesson 12*

---

## In one sentence

> Of 320 problems, **81 are solved by every configuration and 98 by none** — so
> only **141 discriminate**, and everything else is dead weight in every average
> you compute.

---

## The finding

### The three kinds of problem

Every problem in your table falls into one of three buckets:

| Bucket | Count | What it tells you about which configuration to pick |
|---|---|---|
| Solved by **all 10** configurations | 81 | **Nothing.** Every choice is right |
| Solved by **none** | 98 | **Nothing.** Every choice is wrong |
| Solved by **some** | **141** | **Everything.** This is where choice matters |

The two useless buckets are useless *symmetrically*. People find the "too easy"
half obvious and the "too hard" half surprising, but they carry identical
information: zero. If nothing you can do changes the outcome, the outcome cannot
guide you.

**179 of 320 problems — 56% — cannot contribute to your question at all.**

### Where it shows up per tier

The pilot measured it first, tier by tier:

| tier | reasoning off | reasoning high | verdict |
|---|---|---|---|
| HumanEval+ | 90% | 100% | **saturated — no signal** |
| MBPP+ | 93% | 100% | **saturated — no signal** |
| LiveCodeBench easy | 100% | 100% | **saturated — no signal** |
| LiveCodeBench medium | 60% | 50% | discriminates |
| LiveCodeBench hard | 50% | 31% | discriminates |

*(These pilot numbers were later revised by the full grid — lesson 14 has the
final figures. The pattern held; the magnitudes moved.)*

**HumanEval+ and MBPP+ — the two benchmarks almost every code-generation paper
reports — are saturated for 2026-class models.**

### How you found it: the first API call of the project

This is a story worth being able to tell, because it shows the risk register
working.

THESIS.md §11 had already named saturation as the **biggest risk to the whole
thesis**, before any money was spent:

> If the cheapest configuration already passes ~90% of these benchmarks, the
> frontier collapses to a point and CARR trivially learns "always route cheap" —
> a degenerate result an examiner will name immediately.

Then the very first real cell was bought: `HumanEval/0` × all 10 configurations.

> **10 of 10 PASS.** Every no-reasoning configuration solved it, including the
> cheapest model on the roster. Cost ranged **58×** — $0.000081 to $0.004673 —
> for an identical outcome.

One problem is not evidence of a rate, and `HumanEval/0` is close to the easiest
problem in the benchmark. But the direction was exactly the predicted failure
mode, and it appeared **immediately**.

Three things followed, all load-bearing:

1. The pilot sample must be **difficulty-spread**, not the first *N* problems. A
   pilot over `HumanEval/0..9` would have reported ~100% everywhere.
2. The LiveCodeBench hard tier moved from "nice to have" to **required**.
3. **Report the saturation rate as a finding**, not a footnote.

Point 3 is the pivot that turns a threat into a contribution.

### Why it is a *finding* and not an excuse

This is the part to get right, because it can be read two ways, and only one of
them is defensible.

**The bad version:** *"My benchmarks were too easy, so my results are weak."*
That is an apology, and it invites the examiner to agree.

**The right version:**

> **The standard code-generation benchmarks are saturated for 2026 reasoning
> models. Anyone using them to study model or effort selection must report which
> subset of problems carries their signal — because more than half of theirs
> does not.**

That is a claim about the field's measurement practice. It is checkable, it is
useful to other people, and it is *not* about your budget.

And note what makes it credible: you did not merely assert saturation, you
**quantified it** (81/98/141) and you **acted on it** (re-weighted the grid
toward LCB medium and hard, doubled the hard tier by loading LCB v5 alongside
v6, free).

### ⚠️ The consequence that reaches every other chapter

Saturation is not a self-contained result. It changes how every other number
must be read:

- **Averages over all 320 problems are diluted** toward "no difference", because
  179 of them are incapable of showing one. Any effect you measure over the full
  set understates the effect where it exists.
- **Per-tier breakdowns are mandatory**, not decorative. This is the Simpson's
  paradox defence from lesson 08, and THESIS.md §11 names it as a required
  mitigation.
- **The router's job is nearly trivial on 56% of problems**, which is part of why
  it collapsed (lesson 18). If most problems have the same right answer, "always
  say the same thing" scores well.
- **The 98 nobody-solves problems are a ceiling on everything.** No routing
  strategy, no oracle, no amount of thinking reaches them. Your oracle's 98.3%
  is computed over a subset where solutions exist at all.

---

## Why it matters for the writing

This is **Chapter 5's opening section**, and it must come *before* the pass-rate
results, because it tells the reader how to read them.

The structure that works:

1. **The risk, named in advance.** Quote your own §11 — you predicted this
   before spending.
2. **The first observation.** `HumanEval/0`, 10/10, 58× cost spread.
3. **The measurement.** 81 / 98 / 141 of 320.
4. **The per-tier table.**
5. **The consequence.** Why every subsequent result is reported per tier.
6. **The generalisation.** What other researchers should do about it.

Step 1 matters more than it looks. "I anticipated this risk, planned a check for
it, ran the check, and it fired" is a completely different story from "I noticed
late that my benchmarks were easy". Same data. Different researcher.

---

## Do this

**1. See it in your own output.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ0/,/RQ1/p'
```

Look for the `<- saturated, no signal` markers.

**2. Count the three buckets yourself.**

In Studio's SQL console:

```sql
SELECT solved_by, COUNT(*) AS n_problems FROM (
  SELECT g.problem_id,
         CASE WHEN SUM(r.passed) = 0 THEN 'none'
              WHEN SUM(r.passed) = COUNT(*) THEN 'all'
              ELSE 'some' END AS solved_by
  FROM generations g JOIN results r USING (gen_id)
  WHERE g.is_mock = 0
  GROUP BY g.problem_id
) GROUP BY solved_by;
```

You are deriving 81 / 98 / 141 from raw rows. Do it once and you will never
forget where the number comes from.

**3. Look at the 58× spread that started it.**

```bash
uv run python scripts/view.py HumanEval/0
```

Ten PASS rows. Cheapest $0.000081, dearest $0.004673. **Same outcome.**

**4. Practise the framing.**

Write two sentences: one that sounds like an apology, and one that sounds like a
finding. Read both aloud. Notice how different they feel — and that the data
underneath is identical.

---

## Check yourself

1. What are the three buckets, and why are two of them equally uninformative?
2. Which of your benchmarks are saturated, and what does that mean for the field
   that uses them?
3. How did you first notice this, and why does the timing matter?
4. Why is saturation a finding rather than an excuse? Give both framings.
5. Name two ways saturation changes how other results must be read.
6. Why did loading LiveCodeBench v5 alongside v6 matter?

<details>
<summary>Answers</summary>

1. Solved by all (81), by none (98), by some (141). The first two give the same
   outcome regardless of which configuration you choose, so neither can favour
   one choice over another.
2. HumanEval+, MBPP+ and LCB easy. Any study using them for model or effort
   selection must state which subset carries its signal, because most of the
   problems cannot.
3. On the very first purchased cell — `HumanEval/0`, 10/10 pass, 58× cost spread
   — with the risk already named in THESIS.md §11 beforehand. Timing matters
   because it turns the story from "discovered late" into "predicted, checked,
   confirmed, acted on".
4. Apology: "my benchmarks were too easy, so my results are weak". Finding: "the
   standard benchmarks are saturated for 2026 models; anyone studying selection
   on them must report which subset carries their signal." Same data,
   different claim.
5. Any two: averages over all 320 are diluted; per-tier breakdowns become
   mandatory; the router's task is near-trivial on most problems; the 98
   unsolvable problems cap every strategy including the oracle.
6. It doubled the usable (medium + hard) tier from 132 to 258 problems, for
   free — problems cost nothing to download, only to run.

</details>

---

➡️ Next: [Lesson 14 — Finding 2: thinking works, conditionally](14-when-thinking-helps.md)
