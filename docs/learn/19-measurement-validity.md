# Lesson 19 — Finding 7: three ways the platform lies

*Part 2 · about 1 hour · after lesson 18*

**This may be your strongest chapter, because it is the one useful to people who
do not care about your thesis.**

---

## In one sentence

> The platform silently changes which model you get, ignores the parameters you
> send, and does not honour the limits you set — and any study that benchmarks
> open-weight models through an aggregator without accounting for this is
> confounded on both price and precision.

---

## The four findings

### Lie 1 — Provider routing silently changes both price and model

You ask for `deepseek/deepseek-v4-pro`. You have named a model. You have not
named the machine running it.

| Measured fact | Number |
|---|---|
| Providers serving that one slug | **18** |
| Price range, per M output tokens | **$0.87 – $3.48** (4×) |
| What `GET /models` reports | **only the cheapest** provider's price |
| Providers used in one unpinned run | **nine different ones** |
| Billing versus prediction on that run | **1.54×** |
| Quantization range across providers | **fp4 → bf16** |

Two separate problems, and the second is worse:

**Price.** Your cost table says one thing; the bill says another; and nothing
tells you which provider served you. Every CPC and frontier number becomes
irreproducible.

**Precision.** Providers serve different **quantizations** — the model's weights
compressed to 4, 8 or 16 bits (lesson 04). fp4 is a meaningfully different model
from bf16. So unpinned:

> **You are not comparing models. You are comparing an unknown mixture of
> compressed variants, and a failure cannot be attributed to the model rather
> than the compression.**

Your fix: pin provider **and** quantization for every model, `allow_fallbacks:
false`, policy **fp8 or better across the roster** so precision is held constant.
A call either runs at the recorded price and precision or fails outright — and a
failure is recorded and resumable, where a surprise 4× bill is neither.

**And this is not a niche concern.** A survey found **31 of 32 public
repositories use OpenRouter unsafely**. Related published work — *The Silent
Hyperparameter* (May 2026) — quantifies self-hosted backend variance at up to
**16.6 percentage points**. Your contribution is the commercial-aggregator
version, with reasoning modes and cost attached.

### Lie 2 — Advertised reasoning budgets are ignored

You ask the model to think less. It does not.

| What you sent | Reasoning tokens produced |
|---|---|
| `reasoning: {max_tokens: 2000}` | **13,731** — 6.9× the requested budget |
| `reasoning: {effort: "low"}` | **11,926** |

Both were **accepted without error**. Both are listed in the endpoint's
`supported_parameters`. Both were silently ignored. Both then hit the 16,000
ceiling with `finish_reason=length` and returned nothing.

This is *silent non-compliance*, not an unsupported feature — the difference
matters, because an unsupported parameter would at least error.

Two consequences, and both are load-bearing:

1. **Your effort axis is binary in practice.** `{enabled: false}` genuinely
   yields zero reasoning tokens; graded effort levels do not bind. The thesis
   must describe it as off/on, **not as a budget dial**.
2. **It answers the obvious objection to Chapter 7.** *"Why build a runtime abort
   — why not just ask it to think less?"* **Because you cannot.** Ex-ante budget
   control does not work, so runtime monitoring is not a redundant mechanism, it
   is the only one that functions.

### Lie 3 — `max_tokens` is not a hard bound

| Ceiling set | Tokens observed |
|---|---|
| 16,000 | **35,837** |
| 48,000 | **73,037** |

The limit you set is not the limit you get. Which means a cost cap computed from
`max_tokens` is computing from a number the platform treats as advisory — worth
knowing before you rely on one.

### The one that helps — free cancellation

Not everything is bad news:

> **Cancelling a stream mid-reasoning is billed $0.00** — verified on two
> different providers, with no billing record appearing after 10+ minutes.

And reasoning is observable live via `delta.reasoning`, so you can watch the
count climb and kill the call. Measured: abort at ~2,002 reasoning tokens after
33.8 seconds, **billed $0.000000**, where the same cell completed cost
**$0.010978**.

That is what makes Chapter 7's abort a real mechanism rather than a thought
experiment.

**Include this finding.** A chapter that only reports failures reads as a
grievance; one that reports a capability alongside them reads as a survey. It
also happens to be the finding that enables your own intervention.

---

## Why this chapter is your strongest

Four reasons.

**1. It is transferable.** Everything else in your thesis is about *your*
question. This chapter is useful to anyone benchmarking any model through any
aggregator. A reader who cares nothing about reasoning costs still needs it.

**2. It is checkable.** Every claim is a number someone else can reproduce:
18 providers, 4× spread, 6.9× overrun, 1.54× billing, $0.000000 cancellation.

**3. It is a genuine gap.** Your prior-art check found the space *partly*
occupied — *The Silent Hyperparameter*, the LessWrong survey — but the systematic,
quantitative version **on commercial aggregators, with reasoning modes and cost
attached**, is not covered.

