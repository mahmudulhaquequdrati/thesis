# Lesson 01 — What a thesis is, and what yours is

*Part 0 · about 1 hour · no prerequisites*

---

## In one sentence

> A thesis is **one claim you can defend with evidence you produced yourself** —
> not a report of everything you did.

---

## The idea, from zero

### The word itself

"Thesis" is an old Greek word meaning *a position you take*. Not "a project".
Not "a big document". A **position**. Somebody asks "what do you say about X?"
and you say a sentence, and then you spend eighty pages showing why that
sentence is true and what it cost you to find out.

The document is called a thesis because it *contains* a thesis. Most students
get this backwards and write a diary of their project.

### The everyday version

Imagine you tell a friend: *"Buying the expensive coffee beans is a waste of
money."*

That is a thesis. It is a claim. It could be wrong. Somebody could disagree.

Now imagine your friend says "prove it". What would satisfy them?

1. **A clear question.** Waste for whom, doing what? Espresso or filter? Are we
   talking about taste, or caffeine, or price-per-cup?
2. **A way to measure it that they would accept.** Not "I think it tastes the
   same" — a blind taste test, with ten people, on both beans, scored.
3. **The actual numbers.** Not "most people couldn't tell" — *"7 of 10 could not
   tell, and the 3 who could all preferred the cheap one."*
4. **Honesty about the holes.** "This was one roast, one machine, one morning.
   Ten people is not many. I did not test cold brew at all."
5. **What follows from it.** "So for a household making filter coffee, buy the
   cheap beans. For a café doing espresso, I have not tested that and cannot say."

Those five things are literally the chapters of a thesis. Question, method,
results, limitations, conclusion. Everything else is packaging.

### What a thesis is *not*

| It is not | Why people think it is | What to do instead |
|---|---|---|
| A report of everything you built | You worked hard and want credit | Credit comes from the claim being sound, not the effort being visible |
| A tutorial on the topic | Background chapters look like tutorials | Background exists only to make *your* claim understandable |
| A demonstration that something works | Engineering habit | A demo answers "can it be done". A thesis answers "what is true" |
| A place to hide weaknesses | Fear of being marked down | **Naming your own weaknesses is worth marks.** An examiner who finds a hole you did not name assumes you did not look |

### The single most important sentence in this lesson

> **A negative result, honestly measured, is a real thesis. A positive result you
> cannot defend is not.**

Your thesis contains a big negative result — the router does not work — and it is
one of your strongest chapters, because you can say *exactly why* it does not
work. Lesson 18 is about this. Hold the discomfort until then.

---

## Why it is in *your* thesis

Your thesis has a specific claim. Here it is, in the plainest words available:

> **Reasoning models charge you for thinking you cannot see. That thinking is
> worth paying for on hard problems and close to worthless on easy ones — and
> most standard benchmarks are too easy to tell you which is which.**

Notice the shape:

- It is **one sentence**. If yours needs three, it is not one claim yet.
- It **could be false.** Someone could measure and find thinking helps
  everywhere, or nowhere. That is what makes it a claim rather than a slogan.
- It is **about the world**, not about your code. Nobody's thesis is "I built a
  harness". The harness is how you found out.

### It used to be a different claim, and that matters

Your proposal (`Thesis_Project_Proposal.docx`) promised something else: a
**router** — a program that reads a problem and picks the cheapest model that
can solve it. That was the title. That was the claim.

Then you measured, and the router did not work. It added **+0.0 points** over
the dumbest possible baseline (lesson 18).

You have three options when this happens, and only one of them is honest:

| Option | What it looks like | Verdict |
|---|---|---|
| Hide it | Report the router's raw accuracy without the baseline; it looks like 65% success | **Fraud.** Also, the baseline is the first thing an examiner asks for |
| Keep the claim, blame the data | "More data would fix it" | Weak, and in your case *false* — you can prove the features were sufficient |
| **Change the claim to what you actually found** | The thesis is a *measurement* study; the router becomes one measured section that reports a negative | **This one.** It is what you did |

That change is why THESIS.md §14 lists 14 edits owed to the `.docx`. Lesson 39
walks through them. For now, just absorb the principle: **the claim follows the
evidence, never the other way around.**

### What "done" looks like for you

| Chapter | Content | Status today |
|---|---|---|
| 1 Introduction | The invisible cost; the 392-of-412 example | ⬜ write |
| 2 Background | Reasoning models, pricing, benchmarks, prior art | ⬜ write |
| 3 Method | Harness, roster, grading, pinning, cost reconciliation | ✅ built |
| 4 Measurement validity | The three ways the platform lies | ✅ built |
| 5 Results | When thinking helps, saturation, waste, cost-per-correct | ✅ built |
| 6 The frontier | Hull, oracle, value of information | ✅ built |
| 7 Runtime abort | The refuted claim and the honest curve | ✅ built |
| 8 Limitations | Stated plainly | ⬜ write |
| 9 Conclusion | When to pay for thinking | ⬜ write |

"✅ built" means **the evidence exists and is reproducible** — the numbers come
out of `scripts/results.py` every time you run it. What is missing is English
sentences. That is Part 4 of this course.

---

## Do this

Two things, both free, both about ten minutes.

**1. Say your thesis out loud.**

Not read — *say*. To a wall, a friend, a voice memo. In one sentence, no jargon,
as if to someone who has never heard the word "token".

Here is a version to react to (steal it or improve it):

> *"When you ask an AI to write code, it can 'think' first — and it charges you
> for that thinking even though you never see it. I measured when that's worth
> paying for. Answer: on hard problems it doubles your success rate; on the
> problems everyone tests with, it's almost pure waste."*

If you stumbled, that is the point. Say it again until it is smooth. You will
say this sentence a hundred times before you are finished.

**2. Look at what a claim looks like backed by numbers.**

```bash
cd ~/thesis
uv run python scripts/results.py | head -40
```

You should see section headings like `RQ0 saturation` and `RQ1 reasoning
length`, with numbers and sample sizes. You will not understand it yet — that is
lessons 13 to 18. What to notice right now is only this: **every number has a
denominator next to it.** `n=462/118`, not "462". That is what "defensible"
looks like on the page.

---

## Check yourself

1. In your own words, what is the difference between a thesis and a project
   report?
2. Your router failed. Why is that not a disaster?
3. Someone says: "your thesis is that you built a cost-measurement harness."
   What is wrong with that sentence?
4. Why does naming your own limitations *gain* you marks rather than lose them?
5. Say the one-sentence claim from memory.

<details>
<summary>Answers</summary>

1. A report says *what I did*. A thesis says *what is true, and here is why you
   should believe me*. The work appears only as evidence for the claim.
2. Because the claim was updated to match the evidence, and the failure is
   *diagnosed*, not just reported — you can show the features were sufficient and
   the estimator was at fault (lesson 18). A negative result with a cause is a
   contribution.
3. The harness is a *means*, not a claim. Nobody can agree or disagree with
   "I built a harness". The thesis must be a statement about the world that
   could turn out to be false.
4. Because the examiner will find them anyway. Finding them yourself proves you
   understand your own method's boundaries — which is exactly the skill being
   assessed. Unnamed holes read as blind spots.
5. Anything close to: *reasoning models bill for invisible thinking; it is worth
   it on hard problems, worthless on easy ones, and standard benchmarks are too
   easy to tell the difference.*

</details>

---

➡️ Next: [Lesson 02 — What a language model actually is](02-what-is-an-llm.md)
