# Revising the proposal `.docx` — what to change and why

Every number here is reproducible: `uv run python scripts/results.py`.
Supersedes the older list in THESIS.md §14, which predates the reframing and
several results that contradict it.

Work top-down. Edits **1–3 are structural** and change what the document is
about; the rest follow from them. If time is short, 1, 2, 3 and 12 are the ones
that would otherwise be actively wrong at submission.

---

## 1. ⚠️ The title and framing — the biggest edit

**Now:** *Cost-Aware Reasoning Routing (CARR) — a training-free router that
picks the cheapest (model, thinking-mode) pair that still solves the problem.*

**Change to something like:** *When is reasoning worth paying for? A cost
measurement of thinking modes in open-weight code generation.*

**Why.** The router does not work, and the data says so cleanly: a k-NN router
over free features reaches **65.0%**, which is *exactly* the convex hull — it
adds **+0.0 points** and collapses to one configuration. A thesis titled after
its method, where the method fails, spends its whole length apologising.

The measurement is what survives, and it is the stronger contribution anyway.
The router becomes one section reporting a negative-but-diagnostic result
(edit 9).

---

## 2. Research questions — rewrite the list

**Now:** RQ1–RQ5 built around building and evaluating a router.

**Change to:**

| | question | where answered |
|---|---|---|
| RQ1 | What predicts how long a model reasons? | difficulty, monotonically: 642 → 17,547 tokens |
| RQ2 | When is that reasoning wasted, and what does it cost? | 49 calls, 29,584 mean tokens, $0.56, no answer |
| RQ3 | Can waste be cut at runtime? | abort curve; no free threshold exists |
| RQ4 | Is there headroom for a router, and can one exploit it? | 13.8 points exist; a router captures 0 |

Keep RQ5 (held-out model) only if you report it as thin: kimi has 16–23
problems, which is not enough to conclude anything.

---

## 3. §3 Gap analysis — the most-owed rewrite

**Now:** positions the work as the first joint (model × effort) router, citing
RouteLLM, Universal Routing, Budget Guidance, AnytimeReasoner.

**Problem:** that analysis is ~12 months stale. Four closer works exist:

| work | what it already does |
|---|---|
| **Agent-as-a-Router / CodeRouterBench** (Jun 2026) | code routing, 8 backends, released 9,999-task × 8-model matrix with cost |
| **Route-To-Reason** (May 2025) | joint model *and* reasoning-strategy allocation under budget |
| **DART** (Jun 2026) | training-free adaptive thinking budgets, text-only API |
| **HRBench** (May 2026) | 6 models × 5 benchmarks incl. code, 12 switching settings |

**What to claim instead.** Do not claim a novel router. Claim the measurement
and the validity findings, and state the one concrete gap: **CodeRouterBench's
`model` column holds eight model names and nothing else — no effort axis, and
no reasoning-token column at all.** The quantity this thesis is about is the
quantity the nearest prior work does not record.

Also cite **When Routing Collapses** (Feb 2026) — it names the degenerate
outcome that this thesis then reproduces and diagnoses.

---

## 4. Add a new section: measurement validity

There is no equivalent section in the proposal, and this is arguably the most
transferable material in the thesis. Three platform behaviours that invalidate
naive measurement, all verified directly:

1. **Provider routing changes price *and* model.** One slug is served by 18
   providers at **$0.87–$3.48 per M output**. `GET /models` reports only the
   cheapest. Unpinned, one run was served by **nine different providers** and
   billed **1.54× the prediction**. Quantization varies fp4→bf16, so an unpinned
   evaluation compares *different models*.
2. **Advertised reasoning budgets are ignored.** `reasoning:{max_tokens:2000}`
   produced **13,731** reasoning tokens; `effort:"low"` produced 11,926. Both
   accepted without error, both listed in `supported_parameters`.
3. **`max_tokens` does not bind.** Observed 35,837 against a 16,000 ceiling and
   73,037 against 48,000.

Plus one that *enables* a method: **cancelling a stream mid-reasoning is billed
$0.00**, verified on two providers, with reasoning observable live via
`delta.reasoning`.

