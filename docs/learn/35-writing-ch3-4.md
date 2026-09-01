# Lesson 35 — Writing Chapters 3 and 4

*Part 4 · about 3 hours of writing · after lesson 34*

---

## In one sentence

> Chapter 3 must let a stranger rebuild your experiment and get your numbers;
> Chapter 4 must convince them the instrument was trustworthy — and it is the
> chapter your proposal does not have.

---

## Chapter 3 — Method

### The standard

> Could a competent stranger, with your budget and this chapter, reproduce your
> table?

Not "does it sound rigorous". **Could they do it.** Which means every choice that
would change a number must be stated.

### Section by section, with your material

**3.1 The unit of measurement.** One (problem, configuration) pair = one API
call = one row. Show the pipeline diagram: problem + config → paid call → extract
→ grade → row.

**3.2 The roster and provider pinning.** Five open-weight models across **three**
families — say "three" explicitly, and acknowledge two DeepSeek and two Qwen.

Then the pinning, which is the part most papers omit:

> Every model is pinned to one provider and one quantization via
> `provider: {only: [tag], allow_fallbacks: false}`, with a policy of **fp8 or
> better across the roster** so precision is held constant. Prices are
> per-endpoint, not the `/models` headline, and are therefore higher than the
> advertised price for the same slug.

State the trade: **availability for reproducibility.** A pinned provider that is
down produces a failed, resumable call rather than a silently different result.

**3.3 The effort axis.** Two levels, `off` and `high`, **with the model held
constant within each pair** — so a difference is attributable to reasoning rather
than to capability.

⚠️ And the concession that must appear here: **the axis is binary in practice,
not graded.** `{enabled: false}` genuinely yields zero reasoning tokens, but
`effort: "low"` and `reasoning: {max_tokens: N}` were accepted and ignored
(Chapter 4). Do not describe it as a budget dial.

**3.4 Problems.** Pool **884** (HumanEval+ 164, MBPP+ 378, LiveCodeBench 342).
Run **320**. Stratified sampling with a fixed seed, weighted toward the
discriminating tier after the pilot. Say plainly that 320 of 884 is a **budget**
decision — every problem costs 10 API calls — not a filtering one.

**3.5 Protocol.** pass@1, one sample, temperature 0. Give both reasons (halves
cost; makes the cheapest-passing label deterministic) and the cost (no
within-configuration variance). Note that `temperature_sent` is logged because
some thinking endpoints override it.

**3.6 Grading.** One file. EvalPlus's `untrusted_check` — and say why that is a
*correctness* decision: `atol` float comparison, MBPP special oracles.
Subprocess isolation and `reliability_guard`, **with the honest threat model**
(*"not a security sandbox"*; accidents and casual hostility). The second grading
path for LiveCodeBench's two execution styles. Validation against **210 canonical
solutions**, and hand-written references for LCB, which ships none.

And the bug, in one short paragraph:

> A macOS-specific interaction — `setrlimit` cannot lower the address-space limit
> on Darwin — caused the sandbox guard to raise before any test ran, which
> EvalPlus reports as a timeout. Every solution, including the benchmark's own
> canonical ones, silently failed. It was caught by the canonical-solution check
> and fixed by disabling the memory cap; the residual cost is that runaway
> allocation is bounded only by the per-test timeout.

**3.7 Cost measurement.** Reasoning tokens ⊂ completion tokens — state the
double-count trap and that you avoid it. `cost_computed_usd` vs
`cost_actual_usd`, both stored, reconciled in batch (~10s settling), with
disagreement used as a **drift detector**.

**3.8 Cost controls.** The cap aborts before spending, on worst case, against
lifetime spend. A 2.5× safety factor because `max_tokens` does not bind.
Cheapest-first ordering. `request_hash UNIQUE` so nothing is bought twice. And
the best one: **$15 loaded against a $6 cap, so $9 was unspendable regardless of
any bug.** Final spend $5.25.

**3.9 What changed during the study.** ⚠️ **Do not omit this.**

| What happened | What changed |
|---|---|
| First cell: `HumanEval/0`, 10/10 pass, 58× cost spread (44× at pinned prices) | Sampling re-weighted to difficulty-spread; hard tier became load-bearing |
| Pilot: 7 of 16 hard thinking calls truncated at 16k | Ceiling raised 16k → 32k → 48k before the grid |
| Pilot: thinking scored *worse* on hard | Investigated rather than reported; cause was truncation |
| `subset_only` stored but not honoured | Fixed; grid cost fell $7.51 → $4.59 |
| `config_id` derived from price order | Made price-independent; 149 rows repaired via `request_hash` |
| Thinking calls dearer than projected | Grid left unbalanced; comparable statistics restricted to 107 paired problems |

Written as prose, this section is the difference between a method chapter that is
believed and one that is merely read.

---

## Chapter 4 — Measurement validity

### Why it is a chapter and not a subsection

