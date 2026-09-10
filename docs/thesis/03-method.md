# Method

The standard this chapter is written to: a competent stranger, with the same budget and this chapter, could rebuild the table and get the same numbers. Every choice that would change a number is stated. The full configuration files are reproduced in Appendix B and the reproduction commands in Appendix C.

## The unit of measurement

One (problem, configuration) pair is one paid API call is one row. The whole system is the life of that row:

```
   problems table                configs table
   ┌──────────────┐             ┌───────────────────────┐
   │ prompt       │             │ model + effort params │
   │ tests        │             │ pinned provider       │
   │ difficulty   │             │ prices per M tokens   │
   └──────┬───────┘             └───────────┬───────────┘
          │                                 │
          └──────────────┬──────────────────┘
                         ▼
   (1) request_hash -- has this exact call been bought already?   yes -> skip, $0
                         ▼
   (2) cost cap -- could the WORST CASE breach the lifetime limit?  yes -> stop the run
                         ▼
   (3) OpenRouter call: provider pinned, temperature 0, one sample, prompt verbatim
                         ▼
   (4) store raw_response verbatim + prompt/completion/reasoning tokens + computed cost
                         ▼
   (5) extract.py: pull the Python program out of the prose
                         ▼
   (6) verify.py: run it against every hidden test in a guarded subprocess
                         ▼
   (7) results row: passed / base_passed / tests passed / error type
                         ▼
   (8) later, in one batch: GET /generation -> billed cost (cost_actual_usd)
```

Steps (1) and (2) are the money discipline. Storing (4) before (5) is what makes extraction bugs free to fix. Step (8) is separate because the billing record needs about ten seconds to settle, and blocking on it per call would have added hours.

## The roster

Five open-weight models in three families, each run at two effort levels, giving ten configurations. Prices are US dollars per million tokens at the pinned endpoint on the snapshot date, 2026-07-26, copied from `config/models.yaml`.

| Model | Family | Pinned provider / precision | In $/M | Out $/M | Role |
|---|---|---|---|---|---|
| `qwen/qwen3.5-9b` | Qwen | `deepinfra/bf16` | 0.100 | 0.150 | cheapest; the no-reasoning floor |
| `deepseek/deepseek-v4-flash` | DeepSeek | `baidu/fp8` | 0.091 | 0.182 | cost-efficient reasoner |
| `qwen/qwen3.6-35b-a3b` | Qwen | `akashml/fp8` | 0.140 | 1.000 | mid tier |
| `deepseek/deepseek-v4-pro` | DeepSeek | `baidu/fp8` | 0.625 | 1.251 | frontier open-weight reasoner |
| `moonshotai/kimi-k2.6` | Moonshot | `siliconflow/fp8` | 0.770 | 3.400 | held out (RQ5), subset only |

Three points about the roster that an examiner should hear first. It spans **three** families, not five: two DeepSeek, two Qwen, one Moonshot, after GLM was dropped by decision on day one. **No closed-weight reference model was run**, although the proposal mentioned one. And `kimi-k2.7-code`, the strongest coding specialist available, was rejected because one thinking configuration over the full grid would have exceeded the whole budget at $3.50 per million output tokens.

The roster is verified against the aggregator's live model listing by `scripts/verify_roster.py`, which exits non-zero on drift. No model name is hard-coded anywhere in the codebase; the YAML file is the only place that knows.

## Provider and quantization pinning