**The claim to make:** any evaluation of open-weight models through an
aggregator without provider pinning is confounded on both price and precision.

---

## 5. §6.1 Roster — five models, and say how they are pinned

- Remove GLM-5.1. State **five open-weight models across three families**, and
  acknowledge the within-family caveat (two DeepSeek, two Qwen).
- **Add the pinning method**: every model pins one provider *and* one
  quantization (fp8 or better) via `provider: {only: [tag]}`, with
  `allow_fallbacks: false`. Explain that this trades availability for
  reproducibility — a pinned provider that is down produces a failed call rather
  than a silently different, differently-priced result.
- Note prices are per-endpoint, not the `/models` headline.

## 6. §6.2 Problems — separate the pool from the run set

The current text conflates them. State:

- **Pool: 884** — HumanEval+ 164, MBPP+ 378, LiveCodeBench 342.
- **Run: 320 problems, 1,373 generations, $5.24.**
- Coverage is **uneven by design and by budget**: the no-reasoning arm covers
  320 problems for three of five models (`pro|off` 51, `kimi|off` 16), the
  thinking arm 73–104, the held-out model 16–23. Comparable
  statistics therefore use the **107-problem paired set**, and per-config `n` is
  reported on every row.
- Drop the old "MBPP 500 → 150, LCB 200 → 120" numbers entirely.

## 7. §6.2 / Methods — the second grading harness

LiveCodeBench needs execution the evalplus checker cannot do: **217 of its 342
problems are stdin→stdout programs and 125 are methods on a `Solution` class.**
*(Do not quote the older 112 / 63 split — that is LCB v6 alone, and the pool
actually loaded is v5+v6.)*
And **LCB ships no canonical solutions**, so the harness is validated against
**hand-written reference implementations** rather than the benchmark's own.
Say both — a reader will otherwise assume one grader covers everything.

## 8. §6.3 Metrics — CPC and TPC with intervals

- Define CPC = Σcost ÷ Σsolved, TPC likewise in tokens.
- **Report bootstrapped 95% intervals.** CPC is a ratio estimator, therefore
  biased, and normally reported bare.
- Report the denominator with every figure — and note that the paired set
  equalises the *effort arms* per row, **not** the problem set across rows, so
  the cheapest-vs-dearest ratio is not like-for-like (see edit 11).
- State that resampling is over **problems, not calls** — two calls on one
  problem are not independent.
- Say what the intervals revealed: **five adjacent config pairs overlap**, so
  their ordering is not established despite distinct point estimates.

## 9. §5.3 / results — the router section, rewritten as a negative result

- **CARR-oracle is the MCKP integer optimum**, not an ad-hoc ceiling.
- **The comparison baseline is the convex hull, not the best single config.**
  Include the proposition: an optimal non-adaptive budget-constrained strategy
  randomises between at most two configurations, so beating the best single
  config is nearly free.
- Report the result honestly: **oracle 98.3% at $0.00111/problem; hull at the
  same budget 84.5%; headroom 13.8 points; k-NN router captures 0.0 of it and
  collapses to one config.**
- Then the decomposition, which is the point: **feature insufficiency 0.0
  points, estimation error 33.3 points.** The free features are sufficient to
  reach the oracle; the estimator fails because the cheapest-solving label is
  dominated by one configuration. Name the fix — a cost-aware objective rather
  than modal-label classification.
- Caveat the ceiling: fitted over 12 buckets on 60 problems, so optimistic.

## 10. §8 Risks — three of them are no longer risks but results

- **Benchmark saturation: confirmed.** Only **141 of 320** problems
  discriminate; 81 are solved by everything and 98 by nothing. HumanEval+ and
  MBPP+ pass at 72–97% regardless of reasoning.
- **Routing collapse: confirmed.** Cite *When Routing Collapses*, then report
  reproducing it.
- **Budget: held.** $5.24 of a $15 balance, under a $6.00 self-imposed cap
  enforced in code on worst-case spend before each call.

## 11. Results to add — there were none before

