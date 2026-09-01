# Lesson 04 — How you buy tokens, and who you buy them from

*Part 1 · about 45 minutes · after lesson 03*

---

## In one sentence

> You rent a model over the internet by the token — and *who* actually serves
> that model, at what price and at what precision, is not something you get for
> free; you have to pin it down yourself.

---

## The idea, from zero

### What an API is

An **API** (Application Programming Interface) is a way for your program to ask
someone else's program to do something, over the internet.

The everyday analogy is a restaurant. You do not go into the kitchen. You send
an order in a fixed format, and food comes back in a fixed format. The menu is
the API: it tells you what you may ask for and what you will get.

For a language model, an "order" looks roughly like this:

```
POST https://openrouter.ai/api/v1/chat/completions
{
  "model": "deepseek/deepseek-v4-flash",
  "messages": [{"role": "user", "content": "Write a function that..."}],
  "temperature": 0,
  "max_tokens": 48000,
  "reasoning": {"effort": "high"}
}
```

and the reply contains the text plus the `usage` meter from lesson 02.

Your **API key** is the thing that says who to bill. It lives in `.env`, is
never committed to git, and if it leaks someone else spends your money.

### Why OpenRouter and not five separate accounts

Your roster has models from three different companies (DeepSeek, Alibaba's Qwen,
Moonshot). You could sign up to each, learn three different request formats,
manage three keys and three bills.

**OpenRouter** is a middleman: one account, one key, one request format, all the
models. It takes a small markup. Your decisions log records this on 2026-07-25:
*"One key, one schema vs. 6 accounts and 6 adapters."*

For a thesis on a $15 budget with 12 weeks, that is straightforwardly the right
call. But it introduces a problem that took you three findings to discover.

### ⚠️ The thing nobody tells you: a model slug is not a model

When you write `deepseek/deepseek-v4-pro`, you have named a *model*. You have
**not** named a *machine that runs it*.

OpenRouter is a marketplace. Many independent **providers** host the same
open-weight model. And they differ:

| They differ in | Your measured evidence |
|---|---|
| **Price** | `deepseek-v4-pro` is served by **18 providers**, spanning **$0.87 to $3.48** per M output — a 4× spread |
| **Precision (quantization)** | The cheapest endpoints are often `fp4`; others are `fp8` or `bf16` |
| **Which one you get** | Left unpinned, one of your pilot runs was served by **nine different providers**, and billed **1.54× your prediction** |
| **What the price list says** | `GET /models` reports **only the cheapest provider's price** — not the one you will actually be charged |

**Quantization** needs a definition, because it is the more serious half.

A model's knowledge lives in billions of numbers ("weights"). Storing each at
full precision is expensive, so providers **compress** them — 16 bits per number
(`bf16`), 8 bits (`fp8`), or 4 bits (`fp4`). Fewer bits means cheaper and faster
to run, and slightly dumber.

Think of it as a photograph re-saved as a smaller JPEG. Still recognisably the
same picture. Some detail permanently gone.

So if provider A serves `deepseek-v4-flash` at `fp4` and provider B serves it at
`fp8`, and OpenRouter silently routes you to whichever is free:

> **You are not running one experiment. You are running an experiment in which
> the model secretly changes between calls.**

And when a call fails, you cannot tell whether the *model* failed or the
*compression* failed.

### The fix: pin everything

Your [`config/models.yaml`](../../config/models.yaml) pins a specific provider
*and* quantization for every model, and sends it with every request:

```
{"provider": {"order": ["baidu/fp8"], "allow_fallbacks": false}}
```

`allow_fallbacks: false` means: run on this exact endpoint or **fail outright**.
Never quietly substitute.

That is a deliberate trade. A pinned provider that goes down loses you calls.
But — as the file's comment puts it — *"a failure is recorded and resumable; a
surprise 4× bill is neither."*

The policy is **fp8 or better for every model**, so precision is held constant
across the roster. It costs almost nothing: `qwen3.5-9b` gets `bf16` at the same
price as `fp8`, and only Kimi costs more (fp8 $3.40 vs fp4 $2.72).

Which is why the prices in your roster are *higher* than OpenRouter's headline
prices. You are paying for a model you can name.

### Two prices per call, and why you store both

There are two ways to know what a call cost:

| | | |
|---|---|---|
| **`cost_computed_usd`** | `tokens × your price table` | An *estimate*. Instant. |
| **`cost_actual_usd`** | `GET /api/v1/generation?id=…` | **Ground truth** — what you were actually billed |

You store both, on every row. Why both, when one is truth?

**Because a disagreement between them is the only way to detect a silent price
change.** If a provider re-prices and your YAML does not know, `computed` and
`actual` drift apart, and you can see it. Assume the estimate is right and the
drift is invisible forever.

⚠️ One practical wrinkle you measured: `/generation` needs **~10 seconds to
settle** after a call. Blocking on it per call would add hours to a run. So
costs are **reconciled in batch afterwards** (decisions log, 2026-07-25).

### Money discipline, because it is real money

Your project's rules (`CLAUDE.md` §2) exist because the budget was yours:

