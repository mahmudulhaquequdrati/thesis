# Lesson 11 — The question, and why it is real

*Part 2 · about 1 hour · after lesson 10*

---

## In one sentence

> **Reasoning models can "think" before answering. That thinking is billed but
> invisible. When is it worth paying for?**

---

## The idea

That sentence is the whole thesis. Everything else — 2,000 lines of code, 1,373
API calls, $5.25 — exists to answer it with measured numbers instead of
intuition.

Learn it word for word. You will say it in your introduction, in your abstract,
to your advisor, and at your defence.

### Why it is a real question and not a made-up one

A question earns its place in a thesis by passing three tests. Yours passes all
three, and you should be able to give each answer in one breath.

**Test 1 — Is the thing actually hidden?**

Yes, and you measured it on day one:

> A trivial *"write a Python function that reverses a string"* prompt returned
> **412 completion tokens, of which 392 were reasoning.** The visible answer was
> three lines.

Price that call from the text you can see and you understate it about
**twentyfold**. Not a rounding error — an order of magnitude, on the easiest
possible prompt.

**Test 2 — Do the stakes matter?**

Yes, and you measured that too:

> Cost per correct answer spans **305×** across your roster, from $0.00021 to
> $0.06320.

That is the difference between a **$50** and a **$15,000** monthly bill for the
same work. Anyone running code generation at any scale is making this decision,
usually by guessing.

**Test 3 — Does anyone already know the answer?**

No. And this is the part you must be able to defend precisely, because it is
where an examiner will push.

The nearest published work is **CodeRouterBench** (*Agent-as-a-Router*, June
2026): 9,999 coding tasks × 8 models, with per-call cost, released free. It is
genuinely close.

But its `model` column contains eight model *names* and nothing else:

| What it has | What it lacks |
|---|---|
| task × model outcomes | ❌ **no effort axis** — no model appears twice at different thinking levels |
| `input_tokens`, `output_tokens`, `total_tokens` | ❌ **no reasoning-token column at all** |
| per-call `cost_usd` | ❌ closed-weight backends, where yours is open-weight |
| an OOD split | ❌ its router is *trained* (ships a LoRA adapter) |

> **The single field that carries ~95% of a thinking call's cost is the one they
> do not record.**

So the nearest work *sharpens* your claim rather than displacing it. They route
between **models**; you measure across **(model × thinking-mode)** pairs with
reasoning tokens priced.

### The practitioner's version

Strip the academic framing. The question a working engineer actually has is:

> *"Should I turn thinking on for this task?"*

Nobody can tell them. Not the model card, not the pricing page, not the
leaderboard — because leaderboards report accuracy and never report what the
accuracy cost.

Your thesis answers it, with a condition attached: **yes on hard problems (it
more than doubles your success rate), and almost never on the problems that
standard benchmarks contain.**

### ⚠️ This is not the question you started with

Your proposal asked something else:

> *Can a training-free router pick the cheapest (model, thinking-mode) pair that
> still solves a given problem?*

That is a **routing** question. It became a **measurement** question on
2026-07-26, and the decisions log records why:

> **DIRECTION CHANGE, driven by the user and confirmed by the data.** New
> question: when is reasoning worth paying for, and can you tell before you have
> paid?

Two reasons, both good:

1. **The routing question was collapsing.** In the pilot, 13 of 16 problems
   (81%) shared the *same* cheapest-passing configuration. A router that always
   answers "flash, no thinking" would have scored 81%. That degenerate outcome
   even has a name in the literature — *When Routing Collapses* (Feb 2026).
2. **The measurement question does not depend on the router working.** The
   tradeoff curve is a result either way. That is *de-risking*: choosing a
   question whose answer is publishable regardless of which way it comes out.

Deciding this in **week 2** rather than week 10 is one of the better judgements
in the project, and it is worth saying in your Method chapter. The router did
eventually collapse completely (lesson 18) — the reframing was not a hunch, it
was correct.

### The five research questions, in the order they are answered

Your proposal listed RQ1–RQ5. After the reframing they map onto the work like
this:

