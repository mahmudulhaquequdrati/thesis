# Lesson 40 — Defending it

*Part 4 · about 2 hours · **the last lesson***

---

## In one sentence

> Every question you will be asked is one you have already answered in this
> course — the defence is not new work, it is retrieval under mild pressure.

---

## What a defence is actually testing

Not whether your thesis is perfect. Whether **you understand it**.

Which means the worst possible answer is a confident wrong one, and the best
possible answer to something you do not know is: *"I did not measure that. What I
can say is…"* followed by what you did measure.

Three rules:

1. **Answer the question asked.** Not the one you prepared for.
2. **Lead with the number.** *"24.9% to 54.2%, n = 462 and 118"* beats *"well,
   thinking generally helps…"*.
3. **Concede fast and precisely.** A conceded point costs one sentence. A
   defended-then-conceded point costs your credibility for the next twenty
   minutes.

---

## The twenty questions

### On the question and framing

**1. Summarise your thesis in one sentence.**
> Reasoning models can think before answering; that thinking is billed but
> invisible; I measured when it is worth paying for.

**2. Why does this matter?**
> Because you cannot price a call from its answer — 392 of 412 tokens on a
> trivial prompt — and cost per correct answer spans 305× across open-weight
> models. That is a $50 versus $15,000 monthly bill for the same work.

**3. Isn't it obvious that thinking helps on hard problems?**
> The direction was contradicted by my own pilot. The finding is the sharpness of
> the condition — +29 points on hard, +1.0 on MBPP+ — and the fact that 15% of
> spend buys nothing at all. And the benchmarks the field uses cannot show it:
> 179 of my 320 problems cannot distinguish any configuration from another.

**4. Your proposal was about a router. What happened?**
> The pilot showed routing collapsing — 81% of problems shared one
> cheapest-passing configuration. I reframed to measurement in week 2, because the
> measurement yields a result either way. I built and evaluated the router anyway,
> and it added +0.0 points, which confirms the reframing was right.

### On method

**5. Why only 320 problems?**
> Budget. Every problem is 10 API calls. The pool is 884; running all of it was
> not affordable at $15. The 320 are stratified and seeded, weighted toward the
> tier that discriminates.

**6. Why one sample per cell?**
> It halves cost and makes the cheapest-passing label deterministic rather than a
> lottery. The cost is that I cannot measure within-configuration variance, and I
> report that as a limitation.

**7. How do you know your pass/fail labels are right?**
> Grading is in one file wrapping EvalPlus's own checker, because pass/fail is not
> `==` — floats need a tolerance and some problems have bespoke oracles. The
> harness is validated against the benchmarks' canonical solutions: 210 of them,
> all passing. That check caught a macOS bug that was silently failing *every*
> solution.

**8. Your grid is unbalanced. Isn't that fatal?**
> It would be if I compared configurations over their own problem sets — that
> compares different exams. Every comparable statistic is restricted to the 107
> problems where both effort arms were graded, and the denominator is printed on
> every row. Balancing would have cost about $1.50 and required raising my cap; I
> recorded it as a limitation instead.

**9. Why OpenRouter rather than direct providers?**
> One key and one request format instead of six accounts and six adapters, at a
> $15 budget. And it produced Chapter 4: the aggregator behaviours I documented
> are only visible because I used one.

### On results

**10. Walk me through your headline finding.**
> On LiveCodeBench hard, pass rate goes from 24.9% without reasoning to 54.2% with
> it, n = 462 and 118. On MBPP+ the same manipulation moves it 1.0 points. The
> value of reasoning is conditional on difficulty, sharply. And 54.2% is a floor,
> because 26.3% of hard thinking calls still truncate at my ceiling.

**11. Your benchmarks are contaminated. Does anything survive?**
> The absolute pass rates are inflated and I report them as such — release dates
> are stored so exposure can be quantified. But every claim I make is a comparison
> between configurations **on the same problems**, and contamination inflates all
> configurations on a problem roughly equally. It cannot manufacture a 29-point
> gap between effort arms. The comparisons survive; the absolute level does not,
> and I do not claim it.

