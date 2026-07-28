# Lesson 15 — Finding 3: expensive failure

*Part 2 · about 45 minutes · after lesson 14*

---

## In one sentence

> **49 calls burned an average of 29,584 reasoning tokens and returned nothing
> at all** — about **15% of everything you spent** — and a model that thinks for
> a very long time is not working harder, it is failing expensively.

---

## The finding

### Reasoning length rises with difficulty

Mean reasoning tokens, by tier:

| tier | mean reasoning tokens |
|---|---|
| MBPP+ | 642 |
| HumanEval+ | 773 |
| LiveCodeBench easy | 2,693 |
| LiveCodeBench medium | 10,183 |
| **LiveCodeBench hard** | **17,547** |

**27× from easiest to hardest, and monotonic** — every step up in difficulty
raises it. That is reassuring: it means the models' internal sense of difficulty
broadly agrees with the benchmark's labels, which is a small validity check you
get for free.

### But length also predicts *failure*

Now split by outcome instead of by difficulty:

| outcome | n | mean reasoning tokens | spend |
|---|---|---|---|
| passed | 242 | 7,567 | $2.52 |
| failed (wrong answer) | 49 | 7,577 | $0.55 |
| **billed, no answer at all** | **49** | **29,584** | **$0.56** |

Look carefully. There are three groups, not two, and the third is the finding.

- **Passed and failed look identical** — 7,567 vs 7,577 reasoning tokens. Among
  calls that produce *an answer*, length tells you almost nothing about whether
  it is right.
- **The third group is 3.9× longer than either.** These calls never produced an
  answer at all. They thought, and thought, and hit the ceiling.

So the honest statement is not "long thinking means wrong". It is:

> **Very long thinking predicts *not finishing*, and not finishing costs full
> price for zero value.**

That distinction matters. The signal is not about correctness; it is about
**termination**.

### The economics: 15% of the budget bought nothing

$0.56 of $5.24 — call it **one dollar in seven** — went on calls that returned no
usable code.

Restate it at deployment scale: run this workload at a $15,000/month spend and
roughly **$2,200 a month buys literally nothing**. Not "buys a wrong answer" —
buys *no answer*.

That is the sentence a practitioner remembers, and it is the strongest economic
finding in the thesis after the 305× CPC spread.

### Why does a model think forever and produce nothing?

Two mechanisms, and you should distinguish them because only one is the model's
fault:

1. **Non-termination.** The model genuinely fails to converge — it goes round in
   circles, second-guesses, restarts. There is a small published literature on
   this (*ThoughtTerminator*, *SelfBudgeter*, *RecurGuard*), which you cite. **You
   are not claiming novelty on the phenomenon.**
2. **Truncation.** Your `max_tokens` ceiling cut the call off before it could
   finish. The model might have terminated at 60,000 tokens.

Your data cannot fully separate these, and you must say so. What you *can* say is
the joint fact, which is enough to be useful:

> Under a fixed token budget, **26.3% of hard thinking calls do not produce an
> answer**, and those calls cost full price.

That is a real property of deploying reasoning models under a budget — because
real deployments *have* budgets. Framed that way, the ceiling stops being a
measurement flaw and becomes part of the thing measured. Lesson 16 is where that
framing gets tested to breaking point.

### Where your contribution actually is

Be precise, because this is a place where over-claiming is easy:

| Claim | Status |
|---|---|
| "Reasoning models sometimes fail to terminate" | ❌ **Not novel.** ThoughtTerminator (Jul 2025), SelfBudgeter (May 2025), RecurGuard (2026) |
| "Non-termination can be detected from reasoning length" | ❌ Also covered |
| **"It costs 15% of a real code-generation budget, priced across a roster spanning 305× in cost per correct answer"** | ✅ **The economic framing is the less-covered part** |

Your prior-art check (2026-07-26) recorded this honestly and downgraded the
claim at the time:

