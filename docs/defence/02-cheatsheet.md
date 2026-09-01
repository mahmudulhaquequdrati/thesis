# The sheet you take into the room

Print this. One page of numbers and six rehearsed answers. Bringing a number
sheet is **professional, not weak** — nobody expects `$0.06320` from memory.

Every figure regenerates with `uv run python scripts/results.py` (free, offline,
read-only). Re-run it the morning of the viva so you are quoting today's file.

---

## 1. The numbers

**Scale**
`320 problems × 10 configs = 1,373 generations · 1,280 graded · $5.2402`
Pool **884** = HumanEval+ 164 · MBPP+ 378 · LCB 342 (84 easy / 104 med / 154 hard)
Configs = 5 open-weight models × {off, high}. 3 families. Kimi held out, subset only.

**Pass rate, reasoning off → on** *(n off / n on)*

| tier | off | on | n |
|---|---|---|---|
| LCB **hard** | **24.9%** | **54.2%** | 462 / 118 |
| LCB **medium** | **53.3%** | **76.4%** | 317 / 148 |
| MBPP+ | 72.3% | 73.3% | 83 / 30 |
| HumanEval+ | 92.9% | 97.0% | 85 / 33 |
| LCB easy | 94.1% | 100% | 68 / 11 |

🔴 **PER MODEL — lead with this, the aggregate hides a sign reversal**

| tier | model | off | high | delta | cens |
|---|---|---|---|---|---|
| hard | `flash` | 29.2% (154) | **82.1%** (28) | **+52.9** | 11% |
| hard | `qwen3.6-35b` | 22.1% (154) | 27.6% (29) | +5.5 | 17% |
| hard | `qwen3.5-9b` | 22.1% (145) | **3.8%** (26) | **−18.2** | **81%** |
| medium | `flash` | 62.5% (104) | 94.4% (36) | +31.9 | 0% |
| medium | `qwen3.6-35b` | 52.9% (104) | 72.2% (36) | +19.3 | 6% |
| medium | `qwen3.5-9b` | 43.6% (101) | 38.7% (31) | −4.9 | 52% |
| MBPP+ | `qwen3.5-9b` | 80.0% (20) | **55.6%** (18) | **−24.4** | **0%** |
| HumanEval+ | `qwen3.5-9b` | 90.5% (21) | 94.7% (19) | +4.3 | 0% |

Two mechanisms: **non-termination** (`qwen3.5-9b|high` 81% censored on hard,
24,826 mean reasoning tokens, no code on 77%) and **genuine degradation**
(MBPP+, **0% censored**, 368 tokens, terminates, still loses 24 pts on the *same
20 problems*, all failures assertion errors). Easy-benchmark aggregate rows are
model-confounded: `high` arm is 62% `qwen3.5-9b` on MBPP+, 58% on HumanEval+.

⚠️ **Style-matched (quote these)** — hard functional **31.6% (n=114) → 57.3% (n=110), +25.7** ·
medium functional **49.1% (n=163) → 78.0% (n=141), +28.9**. Raw arms sat different
exams: hard `off` is 348 stdin/114 functional, `high` is 8/110. Cause: run order
sorts on `problem_id`, numeric LeetCode ids before letter AtCoder ids, cap fired
inside the prefix. **Nothing claimed about stdin — that arm is n=8.**

**Saturation, per tier (solid)** — HumanEval+/MBPP+/LCB-easy **72–100%** either arm

**Saturation, per problem (⚠ coverage-dependent)** — 320 problems: 141 (44%)
discriminate · **≥1 thinking config: 71/108 = 66%** · **≥6 configs: 60/73 = 82%**.
206 of 320 saw only 2–3 configs. **94 of the 98 "none solved" were never shown a
thinking config.** Drop "76% carries no signal"; keep the per-tier result.

**Reasoning tokens by tier (mean)** — 642 · 773 · 2,693 · 10,183 · **17,547**

**Waste** — passed n=242 mean 7,567 · failed n=49 mean 7,577 · **billed-no-answer n=49
mean 29,584, $0.56 = 15% of reasoning spend ($3.62), 11% of total ($5.24)**
⚠️ **76% of it is one model**: `qwen3.5-9b` **37/99 = 37.4%**; `qwen3.6-35b` 9.5%;
`flash` 4.1%; `pro` 2.8%; `kimi` 0/22. Non-termination is a small-model property.

**Censoring** — hard **26.3%** (31/118), medium 12.2% (18/148) hit the 48k ceiling
→ *54.2% is a floor, not an estimate*

