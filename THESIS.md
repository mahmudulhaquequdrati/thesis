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
| **Stage** | Week 1, Day 1 — scaffold done, awaiting API key |
| **Next action** | **You:** create an OpenRouter account, load ~$10, put the key in `.env`. Then `uv run python scripts/day1_hello.py` |
| **Spend to date** | $0.00 of **$50.00 hard cap** (target: finish under $30) |
| **Rows in dataset** | 0 of ~3,906 |
| **Blocked on** | OpenRouter API key (only you can create it) |

**Recent log**
- `2026-07-25` — Proposal analysed. GLM dropped from roster. Decisions locked (§12). Master doc created.
- `2026-07-25` — Day 1 scaffold: `uv` project on **Python 3.12.13** (system 3.14.3 avoided), `git init`, `openai` + `python-dotenv` installed, `.env` gitignored, `scripts/day1_hello.py` written. Verified working. Waiting on the key to make the first call.
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
| **LiveCodeBench** | Hard, recent competitive problems | Contamination-resistant (filter by release date). **The hard tier that makes RQ4 non-trivial** |
| **Docker** | Sandbox | Generated code is untrusted — will contain infinite loops, `os.system`, file writes. No network, memory cap, timeout |
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
| 🟨 | 1 | Toolchain + one API call | A model's text prints in your terminal — *scaffold done; needs your API key* |
| ⬜ | 2 | Load real benchmark problems | You can print any HumanEval+ problem's prompt and tests |
| ⬜ | 3 | Sandboxed grader | Good code → ✅, bad code → ❌, `while True: pass` → timeout |
| ⬜ | 4 | Connect the pieces | One line prints: `reverse_string \| qwen \| off \| PASS \| 180 tok \| $0.0001` |
| ⬜ | 5 | Save to SQLite | 40 rows queryable: 10 problems × 2 models × 2 settings |
| ⬜ | 5 | `verify_roster.py` | Confirmed list of models that actually exist, with real prices |

### Weeks 2–12
| | Week | Milestone | Spend |
|---|---|---|---|
| ⬜ | 2 | Widen harness: all loaders, all configs, resumability, cost cap, echo tests | $0 |
| ⬜ | 2 | Pilot: 10 problems × 3 configs → real costs + **saturation check** | ~$2 |
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

```
thesis/
├── THESIS.md                   # ← this file, the source of truth
├── CLAUDE.md                   # working rules: doc-update ritual, budget discipline
├── README.md
├── Thesis_Project_Proposal.docx
├── pyproject.toml              # uv, pinned to Python 3.12
├── .env                        # OPENROUTER_API_KEY (gitignored)
├── config/
│   ├── models.yaml             # roster: slug, family, effort params, prices, snapshot date
│   ├── benchmarks.yaml         # sample sizes, seeds, LCB release window
│   └── experiment.yaml         # grid, temperature, max_tokens, HARD COST CAP
├── carr/
│   ├── db.py                   # schema + idempotent upsert
│   ├── providers/
│   │   ├── openrouter.py       # the only real adapter
│   │   └── echo.py             # fake provider — exercises the pipeline at $0
│   ├── effort.py               # native thinking-modes vs. prompt budget-forcing
│   ├── benchmarks/             # humaneval_plus / mbpp_plus / livecodebench loaders
│   ├── execute/                # sandbox.py (Docker) + verify.py
│   ├── runner.py               # resumable, cost-capped grid loop
│   ├── cost.py                 # tokens → USD, reconciled against real charges
│   ├── features.py             # lexical / structural / embedding features
│   ├── router/                 # rules.py, knn.py, oracle.py
│   └── analysis/
│       ├── pareto.py           # frontier + CONVEX HULL baseline (§10.1)
│       ├── knapsack.py         # MCKP oracle + LP bound
│       ├── stats.py            # bootstrap CIs for CPC/TPC
│       ├── evaluate_router.py  # RQ4–RQ5 + gap decomposition
│       └── figures.py          # PNGs for Word
├── scripts/
│   ├── verify_roster.py
│   ├── pilot.py
│   ├── run_grid.py
│   └── make_report.py
├── data/carr.sqlite
└── tests/
```

---

## §8. Database schema

```sql
problems(problem_id PK, benchmark, difficulty, prompt, tests_blob, entry_point, release_date)

configs(config_id PK, model_slug, family, snapshot_date, effort_label, effort_mechanism,
        params_json, price_in_per_m, price_out_per_m)

generations(gen_id PK, problem_id, config_id,
            request_hash UNIQUE,          -- ← resumability lives here
            raw_response, extracted_code,
            prompt_tokens, completion_tokens, reasoning_tokens,
            cost_computed_usd, cost_actual_usd, latency_ms, error, created_at)

results(gen_id PK FK, passed, n_tests_passed, n_tests, exec_ms, error_type)

features(problem_id PK, feature_json, embedding BLOB)

router_runs(run_id PK, variant, scenario, k, split_seed, problem_id, chosen_config_id, ...)
```

**Four design decisions that matter:**

- **`request_hash UNIQUE`** over `(model, effort, prompt, params)`. Checked before every API call; if present, skip. Crash at row 3,000 and restarting costs **$0** for the first 3,000. Every generation is money — never pay twice.
- **`effort_mechanism`** is a column, not a comment. Native thinking-modes and prompt budget-forcing are *not* equivalent (proposal §8 says so). Results must split by mechanism or the effort axis is confounded.
- **`family`** — lets you separate within-family from cross-family routing gains, which matters now the roster is only three families.
- **`raw_response` stored verbatim.** Your code-extraction logic will have bugs. Keeping raw responses lets you re-grade offline for free instead of re-buying 5,000 generations.