| Rule | Why |
|---|---|
| **A cap must abort, not warn** | A warning that continues is not a cap |
| **Cap on *worst case*, not expected** | Expected-case caps are defeated by the one call that runs away |
| **Cap against *lifetime* spend** | Five runs each respecting their own limit still empty the account |
| **Never re-buy a generation** | `request_hash UNIQUE` — a crash at row 3,000 costs $0 to resume |
| **Cheapest configurations first** | If a cap fires, you lose the expensive tail, not the cheap foundation |
| **Do not load the full budget** | $15 loaded, $6 spendable — **$9 is unreachable no matter what a bug does** |

That last row is the best idea in the list, and it is worth a sentence in your
Method chapter. The strongest cost control is money that is not in the account.

Final spend: **$5.25**, against a $15 balance and a $6 abort threshold. Never
breached.

---

## Why it is in *your* thesis

Two chapters, directly.

**Chapter 3 (Method)** must state that every model is served from a pinned
provider at a pinned quantization, and *why*. Without that sentence, a careful
examiner cannot reproduce your prices, and a hostile one can ask whether your
"model comparison" compared models at all.

**Chapter 4 (Measurement validity)** is *built out of this lesson*. It is,
arguably, your strongest chapter, because it generalises past your thesis:

> Any study benchmarking open-weight models through an aggregator without
> pinning is confounded on both price and precision.

And you have a citation showing this is widespread rather than hypothetical: a
survey found **31 of 32 public repositories use OpenRouter unsafely**
(THESIS.md §1 log, 2026-07-26). Related published work — *The Silent
Hyperparameter*, May 2026 — quantifies self-hosted backend variance at up to
16.6 percentage points.

Your contribution here is the commercial-aggregator version of that, with
reasoning modes and real prices attached. Narrow, but real, and *transferable* —
someone reading only Chapter 4 learns something they can use tomorrow.

---

## Do this

**1. Look at the roster and read its comments.**

```bash
cd ~/thesis
cat config/models.yaml
```

The comment block at the top (lines 1–38) is the best single piece of prose in
the repository. Read all of it. Note especially the `deepseek-v4-pro` comment:
the official endpoint is *both* cheapest *and* unquantized, and it is blocked by
your account's data-privacy setting — enabling providers that may train on your
inputs would have saved 30% on the dearest model. You chose privacy. That is a
methodological decision worth one sentence in Chapter 3.

**2. Verify the roster against the live API (free, no key needed).**

```bash
uv run python scripts/verify_roster.py
```

This checks your recorded slugs and prices against OpenRouter's live `/models`.
It exits non-zero if anything drifted. Reproducibility is a graded property —
this script is how you prove the roster was not invented.

**3. See the price spread in one query.**

```bash
uv run python scripts/view.py HumanEval/0
```

Every configuration solved this problem. The cost of doing so ranged **44×**,
from $0.000106 to $0.004630. Identical outcome, 44× the price. Sit with that for
a moment — it is the cleanest single illustration of your thesis's motivation,
and it belongs in Chapter 1.

*(You will see **58×** quoted in the project log and in Chapter-3 history. That
was the same cell priced before providers were pinned — pinning re-priced
several models, and costs were later reconciled against the actual bill. 58× is
the historical observation; **44× is what reproduces today**. This is a good
habit to notice: a price table is a snapshot, and a number computed from one is
only as reproducible as the snapshot behind it.)*

---

## Check yourself

1. What is an API key and why is `.env` gitignored?
2. Why did you use OpenRouter rather than three provider accounts?
3. A model slug names a model. What does it *not* name?
4. What is quantization, and why does an unpinned quantization break a model
   comparison?
5. Why store both a computed and an actual cost when one of them is ground
   truth?
6. Why is "load only $15 when the cap is $6" a better control than a bigger cap?
7. Your roster's prices are higher than OpenRouter's advertised prices. Is that
   a mistake?

<details>
<summary>Answers</summary>

1. The credential that says whose account to bill. Committing it to git would
   publish it, and anyone could spend your balance.
2. One key, one request format, one bill, instead of six accounts and six client
   adapters. A small markup, worth it at this scale.
3. It does not name the *provider* — the machine actually serving it — nor the
   *quantization* that provider uses. Both vary, both change what you pay and
   what you get.
4. Compressing the model's weights to fewer bits (fp4/fp8/bf16) — cheaper and
   slightly less capable. Unpinned, different calls hit different precisions, so
   a failure cannot be attributed to the model rather than the compression, and
   you are no longer comparing like with like.
5. Because their *disagreement* is the only detector of silent price drift. With
   only the estimate, a stale price table corrupts every cost number invisibly.
6. Because it does not depend on the code being correct. A cap is code and code
   has bugs; an unloaded balance is a physical limit.
7. No — deliberate. The headline price is the cheapest, usually most-quantized
   endpoint. You are paying for a pinned fp8-or-better endpoint so that the model
   under test is held constant.

</details>

---

➡️ Next: [Lesson 05 — What a benchmark is](05-benchmarks.md)