**CPC, 107 paired problems** — `flash|off` **$0.00021** [0.00015, 0.00028] →
`kimi|high` **$0.06320** [0.03940, 0.09324] = **305×**. **5 adjacent pairs overlap.**
⚠️ **Not like-for-like** — those rows sat different exams (n=107 vs n=22).
**228×** on the 22 problems they share · **65×** across 6 configs on the *same* 60.

**Frontier, 6 configs × 60 shared problems** *(51 functional / 2 stdin — all 19
hard ones are function-style, so these describe LeetCode-style completions)*

| config | $/problem | acc | 95% CI | |
|---|---|---|---|---|
| `flash\|off` | 0.00016 | 65.0% | [52, 77] | hull |
| `flash\|high` | 0.00177 | **98.3%** | [95, 100] | hull |
| `pro\|high` | 0.01088 | 95.0% | [88, 100] | **dominated — 6× cost; ties 64/68 on shared problems** |

**Oracle 98.3% @ $0.00111 · hull at same budget 84.5% · headroom +13.8 points**

**Router** — k-NN(5) LOO **65.0% = the hull exactly. +0.0 points. 1 config used.**
Decomposition: feature insufficiency **0.0** · estimation error **33.3**
*(ceiling is fitted: 12 buckets, 60 problems, 5 each → optimistic)*

**Abort curve** — 2k: 35% kept [27,44] / 98% saved · 10k: 77% [69,83] / 72% ·
**16k: 88% [82,92] kept for 49% [35,61] saved.** **No free threshold — pooled.**
🔴 **Per model there is one, for two of five:** `qwen3.5-9b` **T=10,000 keeps
46/46 and saves 88%**; `qwen3.6-35b` T=16,000 keeps 43/43, saves 13%; `flash`,
`pro`, `kimi` none. Free exactly where reasoning wasn't earning its keep.

**Platform**
`392 of 412` tokens on "reverse a string" · 18 providers, **$0.87–$3.48**/M ·
9 providers in one run, **1.54×** predicted · `max_tokens:2000` → **13,731**
reasoning tokens (6.9×) · ceiling 16,000 → observed **35,837**; 48,000 → **73,037** ·
abort mid-reasoning **$0.000000** vs **$0.010978** completed

**Denominators** — **107** paired · **60** × **6 configs** · only **5** have all ten
**Provenance** — 132 tests pass · grader validated on **3 canonical solutions in
the standing suite, 210 in a retired one-off sweep** (say both) ·
LCB references 43/43 and 34/34 · seed 20260726 · cap $6.00 of $15.00 loaded

---

## 2. The six answers to have word-perfect

**One sentence.**
> Reasoning models can think before answering; that thinking is billed but
> invisible; I measured when it is worth paying for.

**Why it matters.**
> You cannot price a call from its answer — 392 of 412 tokens on a trivial
> prompt — and cost per correct answer spans 305× across open-weight models.
> That is a $50 versus a $15,000 monthly bill for the same work.

**The headline.**
> The value of reasoning is a property of the model-and-difficulty pair, not of
> difficulty alone. On hard problems it takes deepseek-v4-flash from 29.2% to
> 82.1%, n = 154 and 28, and takes qwen3.5-9b from 22.1% down to 3.8% — but that
> second one is mostly non-termination: 81% of its thinking calls hit my token
> ceiling and returned no code. The cleanest result is on MBPP+, where the same
> small model, on the same twenty problems, with zero truncation and a mean of
> 368 reasoning tokens, falls from 80.0% to 55.6%. That is overthinking measured
> directly.

**The aggregate, if they ask for it.**
> On LiveCodeBench hard function-style problems, the pass rate goes from 31.6%
> without reasoning to 57.3% with it, n = 114 and 110 — a factor of 1.8. On
> MBPP+ the same manipulation moves it 1.0 points. The value of reasoning is
> conditional on difficulty, sharply. Two caveats I put up front: the raw
> tier-level pair, 24.9% to 54.2%, is confounded because the arms sat different
> exams, so I quote the style-matched figure; and 57.3% is a floor, because
> 26.3% of hard thinking calls still truncate at my ceiling.

**Your proposal was a router.**
> The pilot showed routing collapsing — 81% of problems shared one
> cheapest-passing configuration. I reframed to measurement in week two, because
> the measurement yields a result either way. I built the router anyway; it added
> +0.0 points against the convex hull, which confirms the reframing.