- **Thinking more than doubles the pass rate on hard problems: 24.9% → 54.2%**
  (n=462/118); on medium 53.3% → 76.4%. On easy benchmarks it buys almost
  nothing. *The value of reasoning is conditional on difficulty.*
- **Cost per correct answer spans 305×**, $0.00021 to $0.06320 — but report the
  denominator with it: those two rows rest on n=107 and n=22 *different*
  problems. On the 22 they share the ratio is **228×**, and across the six
  configurations that sat the identical 60-problem exam the spread is **65×**.
  Quote whichever you can name the denominator for; all three are large.
- **The cheap model with thinking dominates the frontier model with thinking**:
  `flash|high` at 98.3% costs one sixth of `pro|high` at 95.0% on the frontier
  set — and on the **68 problems the two actually share they tie exactly, 64/68
  each**. Report the tie, not the 3-point gap: it is the stronger claim and it
  does not depend on overlapping intervals.
- **~15% of spend on reasoning-enabled calls bought nothing** ($0.56 of $3.62;
  11% of the $5.24 total). Report the denominator — $0.56/$5.24 is 11%, and an
  examiner will divide.

## 9b. 🔴 NEW — withdraw the "features of the incoming prompt" claim

**Found 2026-09-01, and it is independent of the router's failure.** The three
features are `difficulty tier`, `n_tests` and `prompt_chars`. Only the last is
computable from an arriving prompt:

- **`difficulty`** is LiveCodeBench's *own* hardness label — benchmark metadata.
  For HumanEval+/MBPP+ it degrades to the benchmark name.
- **`n_tests`** is base + plus: **the size of the hidden grading suite**, not
  knowable until the problem has been graded.

So the proposal's §5.2 positioning — routing on "cheap, non-LLM structural and
lexical features" of the incoming prompt — describes something that was not
built. Withdraw it, and say instead:

> The router is evaluated on three problem-level features, two of which are
> benchmark metadata rather than properties of an arriving prompt. A deployable
> version has prompt length plus whatever the prompt text yields — keyword
> presence, structure, signature count — and that was not measured here.

Also qualify the decomposition wherever it appears: **"feature insufficiency
0.0"** means *these* features suffice, and two thirds of them are labels a
deployment would not have. The oracle, hull and 13.8-point headroom are
unaffected — none of them uses these features.

## 10b. 🔴 NEW — do not claim the costs are billed figures

**Found 2026-09-01.** `cost_actual_usd` is populated on **139 of 1,373 rows, all
of them the 2026-07-25 pilot**. The 1,224-call grid was never reconciled, so
every dollar in the results chapter is `cost_computed_usd` — token counts times
the price table.

**Write it as:** *costs are measured token counts priced at the pinned
endpoint's contracted rate; the pilot's 139 calls were additionally reconciled
against `GET /generation`, where billed cost ran 1.354× computed under
pre-pinning routing.*

Do **not** write "every call priced from the actual bill". It is checkable in
one query and it is false.

**Best fix, and it is free:** run `runner.reconcile_costs()` over the 1,207 grid
rows that still carry an `openrouter_gen_id`. If OpenRouter has expired records
that old, report *that* — an unverifiable cost basis stated plainly is worth
more than an unexamined one.

## 11a. 🔴 NEW — the headline is per MODEL, not per tier. Lead with this.

**Found 2026-09-01. It reverses a sign, and it is free — a re-analysis of rows
already bought.** This is the single largest change owed to the results chapter.

The aggregate "thinking helps on hard problems, +29.3" averages over models that
respond in opposite directions:

| tier | model | off | high | delta | censored |
|---|---|---|---|---|---|
| hard | `deepseek-v4-flash` | 29.2% (154) | **82.1%** (28) | **+52.9** | 11% |
| hard | `qwen3.6-35b-a3b` | 22.1% (154) | 27.6% (29) | +5.5 | 17% |
| hard | `qwen3.5-9b` | 22.1% (145) | **3.8%** (26) | **-18.2** | **81%** |
| medium | `deepseek-v4-flash` | 62.5% (104) | 94.4% (36) | +31.9 | 0% |
| medium | `qwen3.6-35b-a3b` | 52.9% (104) | 72.2% (36) | +19.3 | 6% |
| medium | `qwen3.5-9b` | 43.6% (101) | 38.7% (31) | -4.9 | 52% |
| MBPP+ | `qwen3.5-9b` | 80.0% (20) | **55.6%** (18) | **-24.4** | **0%** |
| HumanEval+ | `qwen3.5-9b` | 90.5% (21) | 94.7% (19) | +4.3 | 0% |

