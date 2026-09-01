# Lesson 16 — Finding 4: the claim that was refuted

*Part 2 · about 1 hour · after lesson 15*

**This is the best story in your thesis. Learn it properly — you will be asked
about it.**

---

## In one sentence

> Your pilot found a **free** way to save 44% of thinking spend; the full grid
> proved it was an artefact of your own token ceiling; and catching that is
> better science than the original claim would have been.

---

## The story, in five acts

### Act 1 — A real mechanism

Three facts, measured in order, that together make an intervention possible:

1. **Reasoning length is visible live.** The API streams `delta.reasoning`, so
   you can watch the reasoning-token count climb *while the call is still
   running*.
2. **Cancelling mid-stream is billed $0.00.** Verified twice, on two different
   providers, with no billing record appearing after 10+ minutes.
3. Therefore: **you can watch a call's thinking, and kill it if it runs too
   long, and pay nothing.**

That third point is not a thought experiment. You tested it end to end on
`deepseek-v4-pro | high`: aborted at ~2,002 reasoning tokens after 33.8 seconds,
**billed $0.000000**, where the same cell run to completion cost **$0.010978**.

⚠️ **Provenance of the $0.010978 comparison figure — check before quoting.** The
$0.00 cancellation itself is solid: verified on two providers, with no billing
record appearing afterwards. The *comparison* baseline is weaker. The abort test
was an exploratory call made outside the runner and never written to
`generations`, so **$0.010978 is not reproducible from the database** — and the
only row that carries that exact cost is `qwen3.6-35b-a3b|high` on
`LiveCodeBench/3697` (gen 141), a different model from the `deepseek-v4-pro|high`
the log attributes the test to. Treat "the same cell run to completion cost
$0.010978" as an unverifiable note rather than a datum.

**What to say instead**, from the stored grid and fully reproducible: a
completed `deepseek-v4-pro|high` call costs **$0.012165 on average** (n=73, max
$0.060253), and `kimi|high` **$0.057706** (n=23). An abort saves the whole of
that, not a pro-rata share — which is the actual point, and it does not need the
disputed figure.


This matters more than it first appears. Most "save money on inference" ideas are
*pro-rata* — you pay for what you used. This one is **free cancellation**. That
makes an abort a genuinely different kind of control.

Combined with lesson 03's finding that you **cannot ask a model to think less**
(`effort: "low"` produced 11,926 tokens; `max_tokens: 2000` produced 13,731),
runtime abort is not a redundant mechanism — **it is the only one that works.**

### Act 2 — The pilot's beautiful result

Simulated on pilot data:

> **Abort at 10,000 reasoning tokens: keeps 42 of 42 passes, cuts thinking-config
> spend by 44%.**

A free lunch. No solved problem lost, nearly half the money saved. At 6,000
tokens it saved 78% for 10% fewer solved.

This became the thesis's headline for a few days. It is easy to see why —
it is a clean, actionable, quantified recommendation.

### Act 3 — The doubt

One day later, a check on truncation rates:

> At the pilot's 16,000-token ceiling, **43.8% of LCB-hard and 36.4% of
> LCB-medium thinking calls were cut off and returned nothing.**

And then the thought that unravels it:

> **A censored call cannot succeed.**

⚠️ Say that carefully, because it is true in two different ways and an examiner
may separate them. In the *analysis code* it is true by construction:
`analysis._WASTED` scores any billed, truncated call as solving nothing whatever
the grader said, which is a deliberate choice — a response cut off mid-stream is
not an answer you could ship. Independently of that, it is also true
*empirically*: **zero of the 101 truncated rows produced extracted code that
passed.** Quote the empirical version, because the definitional one cannot be
evidence for itself.

Follow the logic slowly, because it is the whole lesson:

- The pilot's ceiling was 16,000 tokens.
- Any call that passed 16,000 was chopped off and scored as a failure —
  **automatically**, by construction.
- So in the pilot data, **no call above ~16,000 reasoning tokens could ever be
  observed succeeding.**
- The claim "nothing above 10,000 reasoning tokens ever succeeded" therefore
  described **the ceiling**, not the models.

> **The instrument manufactured the finding.**

This is **censoring**, and it is a named hazard in statistics: when your
measurement device cannot record values above a limit, every conclusion about
large values is a property of the device.

The analogy that makes it stick: you own a thermometer that maxes out at 40°C.
You record temperatures all summer and conclude *"it never gets hotter than
40°C here."* Your data supports it perfectly. Your data is worthless for that
question.

### Act 4 — The refutation