**A result you got wrong.**
> My pilot found a free abort threshold: stop at 10,000 reasoning tokens, keep
> every solved problem, save 44%. It was an artefact of my own 16,000-token
> ceiling — a truncated call cannot succeed, so the ceiling manufactured the
> cliff. At 48,000, 56 calls above 10,000 tokens succeeded. What survives is a
> tradeoff: 88% of solutions for a 49% saving. A truncation limit is a censoring
> mechanism.

**Why should I believe any of this.**
> Fixed seeds throughout, so the analysis is byte-identical on re-run. Every call
> priced from measured token counts against the pinned endpoint's contracted
> price — and I should say that only the 139 pilot calls were reconciled against
> the actual bill, not the 1,224-call grid. Grading validated against canonical
> solutions — three in the suite today, 210 in a one-off sweep since retired — a check that caught
> a macOS bug that was silently failing every solution. 132 tests. And raw
> responses stored verbatim, so anything can be re-graded without re-purchasing.

---

## 3. The three rules under pressure

1. **Lead with the number and its denominator.** "24.9% to 54.2%, n = 462 and
   118" beats "well, thinking generally helps".
2. **Concede fast and precisely.** A conceded point costs one sentence. A
   defended-then-conceded point costs your credibility for the next twenty
   minutes.
3. **"I did not measure that. What I can say is…"** is the correct answer to
   anything you do not know. A confident wrong answer is the only fatal one.

---

## 4. Volunteer these before you are asked

- The grid is **unbalanced**; comparable statistics use the **107**-problem
  paired set and the **60**-problem six-config set, printed on every row.
- **Contamination is uncontrolled** — LCB stopped updating 2025-06-05, every
  model is a 2026 release. Absolute pass rates are inflated; **comparisons on the
  same problems survive**, because contamination inflates all configs on a
  problem roughly equally.
- **Intervals overlap** in five adjacent CPC pairs and between `flash|high` and
  `pro|high`. Directions are established; orderings often are not.
- **The 305× is not like-for-like** — 228× on the 22 shared problems, 65× on the
  identical six-config exam. Say the denominator before you are asked for it.
- **🔴 The reasoning traces were never stored** — `raw_response` is
  `message.content` only; `message.reasoning` was available and not captured. So
  `reasoning_tokens` is a **vendor annotation** nothing checks, and the
  overthinking finding can be counted but not inspected. Best answer to "what
  would you do differently".
- **🔴 Two of the router's three "free features" are benchmark metadata** —
  difficulty is LCB's own label and `n_tests` is the hidden grading suite; only
  prompt length is available for a new problem. That falsifies the proposal's
  "features of the incoming prompt" positioning *independently* of the router
  failing, and it weakens "feature insufficiency 0.0". Say it first.
- **The aggregate off-vs-on rows average opposite per-model effects** — +52.9 and
  −18.2 on the same tier. Give the per-model table before you are asked for it.
- **The 81/98/141 split is coverage-dependent** — 82% discriminate at ≥6 configs,
  and 94 of the 98 "unsolvable" were never shown a reasoning config.
- **The effort arms sat different exams** on the hard tier — quote the
  style-matched +25.7, explain the `problem_id` sort order, and say the medium
  effect got *bigger* under matching. Then say the frontier set is 51/2
  functional, so the hull and oracle describe function-style problems.
- **RQ5 is thin** — 16–23 problems on the held-out model. Reported as thin, not
  as a result.
- **The effort axis is binary**, not graded, because the budget parameter is
  accepted and ignored.
- **🔴 AI assistance, if there is any declaration requirement** — say it plainly
  and first: an AI assistant was used for code and prose drafting; `CLAUDE.md`
  and the `Co-Authored-By` trailers on 37 commits are the visible record; the
  design, decisions and claims are yours; every number regenerates from
  `scripts/results.py` on a fixed seed under 132 tests. Draft wording in
  THESIS.md §16. **Undisclosed use is the only version of this that hurts you.**
- **Prior-art claims rest on summaries, not full reads**, for Route-To-Reason,
  Agent-as-a-Router and HRBench.
- **Only 139 of 1,373 rows are reconciled against the actual bill** — all of them
  the pilot. Grid dollars are tokens × the pinned endpoint's contracted price.
  On the 139, billed ran **1.354×** computed (pre-pinning). Free to fix:
  1,207 grid rows still have their `openrouter_gen_id`.
- **$5.24 and $5.25 are both correct** — $5.240216 is the database total across
  1,373 stored generations; $5.25 is account spend including exploratory calls
  never stored as rows. If a document quotes one, know which.

---

⬅️ [Everything, A to Z](00-everything-a-to-z.md) · [The question bank](01-question-bank.md)
