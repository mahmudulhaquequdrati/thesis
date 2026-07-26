# CARR Thesis — Master Document

> **Single source of truth for this thesis.** Everything is here: what we're building, how, what's done, what's next.
> **Update §1 (Status) and §5 (Progress) at the end of every work session.**

**Thesis:** Cost-Aware Reasoning Routing — An Empirical Study of Open-Weight Reasoning Models for Code Generation
**Proposal:** [Thesis_Project_Proposal.docx](Thesis_Project_Proposal.docx) (Revision 2, July 2026)
**Started:** 2026-07-25 · **Target:** 12 weeks → ~2026-10-17

---

## §1. Current Status

| | |
|---|---|
| **Stage** | **Week 1 ✅, pilot run, THESIS REFRAMED.** From *"build a router"* to **"when is reasoning worth paying for?"** — see §2 and the §11 findings. |
| ~~Stage~~ | **Week 1 COMPLETE.** Days 1–5 ✅. Real generations flowing end to end: problem → OpenRouter → extract → grade → row. |
| **Next action** | **Settle three things before the grid:** (a) verify the $0-cancellation result holds across providers and can be observed *live* in a stream, (b) raise `max_tokens` 16k → 32k so truncation stops confounding the effort axis, (c) rebuild the problem set from LCB medium/hard. Then the grid (~$2–4). |
| ~~Next action~~ | ~~**Run the pilot**~~ `uv run python scripts/pilot.py --dry-run` prices it free: **expected $0.29**, this run capped at **$0.37** (1.25× the estimate). It measures the two numbers that size the grid: thinking tokens on *hard* problems, and the saturation rate. In parallel: [docs/advisor-repositioning.md](docs/advisor-repositioning.md) to your advisor |
| **Spend to date** | **$0.583** of **$15.00 loaded** ($14.42 left; runner aborts at $6.00). Grid now priced at **$4.59** — fits. |
| **Rows in dataset** | **149 real** (135 graded). Problem pool **884** (LCB v5+v6 = 342, of which 154 hard / 104 medium). Of ~2,600 (~300 problems × 10 configs — final count set by the pilot). Problem pool: **717 loaded** (HumanEval+ 164, MBPP+ 378, LiveCodeBench 175) + 10 configs |
| **Blocked on** | Nothing. ⚠️ But see the saturation evidence in §11 before choosing the pilot sample |