The ceiling was raised (16k → 32k → 48k) before the grid. The grid then said:

> **56 calls above 10,000 reasoning tokens succeeded.**

The cliff was gone. What replaced it is a **gradient**:

| reasoning tokens | pass rate |
|---|---|
| under 10,000 | **83.8%** |
| 10,000–20,000 | 55.2% |
| above 20,000 | **39.3%** |

Long thinking is *worse*, but far from hopeless. `best_threshold()` — the
function that looks for a free abort point — now correctly returns **None**.

The honest replacement finding:

> **Abort at 16,000 reasoning tokens keeps 212 of 242 solutions (88%) for half
> the cost.**
>
> With intervals: keeping **88% [82, 92]**, saving **49% [35, 61]%**.

And the summary line your own analysis prints:

> ***"No threshold saves money without losing a solved problem."***

⚠️ One residual caveat, which you report rather than hide: **26.3% of hard
thinking calls still truncate at 48,000**, so the ">20k" band's 39.3% is itself
a floor. The censoring is *reduced*, not eliminated. You could only eliminate it
by removing the ceiling — and you deliberately did not, because without a
ceiling the worst case is bounded only by context length (Kimi at 262,144 tokens
is $0.89 for a *single call*), and the cost cap computes its reservation *from*
`max_tokens`, so it would have nothing to bound.

That is a genuine, stated trade: **some censoring, in exchange for a cost cap
that can exist at all.**

### Act 4b — 🔴 The twist: the free threshold *does* exist, per model

Found after the rest of this course was written, and it makes the story better
rather than worse.

"No threshold saves money without losing a solved problem" is a statement about
the **pooled** roster. Split by model, it is **false for two of five**:

| model | free threshold | saving | solutions kept |
|---|---|---|---|
| **`qwen3.5-9b`** | **10,000 tokens** | **88%** | **46 / 46** |
| **`qwen3.6-35b-a3b`** | **16,000 tokens** | **13%** | **43 / 43** |
| `deepseek-v4-flash` | none — every threshold costs a solution | | |
| `deepseek-v4-pro` | none | | |
| `kimi-k2.6` | none | | |

Read `qwen3.5-9b`'s row again: **abort at 10,000 reasoning tokens, keep every
single one of its 46 solutions, and save 88% of what it spent thinking.** That
is exactly the free lunch the pilot claimed — and it is real. It just belongs to
a model, not to a roster.

**Why this is not luck, and how to say so.** Look at *which* models have it.
`qwen3.5-9b` is the model whose reasoning delta is negative on three tiers of
four (lesson 14) and which returns nothing on 37% of its thinking calls (lesson
15). Everything it solved, it solved early; everything long was already doomed,
so cutting the tail is free. `deepseek-v4-flash` gains **+52.9 points** on hard
problems *by* thinking longer — cut its tail and you cut its solutions. The
free threshold appears **exactly where reasoning was not earning its keep**, and
vanishes exactly where it was. That is a mechanism, not a coincidence.

**And notice what this does and does not do to Act 4.** It does **not** restore
the pilot's claim: that claim was about the roster, and at roster level it is
still false, and the 16k ceiling still manufactured part of it. What it does is
replace a flat negative with a conditional positive:

> **Whether a reasoning-length abort is free is a property of the model.** Where
> long reasoning rarely succeeds it is free money. Where it genuinely solves
> hard problems, every threshold costs solutions.

That is a better result *and* a better story: you found a free lunch, disproved
it, and then found the precise conditions under which it is real. Tell it in
that order — it is the most persuasive three minutes you have.

⚠️ Same caveats as the pooled curve: a simulation over completed calls, resting
on the measured $0.00 cancellation, and a threshold chosen on this data is
fitted unless you evaluate it on data it was not chosen on. With 46 solutions
behind `qwen3.5-9b`'s row, say "suggestive and mechanistically explained", not
"established".

### Act 5 — Why this is a strength

Three reasons, and you should be able to give all three without flinching:

1. **A refuted claim beats an unexamined one.** The pilot's version would have
   been in the thesis as a headline recommendation, and it was **false**. Anyone
   reproducing it with a higher ceiling would have found it out — and finding it
   yourself is very different from having it found for you.
2. **The corrected version is still useful.** 88% of solutions for half the cost
   is a real operating point. It is just a *trade-off* rather than a free lunch,
   and honest engineering is full of trade-offs.
3. **It generalises past your thesis.** *"A truncation limit is a censoring
   mechanism, and censored observations bias any analysis of the thing being
   truncated."* Anyone who benchmarks reasoning models under a token cap needs
   that sentence. It is one of the most transferable things you have.

