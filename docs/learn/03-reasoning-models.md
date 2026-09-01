# Lesson 03 — Reasoning models and the invisible bill

*Part 1 · about 1 hour · after lesson 02*

**This is the single most important foundation lesson. Everything else in the
thesis stands on it.**

---

## In one sentence

> A reasoning model writes out its private thinking before answering — you never
> see those tokens, but you pay for every one of them.

---

## The idea, from zero

### Thinking out loud, quietly

Ask someone: *"A bat and a ball cost $1.10. The bat costs $1 more than the ball.
How much is the ball?"*

Most people blurt "10 cents". It is wrong (the answer is 5 cents). People who
get it right almost always **work it out first** — on paper, or in their head —
and only then say the answer.

Language models turned out to be the same. Around 2024–2025, model builders
discovered that if you let a model produce a long stretch of working-out before
its final answer, it gets dramatically better at maths, logic and code.

Then they made it a product. A **reasoning model** does this by default:

```
YOU SEND:   "Solve: a bat and ball cost $1.10..."

MODEL PRODUCES (privately):
    "Let ball = x. Bat = x + 1. So x + x + 1 = 1.10.
     2x = 0.10, x = 0.05. Check: 0.05 + 1.05 = 1.10. ✓"     ← 400 tokens

MODEL PRODUCES (visibly):
    "The ball costs 5 cents."                                ←  6 tokens

YOU SEE:    "The ball costs 5 cents."
YOU PAY FOR: 406 tokens
```

That private stretch is called the **reasoning trace**, or *chain of thought*,
or *thinking*. The tokens in it are **reasoning tokens**.

### Why they are hidden

Model providers hide the trace for competitive reasons — the raw thinking is the
most valuable training signal they have, and they would rather not hand it to
rivals. Some show a summary. Most show nothing.

The consequence for you is severe and simple:

> **You cannot price a call by looking at the answer.**

### The trap, measured on Day 1 of your project

You sent the most trivial prompt imaginable — *"write a Python function that
reverses a string"* — to one model.

| | |
|---|---|
| Visible answer | 3 lines of code, ~20 tokens |
| Completion tokens billed | **412** |
| Of which reasoning | **392** |
| Understatement if priced from visible text | **~20×** |

That is your thesis's origin story. Everything after it exists because of that
number.

### ⚠️ The arithmetic rule that must never be broken

Here is how the meter reports itself:

```
usage:
  prompt_tokens: 99
  completion_tokens: 412                        ← THE BILLED TOTAL
  completion_tokens_details:
    reasoning_tokens: 392                       ← A SUBSET OF THE LINE ABOVE
```

> **Reasoning tokens are *already inside* completion tokens.**

So the cost of that call is:

```
(99 × price_in  +  412 × price_out) ÷ 1,000,000        ✅ correct
(99 × price_in  +  412 × price_out + 392 × price_out) ÷ 1,000,000   ❌ WRONG
```

The wrong version double-charges every thinking call — which means it inflates
**exactly the configurations your thesis is about**, by roughly 2×, and does it
silently. Every cost-per-correct number, every frontier point, every conclusion
would be wrong in the same direction, and nothing would look obviously broken.

This is why [`carr/cost.py`](../../carr/cost.py) is 25 lines with a 14-line
comment. The comment is doing more work than the code.

### Controlling how much it thinks — and why you cannot

You can, in principle, ask for more or less thinking:

```
reasoning: {enabled: false}     ← off. Genuinely produces 0 reasoning tokens
reasoning: {effort: "high"}     ← think hard
reasoning: {effort: "low"}      ← think a little
reasoning: {max_tokens: 2000}   ← think for at most 2,000 tokens
```

Your thesis uses only the first two. **The other two do not work**, and you
proved it:

| What was asked | What happened |
|---|---|
| `reasoning: {max_tokens: 2000}` | **13,731** reasoning tokens — **6.9× the requested budget** |
| `reasoning: {effort: "low"}` | **11,926** reasoning tokens |

Both were accepted without an error. Both are listed as supported by the
endpoint. Both were silently ignored.

**This is why your effort axis is binary — off or on — and it must be described
that way in the thesis, not as a "budget dial".** It is also the answer to the
most obvious objection anyone will raise: *"why not just tell it to think
less?"* Because you can't. That is measured, not assumed.

### The ceiling, and the thing it does to your data

`max_tokens` (the plain one, not the reasoning one) is your safety net: a hard
ceiling on total output. Hit it and the call is chopped off with
`finish_reason = "length"`.

Now combine two facts:

1. A chopped-off call usually contains **only reasoning** — the model never got
   to the answer.
2. You **pay in full** for the chopped-off tokens.