Three reasons, worth stating in its first paragraph:

1. The findings are **about the measuring apparatus**, so they condition every
   number in Chapters 5–7.
2. They **transfer** — they apply to anyone benchmarking open-weight models
   through an aggregator.
3. They **changed the method**: each one produced a mitigation in Chapter 3.

### The structure

**4.1 The setup.** What an aggregator is; why one was used; what you assumed
when you started.

**4.2 Provider routing changes price and model.** 18 providers for one slug,
$0.87–$3.48 per M output. `/models` reports only the cheapest. An unpinned run
served by **nine providers**, billed **1.54×** the prediction. Quantization
spans fp4→bf16.

The consequence, stated sharply:

> An unpinned evaluation does not compare models. It compares an unknown mixture
> of compressed variants at unrecorded prices, and a failure cannot be attributed
> to the model rather than to the compression.

Cite the related work — *The Silent Hyperparameter* (May 2026), up to 16.6pp of
backend variance; the survey finding **31 of 32 public repositories use
OpenRouter unsafely**. It shows this is prevalent, not hypothetical.

**4.3 Advertised reasoning budgets are ignored.** `max_tokens: 2000` → **13,731**
reasoning tokens (6.9×); `effort: "low"` → 11,926. Both accepted without error,
both listed in `supported_parameters`. **Silent non-compliance**, not an
unsupported feature.

Two consequences: the effort axis is binary, and ex-ante budget control does not
work — which is what makes Chapter 7's runtime abort necessary rather than
redundant.

**4.4 `max_tokens` does not bind.** 35,837 against 16,000; 73,037 against 48,000.
Note the consequence for cost control: a cap computed from `max_tokens` is
computed from an advisory number, hence the 2.5× safety factor.

**4.5 One behaviour that enables a method.** Cancelling a stream mid-reasoning is
billed **$0.00**, verified on two providers; reasoning is observable live via
`delta.reasoning`. Measured: abort at ~2,002 reasoning tokens after 33.8s billed
$0.000000, against $0.010978 for the same cell completed.

**4.6 Mitigations.** The table mapping each finding to what changed in the
method.

**4.7 Recommendations.** Written as advice someone can follow tomorrow:

> Pin the provider **and** the quantization. Record both a computed and a billed
> cost, and treat their disagreement as a signal. Report your truncation rate
> alongside any result about long outputs. Do not assume a reasoning-budget
> parameter binds — verify it.

⚠️ **Scope it honestly** in the closing paragraph: the space is partly occupied,
so the contribution is the commercial-aggregator version with reasoning modes and
cost attached. A strong methodology chapter, not the thesis's headline.

---

## Do this

**1. Write §3.9 first.** It is the most distinctive section in the chapter and
you know the material from Part 2. Aim for 600 words as flowing prose, not a
table.

**2. Draft Chapter 4 from the source.**

```bash
cd ~/thesis
sed -n '1,40p' config/models.yaml
```

Every claim in §4.2 is documented there. Write §4.2 with that file open.

**3. Run the reproducibility check and write the sentence.**

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt && echo IDENTICAL
```

Then write: *"All analyses use fixed seeds; repeated runs of the analysis
pipeline produce byte-identical output."* You have just earned that sentence.

**4. Apply the stranger test.** Give §3.2–3.5 to someone who has not seen the
project and ask what they would still need in order to re-run it. Whatever they
name is missing.

---

## Check yourself

1. What is the standard a method chapter must meet?
2. What trade does provider pinning make, and how do you justify it?
3. Why must Chapter 3 concede that the effort axis is binary?
4. Why is "320 of 884" a budget statement rather than a sampling statement?
5. Why does §3.9 ("what changed") make the chapter more credible rather than
   less?
6. Give the three reasons measurement validity deserves its own chapter.
7. How does §4.3 justify Chapter 7's existence?

<details>
<summary>Answers</summary>

1. That a competent stranger with the same budget could reproduce the table from
   the chapter alone.
2. Availability for reproducibility: a pinned provider that goes down produces a
   failed, resumable call, whereas an unpinned one produces a silently different
   model at a different price.
3. Because graded effort controls were accepted and ignored — only
   `{enabled: false}` genuinely changes behaviour. Describing it as a budget dial
   would misstate what was manipulated.
4. Because every problem costs 10 API calls, so the limit is money, not a
   selection criterion. Saying so prevents the reader inferring a filtered
   sample.
5. Because experiments do go wrong, and showing that each problem was detected,
   diagnosed and acted on is evidence the checks work. A flawless account reads
   as insufficient checking.
6. The findings condition every later number; they transfer beyond this thesis;
   and each one produced a concrete change to the method.
7. It shows ex-ante control does not work — you cannot ask a model to think less
   — so a runtime abort is the only mechanism that functions, not a redundant
   one.

</details>

---

➡️ Next: [Lesson 36 — Writing Chapters 5, 6 and 7](36-writing-ch5-7.md)