And note the process that caught it — `analysis.censoring()` now reports the
truncation rate **next to every result**, so this specific failure can never hide
again. The right response to a subtle bug is not resolve; it is a permanent
check.

---

## Why it matters for the writing

This is **Chapter 7**, and it should be written as the narrative above — claim,
doubt, mechanism, refutation, replacement. Not as a tidy "we investigated abort
thresholds and found a tradeoff curve."

Why tell it as a story? Because the *reasoning* is the contribution. The final
number (88% for half the cost) is modest. The demonstration that a token ceiling
silently manufactures findings is not.

Structure:

1. The mechanism, with the three measured facts (live visibility, $0
   cancellation, ex-ante control does not work).
2. The pilot's claim, stated as you believed it.
3. The censoring insight — including the thermometer analogy.
4. The grid's refutation: 56 successes above 10,000; the gradient table.
5. The honest tradeoff curve, with intervals.
6. The residual censoring, and why the ceiling stays.
7. The general lesson for anyone benchmarking under a token cap.

⚠️ **Do not bury this in Limitations.** It is a result. Limitations get skimmed;
Chapter 7 gets read.

---

## Do this

**1. See the abort curve and its intervals.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ3/,$p'
```

Find the line saying no threshold is free.

**2. Look at the picture.**

```bash
uv run python scripts/make_figures.py && open data/figures/04-abort-tradeoff.png
```

Note the confidence band. Its width is the honest statement: the 49% saving is
somewhere between 35% and 61%.

**3. Find the 56 calls that refuted the claim.**

```sql
SELECT COUNT(*) FROM generations g JOIN results r USING (gen_id)
WHERE g.is_mock = 0 AND r.passed = 1 AND g.reasoning_tokens > 10000;
```

**Every one of these was impossible under the pilot's ceiling.** That query is
the refutation in one line.

**4. Measure the censoring that remains.**

```sql
SELECT p.difficulty,
       SUM(finish_reason = 'length') AS truncated,
       COUNT(*) AS n,
       ROUND(100.0 * SUM(finish_reason = 'length') / COUNT(*), 1) AS pct
FROM generations g JOIN problems p USING (problem_id)
WHERE g.is_mock = 0 AND g.reasoning_tokens > 0
GROUP BY p.difficulty;
```

**5. Practise telling the story in 90 seconds.** Out loud. Claim → doubt →
mechanism → refutation → what survives. You will tell this at your defence.

---

## Check yourself

1. What three measured facts make a runtime abort a real mechanism?
2. Why is free cancellation different from a pro-rata saving?
3. State the pilot's claim, and explain in your own words why it was false.
4. Explain censoring with the thermometer analogy.
5. What replaced the claim? Give the numbers *and* the intervals.
6. Why was the ceiling raised to 48,000 rather than removed?
7. Why does this belong in a results chapter rather than in Limitations?

<details>
<summary>Answers</summary>

1. Reasoning length is visible live via `delta.reasoning`; cancelling mid-stream
   is billed $0.00 (verified on two providers); and you cannot control thinking
   length ex ante, since `effort: "low"` and `max_tokens: 2000` are both ignored.
2. Pro-rata means you still pay for what was generated. Free cancellation means
   an aborted call costs nothing at all — verified at $0.000000 against
   $0.010978 for the same completed cell.
3. "Abort at 10,000 reasoning tokens: keeps 42/42 passes, saves 44%." It was
   false because the pilot's 16,000-token ceiling meant no call above ~16,000
   could ever be recorded as a success — so the apparent cliff was the ceiling,
   not the models.
4. A thermometer that maxes at 40°C will never record a temperature above 40°C,
   so it can never disprove "it never gets hotter than 40°C". Your ceiling did
   the same to long reasoning traces.
5. A gradient, not a cliff: 83.8% under 10k, 55.2% at 10–20k, 39.3% above 20k.
   Abort at 16,000 keeps 212/242 solutions — 88% [82, 92] — for a 49% [35, 61]
   saving. No threshold is free.
6. Because with no ceiling the worst case is bounded only by context length (a
   single Kimi call could cost $0.89), and the cost cap computes its reservation
   from `max_tokens`. Some residual censoring was accepted so a cap could exist.
7. Because it is a result, not a shortcoming: the mechanism, the refutation and
   the tradeoff curve are findings. Limitations chapters get skimmed, and this is
   the most transferable material in the thesis.

</details>

---

➡️ Next: [Lesson 17 — Finding 5: the frontier, the hull and the oracle](17-frontier-and-oracle.md)