> *Reasoning non-termination is NOT novel.* The remaining gap — systematic,
> quantitative, on *commercial aggregators* with reasoning modes and cost — is
> real but narrow, and belongs in methodology rather than as a headline.

**Writing that down about your own idea, in your own log, is the behaviour that
makes the rest of the thesis trustworthy.** Do it in Chapter 2 as well: name the
three prior works, state exactly what they cover, and claim only the economic
layer.

---

## Why it matters for the writing

This section belongs in **Chapter 5**, after the pass-rate results, and it sets
up Chapter 7 (the abort mechanism). The chain is:

> Thinking helps on hard problems (lesson 14) → but sometimes it runs away and
> returns nothing (this lesson) → so can you cut it off when it does? (lesson 16)

Presentation notes:

- **Lead with the three-way outcome table.** The passed/failed near-identity is
  what makes the third row surprising; without it, "long calls fail" sounds
  obvious.
- **Convert to money immediately.** 29,584 tokens means nothing to most readers;
  "15% of the budget bought nothing" means everything.
- **State the two mechanisms and admit you cannot separate them.**
- **Cite the three prior works in the same breath**, so the claim is scoped
  before anyone scopes it for you.

---

## Do this

**1. See the three groups.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ2/,/censor/p'
```

**2. Look at the picture.**

```bash
uv run python scripts/make_figures.py && open data/figures/02-reasoning-vs-outcome.png
```

Three bars. The third one towers over the others.

**3. Find the worst individual calls.**

```sql
SELECT problem_id, config_id, reasoning_tokens, completion_tokens,
       finish_reason, cost_actual_usd
FROM generations
WHERE is_mock = 0
ORDER BY reasoning_tokens DESC LIMIT 10;
```

Look at the `finish_reason` column. Then open one of those rows in Studio and
read its `raw_response`. **You are looking at a model thinking itself to death
at your expense** — thousands of tokens of working-out, no answer, full price.

Do this once. It makes the finding physical rather than statistical.

**4. Compute the waste share yourself.**

```sql
SELECT
  SUM(CASE WHEN extracted_code IS NULL OR extracted_code = ''
           THEN cost_actual_usd ELSE 0 END) AS wasted,
  SUM(cost_actual_usd) AS total
FROM generations WHERE is_mock = 0;
```

Divide. You should land near 15%.

---

## Check yourself

1. State the finding with its three numbers: calls, mean tokens, share of spend.
2. Why is "long reasoning means the answer is wrong" the wrong conclusion?
3. What are the two mechanisms behind a long call returning nothing, and can
   your data separate them?
4. What part of this finding is novel, and what part is not? Name the prior
   work.
5. Why does converting 29,584 tokens into "15% of spend" matter for the writing?
6. Why is the monotonic rise in reasoning length across tiers a useful validity
   check?

<details>
<summary>Answers</summary>

1. 49 calls, mean 29,584 reasoning tokens, $0.56 — about 15% of the $5.24 spent
   — returning no usable code at all.
2. Because passing and failing calls have nearly identical mean reasoning length
   (7,567 vs 7,577). Length does not separate right from wrong; it separates
   *finishing* from *not finishing*.
3. Genuine non-termination (the model fails to converge) and truncation (your
   `max_tokens` ceiling cut it off). Your data cannot fully separate them, and
   the thesis says so.
4. The phenomenon is not novel — ThoughtTerminator, SelfBudgeter and RecurGuard
   cover reasoning non-termination. The economic framing (share of a real budget,
   priced across a roster with a 305× CPC spread) is the less-covered part.
5. Because tokens are an abstraction and money is not. "One dollar in seven
   bought nothing" is the sentence a reader carries out of the chapter.
6. Because it shows the models' effort broadly tracks the benchmark's difficulty
   labels — an independent check that the difficulty tiers mean something.

</details>

---

➡️ Next: [Lesson 16 — Finding 4: the claim that was refuted](16-the-abort-story.md)