**What to write:**

- Replace the tier-level headline with **"the value of reasoning is a property
  of the (model, difficulty) pair"**, and give this table.
- Separate the two failure modes, because they need different sentences:
  - **Non-termination** - `qwen3.5-9b|high` censors **81%** of hard calls and
    returns no code on 77%, mean 24,826 reasoning tokens. Its negative delta is
    mostly the model failing to stop, and partly our ceiling: `flash|high`
    censors 11% on the same problems.
  - **Genuine degradation** - on MBPP+ the same model censors **0%**, reasons
    368 tokens, terminates, and still loses 24 points on the **same 20
    problems**, every failure producing extracted code that failed on
    assertions. Overthinking observed directly with truncation ruled out, and a
    cleaner result than anything currently in the chapter.
- Note the easy-benchmark rows are also **model-confounded**: the `high` arm is
  62% `qwen3.5-9b` on MBPP+ and 58% on HumanEval+, against ~25% each in `off`.
  So "MBPP+ 72.3% -> 73.3%" compares a four-model average with a
  mostly-one-model average. Drop it for the per-model rows.

Reproduce: `scripts/results.py`, section **THE EFFECT IS PER MODEL**.

## 11b. NEW - report the style confound, and use the matched figures

**Found 2026-09-01, after the course was written. It changes a headline number,
and it is free to fix — a re-analysis of rows already bought.**

LiveCodeBench ships two execution styles, and the effort arms did not sit the
same exam. On the hard tier the `off` arm is **348 stdin / 114 functional**; the
`high` arm is **8 / 110**.

**The cause is mechanical.** `runner.plan` sorts cells by
`(expected_usd, problem_id)`. Ties inside one configuration break on the problem
id *as a string*, LeetCode ids are numeric and AtCoder ids start with letters,
so all 125 functional problems ran before any of the 217 stdin ones — and the
expensive thinking arm hit the cost cap inside that prefix.

**What to write instead:**

| tier | style | off | on | matched | raw |
|---|---|---|---|---|---|
| hard | functional | 31.6% (n=114) | **57.3%** (n=110) | **+25.7** | +29.3 |
| medium | functional | 49.1% (n=163) | **78.0%** (n=141) | **+28.9** | +23.0 |

- Replace *"more than doubles"* on the hard tier with **"raises the pass rate by
  a factor of 1.8, from 31.6% to 57.3% on function-style problems"**.
- Say explicitly that **nothing is claimed about stdin-style problems**: the
  thinking arm there is n=8.
- Note that the medium-tier effect is **larger** under matching, not smaller —
  the raw pair was not uniformly flattering.
- Label the frontier: those 60 problems are **51 functional / 2 stdin**, and all
  19 of their hard problems are function-style. So the hull, the oracle, the
  13.8-point headroom and the router result describe function-style problems.
- Add it to Limitations, and to the measurement-validity chapter as a second
  worked example of *the run order is part of the method*.

Reproduce: `scripts/results.py`, section **⚠ STYLE CONFOUND**.

## 12. ⚠️ LiveCodeBench contamination — every mention must change

**The property does not hold.** LCB's newest problem is **2025-04-06**, the
dataset stopped updating **2025-06-05**, and every roster model is a **2026**
release. There is no post-cutoff window.

Rewrite every citation of LCB-as-contamination-control to LCB-as-difficulty-tier,
and state the exposure as a limitation, backed by the stored `release_date`
distribution. This is the edit most likely to be caught by an examiner if left.

## 12b. 🔴 NEW — add a generative-AI declaration to the front matter

**The most dangerous omission in the submission, and the cheapest to fix.**