---

## §9. The experiment

### Roster — 3 families, 5 open-weight models + 1 closed reference

| Model | Role | Effort control |
|---|---|---|
| Qwen3.6-small (non-think) | Cheapest tier / no-reasoning baseline | N/A |
| Qwen3.6 | Cheap baseline, permissive licence | Native thinking toggle |
| DeepSeek-V4-Flash | Cost-efficient reasoner, mid tier | Native: Non-think / Think-High (**Think-Max dropped — see below**) |
| DeepSeek-V4-Pro | Frontier open-weight reasoner | Native thinking modes |
| Kimi K2.6 / K2.7-Code | Coding specialist | Budget-forcing (verify at build time) |
| 1 closed small-tier model | Closed reference point | Native effort param if available |

→ **9** (model × effort) configurations.

**Cut for the $50 budget:** DeepSeek-V4-Flash Think-Max. Flash's Think-High and Pro's thinking modes already cover that region of the frontier, so the dropped cell is the most redundant expensive one — the effort axis still spans off → low → high → max across the roster as a whole.

**⚠️ No model name may be hardcoded anywhere.** These names cannot be confirmed without querying the live API — proposal §6.1 notes 6–8 week churn. The roster lives in `config/models.yaml`, validated against OpenRouter's live `/models`, every row carrying a snapshot date.

**Two consequences of dropping GLM:**
- The abstract's "five or more open-weight models" is now true but spans only **three families**. Say so explicitly in the .docx rather than letting an examiner raise it.
- **Hold out Kimi entirely for RQ5** — it's the only non-DeepSeek/Qwen family, so it's the most genuinely out-of-distribution test available. Stronger than holding out a second DeepSeek.

### Problems — 434 total
- **HumanEval+** — all 164 (easy anchor; short outputs, so it's the cheapest tier per problem)
- **MBPP+** — 150 sampled, fixed seed (proposal said 500 — the extra 350 buy nothing)
- **LiveCodeBench** — 120, post-cutoff release window, weighted to hard/medium

**Why not sparsify instead?** Tempting, but no: the routing label is *"cheapest config that passes this problem"*, which is only computable if **every** problem has been run through **every** config. A sparse grid breaks CARR's ground truth. So the budget is cut by reducing *problems*, never by skipping cells.

### Sampling
One sample per problem, `temperature=0` where honoured. Biggest cost lever, and it makes the "cheapest passing config" label deterministic instead of noisy. **Log the actual temperature** — some thinking endpoints silently override it.

### Budget — $50 hard cap, $30 target

434 problems × 9 configs = **~3,906 generations**. Non-think ≈ 400 output tokens; think-max on LiveCodeBench ≈ 6–8k.

| Phase | Allocated | Notes |
|---|---|---|
| Week 1 thin slice | $2 | 40 rows, cheap models only |
| Roster verification | $0.50 | A few tokens per candidate model |
| Week 2 pilot | $2 | 10 problems × 3 configs → real cost numbers |
| **Full grid** | **$18–28** | The main spend |
| Contingency / reruns | remainder | Bugs *will* force a partial re-run |
| **Hard cap** | **$50** | Runner aborts on breach |

Treat $18–28 as a guess until the Week-2 pilot measures it. If the pilot projects over **$28**, cut MBPP+ to 100 before running anything else.

### Four cost controls (build these into `runner.py`)

1. **Hard cap that aborts.** `experiment.yaml` holds `max_spend_usd: 50` and `warn_at_usd: 30`. The runner tracks cumulative spend and *stops* — it does not warn and continue.
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

### Other risks

| Risk | Mitigation |
|---|---|
| Budget overrun | **$50 hard cap** in `experiment.yaml` that *aborts* the run (not warns); `max_tokens` ceiling per config so no single trace runs away; cheapest configs first, so a blowout costs the expensive tail not the cheap foundation; `request_hash` prevents ever paying twice |
| Model deprecation mid-project | Roster in YAML, verified Week 1, snapshot dates recorded |
| Effort control differs across models | `effort_mechanism` logged as a variable; report split by mechanism |
| CARR shows no gain | RQ1–RQ3 stand alone (proposal §8 already says this). The gap decomposition turns a null result into a diagnostic one |
| Generated code damages your machine | Docker sandbox, tested Day 3 |
| Python 3.14 breaks dependencies | Pin 3.12 on Day 1 |

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
6. **§8** — add benchmark saturation to the risk table

---

## §15. How to maintain this document

At the end of each session:
1. Update **§1** — stage, next action, spend, row count, blockers
2. Add a dated line to the **§1 recent log**
3. Tick boxes in **§5** (⬜ → 🟨 → ✅)
4. Log any decision in **§12**, with its reason
5. Update whichever of §4 / §7 / §8 / §9 / §11 / §13 / §14 the work touched
6. Check numbers are consistent everywhere:
   ```bash
   grep -n '\$50\|434\|3,906\|9 config' THESIS.md README.md CLAUDE.md
   ```
7. Commit

[CLAUDE.md](CLAUDE.md) §1 holds the full table of what to update when — it is
binding on any AI assistant working in this repo.

**If a fact lives in two places, this file wins.** §12 is the one exception:
it is append-only history, so superseded values stay there struck through.