**12. You say the cheap model beats the expensive one. Are you sure?**
> `flash|high` reaches 98.3% at one sixth the cost of `pro|high` at 95.0% — but
> the accuracy intervals overlap, [95,100] against [88,100]. So the direction is
> suggestive, not established. What the data supports is that the more expensive
> model shows no measurable advantage at six times the price.

**13. Why compare against a convex hull rather than the best single model?**
> Because if you may split traffic, everything on the line between two
> configurations is achievable — that is a two-constraint linear program whose
> optimum uses at most two configurations. So beating the best single model is
> nearly free and proves little. The hull is blind to the problem, so a router's
> margin over it is exactly the value of problem-level information.

**14. Your router failed. Why is that in the thesis?**
> Because it is a measured answer to RQ4 against the correct baseline, and because
> it is diagnosed. The decomposition shows 0.0 points of feature insufficiency
> and 33.3 of estimation error: the features are sufficient, the estimator is not,
> because the cheapest-passing label is dominated by one configuration and a
> nearest-neighbour vote returns the modal label. The fix is a cost-aware
> objective. Against the weaker baseline, it would have looked like a success.

**15. Tell me about a result you got wrong.**
> My pilot found a free abort threshold — stop at 10,000 reasoning tokens, keep
> every solved problem, save 44%. It was an artefact of my own 16,000-token
> ceiling: a truncated call cannot succeed, so the ceiling manufactured the cliff.
> At 48,000, 56 calls above 10,000 tokens succeeded. What survives is an honest
> tradeoff — 88% of solutions [82,92] for a 49% saving [35,61] — and a general
> lesson: a truncation limit is a censoring mechanism.

### On contribution and limits

**16. What is genuinely novel here?**
> The table — (model × thinking-mode → pass/fail, reasoning tokens, dollars) for
> code generation. The nearest work, CodeRouterBench, has eight model names, no
> effort axis and no reasoning-token column. Plus the measurement-validity
> findings, and the gap decomposition. I do not claim novelty on routing or on
> overthinking, and I cite the work that covers both.

**17. What would you do differently?**
> Raise the token ceiling before the pilot rather than after — the censoring cost
> me a headline. Budget the thinking arm to match the no-reasoning arm, so more
> than 107 problems are comparable. And prototype the router against
> CodeRouterBench's free data before building my own, which would have exposed the
> label-dominance problem at $0.

**18. What is your weakest result?**
> RQ5. The held-out model ran on 16–23 problems, which is not enough to conclude
> anything about transfer, and I report it as thin rather than reporting a number
> from it.

**19. What should someone reading this do differently tomorrow?**
> Practitioner: enable reasoning on hard problems, leave it off elsewhere, expect
> ~15% of spend to buy nothing, and abort at 16k if they will trade 12% of
> solutions for half the cost. Researcher: pin the provider and quantization,
> report truncation rates, and state which subset of their benchmark carries
> signal.

**20. What next?**
> A cost-aware routing objective rather than modal-label classification — the
> decomposition says that is the binding constraint. A re-measurement without a
> binding ceiling, to estimate the long-reasoning tail rather than bound it. And a
> contamination-controlled hard tier, which does not currently exist publicly.

---

## Three questions that need care

**"Your sample is tiny. How can you conclude anything?"**

Do not get defensive; separate the claims.

> The large effects are robust to the sample size — a 29-point pass-rate gap and
> a 305× cost spread are not fragile at n = 107. The fine-grained orderings are
> not: five adjacent CPC pairs have overlapping intervals and I say so explicitly.
> Directions are established; individual orderings often are not, and I mark which
> is which.

**"This is engineering, not research."**