| RQ | The question in plain words | Lesson | Answer, in one line |
|---|---|---|---|
| **RQ0** | Can these benchmarks even tell configurations apart? | 13 | Mostly not — only 141 of 320 problems discriminate |
| **RQ1** | Does thinking help, and where? | 14 | Yes — doubles the pass rate on hard, ~nothing on easy |
| **RQ2** | When does thinking stop paying off? | 15 | When it runs long — 29,584 mean tokens for nothing, 15% of reasoning spend |
| **RQ3** | Can you cut a call off once thinking runs long? | 16 | Yes, but not for free. **No threshold saves money without losing a solved problem** |
| **RQ4** | What is problem-level information worth? | 17 | **13.8 accuracy points** over a problem-blind mixture |
| **RQ4b** | Can a cheap router capture it? | 18 | **No — +0.0 points.** And the decomposition says exactly why |
| **RQ5** | Does it transfer to an unseen model? | 20 | Under-powered. Kimi ran on 16–23 problems; reported as a limitation |

RQ0 was not in the proposal. It emerged from the data on the very first API call
and became load-bearing. **Discovering that you need a question you did not plan
is a good sign, not a bad one** — but it must be presented as a deliberate check
you ran, not an accident you tripped over.

---

## Why it matters for the writing

Chapter 1 is built from this lesson and nothing else:

1. **The hook** — the 392-of-412 example. Concrete, verifiable, one sentence.
2. **The stakes** — 305× CPC spread, $50 vs $15,000.
3. **The gap** — CodeRouterBench is closest and has no reasoning-token column.
4. **The question** — the one sentence at the top of this lesson.
5. **The contributions** — what you will deliver, listed.
6. **The roadmap** — what each chapter does.

Lesson 34 writes it with you. For now, know that **the hardest part of Chapter 1
is already done**, because you have the numbers that make each of those five
items concrete rather than hand-waving.

---

## Do this

**1. Read the compact statement of the science.**

```bash
cd ~/thesis
open docs/research-framing.md      # or: less docs/research-framing.md
```

Read §1 and §7 (the one-paragraph version). §7 is very close to your abstract.
Read it twice — you will rewrite it in lesson 34.

**2. Reproduce the origin story.**

```bash
cat scripts/day1_hello.py
```

Fifteen lines. This is where 392-of-412 came from. Note that it is *kept* in the
repository rather than deleted — the script that produced a headline number
should survive.

**3. Practise the three defences out loud.**

Someone asks: *"Isn't this obvious? Of course thinking helps on hard problems."*

Your answer has three parts:

- **The cost is invisible**, so nobody knows what they are paying — 392 of 412
  tokens on a trivial prompt.
- **The magnitude was not known**: doubling on hard, ~4 points on easy, and 15%
  of all spend buying literally nothing.
- **The benchmarks everyone uses cannot show it** — 179 of 320 problems in the
  standard suites are incapable of distinguishing any configuration from any
  other.

Say it until it flows.

---

## Check yourself

1. State the thesis question from memory.
2. Give the three tests a research question must pass, and your evidence for
   each.
3. What does CodeRouterBench have, and what is the one column it lacks?
4. Why did the thesis change from a routing question to a measurement question,
   and when?
5. Why is that change *de-risking* rather than backing down?
6. Which RQ was not in the proposal, and where did it come from?

<details>
<summary>Answers</summary>

1. Reasoning models can think before answering; that thinking is billed but
   invisible; when is it worth paying for?
2. Is the thing hidden (392 of 412 tokens, ~20× understatement); do the stakes
   matter (305× CPC spread, $50 vs $15,000/month); does anyone already know
   (no — the nearest work has no effort axis).
3. 9,999 tasks × 8 models with per-call cost and an OOD split. It has **no
   reasoning-token column and no effort axis** — the field carrying most of a
   thinking call's cost is absent.
4. On 2026-07-26, because the pilot showed routing collapsing (81% of problems
   shared one cheapest-passing configuration) and because the measurement
   question yields a result either way.
5. Because the new question's answer is publishable whichever way it comes out,
   while the old one required the router to succeed. The router later added
   +0.0 points, so the reframing was vindicated.
6. RQ0, saturation. It appeared on the very first API call — `HumanEval/0`
   passed by all 10 configurations — and was already named as the top risk in
   THESIS.md §11.

</details>

---

➡️ Next: [Lesson 12 — The experimental design](12-the-design.md)