**Recent log**
- `2026-07-26` — **Analysis module, a doubled hard tier, and two bugs found while building them. $0 spent.** `carr/analysis.py` + `scripts/results.py` produce the thesis's results from whatever is in the database (free, read-only). **LiveCodeBench v5 loaded alongside v6** — pool 884 problems, LCB 342 with **154 hard / 104 medium**, so the usable tier doubles from 132 to 258 and the abort threshold is no longer estimated on seven hard problems. **Grid re-weighted by the pilot**: the easy benchmarks drop to 20-problem anchors (they measure the saturation *finding*, not routing), and all 258 LCB medium+hard go in. ⚠️ **Bug 1 — `config_id` was a config's position in a price-sorted list.** Repricing `deepseek-v4-pro` swapped it with `qwen3.6-35b-a3b`, and **8 already-bought generations were recorded against the wrong model.** It surfaced only as a UNIQUE failure during an unrelated migration; every per-model number would otherwise have been quietly wrong. Identity is now alphabetical and price-independent; `tier_index` stays as the cheapest-first *run order*. Repaired via `request_hash` as ground truth — all 149 rows resolved exactly, none guessed, and verified to change no conclusions. ⚠️ **Bug 2 — `subset_only` was stored but never honoured**, so the runner planned kimi over the whole grid at $3.40/M. Fixed; grid cost falls **$7.51 → $4.59**, which is what makes it fit the $6 cap.
- `2026-07-26` — **✅ The intervention is proven to work, end to end.** `delta.reasoning` is observable **live** in the stream, so a reasoning-token threshold can fire mid-generation. Tested on `deepseek-v4-pro | high` (pinned baidu/fp8): aborted at ~2,002 reasoning tokens after 33.8s, **billed $0.000000**, where the same cell run to completion cost **$0.010978**. Verified on a second provider, so it is not a DeepInfra quirk. Config changes made: **`max_tokens` 16k → 32k** (at 16k, 12 of 12 truncated calls returned zero code — we were measuring our own ceiling, not the model), **`abort.reasoning_tokens`** added but left `null` (the grid must run unaborted first or the threshold would be fitted on the data it is evaluated against), and **`rate_limit_retries: 3`** because `allow_fallbacks: false` means an overloaded pinned provider 429s and loses the cell — safe to retry precisely because a 429 is billed $0. Advisor one-pager written: [docs/advisor-update.md](docs/advisor-update.md).
- `2026-07-26` — **🔴 You cannot ask these models to think less. The advertised control is silently ignored.** Tested on `qwen/qwen3.5-9b` (pinned deepinfra/bf16) against a hard AtCoder problem: `reasoning: {max_tokens: 2000}` produced **13,731 reasoning tokens — 6.9× the requested budget**; `reasoning: {effort: "low"}` produced **11,926**. Both accepted without error, both hit the 16,000 ceiling with `finish_reason=length`, both returned nothing. `reasoning` *is* listed in the endpoint's `supported_parameters`, so this is silent non-compliance rather than an unsupported feature. **Two consequences.** (1) It answers the obvious objection to the reframed thesis — "why not just tell it to think less?" You can't. Ex-ante budget control does not work here, so runtime monitoring and abort is not a redundant mechanism but the only one that functions. (2) Our effort axis is therefore **binary in practice** (`{enabled:false}` genuinely yields 0 reasoning tokens; graded effort levels do not bind) and must be described that way, not as a budget dial.
- `2026-07-26` — **🔴 DIRECTION CHANGE, driven by the user and confirmed by the data. The thesis is no longer about routing.** New question: **when is reasoning worth paying for, and can you tell before you have paid?** Three findings, all from data already bought. **(1) Reasoning length scales monotonically with difficulty** — 963 → 2,955 → 7,009 → 9,449 mean reasoning tokens across easy-bench → LCB easy → medium → hard. **(2) Reasoning length predicts failure**: calls that PASS average **2,333** reasoning tokens; calls that return *nothing* average **11,878**. Every truncated call — 12 of 12 — produced zero usable code. **(3) Cancelling a stream mid-reasoning is billed $0.00** (verified twice, no billing record after 10+ min). So a length-based abort is a real intervention, not a pro-rata saving. Simulated on the pilot data: **abort at 10,000 reasoning tokens keeps 42/42 passes and cuts thinking-config spend 44%**; at 6,000 it saves 78% for 10% fewer solved. Routing is demoted to a section. Why this is better: it does not depend on routing working (it collapsed at 81%), and the tradeoff curve is a result either way.
- `2026-07-26` — **Prior-art check on the two proposed pivots — both weaker than claimed, recorded honestly.** *Reasoning non-termination is NOT novel*: [ThoughtTerminator](https://arxiv.org/pdf/2507.04023), [SelfBudgeter](https://arxiv.org/pdf/2505.11274), [RecurGuard](https://arxiv.org/html/2606.07968v1) already cover it. *The aggregator/quantization confound is partly occupied*: [The Silent Hyperparameter](https://arxiv.org/abs/2605.19537) (May 2026) quantifies self-hosted backend variance at up to 16.6pp, and a [LessWrong post](https://www.lesswrong.com/posts/KsyoSAyBRXtwzSugg/not-pinning-your-openrouter-provider-might-invalidate-your) found 31/32 repos use OpenRouter unsafely. The remaining gap — systematic, quantitative, on *commercial aggregators* with reasoning modes and cost — is real but narrow, and belongs in methodology rather than as a headline.
- `2026-07-26` — **PILOT RUN ($0.578 total). It found what it was built to find, and the answer changes the design.** 149 generations, 135 graded, 15 stratified problems × 10 configs. **(1) Saturation confirmed and quantified:** HumanEval+ 90–100%, MBPP+ 93–100%, LCB-easy 100% — no routing signal at all. Only **LCB medium (50–60%) and hard (31–50%) discriminate**, and the pool holds just 132 of those. **(2) Routing collapse:** 13 of 16 problems (81%) have the *same* cheapest-passing config, `deepseek-v4-flash | off`. That is the "When Routing Collapses" phenomenon §15.3 cites, in our own data. **(3) ⚠️ The effort axis is confounded by `max_tokens`:** on LCB hard, **7 of 16 thinking calls hit the 16,000-token ceiling and returned nothing**. Thinking scores *worse* than not-thinking there (31% vs 50%) — but that is truncation, not capability. **(4) The cost trap, measured:** $0.099 — **17% of all pilot spend** — bought calls that returned nothing usable, almost all thinking configs on hard problems; `deepseek-v4-pro|high` alone wasted $0.064 across 4 calls averaging 10,754 reasoning tokens.
- `2026-07-26` — **Searched for harder/newer problems before spending. Two findings, one of them important.** (1) **There is no public code-generation benchmark shipping 2026 problems with test cases.** The frontier is LiveCodeBench-Pro at 2025 Q3 (gated, needs an HF login); LCB proper stopped at 2025-04. Genuinely post-cutoff problems would mean scraping AtCoder/Codeforces and building a benchmark — months, not a step. So contamination stays a reported limitation rather than something we can engineer away. (2) ⚠️ **Found the closest prior art yet: [Agent-as-a-Router / CodeRouterBench](https://arxiv.org/abs/2606.22902) (Jun 2026)** — routing for coding tasks, 8 backends, 9,999 tasks × 8 models released free. Checked against the data: it has **no effort axis and no reasoning-token column**, and its router is trained (LoRA). It sharpens our claim rather than displacing it, but it must be cited (§15.3) — and its 79,992-row matrix is the best free target yet for prototyping `router/knn.py` at $0 (§15.2).
- `2026-07-26` — **Balance raised $4.00 → $15.00; the spending rule tightened rather than loosened.** A bigger balance is not a bigger budget. `abort_at_usd` is **$6.00**, so **$9 of the balance is unspendable** whatever a bug does, and a new per-run ceiling (`run_headroom: 1.25`) keeps any single run within 1.25× *its own* estimate even when the lifetime cap has room — the "if it can be done for $2, never spend $2.20+" rule made mechanical. An early stop costs a re-invocation, not money, because bought cells are skipped for free.
- `2026-07-26` — **Runner, cost cap and pilot built. $0 spent.** `config/experiment.yaml` (the caps finally have a home), `carr/experiment.py` (stratified sampling, fixed seed), `carr/runner.py` (the paid loop) and `scripts/pilot.py`. **The cap aborts before spending, on worst case, against lifetime DB spend** — 16 tests in `tests/test_runner.py` prove it, including that a zero-headroom cap buys literally nothing and that a mid-run stop is resumable. Pilot priced at **expected $0.29 / worst case $2.37** over 15 stratified problems × 10 configs. ⚠️ **Latent bug found and fixed: `request_hash` did not include `problem_id`,** so two problems sharing a prompt would collide and the second would silently get no row, no result and no routing label. Zero collisions in the current 717-problem pool, so it was invisible rather than harmful — now closed, with the 10 existing rows migrated in place rather than re-bought.
- `2026-07-26` — **LiveCodeBench loaded — the hard tier exists. $0 spent.** `carr/benchmarks/livecodebench.py` (download + cache + decode) and a second grading path in `verify.py`, because LCB shares nothing with evalplus: 112 problems are stdin→stdout programs, 63 are methods on a `Solution` class, and **LCB ships no canonical solutions at all**. Pool is now **717 problems**; 80 of the 175 LCB problems are `hard`. ⚠️ **Two findings.** (1) **LCB is not contamination-controlled for us** — its newest problem is 2025-04-06, the dataset stopped updating 2025-06-05, and every model on the roster is a 2026 release. It enters as a *difficulty* tier only; `release_date` is stored so exposure can be reported. The proposal's contamination claim is now wrong (§14). (2) With no canonical solutions there is nothing to run through the grader as known-good, so `tests/test_verify_lcb.py` uses **hand-written reference solutions** for both styles — the only thing standing between us and an LCB version of the macOS `setrlimit` bug. 11 LCB tests pass; the references score 43/43 and 34/34.
- `2026-07-26` — **Day 4 ✅ — Week 1 complete. First real generations, $0.0103.** `carr/providers/openrouter.py` + `scripts/run_one.py` (hard cap on *worst-case* spend that aborts before sending; dedup; cheapest-expected-first). One problem × all 10 configs. **Three findings, two of them serious.** (1) ⚠️ **Saturation is real and immediate: 10/10 configs solved `HumanEval/0`, including every no-reasoning config.** That is the risk §11 names as most likely to invalidate the headline result, visible on the very first cell. The pilot sample must be difficulty-spread, and the LiveCodeBench hard tier moves from "nice to have" to load-bearing. (2) **Thinking tokens measured far below assumption: mean 963 (range 278–1,915) against the 3,500 guess.** Grid re-prices from $3.66 to **$1.76** — but this is one easy problem, not a pilot; hard problems will pull it up. (3) **58× cost spread for an identical outcome** — $0.000081 (flash·off) to $0.004673 (kimi·high), all PASS. That spread is the thesis. Routing target for this problem: `deepseek-v4-flash | off`, as §9 predicted.
- `2026-07-26` — **Kimi given both effort levels; roster 9 → 10 configs (+$0.10).** `subset_only` cuts *problems*, never the effort axis. With one effort kimi had a single point on the cost-accuracy plane, no measurable thinking delta, and RQ5 would have tested transfer along the model axis only — not the effort axis, which is what the thesis is about. Also corrected a pre-existing count error: the grid is **~2,600 rows**, not 2,700 (8 full configs × 300 + 2 held-out × 100); the old figure assumed kimi ran the full 300, contradicting `subset_only`.
- `2026-07-26` — **Mock data removed; `scripts/studio.py` added.** All 360 seeded rows deleted, along with `seed_mock.py`, `make_viewer.py` and `providers/echo.py` — they had done their job (proving the chain and the dedup) and keeping fake rows next to real ones is a hazard. `scripts/init_db.py` now builds the database from real, free sources only: **542 problems** from evalplus + **10 configs** from the roster, with `generations`/`results` deliberately empty. Studio is a local SQLite browser (stdlib only, loopback only) with sort, search, pagination, a read-only SQL console, and row edit/delete. It introspects the schema per request, so it adapts to whatever the file contains. **Every write snapshots the database to `data/backups/` first** — verified by deleting 2 rows and confirming the snapshot still held 542. `--read-only` disables writing.
- `2026-07-26` — **Pipeline made visible, on mock data, for $0.** Built `carr/{effort,db,extract,cost}.py` + `carr/providers/{base,echo}.py`, so the whole chain (problem → prompt → response → extract → grade → row) runs end to end with `EchoProvider` standing in for the API. Two viewers: `scripts/view.py` (terminal) and `scripts/make_viewer.py` → a self-contained `data/viewer.html`. **`request_hash` dedup proven working** — a re-run inserts 0 rows, so a crashed grid restart is free. **Three real bugs caught before any money was spent:** (1) `scripts/inspect.py` shadowed the stdlib `inspect` module and broke every script in `scripts/` → renamed `view.py`; (2) the echo provider's fallback mutation appended an *unreachable* `return None`, so rows labelled as failures graded PASS → now shadows the entry point; (3) `docs/codebase-tour.md`'s "$3.61" grid cost was not reproducible from the script — the real cause was `--in-tokens 600`, a pre-Day-2 guess, now defaulted to the measured 100. Roster re-verified live: all 5 slugs exist, prices match, `reasoning` supported. **`scripts/verify_roster.py` now exists** — four docs referenced it and it never had.
- `2026-07-25` — Proposal analysed. GLM dropped from roster. Decisions locked (§12). Master doc created.
- `2026-07-25` — Day 1 scaffold: `uv` project on **Python 3.12.13** (system 3.14.3 avoided), `git init`, `openai` + `python-dotenv` installed, `.env` gitignored, `scripts/day1_hello.py` written. Verified working. Waiting on the key to make the first call.
- `2026-07-25` — **Prior-art check (§15). Two findings.** (1) The problems are free to download; the *table* must be generated by us — no published dataset has (model × thinking-mode) on code with reasoning-token cost. But RouterBench / LLMRouterBench / HRBench release per-query data we can prototype CARR against for $0. (2) ⚠️ **The proposal's §3 gap analysis is ~12 months stale** — Route-To-Reason, DART and HRBench already occupy much of the claimed gap. Novelty re-positioned to *cheapest possible router*. Advisor conversation owed.
- `2026-07-26` — **Day 3 ✅ — grader done, and it found a real bug.** Chose evalplus's `untrusted_check` over Docker: it ships subprocess isolation *and* handles grading subtleties (`atol`, MBPP special oracles) that hand-rolled checks get silently wrong. **Critical macOS bug found:** evalplus caps memory via `setrlimit(RLIMIT_AS)`, which Darwin refuses to lower at any value; the exception fires as the first statement of `reliability_guard`, killing the subprocess before any test runs *and* before `os.system` is disabled. evalplus reports this as a **timeout**, so every solution — including its own canonical ones — silently "fails". Undiagnosed this would have burned the entire $4 on garbage. Fixed via `EVALPLUS_MAX_MEMORY_BYTES=-1`; trade-off is no memory cap, bounded now only by the timeout. 8/8 tests pass.
- `2026-07-25` — **Day 2 ✅.** `evalplus` installed; HumanEval+ (164) and MBPP+ (**378**, not 500 — evalplus drops broken problems) loaded. **Measured prompt sizes: median 99 tokens (HE+) and 36 (MBPP+), ~6× smaller than assumed** — input cost is negligible, so effectively 100% of the budget is output+reasoning tokens. Grid re-estimated at **$3.61** (was $3.82). Full send/store contract written to [docs/data-spec.md](docs/data-spec.md).
- `2026-07-25` — **Day 1 ✅ + roster verified (pulled forward from Day 5).** Key works. All proposal candidates exist on OpenRouter with real prices now in `config/models.yaml`. Two empirical findings: (1) a trivial "reverse a string" prompt burned **392 reasoning tokens out of 412** — the reasoning-token trap confirmed at 20× understatement; (2) `/generation` returns ground-truth `total_cost` but needs **~10s to settle**, so `runner.py` must batch-reconcile costs afterwards rather than block per call. Budget re-sized to the **$4.00 actually loaded**: grid costs $3.82 at 3,500 thinking-tokens but **$6.15 at 6,000** — the pilot is now a hard gate. Advisor one-pager written.
- `2026-07-25` — **Budget cut $100 → $50.** Grid re-fitted: 514 → 434 problems (MBPP+ 200→150, LCB 150→120), 10 → 9 configs (dropped DeepSeek-Flash Think-Max). Added four cost controls to §9. `CLAUDE.md` created with the mandatory doc-update ritual.

---

## §2. What we are building (plain English)

### The question

When you ask an AI to write code you pick two things: **which model**, and **how hard it thinks**. Thinking harder costs more — sometimes 100× more. Sometimes that's necessary. Usually it isn't. Nobody has systematically measured *when*.

### The entire thesis, in four rows

| problem | model | thinking | passed? | tokens | cost |
|---|---|---|---|---|---|
| `reverse_string` | qwen-small | off | ✅ | 180 | $0.0001 |
| `reverse_string` | deepseek-pro | max | ✅ | 4,200 | $0.0180 |
| `graph_dp_hard` | qwen-small | off | ❌ | 300 | $0.0002 |
| `graph_dp_hard` | deepseek-pro | max | ✅ | 9,100 | $0.0400 |

- Rows 1–2: identical outcome, **180× the price**. Pure waste.
- Rows 3–4: the cheap model fails — the expensive one is genuinely earning its cost.

**The thesis = build this table with ~5,000 rows, then write a program that predicts which situation a new problem is in, before calling any model.** That program is CARR.

### The analogy

You manage 5 developers — some cheap juniors, some expensive seniors; some can work "quickly" or "very carefully" (careful = more billable hours). 500 tickets arrive. Today, every ticket goes to the best senior working carefully. Your thesis: **read the ticket first, assign the cheapest person who can still solve it** — and prove that saves 60–70% of the money while still solving 90–95% of tickets.

### The three artifacts

**1. The machine (harness).** A Python program that loops:
> coding problem → send to model with a thinking setting → get code back → run it against test cases → record pass/fail, tokens, cost

Run ~5,000 times. **This is ~70% of the work.** It's plumbing, not AI. It must be resumable, because every run costs real money and *will* crash halfway.

**2. The table (dataset).** One SQLite file holding every row. **This is the real scientific asset** — RQ1–RQ3 are literally SQL queries against it. If the code is lost but this file survives, the thesis survives.

**3. The predictor (CARR).** Given a *new* problem: find the most similar problems already in the table, see which model+setting was cheapest-but-still-passing for them, use that. Nearest-neighbour lookup — no training, no gradients, a few hundred lines. **Cannot be written until the table exists.**

---

## §3. Research questions (what the table must answer)

| RQ | Question | Answered by |
|---|---|---|
| **RQ1** | What's the cost-vs-accuracy Pareto frontier across models and thinking modes? | `SELECT` over the table + `pareto.py` |
| **RQ2** | How does the ranking shift from easy (HumanEval+) to hard (LiveCodeBench)? | Same, grouped by benchmark |
| **RQ3** | When does more thinking stop paying off? | Tokens vs. difficulty vs. pass rate |
| **RQ4** | Can a training-free router beat every fixed strategy? | CARR vs. **convex hull** (§10.1) |
| **RQ5** | Does CARR still work on an unseen benchmark and an unseen model? | Held-out scenarios; Kimi held out entirely |

**RQ1–RQ3 are a complete publishable contribution on their own.** Reaching them (Week 5) means the thesis cannot fail outright, even if CARR disappoints.

---

## §4. The elements (every tool, and why)

| Element | What it is | Why we use it |
|---|---|---|
| **uv** | Python package/env manager | Already installed. Faster and less painful than pip+venv |
| **Python 3.12** | Language runtime | ⚠️ Your system has **3.14.3** — too new; `evalplus` and embedding libs lack wheels. **Pin 3.12 on Day 1** or you'll hit this in Week 3 |
| **OpenRouter** | One API, one key, all models | Avoids 6 separate accounts and 6 client adapters. Small markup, worth it |
| **`openai` SDK** | HTTP client | OpenRouter is OpenAI-compatible — set `base_url`, done. No custom client needed |
| **evalplus** | HumanEval+ / MBPP+ problems + extended tests | The standard. Gives problems *and* graders |
| **LiveCodeBench** | Hard, recent competitive problems | **The hard tier that makes RQ4 non-trivial** — 80 hard of 175. ⚠️ *Not* contamination-resistant for us: it stopped updating in 2025 and our models are 2026. Loaded as plain JSONL from HuggingFace, so no `datasets` dependency |
| ~~Docker~~ → **evalplus `untrusted_check`** | Sandbox + grader | Reversed on Day 3. evalplus ships subprocess isolation, timeouts and `reliability_guard` (disables `os.system`, `os.fork`, ~40 more) — **and gets grading right**: `atol` float comparison and MBPP special oracles that hand-rolled grading would silently mislabel. Docker saved ~2 GB RAM on the 8 GB M2 |
| **SQLite** (stdlib `sqlite3`) | The dataset | Zero setup, one portable file, real SQL. No server needed |
| **pandas** | Analysis | Turning the table into results |
| **matplotlib** | Figures | Exports PNG for pasting into Word |
| **numpy / scipy** | Math | `scipy.spatial.ConvexHull` for §10.1; `scipy.stats` for bootstrap CIs |
| **fastembed** | Text embeddings for k-NN | ⚠️ Use this, **not** sentence-transformers — it's ONNX-based and avoids a ~2 GB torch install. Matters on your 8 GB M2. Model: `BAAI/bge-small-en-v1.5` (~130 MB) |
| **PyYAML** | Config files | Roster/grid live in YAML, never hardcoded |
| **pytest** | Tests | Especially for the sandbox — it must be provably safe |
| **python-docx** | Optional | Emit results tables straight into Word |

**Hardware note:** M2, 8 GB RAM. Self-hosting models locally is off the table — everything runs through the OpenRouter API. Your Mac only orchestrates and grades.

---

## §5. Progress tracker

Legend: ⬜ not started · 🟨 in progress · ✅ done

### Week 1 — the thin slice
| | Day | Task | Done when |
|---|---|---|---|
| ✅ | 1 | Toolchain + one API call | **Done.** Key verified; 412 completion tokens of which **392 were reasoning** |
| ✅ | 2 | Load real benchmark problems | **Done.** `scripts/day2_inspect_problems.py`; full contract in [docs/data-spec.md](docs/data-spec.md) |
| ✅ | 3 | Sandboxed grader | **Done.** 8/8 tests pass incl. canonical solutions, infinite loop, hostile `os.system` |
| ✅ | 4 | Connect the pieces | **Done.** `HumanEval/0 | qwen/qwen3.5-9b | off | PASS | 1006/1006 | 614 tok | $0.000106` — then all 10 configs, $0.0103 |
| ✅ | 5 | Save to SQLite | **Done.** `carr/db.py` schema + dedup, tested; `scripts/init_db.py` loads 542 problems + 10 configs. Empty grid is the correct state |
| ✅ | 5 | Roster verification | **Done early**, and `scripts/verify_roster.py` now makes it repeatable |
| ✅ | — | See the data | **Done.** `scripts/studio.py` (browser, any schema, edit/delete) and `scripts/view.py` (terminal, CARR-specific) |

### Weeks 2–12
| | Week | Milestone | Spend |
|---|---|---|---|
| ✅ | 2 | Widen harness: all loaders, all configs, resumability, cost cap | **Done, $0.** `carr/runner.py` + `config/experiment.yaml`; 16 tests on the cap alone |
| ⬜ | 2 | Pilot: 15 **difficulty-spread** problems × 10 configs → thinking tokens on HARD problems + **saturation rate** | **~$0.29** (worst case $2.37) |
| ⬜ | 3–4 | **Full grid run** (cheapest configs first) | $18–28 |
| ⬜ | 5 | RQ1–RQ3: Pareto frontier, convex hull, CPC/TPC with CIs | $0 |
| ⬜ | 6–7 | CARR: features, oracle, rules, k-NN, 4 scenarios, gap decomposition | $0 |
| ⬜ | 8–9 | Formal section + figure generation | $0 |
| ⬜ | 10–12 | Thesis writing, polish, submission | $0 |

**Week 5 is the safety line** — past it, RQ1–RQ3 stand alone as a contribution regardless of CARR's outcome.

---

## §6. Week 1, day by day

Don't build the architecture yet. Build one thin end-to-end slice, then widen it. Each day ends with something that runs.

### Day 1 — Make one API call (~$0.01)
1. `uv init`, **pin Python 3.12** in `pyproject.toml`
2. `uv add openai python-dotenv`
3. Create an OpenRouter account, generate an API key, load **$10** (covers Weeks 1–2 comfortably; top up to ~$35 before the Week-3 grid run, and never load the full $50 — an unloaded balance is your last line of defence against a runaway loop)
4. Put the key in `.env`; add `.env` to `.gitignore`
5. `git init` — this is a thesis; version it from day one
6. Write ~15 lines: send *"write a Python function that reverses a string"* to one cheap model, print the response

**Done when:** a model's text appears in your terminal.
**You'll learn:** what the response object contains — especially the `usage` field, which is where all your cost data comes from.

### Day 2 — Get real problems
1. `uv add evalplus`
2. Load HumanEval+, print problem `HumanEval/0` — prompt and tests
3. Print the `test` field and read it

**Done when:** you can print any problem's prompt and its tests.
**You'll learn:** a benchmark problem is just *a prompt* + *a set of assertions*. Nothing more.

### Day 3 — Run untrusted code safely
1. Install Docker Desktop
2. Write `grade(code: str, problem) -> bool`: write code+tests to a temp file, run in a container (no network, memory cap, ~10s timeout), return pass/fail
3. Test with three inputs: correct code, wrong code, and `while True: pass`

**Done when:** ✅, ❌, and a clean timeout — no hung Mac.
**Why this matters:** models *will* eventually generate `os.system('rm -rf ...')`. Never run generated code unsandboxed.

### Day 4 — Connect the pieces
Chain Days 1–3: real problem → model → extract code from the response (markdown fences) → grade → print the row. One problem, one model.

**Done when:** `reverse_string | qwen | off | PASS | 180 tok | $0.0001` prints.
**This single line is your thesis in miniature.** Everything after is scale.

### Day 5 — Save instead of print
1. Create the SQLite DB using the §8 schema
2. Write rows instead of printing
3. Loop 10 problems × 2 models × 2 thinking settings = 40 rows
4. Write and run `verify_roster.py` — query OpenRouter's live `/models`, check which candidates exist, their real prices, and whether their thinking-mode parameter is accepted

**Done when:** `SELECT * FROM results` returns 40 rows, and `config/models.yaml` holds only confirmed-live models.
**Total Week 1 spend:** under $2.

> **End of Week 1 you have a working miniature of the entire thesis.** The remaining 11 weeks widen and analyse it. That's far safer than a beautiful architecture that has never made an API call.

---

## §7. Repository layout (grown into, not built upfront)

`✅` = exists today. Everything unmarked is planned, not written — the tree is a
map of where things will go, not a claim that they are there.

```
thesis/
├── THESIS.md                ✅ # ← this file, the source of truth
├── CLAUDE.md                ✅ # working rules: doc-update ritual, budget discipline
├── docs/
│   ├── codebase-tour.md     ✅ # ← START HERE to learn the code, file by file
│   ├── data-spec.md         ✅ # exact send/store contract
│   └── advisor-repositioning.md ✅
├── README.md                ✅
├── Thesis_Project_Proposal.docx ✅
├── pyproject.toml           ✅ # uv, pinned to Python 3.12
├── .env                     ✅ # OPENROUTER_API_KEY (gitignored)
├── config/
│   ├── models.yaml          ✅ # roster: slug, family, effort params, prices, snapshot date
│   └── experiment.yaml      ✅ # HARD COST CAP, temperature, max_tokens, strata, seed
├── carr/
│   ├── db.py                ✅ # schema + idempotent upsert + read helpers
│   ├── providers/
│   │   ├── base.py          ✅ # the Provider contract: Generation, Usage
│   │   └── openrouter.py    ✅ # the real adapter. Every call costs money
│   ├── effort.py            ✅ # models.yaml → the 10 configs, cheapest first
│   ├── experiment.py        ✅ # experiment.yaml + stratified, seeded sampling
│   ├── runner.py            ✅ # THE paid loop. Cap aborts before spending
│   ├── extract.py           ✅ # raw response → runnable Python
│   ├── cost.py              ✅ # tokens → USD (reasoning ⊂ completion, never added twice)
│   ├── benchmarks/
│   │   └── livecodebench.py ✅ # download, cache, decode. HE+/MBPP+ come from evalplus
│   ├── execute/
│   │   ├── verify.py        ✅ # THE grader: evalplus path + LiveCodeBench path
│   │   └── _lcb_runner.py   ✅ # LCB subprocess entry point. Never import it
│   ├── runner.py               # resumable, cost-capped grid loop
│   ├── features.py             # lexical / structural / embedding features
│   ├── router/                 # rules.py, knn.py, oracle.py
│   └── analysis/
│       ├── pareto.py           # frontier + CONVEX HULL baseline (§10.1)
│       ├── knapsack.py         # MCKP oracle + LP bound
│       ├── stats.py            # bootstrap CIs for CPC/TPC
│       ├── evaluate_router.py  # RQ4–RQ5 + gap decomposition
│       └── figures.py          # PNGs for Word
├── scripts/
│   ├── day1_hello.py        ✅ # one API call; where the 392/412 reasoning finding came from
│   ├── probe_cost_endpoint.py ✅ # proved /generation needs ~10s to settle
│   ├── day2_inspect_problems.py ✅ # what a benchmark problem actually is
│   ├── estimate_cost.py     ✅ # price the grid before running it
│   ├── verify_roster.py     ✅ # roster vs live /models — free, exits non-zero on drift
│   ├── init_db.py           ✅ # build the DB from evalplus + the roster (real, free)
│   ├── run_one.py           ✅ # one problem through 1..N configs. COSTS MONEY
│   ├── studio.py            ✅ # local DB browser: any schema, SQL console, edit/delete
│   ├── studio.html          ✅ # its UI — served by studio.py, not opened directly
│   ├── view.py              ✅ # terminal viewer  (NOT inspect.py — shadows the stdlib)
│   ├── pilot.py             ✅ # the pilot / the grid. COSTS MONEY
│   └── run_grid.py             # not needed: pilot.py --set grid
├── data/
│   ├── carr.sqlite          ✅ # gitignored. THE scientific asset — back it up
│   └── backups/             ✅ # gitignored. Auto-snapshot before any studio write
└── tests/
    ├── test_verify.py       ✅ # 8 tests — the grader must be right
    ├── test_verify_lcb.py   ✅ # 11 tests — hand-written references, no canonicals exist
    ├── test_runner.py       ✅ # 16 tests — THE COST CAP. Proves it aborts
    ├── test_extract.py      ✅ # 11 tests — extraction must never raise or invent
    └── test_db.py           ✅ # 13 tests — never pay twice
```

**Naming trap worth remembering:** the terminal viewer is `scripts/view.py`, not
`inspect.py`. Python puts a script's own directory first on `sys.path`, so a file
named `inspect.py` in `scripts/` shadows the stdlib `inspect` module and breaks
every other script in that directory — including, silently, the seeding run.

---

## §8. Database schema

**Implemented in [`carr/db.py`](carr/db.py) as of 2026-07-26.** That file is now
authoritative; the sketch below is the summary. `features` and `router_runs` are
still sketches — they are not created, because nothing populates them yet and an
empty table implies a contract that has not been designed.

```sql
problems(problem_id PK, benchmark, difficulty, prompt, entry_point,
         n_tests, prompt_chars, n_base_tests, n_plus_tests, release_date)

configs(config_id PK, model_slug, family, effort_label, effort_mechanism,
        params_json, price_in_per_m, price_out_per_m, snapshot_date,
        held_out, subset_only, UNIQUE(model_slug, effort_label))

generations(gen_id PK, problem_id, config_id,
            request_hash UNIQUE,          -- ← resumability lives here
            openrouter_gen_id, raw_response, extracted_code,
            prompt_tokens, completion_tokens, reasoning_tokens,
            cost_computed_usd, cost_actual_usd, finish_reason,
            latency_ms, temperature_sent, error,
            is_mock, mock_mode,           -- ← mock rows can never masquerade
            created_at)

results(gen_id PK FK, passed, base_passed, n_tests_passed, n_tests_total,
        error_type CHECK IN ('assertion','timeout'), exec_ms)

-- sketches only, not created yet:
features(problem_id PK, feature_json, embedding BLOB)
router_runs(run_id PK, variant, scenario, k, split_seed, problem_id, chosen_config_id, ...)
```

**Migration note (2026-07-26, first schema).** Four conflicts between this
section and `docs/data-spec.md` §6 were resolved when the schema was actually
built, and the code won each time:

| Conflict | Resolution | Why |
|---|---|---|
| `results.n_tests` vs `n_tests_total` | **`n_tests_total`** | matches `GradeResult` in `verify.py`, so no renaming layer can drop it |
| `base_passed` had no column in either spec | **added** | `grade()` already produces it, and it is the signal the §11 saturation check needs |
| `error_type` domain listed `syntax`/`exception` | **narrowed to `assertion`/`timeout`, enforced by CHECK** | those are the only two values `grade()` emits; a documented-but-impossible value is a trap |
| neither spec had a mock flag | **added `is_mock` + `mock_mode`** | without it a seeded row and a $0.0006 purchased row are indistinguishable |

**Five design decisions that matter:**

- **`is_mock`** — every analysis query must filter `is_mock = 0`. `db.summary()` reports real spend with that filter applied, so a non-purchased row can never inflate a cost number. `mock_mode` traces a synthetic row back to whatever produced it. Nothing writes these today; they stay because the failure they prevent is invisible once it happens.

- **`request_hash UNIQUE`** over `(model, effort, prompt, params)`. Checked before every API call; if present, skip. Crash at row 3,000 and restarting costs **$0** for the first 3,000. Every generation is money — never pay twice.
- **`effort_mechanism`** is a column, not a comment. Native thinking-modes and prompt budget-forcing are *not* equivalent (proposal §8 says so). Results must split by mechanism or the effort axis is confounded.
- **`family`** — lets you separate within-family from cross-family routing gains, which matters now the roster is only three families.
- **`raw_response` stored verbatim.** Your code-extraction logic will have bugs. Keeping raw responses lets you re-grade offline for free instead of re-buying 5,000 generations.

---

## §9. The experiment

### Roster — 3 families, 5 open-weight models + 1 closed reference

✅ **RE-VERIFIED against OpenRouter's live `/models` on 2026-07-26** — all 5 slugs still served, prices unchanged, `reasoning` present in `supported_parameters` for every one. Reproduce with `uv run python scripts/verify_roster.py` (free, no key, exits non-zero on drift). Prices are USD per million tokens. Canonical copy: [`config/models.yaml`](config/models.yaml).

| Model slug | Family | Role | in $/M | out $/M |
|---|---|---|---|---|
| `qwen/qwen3.5-9b` | qwen | Cheapest tier; the frontier floor | 0.100 | **0.150** |
| `deepseek/deepseek-v4-flash` | deepseek | Cost-efficient reasoner, mid tier | 0.0938 | **0.1876** |
| `qwen/qwen3.6-35b-a3b` | qwen | Mid tier, permissive licence | 0.140 | **1.000** |
| `deepseek/deepseek-v4-pro` | deepseek | Frontier open-weight reasoner | 0.435 | **0.870** |
| `moonshotai/kimi-k2.6` | moonshot | **RQ5 held-out**, subset only | 0.646 | **2.720** |

**4 models × 2 efforts (off / high) = 8 configs, + 1 held-out = 9.** Pairing each model with *itself* at two effort levels keeps the effort axis clean — within a pair, only the thinking mode changes.

**Three findings from verification:**
- **`deepseek-v4-flash` at $0.188/M output is the bargain of the roster** — cheaper per output token than `qwen3.6-35b` despite ranking higher. Expect it to dominate a long stretch of the Pareto frontier.
- **Output prices span 18×** across the roster ($0.15 → $2.72). Combined with thinking's ~10× token multiplier, the most expensive config costs ~180× the cheapest. That spread *is* the thesis.
- **`kimi-k2.7-code` ($3.50/M out) was rejected** — the best coding specialist available, but one thinking config over the full grid would exceed the entire budget. `kimi-k2.6` replaces it as the held-out model, on a subset.

**Held-out model runs on a subset, not the full grid.** RQ5 asks whether CARR transfers to an unseen model; that doesn't require full coverage, and at $2.72/M the full grid would cost more than every other config combined.

**⚠️ No model name may be hardcoded anywhere** — `config/models.yaml` is the only place that knows. Re-run `scripts/verify_roster.py` before the grid; proposal §6.1 notes 6–8 week churn.

**Two consequences of dropping GLM:**
- The abstract's "five or more open-weight models" is now true but spans only **three families**. Say so explicitly in the .docx rather than letting an examiner raise it.
- **Hold out Kimi entirely for RQ5** — it's the only non-DeepSeek/Qwen family, so it's the most genuinely out-of-distribution test available. Stronger than holding out a second DeepSeek.

### Problems — ~300 total (the working figure)

⚠️ **434 was the $50-budget figure and is superseded.** When the real balance
turned out to be $4.00 (since raised to $15.00), the grid was re-sized to ~300 and every cost estimate
since uses 300. The 434 breakdown is kept below as history; the **final count is
set by the pilot**, which measures mean thinking tokens.

- **HumanEval+** — all 164 (easy anchor; short outputs, so it's the cheapest tier per problem)
- **MBPP+** — sampled from the **378 available** (evalplus drops broken ones; the proposal's "500" does not exist)
- **LiveCodeBench** — ✅ **loaded 2026-07-26: 175 problems** (80 hard, 52 medium, 43 easy; 112 stdin-style AtCoder, 63 function-style LeetCode). This is the hard tier that stops RQ4 from degenerating.
- *(superseded: 164 + 150 + 120 = 434 at the $50 budget)*

**Pool vs sample — they are different numbers.** The database holds **717
problems**, which is *everything* these three benchmarks contain, not a
selection: HumanEval+ is all 164, MBPP+ is all 378 (evalplus drops broken ones
from the original 500), LCB v6 is all 175. The **~300 we plan to run** is a
budget decision, because every problem costs 10 API calls. The pilot sets the
final number, and at the tokens measured so far more than 300 may be affordable.

### ⚠️ LiveCodeBench is NOT contamination-controlled for us

The proposal cites LCB for contamination resistance. That property does not
hold here, and the claim has to be dropped or heavily qualified:

| | |
|---|---|
| Newest LCB problem | **2025-04-06** |
| LCB dataset last updated | **2025-06-05** — it stopped; the "temporally updating benchmark" has not shipped a release in 13 months |
| Our models | all **2026** releases |

There is no post-cutoff window available. Every LCB problem predates every
model on the roster by at least nine months.

**LCB therefore enters this thesis as a difficulty tier, not as a contamination
control.** `problems.release_date` stores each `contest_date` so the exposure
can be *quantified and reported as a limitation* rather than assumed away. This
is a §14 `.docx` edit: the proposal's contamination argument is now wrong.

**Why not sparsify instead?** Tempting, but no: the routing label is *"cheapest config that passes this problem"*, which is only computable if **every** problem has been run through **every** config. A sparse grid breaks CARR's ground truth. So the budget is cut by reducing *problems*, never by skipping cells.

### Sampling
One sample per problem, `temperature=0` where honoured. Biggest cost lever, and it makes the "cheapest passing config" label deterministic instead of noisy. **Log the actual temperature** — some thinking endpoints silently override it.

### Budget — **$15.00 loaded**, aborts at $6.00, $50 ceiling

Balance on the OpenRouter account is **$15.00** (topped up 2026-07-26 from
$4.00). **A bigger balance is not a bigger budget.** The projected work is
$2–4, so `config/experiment.yaml` sets `abort_at_usd: 6.00` and the remaining
**$9 is unspendable** no matter what a bug does. Raising that is an edit
somebody has to make on purpose.

Two ceilings, and a run obeys whichever binds first:

| | | |
|---|---|---|
| **Lifetime** | `abort_at_usd: 6.00` | total across every run ever |
| **Per run** | `run_headroom: 1.25` | 1.25 × *that run's own* estimate |

The per-run one operationalises the rule "if it can be done for $2, never spend
more than $2.20". It matters because the lifetime cap having room is not a
reason for a single run to drift. An early stop costs nothing: bought cells are
skipped for free, so resuming is a re-invocation, not a re-purchase.

Run `uv run python scripts/estimate_cost.py` for live arithmetic over the verified prices.

At the current assumptions (300 problems, **100 in-tok** — the Day 2 *measured*
median, not the old 600 guess — 350 out-tok off, 3,500 out-tok thinking) the grid
costs **$3.55**, comfortably inside the $6.00 abort threshold — where at $4.00 loaded it was a rounding error rather than a margin.

**⚠️ The whole plan hangs on one unmeasured number: mean thinking tokens.**

| Mean thinking tokens | Grid cost | Verdict |
|---|---|---|
| 3,500 | **$3.55** | Fits, barely |
| 6,000 | **$5.89** | **Over** — supports ~203 problems |
| 9,000 | **$8.69** | **Over** — supports ~138 problems |

*(Reproduce: `uv run python scripts/estimate_cost.py --think-tokens 6000`.
These replace two earlier and mutually inconsistent tables — $3.82/$6.15/$8.96
in this section, which used the pre-Day-2 600-token prompt guess, and
$3.61/$5.94/$8.75 in the codebase tour, which was not reproducible from the
script at all. The default `--in-tokens` is now 100, so one number is
authoritative.)*

Day 1 measured **392 reasoning tokens for "reverse a string"** — the easiest problem imaginable. LiveCodeBench hard problems will be far higher, so 3,500 is probably optimistic.

**Therefore the pilot is a gate, not a formality.** Measure the real means, rerun `estimate_cost.py`, *then* choose the problem count. Do not launch the grid on guesses.

| Phase | Cost | Status |
|---|---|---|
| Day 1 verification | ~$0.001 | ✅ spent |
| Days 2–5 slice (40 rows) | ~$0.05 | pending |
| Pilot (measure tokens) | ~$0.30 | **the gate** |
| Full grid | $2.5–3.5 | sized *after* the pilot |
| **Loaded balance** | **$15.00** | abort at $6.00; $9 unspendable |

If the pilot shows the grid needs more than ~$3.50, the options are: cut problems (cheapest fix), drop the held-out model (costs RQ5), or add ~$5 to the account.

### Four cost controls (build these into `runner.py`)

1. **Hard cap that aborts.** ✅ Built and tested (16 tests in `tests/test_runner.py`). `config/experiment.yaml` holds `abort_at_usd: 6.00`; `carr/runner.py` refuses any call whose *worst case* would push **lifetime** spend past it, and a per-run `run_headroom` keeps a single run near its own estimate. It stops — it does not warn and continue.
2. **`max_tokens` ceiling per config.** The largest single cost risk is a reasoning trace that runs away to 30k tokens on one hard problem. Cap it. A truncated response is a legitimate ❌ and costs a known amount.
3. **Cheapest configs first.** Order the run by ascending price. A blowout then costs you the expensive tail, not the cheap foundation you'd have to re-buy.
4. **Never pay twice.** The `request_hash UNIQUE` check (§8) is a cost control, not just a convenience.

### Cost must be measured, not estimated
Two traps specific to reasoning models:
1. **Reasoning tokens are billed but usually absent from the visible response text.** Read `usage.completion_tokens_details.reasoning_tokens`. Deriving cost from response length understates it by **5–10×** and would invalidate every CPC number in the thesis.
2. **Prefer ground truth.** After each call, fetch `GET /api/v1/generation?id=<id>` for the actually-charged amount; store it beside your computed estimate. When they disagree, the API is right and your price table is stale.

---

## §10. The formal section (~2 pages, written Week 8)

**There is no invented mathematics here** — CARR is a lookup table. But there is correct *formalization*, and one piece fixes a real weakness in the central claim.

### 10.1 The RQ4 baseline is too weak — fix it

The proposal compares CARR against "the strongest single configuration." Formalize: each config is a point (cost `cᵢ`, accuracy `aᵢ`). If you may randomize — send fraction `pᵢ` of problems to config *i* — the achievable set is the **convex hull** of those points. Maximizing accuracy subject to `Σpᵢcᵢ ≤ B`, `Σpᵢ = 1`, `pᵢ ≥ 0` is a linear program with two constraints, so an optimal basic solution has at most two nonzero weights:

> **Proposition.** The optimal non-adaptive budget-constrained routing strategy randomizes between at most **two** configurations, and lies on the upper convex hull of the cost-accuracy frontier.

That mixture beats any single fixed config at most budget levels. So "CARR beats the best single model" is nearly free and proves little. **The honest bar: CARR must beat the convex hull** — and it can, because the hull is blind to the problem while CARR reads its features. This gives a far sharper claim:

> CARR's margin over the convex hull *is* the measured value of problem-level information for routing.

`pareto.py` computes the hull as a **first-class baseline**; RQ4 is judged against it.

### 10.2 Three smaller additions
- **Routing as multiple-choice knapsack.** Picking one config per problem under a budget is a classic MCKP; `CARR-oracle` is exactly its integer optimum, and the LP relaxation bounds the gap between hull and oracle.
- **Oracle-gap decomposition.** Split the CARR→oracle gap into *feature insufficiency* + *label noise* + *estimation error*. This is the most genuinely **yours**, and it converts a negative result into a diagnostic one.
- **CPC needs confidence intervals.** Cost-per-correct is `Σcost / Σcorrect` — a ratio estimator, therefore biased, and almost always reported bare. Bootstrap it so you never claim a frontier difference that's within noise.

**Be honest in the .docx:** MCKP is classical, the k-NN bound is Cover & Hart (1967), bootstrapping is standard. What's yours is the gap decomposition and applying the right frame to a literature that benchmarks loosely. That's a defensible formal contribution — just don't call it new mathematics.

---

## §11. Risks

### ⚠️ Biggest risk — benchmark saturation (not in proposal §8)

HumanEval+ and MBPP are **nearly saturated** for 2026-class reasoning models. If the *cheapest* config already passes ~90% of them: the frontier on those benchmarks collapses to a point, "cheapest passing config" is *the cheapest config* almost everywhere, and CARR trivially learns "always route cheap" — a degenerate result an examiner will name immediately.

**Mitigation:** weight the mix toward LiveCodeBench hard/medium and **always report per-difficulty breakdowns**. Framed correctly this is a *finding* — it's precisely RQ3's answer: *reasoning effort is wasted on easy problems; routing gains concentrate entirely in the hard tier.* But it must be a framing chosen now, not a shock in Week 10.

**Action:** check the pass-rate spread during the Week-2 pilot. If the cheapest config solves 9 of 10 HumanEval+ problems, rebalance the sample immediately.

> ### 🔴 2026-07-26 (evening) — MEASURED IN THE PILOT
>
> | tier | reasoning off | reasoning high | verdict |
> |---|---|---|---|
> | HumanEval+ | 90% | 100% | **saturated — no signal** |
> | MBPP+ | 93% | 100% | **saturated — no signal** |
> | LCB easy | 100% | 100% | **saturated — no signal** |
> | LCB medium | 60% | 50% | discriminates |
> | LCB hard | **50%** | **31%** | discriminates |
>
> **76% of the 717-problem pool produces no routing signal whatsoever.** The
> usable set is the 132 LCB medium+hard problems, and we sampled only 7.
>
> **Routing collapse is already visible:** 13 of 16 problems (81%) share the
> same cheapest-passing config, `deepseek-v4-flash | off`. A router that always
> answers "flash, no thinking" would score 81% on this sample. That is the
> degenerate result §15.3's *When Routing Collapses* names.
>
> **Three consequences for the grid design:**
> 1. **Drop or heavily downweight the easy benchmarks.** Spending the grid
>    budget on HumanEval+/MBPP+ buys rows that cannot inform routing.
> 2. **More hard problems are now required, not optional.** 132 is too thin for
>    k-NN plus bootstrap CIs. LiveCodeBench's earlier releases (v1–v5) add ~880
>    more, free — see §9.
> 3. **Report the saturation rate as a finding.** "Reasoning is unnecessary on
>    N% of standard benchmark problems" is a real result, and we now have the
>    number.
>
> ### ⚠️ 2026-07-26 (earlier) — this is no longer hypothetical
>
> The **first real cell** of the grid, `HumanEval/0` × all 10 configs, came back
> **10/10 PASS**. Every no-reasoning config solved it, including the cheapest
> model on the roster. Cost ranged 58× — $0.000081 to $0.004673 — for an
> identical outcome.
>
> One problem is not evidence of the rate, and `HumanEval/0` is close to the
> easiest problem in the benchmark. But the direction is exactly the failure
> mode this section describes, and it appeared immediately.
>
> **Three consequences, all now load-bearing:**
> 1. **The pilot sample must be difficulty-spread, not the first N problems.**
>    A pilot over `HumanEval/0..9` would report ~100% pass everywhere and teach
>    nothing.
> 2. **The LiveCodeBench hard tier moves from "nice to have" to required.** If
>    HumanEval+ and MBPP+ saturate, RQ4 has no headroom to route in: the answer
>    to "which config should I use" becomes "always the cheapest", which is a
>    true but empty result.
> 3. **Report the saturation rate as a finding, not a footnote.** "Reasoning is
>    unnecessary on N% of standard benchmark problems" is a legitimate and
>    interesting result — but only if it is measured deliberately rather than
>    discovered in the discussion section.

### Other risks

| Risk | Mitigation |
|---|---|
| Budget overrun | **$50 hard cap** in `experiment.yaml` that *aborts* the run (not warns); `max_tokens` ceiling per config so no single trace runs away; cheapest configs first, so a blowout costs the expensive tail not the cheap foundation; `request_hash` prevents ever paying twice |
| Model deprecation mid-project | Roster in YAML, verified Week 1, snapshot dates recorded |
| **⚠️ LiveCodeBench contamination is uncontrolled** | LCB stopped updating (newest problem 2025-04-06); every roster model is a 2026 release, so there is no post-cutoff window. **Mitigation is honesty, not filtering:** `problems.release_date` stores every contest date, the limitation is reported explicitly, and LCB is positioned as a *difficulty* tier rather than a contamination control. A suspiciously high pass rate on LCB hard problems should be read as possible memorisation |
| **🔴 `max_tokens` confounds the effort axis** | On LCB hard, **7 of 16 thinking calls hit the 16,000-token ceiling and returned no answer**; on LCB medium, 4 of 12. Reasoning-high therefore scores *below* reasoning-off on hard problems (31% vs 50%), which measures truncation rather than capability. Two honest options, and the choice must be explicit: raise the ceiling (costs more, measures capability) or keep it and report "fails to terminate within budget" as a genuine property of the config (defensible — real deployments have budgets). **Currently unresolved; it must be settled before the grid.** |
| **The LCB grader has no reference implementations to check itself against** | evalplus ships canonical solutions; LCB ships none, so `test_canonical_solutions_pass` has no LCB equivalent. Replaced by hand-written reference solutions in `tests/test_verify_lcb.py`, covering both execution styles. Without them an LCB harness bug would read as "all models fail hard problems" |
| Effort control differs across models | `effort_mechanism` logged as a variable; report split by mechanism |
| CARR shows no gain | RQ1–RQ3 stand alone (proposal §8 already says this). The gap decomposition turns a null result into a diagnostic one |
| Generated code damages your machine | evalplus `untrusted_check` (subprocess + `reliability_guard`), tested Day 3 — **not Docker**, which was reversed on Day 3. Note evalplus's own docstring says it "is NOT a security sandbox": it contains accidents and casual hostility, not a determined adversary |
| **A silent grader or extractor bug corrupts every number** | `test_canonical_solutions_pass` — a reference solution that fails means the harness is broken, not the model. This is what caught the macOS `setrlimit` bug. It has also been run at scale (210 canonical solutions, both benchmarks, all PASS) before the fixture was retired |
| Paying twice for the same generation | `request_hash UNIQUE`, **proven working** by `tests/test_db.py` and by a 360-row re-run that inserted 0 |
| Non-purchased rows leaking into results | `generations.is_mock`; `db.summary()` computes spend with `is_mock = 0`. `init_db.py --reset` refuses to run when paid rows exist |
| **Losing the database to a careless edit** | `scripts/studio.py` snapshots the whole file to `data/backups/` before its first write of each session, and its SQL console is on a read-only connection. `--read-only` disables writing entirely |
| Python 3.14 breaks dependencies | Pin 3.12 on Day 1 |
| **Novelty erosion** — 2026 work (HRBench, Route-To-Reason, DART) already occupies much of the claimed gap | Re-position to the *cheapest-possible-router* claim (§15.3); benchmark against DART/RTR rather than RouteLLM; read those papers before writing more. **The empirical table remains ours regardless** |

---

## §12. Decisions log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-25 | OpenRouter as sole backend | One key, one schema vs. 6 accounts and 6 adapters |
| 2026-07-25 | ~~Budget cap $100~~ → **$50 hard cap, $30 target** | User constraint, revised down. Grid re-fitted: 514 → 434 problems, 10 → 9 configs |
| 2026-07-25 | Cut problems, not grid cells | The routing label is "cheapest config that passes", which needs every problem × every config. A sparse grid destroys CARR's ground truth |
| 2026-07-25 | Dropped DeepSeek-Flash Think-Max | Most redundant expensive cell — Flash Think-High and Pro's modes already cover that frontier region |
| 2026-07-25 | **GLM-5.1 dropped** | User decision. Roster → 3 families |
| 2026-07-25 | Kimi held out for RQ5 | Only non-DeepSeek/Qwen family → most honest OOD test |
| 2026-07-25 | Formal section included | Proposal had zero formal content; hull baseline also fixes RQ4 |
| 2026-07-25 | MBPP 500 → 200, LCB 200 → 150 | Extra problems buy nothing; budget better spent on the hard tier |
| 2026-07-25 | n=1, temperature=0 | Halves cost *and* makes routing labels deterministic |
| 2026-07-25 | Thin vertical slice before architecture | Avoids a clean design that has never made an API call |
| 2026-07-25 | Generate our own table; don't hunt for an existing one | No published dataset has (model × thinking-mode) on code with reasoning-token cost. Problems are free; the table is the contribution (§15.1) |
| 2026-07-25 | Prototype CARR on RouterBench/HRBench data first | Debugs the router at $0 while our own grid runs; removes the Week 6–7 risk (§15.2) |
| 2026-07-25 | Roster verified; `kimi-k2.7-code` rejected | $3.50/M output — one thinking config over the full grid would exceed the whole budget. `kimi-k2.6` ($2.72) is the held-out model instead |
| 2026-07-25 | Held-out model runs on a **subset**, not the full grid | RQ5 asks whether CARR transfers to an unseen model; that needs no full coverage, and full coverage would cost more than every other config combined |
| 2026-07-25 | Effort pairs hold the **model constant** | `qwen3.5-9b` off/high rather than two different small models — within a pair only the thinking mode varies, so the effort axis is unconfounded |
| 2026-07-25 | Cost reconciliation is **batched, not per-call** | `/generation` needs ~10s to settle; blocking on it would add hours to the grid run |
| 2026-07-25 | **Re-position the novelty claim** | 2026 work already occupies the joint-axis and training-free gaps. New claim: *cheapest possible router* — no forward pass, no drafts, no hidden states, no training (§15.3) |
| 2026-07-26 | **Build the pipeline against a mock provider before the real one** | Everything downstream of the API call (extraction, grading, schema, viewers) can be exercised for $0. Only the paid call is faked, so the pilot's first dollar is spent on a path that already works. It also turned the seeder into a mass-scale canonical-solution check |
| 2026-07-26 | `generations.is_mock` + `mock_mode` as real columns | A seeded row and a $0.0006 purchased row are otherwise indistinguishable. `mock_mode` is what lets the seeder assert every *canonical* row passed |
| 2026-07-26 | `results.base_passed` added; `error_type` narrowed to `assertion`/`timeout` | `grade()` already produces `base_passed` and *never* produces `syntax`/`exception`. The schema now matches the code exactly rather than an aspiration |
| 2026-07-26 | Terminal viewer named `view.py`, **not** `inspect.py` | A script named `inspect.py` shadows the stdlib module for every other script in `scripts/`, and it broke the seeding run silently |
| 2026-07-26 | `--in-tokens` default 600 → **100** | 600 was a pre-Day-2 guess; Day 2 measured medians of 99 (HE+) and 36 (MBPP+). Two docs carried mutually inconsistent grid costs derived from the two values. Grid is **$3.55**, single-sourced from the script |
| 2026-07-26 | Exact prices in the roster (`0.0938/0.1876`) rather than rounded | `cost_computed_usd` is compared against `cost_actual_usd` to detect silent price drift; a 0.2% rounding error would read as permanent drift |
| 2026-07-26 | **`request_hash` now includes `problem_id`** | Two problems sharing a prompt collided: the second silently got no generation, no result and no routing label. CARR's target is "cheapest config that passes *this* problem", which needs every problem run through every config, so the hole would have been invisible. Zero collisions in the current pool, so the fix costs nothing; existing rows were migrated in place, not re-bought |
| 2026-07-26 | The cap is checked against **lifetime** spend, not per-run | Five runs that each respect their own limit still empty the account |
| 2026-07-26 | Cheapest-first ordering is **global**, across problems, not per problem | If the cap fires, the result is a complete cheap foundation rather than a random half of every problem |
| 2026-07-26 | `retries: 0` in `experiment.yaml` | A retry loop is how a cost cap gets defeated. A failed call is recorded and skipped; re-running the script picks it up |
| 2026-07-26 | **LiveCodeBench adopted as a difficulty tier, and its contamination claim dropped** | The saturation finding made a hard tier load-bearing, and LCB is the only source of one. But its contamination-resistance depends on release-date filtering, and there is no post-cutoff window left: it stopped updating in 2025, our models are 2026. Reporting the exposure is the only honest option |
| 2026-07-26 | LCB grading lives in `verify.py` as a **second path**, not a second module | CLAUDE.md keeps grading in one file. Nothing is shared with the evalplus path — no canonical solutions, no `atol`, no special oracles, and two execution styles — so it is a branch in `grade()` rather than an abstraction over both |
| 2026-07-26 | LCB stdin problems get one added sentence about reading stdin | The statement alone does not say how the program receives input, so the task is not well-posed. It is a constant string, identical across every config, so it cannot confound the effort axis — but it *is* a documented deviation from "send the prompt unmodified" |
| 2026-07-26 | One subprocess per (problem, config), not per test | 175 problems × ~43 tests × 10 configs would be 75,000 interpreter startups. The cost is that one non-terminating test times out the whole problem, which is what evalplus already does |
| 2026-07-26 | **Kimi held-out model gets BOTH effort levels** (roster 9 → 10 configs, +$0.10) | `subset_only` is a cut to the number of *problems*, not to the effort axis. With one effort kimi had a single point on the cost-accuracy plane and no measurable thinking delta, so RQ5 would have tested transfer along the model axis only. The `off` half is the cheap one — no thinking, ~350 output tokens |
| 2026-07-26 | Run order is by **expected** cost; `config_id` stays ordered by output price | They differ: `off` and `high` share a per-token price but burn ~10× different token counts. `config_id` is an identity that must never move; run order is a budget policy that should |
| 2026-07-26 | The cost cap aborts on **worst case** (`max_tokens` × output price), not expected case | An expected-case cap is not a cap. `run_one.py` computes the worst case for every cell before sending anything, and refuses the whole invocation if it exceeds `--max-usd` |
| 2026-07-26 | **Mock rows and the mock machinery deleted once they had paid for themselves** | They proved the chain, the dedup and the grader across 542 problems. Keeping fake rows beside real ones in the scientific asset is a standing hazard, and `is_mock` is a guard against a mistake that no longer needs to be possible. Recoverable from commit `f3da6ff` if offline runner tests are wanted later |
| 2026-07-26 | Studio is a **local server**, not a static page | A `file://` page cannot write to SQLite, and the ask was to edit and delete rows. Stdlib `http.server`, loopback only, no auth and no new dependency |
| 2026-07-26 | **Auto-snapshot before every write**, and a read-only SQL console | `generations` cannot be rebuilt without paying again, so a delete button on it needs an undo. `data/backups/` keeps the last 10 |
| 2026-07-26 | Studio introspects the schema per request rather than hardcoding CARR's tables | The schema will change when `features` and `router_runs` land, and a browser that needs editing every time the schema moves would simply not be used |
| 2026-07-26 | `scripts/verify_roster.py` finally written | Four files instructed the reader to run it and it had never existed — the roster was verified by hand and only the result committed. §9 requires re-verification before the grid, which needs a script that exists |

---

## §13. Glossary

| Term | Meaning |
|---|---|
| **Configuration / config** | One (model, thinking-setting) pair. ~10 of them. The thing CARR chooses between |
| **Effort / thinking mode** | How much the model reasons before answering. Native switch where available; otherwise a token cutoff |
| **Budget forcing** | Faking an effort level by hard-capping reasoning tokens, for models with no native switch |
| **pass@1** | Did the model's single attempt pass all tests? Your accuracy metric |
| **CPC** | Cost-Per-Correct-answer = total $ ÷ number solved. Headline economic metric |
| **TPC** | Tokens-Per-Correct-answer. Same idea, token-denominated |
| **Pareto frontier** | Configs where you can't get cheaper without losing accuracy. The rest are *dominated* — strictly worse |
| **Convex hull** | The frontier you get by *mixing* two configs. The correct baseline (§10.1) |
| **Oracle** | A cheat that always knows the cheapest passing config. Upper bound; not a real method |
| **k-NN** | For a new problem, find the *k* most similar known problems and copy what worked for them |
| **Contamination** | When a benchmark problem was in a model's training data — it "remembers" rather than solves. Why LiveCodeBench is date-filtered |
| **Saturation** | When a benchmark is too easy for modern models, so all configs score the same and comparison is meaningless (§11) |

---

## §14. Edits required to the .docx before submission

1. **§6.1** — remove GLM-5.1; state **three families / five open-weight models**; acknowledge the within-family caveat
2. **§1, §4-RQ4** — comparison target becomes **the convex hull of the frontier**, not "strongest single configuration"
3. **§5.3** — note CARR-oracle is the MCKP integer optimum, not an ad-hoc ceiling
4. **§6.2** — MBPP 500 → **150**; LiveCodeBench 200 → **120** hard/medium-weighted, with rationale (a $50 inference budget; state it plainly — budget-constrained sampling is normal and honest)
5. **§6.3** — CPC/TPC reported with bootstrap confidence intervals
6. **§8** — add benchmark saturation to the risk table; cite [When Routing Collapses](https://arxiv.org/pdf/2602.03478), which names the phenomenon
7. **§3 — rewrite the gap analysis (biggest edit owed).** Add Route-To-Reason, DART, HRBench, LLMRouterBench. Re-position from "first joint (model × effort) router" to "the cheapest possible router" (§15.3)
8. **§1, §9** — drop "first systematic evaluation"; HRBench (May 2026) covers much of that ground
9. **⚠️ Wherever LiveCodeBench is cited for contamination resistance — rewrite it.** The property does not hold: LCB's newest problem is 2025-04-06, the dataset stopped updating 2025-06-05, and every roster model is a 2026 release. Re-position LCB as the *difficulty* tier that keeps RQ4 from degenerating, and state the contamination exposure as a limitation with the `release_date` distribution to back it up (§9, §11)
10. **§6.2 problem counts** — the pool is **717** (HumanEval+ 164, MBPP+ 378, LCB 175); the *run* set is ~300 and is set by the pilot. State pool and sample separately; the current text conflates them
11. **§6.2 / methods** — note that LCB problems are graded by a second harness (stdin→stdout and `Solution`-method execution) with hand-written reference solutions, because LCB ships no canonical implementations

---

## §15. Prior art and external datasets (checked 2026-07-25)

### 15.1 Where the data comes from

| Component | Source | Cost |
|---|---|---|
| The 434 problems + their tests | Download: `evalplus` (HumanEval+/MBPP+), LiveCodeBench on HuggingFace | **$0** |
| **The table** (model × effort → pass/fail, tokens, cost) | **Generated by us via the OpenRouter API** | ~$20–28 |

We never author problems. But nobody has published our table, because nobody has run *(model × thinking-mode)* on code while measuring reasoning-token cost per problem. **Generating it is the thesis's empirical contribution.**

### 15.2 Existing datasets we can exploit for free

| Dataset | Contents | Use |
|---|---|---|
| [RouterBench](https://ar5iv.labs.arxiv.org/html/2403.12031) | 405k outcomes, 11 models, per-query cost, incl. HumanEval/MBPP. Already uses **convex-hull evaluation** | $0 prototyping; confirms our hull baseline (§10.1) is standard practice, not novel |
| [LLMRouterBench](https://arxiv.org/html/2601.07206v1) | 33 models, 21 datasets, 400k instances, released. **Explicitly no effort axis** | $0 prototyping; cite as the model-only baseline |
| [HRBench](https://github.com/usail-hkust/HRBench) | 6 models × 5 benchmarks incl. code, 12 switching settings, data + code released | Free comparison point — **and a novelty threat, see 15.3** |
| EmbedLLM | Per-question model correctness vectors | The RQ5 held-out-model mechanism |
| **[CodeRouterBench](https://huggingface.co/datasets/Lance1573/CodeRouterBench)** (Jun 2026, MIT, ungated) | **9,999 code tasks × 8 models = 79,992 rows** with `score`, `cost_usd`, input/output tokens, latency. 9 task dimensions; sources include LCB, BigCodeBench, MBPP, HumanEval, SWE-bench, DS-1000. Has its own OOD split (176 tasks) | **The best free prototyping target we have found** — code-specific, 2026, and shaped exactly like our own table. Build and debug `router/knn.py` against this for $0. **Also prior art: see 15.3** |

> **Action (Week 6):** build and debug `router/knn.py` against RouterBench or HRBench data **while our own grid is still running**. Removes the Week 6–7 risk at zero cost.

### 15.3 ⚠️ The proposal's §3 gap analysis is ~12 months stale

The proposal cites RouteLLM (2025), Universal Routing (2025), Budget Guidance (2026), AnytimeReasoner (2025). Four much closer works have appeared:

| Work | Why it threatens our claim |
|---|---|
| [Route-To-Reason](https://arxiv.org/html/2505.19435v1) (May 2025) | "Dynamically allocates **both language models and reasoning strategies**… under budget constraints." This *is* our joint (model × effort) claim, and it predates the proposal |
| [DART](https://arxiv.org/html/2606.23181v1) (Jun 2026) | "**Training-Free** Adaptive Thinking Budgets", text-only API access — our training-free, provider-agnostic angle |
| [HRBench](https://arxiv.org/html/2605.28398v1) (May 2026) | 6 models × 5 benchmarks **including code**, 12 controlled switching settings — substantially covers RQ1–RQ3 |
| [When Routing Collapses](https://arxiv.org/pdf/2602.03478) (Feb 2026) | Names our saturation risk (§11) as a published phenomenon: routers degenerating to always picking one model |
| **[Agent-as-a-Router / CodeRouterBench](https://arxiv.org/abs/2606.22902) (Jun 2026)** | **The closest work yet, and it must be cited.** Routing for *coding* tasks, 8 backends, released task×model matrix with per-call cost. Nearest neighbour to RQ1–RQ4 |

**What CodeRouterBench does NOT have — checked against the released data, 2026-07-26.** Its `model` column holds eight *model names* and nothing else: `claude-opus-4-6`, `claude-sonnet-4-6`, `gpt-5.4`, `glm-5`, `kimi-k2.5`, `MiniMax-M2.7`, `Qwen3-Max`, `qwen3.5-plus`.

1. **No effort axis at all.** One row per (task, model). No thinking-mode dimension, so no model appears twice at different reasoning budgets. Our whole effort axis is absent.
2. **No reasoning-token column.** Columns are `input_tokens`, `output_tokens`, `total_tokens` — the field Day 1 showed carries 95% of a thinking call's cost is simply not recorded.
3. **Closed-weight backends**, where our roster is open-weight.
4. **Their router is trained** — the release ships a LoRA adapter (`acrouter-qwen35-08b-router-lora`).

So the nearest 2026 work sharpens our claim rather than displacing it: they route *between models*, we route *between (model × thinking-mode) pairs*, training-free, with reasoning tokens priced.

**What still survives.** DART must *generate draft answers* to route, so it is not pre-inference and it costs tokens. RTR appears to require training. CodeRouterBench has no effort axis and no reasoning-token accounting. None is feature-only over the joint axis. The defensible niche is narrower but real:

> **The cheapest possible router — no forward pass, no drafts, no hidden states, no training — evaluated on code, jointly over model and effort.**

A "how far can a nearly-free router get?" claim, benchmarked against **DART and RTR**, not RouteLLM.

**Confidence:** based on search summaries and PDF extraction, not full reads. Existence and rough scope are reliable; precise claims are not.

**Owed before writing more:**
- [ ] Read **HRBench** and **Route-To-Reason** in full — they decide how much re-positioning is needed
- [ ] Check whether RTR is genuinely training-based (if so, our training-free angle holds)
- [ ] Check whether HRBench does *joint* model+effort or effort-switching per model
- [ ] **Read Agent-as-a-Router ([arXiv 2606.22902](https://arxiv.org/abs/2606.22902)) in full** — closest prior art, June 2026, and its data is free
- [ ] Prototype `router/knn.py` on CodeRouterBench while our own grid runs (§15.2)
- [ ] **Raise with the advisor** — a stale gap analysis is what gets flagged at defense

---

## §16. How to maintain this document

At the end of each session:
1. Update **§1** — stage, next action, spend, row count, blockers
2. Add a dated line to the **§1 recent log**
3. Tick boxes in **§5** (⬜ → 🟨 → ✅)
4. Log any decision in **§12**, with its reason
5. Update whichever of §4 / §7 / §8 / §9 / §11 / §13 / §14 / §15 the work touched
6. Check numbers are consistent everywhere:
   ```bash
   grep -rn '\$50\|\$4\.00\|300 problems\|2,600\|10 config\|\$3\.55' \
     THESIS.md README.md CLAUDE.md docs/
   ```
7. Commit

[CLAUDE.md](CLAUDE.md) §1 holds the full table of what to update when — it is
binding on any AI assistant working in this repo.

**If a fact lives in two places, this file wins.** §12 is the one exception:
it is append-only history, so superseded values stay there struck through.