> The engineering is the instrument. The research is what it measured: that the
> value of reasoning is conditional on difficulty, that most standard benchmark
> problems cannot detect the difference, that 15% of spend returns nothing, and
> that the platform silently substitutes models and ignores its own parameters. And
> one of my own claims was refuted by my better data, which I report.

**"Why should I believe any of these numbers?"**

> Because they are reproducible. Fixed seeds throughout — running the analysis
> twice produces byte-identical output. Every call priced from the actual bill,
> not an estimate, with both stored so drift is visible. Grading validated against
> 210 canonical solutions. 119 tests, of which the largest group covers the cost
> cap and never paying twice. And the raw responses are stored verbatim, so
> anything can be re-graded without re-purchasing.

---

## Preparing, practically

**Two weeks before:** re-read Part 2 of this course. Re-run
`scripts/results.py` and read it top to bottom. Verify the roster still resolves.

**One week before:** answer all twenty questions out loud, timed, two minutes
each. Record yourself once — you will hear the hedging.

**The day before:** re-read your own limitations chapter. It is the most likely
source of questions, and knowing it cold makes you look unshakeable, because you
will be agreeing with the examiner before they finish.

**On the day:** bring the numbers. Nobody expects 305× and $0.06320 from memory.
A one-page sheet of headline figures is professional, not weak.

---

## The last thing

You did a real piece of research. You asked a question nobody had answered, you
measured it carefully, you caught two of your own errors before anyone else
could, you reported a negative result with a diagnosis instead of hiding it, and
you did the whole thing for **$5.25**.

The thesis is not the code, and it is not the document. **It is the table** — and
the fact that every rule in that repository exists to stop the table being
quietly wrong.

Twice it *was* quietly wrong. Both times, the checks caught it.

That is the thesis.

---

## Check yourself

1. What is a defence actually testing?
2. What is the best answer to a question you cannot answer?
3. Give the contamination answer in full.
4. Why did you compare against the convex hull, and what does that admission
   show?
5. Tell the abort-refutation story in under 90 seconds.
6. Name your weakest result and how you report it.
7. What would you do differently, and why is having an answer important?

<details>
<summary>Answers</summary>

1. Whether you understand your own work — its claims, its evidence and its
   boundary — not whether the work is flawless.
2. "I did not measure that. What I can say is…" followed by what you did measure.
   A confident wrong answer is the worst possible outcome.
3. Absolute pass rates are inflated and reported as such, with release dates
   stored so exposure is quantifiable; but every claim is a comparison between
   configurations on the same problems, and contamination inflates all
   configurations on a problem roughly equally, so it cannot generate the
   29-point gap between effort arms. Comparisons survive; the absolute level is
   not claimed.
4. Because a fixed traffic split already beats the best single configuration, so
   that bar proves little; the hull is problem-blind, so the margin over it is the
   value of problem-level information. Admitting it shows you chose the harder
   test — against the easier one the router would have looked successful.
5. Pilot found a free threshold at 10,000 tokens; the 16,000-token ceiling meant
   truncated calls could never succeed, so the ceiling manufactured the cliff; at
   48,000, 56 calls above 10,000 tokens succeeded; what survives is 88% of
   solutions [82,92] for a 49% saving [35,61], and the general lesson that a
   truncation limit censors.
6. RQ5 — the held-out model ran on 16–23 problems, too few to conclude anything,
   so it is reported as thin rather than as a result.
7. Raise the ceiling before the pilot; budget the thinking arm to match the
   no-reasoning arm; prototype the router on free data first. Having an answer
   shows you can evaluate your own design rather than only execute it.

</details>

---

**🎓 Course complete.**

You started knowing nothing about a thesis. You now know what one is, every
concept yours is built from, every finding and its caveats, every module of the
code and the bug each rule prevents, how to write each chapter, and how to defend
it.

**Go and write it.** Start with Chapter 5, section 1 — lesson 36 tells you how,
and you already know the material.

⬅️ [Back to the index](00-index.md)