The repository has **no AI-use declaration anywhere**, while **37 commits carry
`Co-Authored-By: Claude`** and `CLAUDE.md` is a standing instruction file for an
AI assistant. An examiner who opens `git log` finds this in ten seconds, and an
undisclosed-use finding is an academic-integrity matter rather than a
methodological one.

Disclosed use is normally fine. Undisclosed use is not. **Draft wording is in
THESIS.md §16** — check it against the department's actual regulations, which
may require a specific form of words or an appendix of prompts.

Two things the declaration should carry, because they are true and they are what
an examiner is really asking about:

- **What was verified independently.** Every reported number regenerates from
  `data/carr.sqlite` via `scripts/results.py` under a fixed seed; the analysis
  is covered by 132 tests; raw responses are stored so anything can be re-graded
  without re-purchasing.
- **What is not verified.** The prior-art claims in §15 rest on search summaries
  and PDF extraction rather than full reads, and are marked as such.

## 13. Limitations — write this section properly

- Coverage uneven; comparable statistics rest on 60–107 problems.
- Several intervals overlap; directions are clearer than orderings.
- **Censoring: 26.3% of hard thinking calls still truncate at 48,000 tokens**,
  so the long-reasoning tail is a floor, not an estimate.
- Contamination uncontrolled (edit 12).
- **The effort axis is binary in practice**, not graded — `off` genuinely yields
  zero reasoning tokens, but graded effort levels do not bind (edit 4.2).
- One sample per problem at temperature 0; no within-cell variance measured.
- RQ2 overlaps existing overthinking work (ThoughtTerminator, SelfBudgeter,
  RecurGuard).

## 13b. 🔴 NEW — the abort chapter must report per-model thresholds

**Found 2026-09-01.** The chapter's conclusion, *"no threshold saves money
without losing a solved problem"*, is a **pooled** statement. Per model:

| model | free threshold | saving | solutions kept |
|---|---|---|---|
| **`qwen3.5-9b`** | **10,000** | **88%** | **46/46** |
| **`qwen3.6-35b-a3b`** | **16,000** | **13%** | **43/43** |
| `deepseek-v4-flash` | none | | |
| `deepseek-v4-pro` | none | | |
| `kimi-k2.6` | none | | |

Write the conclusion as: **whether a reasoning-length abort is free is a
property of the model.** Where long reasoning rarely succeeds it is free money;
where it genuinely solves hard problems, every threshold costs solutions. Tie it
to edit 11a — the free threshold appears exactly for the models whose reasoning
delta is negative.

Keep the refutation in edit 14 unchanged: the *roster-level* free threshold is
still false, and the 16k ceiling still manufactured part of the pilot's version.

## 14. Include the self-refutation — do not quietly drop it

The pilot appeared to show a **free** abort threshold: stop at 10,000 reasoning
tokens, keep every solved problem, save 44%. **The full grid refuted it.** The
pilot ran under a 16,000-token ceiling; truncated calls cannot succeed, so the
ceiling manufactured the cliff. At 48,000, **56 calls above 10,000 reasoning
tokens succeeded**.

Report it. It demonstrates the general hazard — *a truncation limit is a
censoring mechanism, and censored observations bias any analysis of the
quantity being truncated* — and correcting your own headline is a strength.

What survives is an honest tradeoff: **abort at 16,000 keeps 88% of solutions
[82, 92] for 49% of the cost [35, 61]**.

---

## Figures to insert

Generated by `uv run python scripts/make_figures.py` into `data/figures/`:

| file | goes in |
|---|---|
| `01-effort-by-tier.png` | Results — the aggregate conditional finding. **Do not use it alone**; pair it with 05 |
| `05-effect-by-model.png` | Results — **the real headline**: the per-model effect, with the sign reversal and the truncation share on each bar |
| `02-reasoning-vs-outcome.png` | Results — long reasoning means failure |
| `03-frontier-and-hull.png` | The frontier section — hull, oracle, 13.8-point gap |
| `04-abort-tradeoff.png` | Runtime abort — the curve, with its CI band |