So a truncated thinking call is the worst possible outcome: **maximum cost, zero
value.** In your data, **49 calls burned an average of 29,584 reasoning tokens
and returned nothing at all**, costing $0.56 — **15% of everything you spent on
reasoning-enabled calls**, and 11% of all spend.

And there is a subtler consequence that lesson 16 is entirely about: a ceiling
does not just cause failures, it **censors your measurements**. If you cannot
observe any call longer than 16,000 tokens succeeding, you may wrongly conclude
that long thinking never succeeds — when in fact you just never let it finish.
Your pilot made exactly that mistake, and the grid caught it.

---

## Why it is in *your* thesis

Because it *is* your thesis. Restated with this lesson's vocabulary:

> **Reasoning tokens are billed and invisible. When are they worth paying for?**

Every finding is a statement about reasoning tokens:

| Lesson | Finding | The reasoning-token statement |
|---|---|---|
| 14 | Thinking works, conditionally | On hard problems, spending reasoning tokens **doubles** the pass rate (24.9% → 54.2%); on easy ones it buys ~4 points |
| 15 | Expensive failure | Passing calls average **7,567** reasoning tokens; calls returning nothing average **29,584** |
| 13 | Saturation | On 81 of 320 problems, reasoning tokens change nothing — everything already passes |
| 16 | The abort | Can you cut a call off once its reasoning gets too long? Yes — but not for free |
| 17 | The frontier | Reasoning tokens on a *cheap* model beat a frontier model at 1/6 the price |

And your database has a column for it — `generations.reasoning_tokens` — on all
1,373 rows. **CodeRouterBench, the closest published work to yours (9,999 tasks
× 8 models), does not have that column.** That absence is a large part of why
your table is a contribution at all.

---

## Do this

**1. See a reasoning trace's size against its answer.**

```bash
cd ~/thesis
uv run python scripts/view.py --list | head -20
```

Pick a LiveCodeBench problem id from that list (they look like `lcb/...`), then:

```bash
uv run python scripts/view.py <that-problem-id>
```

Compare the `off` rows with the `high` rows. The `high` rows will have token
counts an order of magnitude larger, for the same problem, often with the same
pass/fail outcome.

**2. Read the 25-line file the whole cost model lives in.**

```bash
cat carr/cost.py
```

Read the docstring twice. It is the clearest statement of the double-count trap
in the repository, and you will paraphrase it in Chapter 3 of the thesis.

**3. Feel the money.**

Compute in your head, then check:

- Flash `off` on an easy problem: ~350 output tokens at $0.182/M →
  `350 × 0.182 ÷ 1e6` = **$0.000064**
- Kimi `high` on a hard problem: ~30,000 output tokens at $3.40/M →
  `30,000 × 3.40 ÷ 1e6` = **$0.102**

**Ratio: about 1,600×.** Same problem, same "please write this function". That
spread is the thing you measured.

---

## Check yourself

1. What is a reasoning token, and why can't you see it?
2. Are reasoning tokens counted inside `completion_tokens` or in addition to
   them? What breaks if you get this backwards?
3. Your Day 1 call: 412 completion tokens, 392 reasoning. If you had priced it
   from the visible answer, how far off would you be?
4. Why is your thesis's effort axis binary rather than a dial?
5. Why is a truncated thinking call the worst possible outcome, economically?
6. What is the difference between a truncation *causing failures* and a
   truncation *censoring your measurements*?

<details>
<summary>Answers</summary>

1. A token the model produces while working out its answer, before writing the
   answer. Providers hide the trace, mostly to protect competitive advantage.
2. **Inside.** If you add them separately you double-charge every thinking call,
   inflating precisely the configurations under study by ~2×, silently, in a way
   no output looks wrong about.
3. ~20× understated — you would have priced ~20 visible tokens instead of 412
   billed ones.
4. Because graded effort controls do not bind: `effort: "low"` produced 11,926
   reasoning tokens and `max_tokens: 2000` produced 13,731. Only
   `{enabled: false}` genuinely changes behaviour, so the honest description is
   off/on.
5. You pay for every token generated up to the ceiling, and you receive nothing
   usable. Maximum cost, zero value — 49 such calls cost you $0.56, 15% of the
   reasoning arm's $3.62 and 11% of all spend.
6. Causing failures means those calls fail — bad, but a real property you can
   report. Censoring means *you can never observe what would have happened*
   above the ceiling, so any conclusion about long reasoning is biased by the
   ceiling itself. That is lesson 16, and it invalidated one of your headlines.

</details>

---

➡️ Next: [Lesson 04 — How you buy tokens, and who you buy them from](04-buying-tokens.md)