Every call carries `{"provider": {"only": [tag], "allow_fallbacks": false}}`, where the tag names one provider **and** one precision (`baidu/fp8`, `deepinfra/bf16`). The roster policy is **fp8 or better for every model**, so precision is held constant. Prices are the pinned endpoint's, not the aggregator's headline (the cheapest provider's), and are therefore higher than the advertised price for the same model.

The trade is availability for reproducibility. A pinned provider that is down produces a failed, recorded, resumable call. An unpinned call produces a silently different model at a different price. Chapter 4 gives the measurement that forced this decision: before pinning, a single run was served by nine providers and billed 1.54× the prediction.

One exception is recorded honestly. DeepSeek's own endpoint for `deepseek-v4-pro` is both the cheapest and unquantized, but the account's data policy blocks it; the pinned `baidu/fp8` endpoint costs $1.251 rather than $0.870 per million output tokens.

## The effort axis

Each model is paired with **itself** at two settings: `reasoning: {enabled: false}` ("off") and `reasoning: {effort: "high"}` ("high"). Within a pair the only thing that changes is the thinking switch, so a difference in pass rate or cost is attributable to reasoning rather than to a different model's capability.

The axis is **binary in practice, not graded**. `{enabled: false}` yields zero reasoning tokens on 1,023 of the 1,025 `off` calls (two `qwen3.6-35b-a3b` calls reported non-zero counts, and they are billed and kept). Graded settings between off and high (`effort: "low"`, `reasoning: {max_tokens: N}`) were accepted by the API and ignored by the model (Chapter 4.3). The thesis therefore describes reasoning as on or off, never as a budget dial. The `effort_mechanism` column records that every configuration here uses the native toggle; the proposal's fallback of prompt-level budget forcing was never needed and would not have been comparable.

## Problems: pool, run set, strata, seed

The **pool** is everything the three benchmarks contain as loaded: 884 problems. The **run set** is what the budget allowed: 320 problems, because each problem costs ten API calls. Those are different numbers and are never conflated.

| Stratum | Pool | Run set | Why this weight |
|---|---|---|---|
| HumanEval+ | 164 | 21 | anchor: measures saturation, not routing |
| MBPP+ | 378 | 20 | anchor |
| LCB easy | 84 | 21 | anchor |
| LCB medium | 104 | 104 | all of them: discriminates |
| LCB hard | 154 | 154 | all of them: discriminates |

The weighting was set **after the pilot** (§3.13), which measured the three easy tiers at 90–100% pass regardless of reasoning. Spending grid budget there would have bought rows that inform nothing. The easy tiers are kept as twenty-problem anchors because the saturation rate is itself a reported finding and needs a measured denominator.

Sampling is stratified and seeded: within each stratum, problems are sorted by id and drawn with a random generator seeded on `(20260726, stratum)`, so the selection depends only on the seed, the stratum and the pool, not on insertion order or on how many other strata were requested. The held-out model runs on a 100-problem subset drawn the same way.

LiveCodeBench problems come in two execution styles: **217 stdin→stdout programs** (AtCoder) and **125 methods on a `Solution` class** (LeetCode). Within the hard tier the pool is 117 stdin to 37 functional. This matters in §3.13 and Chapter 5.4.

## Protocol

- **One sample per cell, temperature 0.** This halves the cost relative to two samples and makes the label "cheapest configuration that passes this problem" deterministic rather than a lottery. The price is that no within-configuration variance is measured, and (Chapter 8) that determinism is assumed, not verified: `temperature_sent` records what was sent, not what the endpoint applied.
- **The prompt is sent verbatim** as a single user message. No system prompt, no "you are an expert programmer", no "think step by step", no examples. Any of those would change token counts and confound the effort axis. The one documented deviation: stdin-style LiveCodeBench problems receive one added sentence saying the program reads standard input, because the statement alone does not say how input arrives. It is a constant string, identical across every configuration, so it cannot confound the effort comparison.
- **`max_tokens`** is set per effort: 16,000 for `off`, 48,000 for `high`. It is a cost control, not a quality setting. A truncated answer is a legitimate failure that cost a known, bounded amount. §3.13 gives the history of this ceiling.
- **Retries: zero**, except for rate-limit responses (billed $0), because a retry loop is how a cost cap gets defeated. A failed call is recorded and skipped; re-running the script picks it up.
- **Concurrency:** 24 parallel API calls, dispatched only when the whole in-flight set's worst case fits under the cap; 6 parallel graders.

## Extraction

`carr/extract.py` pulls the program out of the reply: a fence tagged `python` or `py` first, then any fence, then the whole reply if it parses as Python. Among several fenced blocks it takes the **longest that parses**, because models often print a short usage example after the real solution. An unterminated fence (a reply cut off by the token ceiling) is accepted, so a truncated answer is graded as the broken code it is rather than silently becoming "no code". The function returns `None` rather than raising: an unparseable reply is a data point, not a reason to crash a run that has already spent money. Ten tests cover it, including hostile input.

## Grading

Grading lives in exactly one file, `carr/execute/verify.py`, and nothing else in the repository may grade code. That rule exists because pass/fail is not string equality and a second grader is a second chance to be silently wrong.

**EvalPlus path (HumanEval+, MBPP+).** The extracted code is passed to EvalPlus's own `check_correctness`, which runs it in a subprocess under a timeout and its `reliability_guard` (which disables `os.system`, `os.fork`, `subprocess` and roughly forty other calls), compares floating-point answers with the per-problem tolerance, and applies MBPP's special oracles. A problem passes only if it survives both the base tests and the extended "plus" tests. The threat model is stated as EvalPlus states it: this is *not* a security sandbox; it contains accidents and casual hostility, which is the realistic threat from benchmark solutions.

**LiveCodeBench path.** Nothing is shared with the EvalPlus path: LCB ships no canonical solutions, no tolerances, no special oracles, and two execution styles. A separate subprocess entry point (`_lcb_runner.py`) applies the same `reliability_guard`, then for stdin-style problems re-executes the whole program once per test with a fresh global scope and the test's input on standard input, and for functional problems instantiates `Solution` and calls the entry point once per test with JSON-decoded arguments. Outputs are compared after whitespace normalisation (stdin) or as parsed JSON values (functional). One subprocess runs the whole test set for a problem, because 342 problems × ~40 tests × 10 configurations would otherwise be over a hundred thousand interpreter start-ups; the cost is that one non-terminating test times out the whole problem, which is the behaviour EvalPlus already has. Timeouts scale with the test count: 15 seconds plus 0.4 seconds per test, capped at 90.

**Validation.** A test grades the benchmarks' own canonical solutions and demands they pass. In the standing suite that test is parametrised over three HumanEval tasks; a one-off sweep of 210 canonical solutions across both benchmarks was run once, all passing, and its fixture retired. Because LiveCodeBench ships no canonical solutions, hand-written reference implementations for both styles serve the same purpose (43/43 and 34/34 tests). The rule these encode: **a reference solution that fails means the harness is broken, not the model.** §3.13 describes the bug this caught.

## Cost measurement

Two cost columns are stored for every call.

**Computed cost** from token counts and the pinned price table:

$$
c_{\text{computed}} = \frac{n_{\text{prompt}} \cdot p_{\text{in}} + n_{\text{completion}} \cdot p_{\text{out}}}{10^{6}},
$$

where $n_{\text{completion}}$ already includes reasoning tokens. Reasoning tokens are never added again. A test pins this.

**Billed cost** from the aggregator's `GET /generation` record, fetched in one batch after a run because the record needs about ten seconds to settle. Wherever both exist the billed figure wins, and the difference between them is a **drift detector**: a consistent gap means the price table is stale or the pin has broken, and the runner prints a warning if the ratio exceeds 5%.

**How far the billed figure actually reaches must be stated plainly.** It is populated on 139 of 1,373 rows, all from the 2026-07-25 pilot. The 1,224-call grid was never reconciled, so every dollar in Chapters 5–7 is a computed figure: measured token counts priced at the pinned endpoint's contracted rate. That is defensible, because with `allow_fallbacks: false` the endpoint's price is contractual rather than a routing lottery. It is not the same as having checked. On the 139 rows where checking was possible, billed ran 1.354× computed overall ($0.5124 against $0.3784), and 2.16–2.51× on `deepseek-v4-pro`. The best reading is that this is evidence *for* the pinning finding, since the pilot ran before pinning; it is presented as an argument, not a fact. The reconciliation is free to run over the 1,217 grid rows that still carry a generation id, and is listed as the first action owed (Chapter 9).

## Cost controls

Four controls, all built and tested (19 tests on the paid loop alone).

**1. A cap that aborts, not warns.** Before dispatching a call the runner checks

$$
S_{\text{lifetime}} + R_{\text{in-flight}} + 2.5 \cdot \frac{n_{\text{prompt}} \, p_{\text{in}} + \texttt{max\_tokens} \cdot p_{\text{out}}}{10^{6}} \;\le\; \texttt{abort\_at\_usd},
$$

where $S_{\text{lifetime}}$ is everything ever bought into the database (re-read from the database, not tracked in memory), $R_{\text{in-flight}}$ is the worst case already reserved by calls not yet returned, and the factor 2.5 exists because `max_tokens` is not a hard bound: one call returned 35,837 tokens against a 16,000 ceiling. If the inequality fails, the run stops, having spent nothing extra. The cap is checked against *lifetime* spend because five runs that each respect their own limit still empty the account. A second, per-run ceiling stops any single run at 1.25× its own estimate even when the lifetime cap has room.

**2. `max_tokens` per effort**, 16,000 / 48,000, which is also what the worst case is computed from.

**3. Cheapest first, globally.** Cells are ordered by expected cost across the whole plan, so if the cap fires it fires on the expensive tail and leaves a complete cheap foundation rather than a random half of every problem. §3.13 records the consequence.

**4. Never pay twice.** `request_hash` is a SHA-256 over (model, effort label, prompt, effort parameters, problem id), stored with a `UNIQUE` constraint and checked before every call. A crash at row 3,000 costs $0 to resume from. This was proven by a 360-row re-run that inserted zero rows.

The lifetime cap was set at **$6.00 against a $15.00 balance**, so $9 was unspendable whatever a bug did. A larger balance is not a larger budget. Final spend: $5.24 in the database, $5.25 on the account (the difference is exploratory calls made outside the runner and never stored as rows).

## The database

Four tables in one SQLite file, `data/carr.sqlite` (schema in Appendix A):

| Table | One row is | Cost to rebuild |
|---|---|---|
| `problems` | one problem: prompt, tests, benchmark, difficulty, release date, test count, prompt length | free |
| `configs` | one (model, effort) pair with prices, pinned provider, snapshot date | free |
| `generations` | **one API call**: raw response, extracted code, tokens, reasoning tokens, computed and billed cost, finish reason, latency, error | **real money** |
| `results` | that call's grade: passed, base passed, tests passed, error type | free (re-runnable) |

Five schema decisions matter. `request_hash UNIQUE` enforces never paying twice at the database rather than by discipline. `raw_response` is stored verbatim, so any extraction bug is fixed by re-grading, not re-buying. `cost_actual_usd` sits beside `cost_computed_usd` so drift is visible. `is_mock` marks any row not bought from a real API, and every analysis query filters on it (no such rows exist today; the column stays because the failure it prevents is invisible once it happens). `effort_mechanism` is a column, not a comment, because native toggles and prompt-level budget forcing are not equivalent.

## Analysis and statistics

Every number in Chapters 5–7 is produced by `carr/analysis.py` and printed by `scripts/results.py`, which reads the database and touches no API. Three rules govern the statistics.

**Denominators travel with rates.** Every percentage is printed with its $n$, and every comparison names the problem set both sides sat.

**Comparable statistics use a shared problem set.** The grid is unbalanced (§3.13), so a per-configuration number over that configuration's *own* problems compares models on different exams. Two shared sets are used: the **107 paired problems** where both effort arms have a graded, billed result (for effort comparisons and cost per correct answer), and the **60 problems shared by six configurations** (for the frontier, hull, oracle and router). All ten configurations share only five problems, which is useless.

**Uncertainty is a bootstrap over problems.** For a statistic $\theta$ computed on $n$ problems, draw $n$ problems with replacement, recompute $\theta$, repeat $B$ times (10,000 by default, 2,000 for figures), and report the 2.5th and 97.5th percentiles as the 95% interval [@efron1979]. Two details matter. Problems are resampled, never calls, because ten calls on one problem are one problem observed ten ways. And a ratio is recomputed *as a ratio* on each resample:

$$
\text{CPC}(S) = \frac{\sum_{i \in S} c_i}{\sum_{i \in S} s_i}, \qquad
\text{TPC}(S) = \frac{\sum_{i \in S} t_i}{\sum_{i \in S} s_i},
$$

with $c_i$ the cost, $t_i$ the completion tokens and $s_i$ the pass indicator of problem $i$. The mean of per-problem ratios is a different quantity and is wrong; a test pins the distinction. The bootstrap is seeded and implemented in the standard library, with no numerical dependency.

**Two outcome classes are separated before any rate is computed.** A row with an error and no bill (a 404 from a pinned provider, a rate limit) is an **infrastructure** outcome; it says nothing about the model and is excluded from every rate. A row that was billed and returned no usable answer (truncated at the ceiling, or an error after tokens were produced) is a **model** outcome, the most expensive kind, and is scored as solving nothing. Eighteen of the 68 error rows are infrastructure; fifty are model outcomes. Empirically, zero of the 101 truncated-or-errored billed rows produced code that passed, so the "cannot succeed" scoring is not merely definitional.

## What changed during the study

A method chapter in which nothing went wrong is not credible to anyone who has run an experiment. Everything below is dated in the project log.

| Date | What happened | What changed |
|---|---|---|
| 2026-07-25 | First call: 392 of 412 tokens were reasoning | The question of the thesis |
| 2026-07-25 | Balance was $4.00, not $50 | Grid re-sized from 434 problems to ~300; pilot made a hard gate |
| 2026-07-26 | Grader bug on macOS: EvalPlus caps memory with `setrlimit`, which Darwin refuses at any value; the exception fires as the first statement of the guard, killing the subprocess before any test, and EvalPlus reports that as a timeout. Every solution, including canonical ones, silently failed | Caught by the canonical-solution test. Fixed by disabling the memory cap; runaway allocation is now bounded only by the timeout |
| 2026-07-26 | A script named `inspect.py` shadowed the standard-library module and broke every script in its directory | Renamed `view.py`; the rule is recorded |
| 2026-07-26 | First real cell: `HumanEval/0` solved by all 10 configurations at a 44× cost spread | Saturation risk moved from hypothetical to observed; pilot sample made difficulty-spread |
| 2026-07-26 | `request_hash` did not include `problem_id`; two problems sharing a prompt would collide | Fixed; zero collisions in the pool; 10 rows migrated in place |
| 2026-07-26 | Unpinned run served by nine providers, billed 1.54× the prediction | Provider **and** quantization pinned; `allow_fallbacks: false` |
| 2026-07-26 | Pilot (15 problems × 10 configs, $0.58): easy tiers 90–100% regardless of reasoning; 81% of problems share the same cheapest solver; 7 of 16 hard thinking calls truncated at 16,000 tokens | Thesis reframed from router to measurement; grid re-weighted to medium/hard; ceiling raised |
| 2026-07-26 | Reasoning budget parameters accepted and ignored (2,000 requested, 13,731 produced) | Effort axis described as binary |
| 2026-07-26 | Cancelling a stream mid-reasoning verified billed $0.00 on two providers | Runtime abort became a real intervention to study |
| 2026-07-26 | `config_id` was a position in a price-sorted list; repricing one model swapped two ids and 8 bought rows were attributed to the wrong model | Identity made alphabetical and price-independent; all 149 rows repaired exactly via `request_hash` |
| 2026-07-26 | `subset_only` stored but never honoured; runner planned the held-out model over the full grid | Fixed; projected grid cost fell $7.51 → $4.59 |
| 2026-07-26 | Ceiling 16k → 32k → 48k for thinking; 16k kept for `off` | Not removed: the cap computes its reservation from `max_tokens` |
| 2026-07-27 | Expected output tokens for `off` were guessed at 350; measured 3,165 (LCB problems make even non-thinking models write thousands of tokens) | Estimates replaced by measurements; a $4.59 grid was really $10.34 |
| 2026-07-27 | Grid run stopped at the cap, cheapest-first, with the thinking arm partial | Grid left unbalanced; comparable statistics restricted to shared sets. Balancing would have cost about $1.50 and required raising the cap; recorded as a limitation instead |
| 2026-07-27 | Grid refuted the pilot's free abort threshold | Chapter 7 |
| 2026-09-01 | Adversarial audit found the run order's `problem_id` tiebreak had sorted every numeric LeetCode id before every alphabetic AtCoder id, so the thinking arm is almost entirely function-style on LCB | Within-style comparison added (Chapter 5.4); frontier labelled as function-style |

The last entry deserves its own sentence, because it is the kind of defect that only a reproducible pipeline reveals: **the run order is part of the method**, and a tie-break nobody thought about changed which exam the two effort arms sat.

## Tests

The repository carries 132 automated tests, all passing at the time of writing (Appendix D lists every one). The largest groups guard the cost cap (19) and the never-pay-twice property (18). Each test is a record of a failure that was observed or feared, and the two that matter most are the canonical-solution check (which caught the grader bug) and the ratio-of-sums check (which prevents the standard CPC mistake).

## Reproducibility

All sampling, splits and bootstraps use the fixed seed 20260726. Running `scripts/results.py` twice produces byte-identical output. The database, the configuration files, the code and the figures are the artefact; the figures are regenerated from the database and never hand-edited. Python is pinned to 3.12 because the grading library has no wheels for 3.14. The one dependency added after day one is `matplotlib`, for the figures; the convex hull and the bootstrap need nothing beyond the standard library.