**4. It has consequences inside your own thesis**, which proves it is not a
digression:

| Finding | Consequence in your work |
|---|---|
| Provider routing | Pinned roster; prices in `models.yaml` are pinned-endpoint prices, not headline |
| Quantization varies | fp8-or-better policy, so the effort axis is not confounded by precision |
| Budgets ignored | Effort axis described as binary; runtime abort justified |
| `max_tokens` soft | Ceiling raised twice; censoring reported next to every result |
| Free cancellation | Chapter 7's mechanism exists at all |

**⚠️ Be honest about the scope.** Your prior-art check (2026-07-26) recorded:

> The remaining gap — systematic, quantitative, on *commercial aggregators* with
> reasoning modes and cost — is real but **narrow**, and belongs in methodology
> rather than as a headline.

So: a strong **chapter**, not the thesis's headline claim. Position it as
Chapter 4 (Measurement validity), between Method and Results, where it explains
why the results can be trusted.

---

## Why it matters for the writing

This is **Chapter 4**, and it is currently **absent from your proposal
entirely** — one of the four *structural* `.docx` edits (lesson 39).

Structure that works:

1. **The setup.** What an aggregator is and why one is used.
2. **Finding 1** — provider routing. The 18/4×/1.54× numbers, then quantization,
   then why unpinned means comparing different models.
3. **Finding 2** — ignored reasoning budgets, with both consequences.
4. **Finding 3** — soft `max_tokens`.
5. **The helpful one** — free cancellation, with the $0.000000 vs $0.010978
   measurement.
6. **The mitigations you applied**, as the table above.
7. **The general recommendation** for anyone benchmarking this way.

Item 7 is what makes it a contribution rather than a lab note. Write it as
advice a reader can follow: pin the provider, pin the quantization, record both
computed and actual cost, and report your truncation rate.

---

## Do this

**1. Read the roster's comment block.**

```bash
cd ~/thesis
sed -n '1,40p' config/models.yaml
```

Every claim in this lesson is documented there, at the point where it changes
the code. That is where the chapter's raw material lives.

**2. See the price gap yourself.**

```bash
uv run python scripts/verify_roster.py
```

Compare its reported headline prices against `price_out_per_m` in the YAML. For
`deepseek-v4-pro`: **$0.870 headline vs $1.251 pinned.** You pay 44% more to
know what you are running. *That is the price of validity, and it is a
quantified sentence for your chapter.*

**3. Check the drift detector.**

```sql
SELECT COUNT(*) AS n,
       ROUND(AVG(cost_actual_usd / NULLIF(cost_computed_usd, 0)), 3) AS actual_over_computed
FROM generations
WHERE is_mock = 0 AND cost_actual_usd IS NOT NULL AND cost_computed_usd > 0;
```

A ratio near 1.0 means your price table matches reality. **This query is the
reason both columns exist** — with only the estimate, drift is invisible forever.

**4. Find the calls that exceeded their own ceiling.**

```sql
SELECT MAX(completion_tokens) FROM generations WHERE is_mock = 0;
```

Compare with `max_tokens` in `config/experiment.yaml`.

---

## Check yourself

1. Name the three lies and the one helpful behaviour.
2. Why is unpinned quantization worse than unpinned price?
3. What does "silent non-compliance" mean, and why is it worse than an
   unsupported parameter?
4. How does Lie 2 justify Chapter 7's existence?
5. Why is this chapter more transferable than the rest of your thesis?
6. Why should you *not* make it the thesis's headline claim?
7. What does paying $1.251 instead of $0.870 per M tokens buy you?

<details>
<summary>Answers</summary>

1. (a) Provider routing silently changes price and model; (b) reasoning budget
   parameters are accepted and ignored; (c) `max_tokens` is not a hard bound.
   Helpful: cancelling a stream mid-reasoning is billed $0.00.
2. Because a price surprise is a cost problem, but a precision surprise is a
   *validity* problem — you no longer know which model you tested, and a failure
   cannot be attributed to the model rather than the compression.
3. The parameter is accepted, listed as supported, and then ignored. It is worse
   than an unsupported parameter because there is no error — you believe you
   have control that you do not have.
4. Because ex-ante control does not work: you cannot ask the model to think
   less. Runtime monitoring and abort is therefore the only functioning
   mechanism, not a redundant one.
5. Because it is about the measuring apparatus rather than the specific question.
   Anyone benchmarking any model through any aggregator needs it.
6. Because the space is partly occupied — *The Silent Hyperparameter* and the
   LessWrong survey — so the genuinely novel slice (commercial aggregators, with
   reasoning modes and cost) is real but narrow. It is a strong methodology
   chapter, not the headline.
7. A model whose identity you can state: a pinned provider at fp8 or better, at a
   price that does not move. 44% more, for a comparison that means something.

</details>

---

➡️ Next: [Lesson 20 — What this is *not*](20-limitations.md)
