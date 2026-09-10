# References {.unnumbered}

::: {#refs}
:::

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix A: Database schema {.unnumbered}

The authoritative schema is `carr/db.py`. Reproduced verbatim.

```sql
-- One row per benchmark problem. Free to rebuild from evalplus.
CREATE TABLE IF NOT EXISTS problems (
    problem_id    TEXT PRIMARY KEY,      -- task_id, e.g. 'HumanEval/0'
    benchmark     TEXT NOT NULL,         -- humaneval_plus | mbpp_plus | livecodebench
    difficulty    TEXT,                  -- LCB provides this; NULL for HE+/MBPP+
    prompt        TEXT NOT NULL,         -- sent to the model VERBATIM
    entry_point   TEXT NOT NULL,         -- function the tests call
    n_tests       INTEGER NOT NULL,      -- base + plus
    prompt_chars  INTEGER NOT NULL,
    n_base_tests  INTEGER NOT NULL,
    n_plus_tests  INTEGER NOT NULL,
    release_date  TEXT                   -- LCB only; contest date, for reporting exposure
);

-- One row per (model x effort), from config/models.yaml.
CREATE TABLE IF NOT EXISTS configs (
    config_id        INTEGER PRIMARY KEY,
    model_slug       TEXT NOT NULL,
    family           TEXT NOT NULL,
    effort_label     TEXT NOT NULL,      -- off | high
    effort_mechanism TEXT NOT NULL,      -- native_toggle | budget_forcing (not equivalent)
    params_json      TEXT NOT NULL,      -- the exact `reasoning` block sent
    price_in_per_m   REAL NOT NULL,
    price_out_per_m  REAL NOT NULL,
    snapshot_date    TEXT NOT NULL,
    held_out         INTEGER NOT NULL DEFAULT 0,
    subset_only      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (model_slug, effort_label)
);

-- One row per API call. THE MONEY TABLE. Unrebuildable without paying again.
CREATE TABLE IF NOT EXISTS generations (
    gen_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id         TEXT NOT NULL REFERENCES problems(problem_id),
    config_id          INTEGER NOT NULL REFERENCES configs(config_id),
    request_hash       TEXT NOT NULL UNIQUE,   -- checked BEFORE every call
    openrouter_gen_id  TEXT,             -- for batched cost reconciliation
    raw_response       TEXT,             -- verbatim; enables free offline re-grading
    extracted_code     TEXT,
    prompt_tokens      INTEGER,
    completion_tokens  INTEGER,
    reasoning_tokens   INTEGER,          -- SUBSET of completion_tokens; never add twice
    cost_computed_usd  REAL,             -- tokens x the price table
    cost_actual_usd    REAL,             -- GET /generation total_cost
    finish_reason      TEXT,             -- stop | length | error
    latency_ms         INTEGER,
    temperature_sent   REAL,
    error              TEXT,             -- NULL on success
    is_mock            INTEGER NOT NULL DEFAULT 0,
    mock_mode          TEXT,
    created_at         TEXT NOT NULL
);

-- One row per graded generation. Free to regenerate from raw_response.
CREATE TABLE IF NOT EXISTS results (
    gen_id         INTEGER PRIMARY KEY REFERENCES generations(gen_id),
    passed         INTEGER NOT NULL,   -- survived BOTH base and plus tests
    base_passed    INTEGER NOT NULL,
    n_tests_passed INTEGER NOT NULL,
    n_tests_total  INTEGER NOT NULL,
    error_type     TEXT CHECK (error_type IN ('assertion', 'timeout')),
    exec_ms        INTEGER
);
```

The `request_hash` is a SHA-256 over the JSON serialisation of (model slug, effort label, prompt, effort parameters with sorted keys, problem id). Tests confirm it changes when any component changes and cannot be confused by concatenation.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix B: Configuration files {.unnumbered}

## B.1 The roster (`config/models.yaml`, abridged) {.unnumbered}

```yaml
snapshot_date: "2026-07-26"
verified_against: "https://openrouter.ai/api/v1/models"
models:
  - slug: qwen/qwen3.5-9b
    provider: deepinfra/bf16
    family: qwen
    price_in_per_m: 0.100
    price_out_per_m: 0.150
    context_length: 262144
    efforts:
      - {label: "off",  mechanism: native_toggle, params: {reasoning: {enabled: false}}}
      - {label: "high", mechanism: native_toggle, params: {reasoning: {effort: "high"}}}
  - slug: deepseek/deepseek-v4-flash
    provider: baidu/fp8
    family: deepseek
    price_in_per_m: 0.091
    price_out_per_m: 0.182
    context_length: 1048576
    efforts: [same two settings]
  - slug: qwen/qwen3.6-35b-a3b
    provider: akashml/fp8
    family: qwen
    price_in_per_m: 0.140
    price_out_per_m: 1.000
    context_length: 262144
    efforts: [same two settings]
  - slug: deepseek/deepseek-v4-pro
    provider: baidu/fp8         # DeepSeek's own endpoint ($0.870, unquantized) is blocked by the account's data policy
    family: deepseek
    price_in_per_m: 0.625
    price_out_per_m: 1.251
    context_length: 1048576
    efforts: [same two settings]
held_out:
  - slug: moonshotai/kimi-k2.6
    provider: siliconflow/fp8
    family: moonshot
    subset_only: true
    price_in_per_m: 0.770
    price_out_per_m: 3.400
    context_length: 262144
    efforts: [same two settings]
rejected:
  - {slug: moonshotai/kimi-k2.7-code, reason: "$3.50/M output; one thinking config over the grid exceeds the budget"}
  - {slug: qwen/qwen-2.5-7b-instruct, reason: "no reasoning support; qwen3.5-9b with reasoning off is a better baseline"}
  - {slug: z-ai/glm-5.1, reason: "dropped by decision 2026-07-25"}
```

## B.2 The experiment (`config/experiment.yaml`, abridged) {.unnumbered}

```yaml
budget:
  max_spend_usd: 50.00      # the ceiling from CLAUDE.md
  loaded_usd: 15.00         # on the account
  abort_at_usd: 6.00        # where the runner stops, permanently, across every run
  warn_at_usd: 3.00
  run_headroom: 1.25        # a run stops at 1.25x its own estimate
generation:
  temperature: 0.0
  n: 1
  max_tokens: {"off": 16000, "high": 48000}   # keys quoted: YAML 1.1 parses bare `off` as False
  retries: 0
  rate_limit_retries: 3     # 429s are billed $0, so retrying them cannot defeat the cap
  concurrency: 24
  grade_concurrency: 6
abort:
  reasoning_tokens: null    # off while building the dataset; a threshold chosen on the same data is fitted
expected_completion_tokens: {"off": 3165, "high": 4134}   # MEASURED from 1,132 calls; used only for ordering and estimates
sampling:
  seed: 20260726
  held_out_subset: 100
  pilot: {strata: {humaneval_plus: 3, mbpp_plus: 3, livecodebench_easy: 2, livecodebench_medium: 3, livecodebench_hard: 4}}
  grid:  {strata: {humaneval_plus: 20, mbpp_plus: 20, livecodebench_easy: 20, livecodebench_medium: 104, livecodebench_hard: 154}}
```

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix C: Reproducing every number {.unnumbered}

Nothing below spends money unless marked.

```bash
uv sync                                   # Python 3.12 environment
uv run pytest                             # 132 tests, about two minutes
uv run python scripts/init_db.py          # problems + configs from free sources (idempotent)
uv run python scripts/verify_roster.py    # roster vs the live model listing; exits non-zero on drift
uv run python scripts/results.py          # every number in Chapters 5-7, from data/carr.sqlite
uv run python scripts/make_figures.py     # the eight figures into data/figures/
uv run python scripts/view.py --list      # every problem, one line each
uv run python scripts/view.py HumanEval/0 # one problem across all configurations
uv run python scripts/studio.py           # local database browser at http://127.0.0.1:8787

# Reproducibility check: byte-identical output
uv run python scripts/results.py > /tmp/a.txt && uv run python scripts/results.py > /tmp/b.txt && diff /tmp/a.txt /tmp/b.txt && echo IDENTICAL

# Spends money (always dry-run first):
uv run python scripts/pilot.py --set grid --dry-run
uv run python scripts/pilot.py --set grid --yes
```

The database `data/carr.sqlite` is the scientific asset. It is not in version control and must be backed up separately; `data/backups/` holds automatic pre-write snapshots taken by the browser.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix D: Test inventory {.unnumbered}

132 tests, all passing on 2026-09-11 (`uv run pytest`, 132 seconds). Grouped by the failure each group prevents.

| File | n | What is proved |
|---|---|---|
| `tests/test_verify.py` | 8 | Correct code passes; wrong code fails; an infinite loop times out cleanly; a syntax error fails without crashing; hostile code (`os.system`) is contained; the benchmark's own canonical solutions pass (parametrised over three HumanEval tasks) |
| `tests/test_verify_lcb.py` | 11 | Dataset shape; the contamination window is recorded; the prompt is identical across configurations; stdin-style correct/wrong/crash/infinite-loop; functional correct/wrong/missing `Solution` class; starter-code names are in scope |
| `tests/test_runner.py` | 19 | The plan covers every cell, is cheapest-first globally, skips bought cells; the cap stops before spending, uses worst case not expected, counts lifetime spend; a stopped run is resumable; rows are marked real; a failed call is recorded without a result; reasoning tokens are stored and not double-charged; sampling is deterministic, seed-sensitive, stratum-independent; an empty stratum is an error; `off` is not parsed as a boolean; thinking gets more headroom; problem-major order completes rows |
| `tests/test_db.py` | 18 | The hash is stable across key order, covers each axis, separates problems sharing a prompt, cannot be confused by concatenation; duplicates return `None`; other integrity errors still raise; configs round-trip; `config_id` does not depend on price; every model has both efforts; the `error_type` domain is enforced; results mirror `GradeResult`; the cheapest passing configuration is the routing target; mock rows are excluded from real spend; cost handles missing counts |
| `tests/test_extract.py` | 10 | Tagged and untagged fences; bare code; the longest block wins; an invalid block loses to a valid one; a truncated fence still returns partial code; prose-only and empty input return `None`; hostile input never raises |
| `tests/test_stats.py` | 10 | Same seed gives an identical interval; different seeds agree; a Bernoulli interval covers the truth at the right width; smaller samples give wider intervals; a ratio is not the mean of ratios; ratio is `None` when nothing was solved; empty input returns NaN; a single observation claims no spread |
| `tests/test_analysis.py` | 46 | All-solved and none-solved are both useless; billed cost wins over the table; mock rows excluded; truncated and errored calls count as wasted and never as passes; aborted calls cost nothing; no free threshold when long reasoning succeeds; unbilled errors are not model failures; censoring is reported; the paired set requires both arms; CPC is a ratio of sums; intervals bracket the point estimate; the abort CI resamples problems; Pareto drops dominated points; the hull drops points a mixture beats; the oracle picks the cheapest solver and still pays for unsolved problems; figures render and one failure does not lose the others; style composition and matched effect; unanimity is easier with fewer voters; the coverage report separates never-asked from never-solved; the per-model effect keeps opposite signs apart; waste is attributed to the model that burned it; a free threshold can exist for one model and not another |
| `tests/test_router.py` | 10 | Features are free; difficulty is ordinal; the label is the cheapest solver; no label when nothing solved; evaluation never trains on the held-out problem; a router cannot win by abstaining; a perfect router matches the oracle; the decomposition blames the estimator when features suffice and the features when they are uninformative; collapse is visible in the output |

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix E: Timeline, decisions, and edits owed to the proposal {.unnumbered}

## E.1 Timeline {.unnumbered}

| Date | Milestone | Spend |
|---|---|---|
| 2026-07-25 | Proposal analysed; GLM dropped; budget cut $100 → $50; project scaffolded on Python 3.12; first API call (392 of 412 tokens reasoning); roster verified against live prices; benchmarks loaded; data contract written | ~$0.001 |
| 2026-07-26 | Grader built, macOS bug caught; pipeline proven on a mock provider; mock data deleted; first real cell (10/10 pass, 44× spread); LiveCodeBench loaded; runner and cost cap built; `request_hash` bug fixed; balance $4 → $15 with cap at $6; providers and quantization pinned; pilot run; thesis reframed; budget parameters found ignored; free cancellation verified; analysis module; `config_id` and `subset_only` bugs fixed; ceiling raised to 48k | $0.58 (pilot) |
| 2026-07-27 | Token estimates re-measured; grid run to the cap; pilot headline refuted; bootstrap intervals; CPC/TPC; frontier, hull, oracle; figures; router and gap decomposition; research framing and proposal-edit list written | $5.25 total |
| 2026-07-28 | Learning materials (START-HERE, 40-lesson course) | $0 |
| 2026-09-01 | Adversarial audit: twelve defects found and fixed, including the per-model sign reversal, the style confound, the coverage dependence, the unreconciled costs and the feature-availability critique; 419 examiner questions drafted | $0 |
| 2026-09-11 | This document assembled; three figures added; citations verified against arXiv; second adversarial pass (Appendix H) | $0 |

## E.2 Decisions with their reasons (selected) {.unnumbered}

| Decision | Reason |
|---|---|
| One aggregator as the sole backend | One key and one schema against six accounts and six adapters |
| Cut problems, never grid cells | The routing label needs every problem run through every configuration |
| Each model paired with itself at two efforts | Within a pair only the thinking mode changes |
| Kimi held out, on a subset, at both efforts | Only non-DeepSeek/Qwen family; full coverage would cost more than the rest combined; one effort would give a single point with no thinking delta |
| Temperature 0, one sample | Halves cost; deterministic label |
| Cap on worst case, against lifetime spend, before dispatch | An expected-case cap is not a cap; five careful runs still empty an account |
| Cheapest first, globally | A stop costs the expensive tail |
| Retries zero except rate limits | A retry loop defeats a cap; a 429 is billed $0 |
| Ceiling raised, never removed | The cap computes its reservation from `max_tokens` |
| Abort threshold left off while building the dataset | A threshold chosen on the data it is evaluated against is fitted |
| Grid re-weighted to medium and hard after the pilot | Easy tiers pass 90–100% regardless; rows there inform nothing |
| Report per model, per style, and at several coverages | Aggregates hid a sign reversal, a composition effect and a budget artefact |
| Report costs as computed from pinned prices | The "priced from the bill" claim was true of the pilot and false of the grid |
| Leave the grid unbalanced | Balancing cost ~$1.50 and a raised cap; a stated limitation is better than a reopened budget |

## E.3 Edits owed to the proposal document {.unnumbered}

The submitted proposal (Revision 2, July 2026) needs these changes before final submission. The four marked structural would be actively wrong if left.

1. **Structural.** Title and framing: the router adds +0.0 points; the thesis is a measurement study.
2. **Structural.** Research questions: replace the router-centred RQ1–RQ5 with the list in Chapter 1.
3. **Structural.** §3 gap analysis: cite Route-To-Reason, DART, HRBench, When Routing Collapses and Agent-as-a-Router; claim the measurement, not a novel router; state the one checkable gap (no effort axis, no reasoning-token column in CodeRouterBench).
4. **Structural.** Add a measurement-validity section (Chapter 4).
5. Roster: five models, three families, no closed reference; describe pinning.
6. Problems: separate the 884 pool from the 320 run set; drop "MBPP 500", "LCB 200"; state coverage.
7. Methods: two grading paths; hand-written references for LiveCodeBench.
8. Metrics: CPC and TPC with bootstrap intervals over problems; report denominators.
9. Router section rewritten as a negative-but-diagnostic result against the hull; withdraw the "features of the incoming prompt" claim.
10. Risks: saturation, collapse and budget are results, not risks.
11. Results: per-model effect leads; style-matched figures; all three CPC spreads with denominators; the 64/68 tie; waste with both denominators.
12. **Structural.** Every LiveCodeBench contamination claim becomes a difficulty-tier statement with the exposure reported.
13. Add the generative-AI declaration to the front matter.
14. Limitations chapter (Chapter 8); the abort chapter reports per-model thresholds; the self-refutation is included, not dropped.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix F: Glossary {.unnumbered}

| Term | Meaning |
|---|---|
| Abort (runtime) | Cancelling a call mid-stream once reasoning exceeds a threshold. Billed $0.00 here |
| Aggregator | A service reselling many providers' models behind one API. OpenRouter |
| `atol` | Absolute tolerance for comparing floating-point answers; why grading is not `==` |
| Bootstrap | Estimating uncertainty by resampling one's own data with replacement, thousands of times |
| Budget forcing | Faking an effort level by capping reasoning tokens. Does not work here: the parameter is ignored |
| Censoring | Observing only that a value exceeded a cutoff. The `max_tokens` ceiling censors reasoning length |
| Configuration | One (model, thinking-setting) pair. Ten here |
| Contamination | A benchmark problem was in the model's training data |
| Convex hull | The cost-accuracy points achievable by mixing configurations. The honest baseline |
| Coverage | How many configurations actually ran on a problem |
| CPC | Cost per correct answer, Σ dollars ÷ Σ solved |
| Discriminating problem | One some configurations solve and others do not |
| Dominated | Beaten by another configuration on both cost and accuracy |
| Effort | How hard the model reasons. Binary in practice: off or high |
| EvalPlus | The library providing HumanEval+, MBPP+, extended tests and the checker |
| Feature ceiling | The best any router using only the given features could do. Fitted, so optimistic |
| `finish_reason` | Why generation stopped. `length` means censored |
| Free features | Features costing no API call |
| Gap decomposition | Splitting router-to-oracle into feature insufficiency and estimation error |
| Held-out model | Kimi, kept out of every design decision |
| k-NN | Copy what worked for the k most similar known problems |
| LCB | LiveCodeBench |
| Leave-one-out | Train on all problems but one, predict that one, repeat |
| MCKP | Multiple-choice knapsack problem |
| Oracle | The cheat that always picks the cheapest configuration that solves each problem |
| Paired problems | The 107 problems with both effort arms graded |
| Pareto frontier | The non-dominated configurations |
| pass@1 | One attempt passes every hidden test |
| Provider | The company serving a model behind the aggregator |
| Quantization | Compressing weights (bf16 → fp8 → fp4); cheaper and measurably worse |
| Reasoning tokens | The invisible thinking; billed; a subset of completion tokens |
| `request_hash` | Unique fingerprint of a call; makes a crashed run free to resume |
| Router | Picks a configuration before calling any model |
| Saturation | A benchmark too easy to distinguish configurations |
| Style (LCB) | stdin→stdout program, or method on a `Solution` class |
| Token | About three quarters of a word; the unit of everything, including the bill |
| TPC | Tokens per correct answer |
| Value of problem-level information | Oracle minus hull at equal budget: 13.8 points |
| Wasted call | Billed, but returned no usable answer |

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix G: Full tables {.unnumbered}

## G.1 Per-configuration coverage, outcomes and spend (all billed rows) {.unnumbered}

| Configuration | Generations | Passed | Truncated | Spend | Mean completion tok | Mean reasoning tok |
|---|---|---|---|---|---|---|
| qwen3.5-9b \| off | 318 | 130 | 35 | $0.2791 | 5,781 | 0 |
| qwen3.5-9b \| high | 104 | 46 | 37 | $0.2767 | 18,308 | 12,806 |
| deepseek-v4-flash \| off | 320 | 163 | 5 | $0.0753 | 1,056 | 0 |
| deepseek-v4-flash \| high | 74 | 66 | 3 | $0.1536 | 10,945 | 10,470 |
| qwen3.6-35b-a3b \| off | 320 | 144 | 12 | $1.0533 | 3,217 | 71 |
| qwen3.6-35b-a3b \| high | 74 | 43 | 7 | $0.9793 | 13,166 | 8,718 |
| deepseek-v4-pro \| off | 51 | 39 | 0 | $0.0287 | 278 | 0 |
| deepseek-v4-pro \| high | 73 | 66 | 2 | $0.8880 | 8,895 | 8,418 |
| kimi-k2.6 \| off | 16 | 11 | 0 | $0.1788 | 3,202 | 0 |
| kimi-k2.6 \| high | 23 | 21 | 0 | $1.3272 | 17,682 | 16,315 |
| **Total** | **1,373** | | | **$5.2402** | | |

Note: `qwen3.6-35b-a3b | off` reports a small non-zero mean reasoning count (71); the endpoint occasionally emits reasoning tokens with reasoning disabled, and they are billed. Spend by effort: `off` $1.6153, `high` $3.6250.

## G.2 The run set by stratum and style {.unnumbered}

| Stratum | Problems run | Pool | Style split in pool (stdin / functional) |
|---|---|---|---|
| HumanEval+ | 21 | 164 | n/a |
| MBPP+ | 20 | 378 | n/a |
| LCB easy | 21 | 84 | 50 / 34 |
| LCB medium | 104 | 104 | 50 / 54 |
| LCB hard | 154 | 154 | 117 / 37 |

## G.3 Problem statistics {.unnumbered}

| Benchmark | Mean prompt chars (min–max) | Mean hidden tests (min–max) |
|---|---|---|
| HumanEval+ | 451 (115–1,360) | 758 (12–1,100) |
| MBPP+ | 158 (83–485) | 109 (3–150) |
| LiveCodeBench | 1,540 (523–3,935) | 40 (2–52) |

## G.4 The first cell: `HumanEval/0` × 10 configurations {.unnumbered}

All ten passed. Cost from $0.000106 (`qwen3.5-9b | off`) to $0.004630 (`kimi-k2.6 | high`): 44× at pinned prices, for an identical outcome. Reasoning tokens on the thinking arm ranged from 278 to 1,915.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix H: The adversarial self-audit of this draft {.unnumbered}

Before this document was assembled, a hostile-examiner pass over the project (2026-09-01) found twelve defects in the analysis, all fixed and all now reflected in Chapters 5–8. After this draft was written, a second pass was run over the draft itself on 2026-09-11, checking every derived number against the database and every citation against arXiv. What it found, and what was done:

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | The abstract and conclusion said 15% of reasoning spend was wasted, "three quarters of it from one model". Three quarters is the share of wasted *calls* (37 of 49); by dollars that model's share is 43% ($0.24 of $0.56) | Would have been caught by a reader with a calculator | Wording changed to "three quarters of those calls" in both places |
| 2 | `scripts/results.py` reported five adjacent CPC pairs with overlapping intervals but printed only four: the print loop sliced the list to `[:4]`. The draft had copied the printed four | Real code defect; the fifth pair (`kimi|off` vs `qwen3.6-35b|high`) was omitted from Chapters 5 and 8 | Slice removed in `results.py`; both chapters now list five |
| 3 | The oracle's routing breakdown was stated as "18 of 59 to the thinking configuration"; recomputed, it is 17 to `flash|high` and 1 to `qwen3.5-9b|high` | Minor imprecision | Stated exactly |
| 4 | Chapter 3 said reasoning-off "genuinely yields zero reasoning tokens". Two of the 1,025 `off` calls (both `qwen3.6-35b-a3b`) reported non-zero reasoning counts and were billed for them | Overclaim on a load-bearing sentence | Qualified with the exact count in Chapters 3 and 4 |
| 5 | The project log recorded ThoughtTerminator as arXiv 2507.04023; that identifier resolves to a different paper (Srivastava et al.). The correct identifier is 2504.13367 (Pu et al., April 2025) | A wrong citation an examiner can check in seconds | Corrected in the bibliography and in the project log; all 22 arXiv identifiers verified (Appendix I) |
| 6 | The pilot was described as 15 problems; the reconciled pilot rows cover 16 problems (the 15 stratified plus `HumanEval/0` from the first cell), 149 generations | Minor | Corrected in Chapter 7 |
| 7 | The project log states the pass rate under 10,000 reasoning tokens as 83.8% (186/222); with the documented rule that unbilled infrastructure failures are excluded, it is 84.2% (186/221) | The two denominators differ by one unbilled row | The thesis uses the billed denominator and states it |
| 8 | The project log says 1,207 grid rows still carry a generation id; the database holds 1,217 | Stale count | Thesis uses 1,217 |
| 9 | The log says 37 commits carry the AI co-author trailer; at assembly it is 38 of 39 | Stale count | Declaration uses 38 of 39 |
| 10 | Figures were referenced by section-style numbers that nothing generated | Broken cross-references | Captions numbered 1–8 in order of appearance; references fixed |
| 11 | `qwen3.6-35b-a3b | off` shows a non-zero mean reasoning count (71) in Appendix G, which contradicts the "off yields zero" reading | Same root cause as #4 | Explained in the table note |
| 12 | Every percentage in Chapters 5–7 was re-derived from `scripts/results.py` output on 2026-09-11 and every count in Appendix D from the test file names; the 4.3× token multiplier, the 6.1× price ratio, the 63% oracle cost ratio and the 1.8× within-style factor were recomputed by hand from the tabulated values | Verification, no defect | None needed |

Three things the audit could not resolve and that remain owed: the grid's cost reconciliation (free, 1,217 rows), full reads of three cited papers (Appendix I), and the department's exact wording for the AI-use declaration.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Appendix I: Citation verification status {.unnumbered}

Every arXiv identifier in the bibliography was resolved against arxiv.org on 2026-09-11 and its title and first author confirmed. **Full read** means the paper was read in its entirety; **abstract** means the assessment in Chapter 2 rests on the abstract, a summary, or extracted text.

| Work | Identifier | Resolved | Basis of the assessment |
|---|---|---|---|
| HumanEval (Chen et al. 2021) | 2107.03374 | yes | full read |
| MBPP (Austin et al. 2021) | 2108.07732 | yes | full read |
| EvalPlus (Liu et al. 2023) | 2305.01210 | yes | full read; library used directly |
| LiveCodeBench (Jain et al. 2024) | 2403.07974 | yes | full read; dataset used directly |
| RouterBench (Hu et al. 2024) | 2403.12031 | yes | abstract and evaluation section |
| RouteLLM (Ong et al. 2024) | 2406.18665 | yes | abstract |
| Universal routing (Jitkrittum et al. 2025) | 2502.08773 | yes | abstract |
| Budget Guidance (Li et al. 2025) | 2506.13752 | yes | abstract |
| AnytimeReasoner (Qi et al. 2025) | 2505.13438 | yes | abstract |
| Route to Reason (Pan et al. 2025) | 2505.19435 | yes | **abstract only; "appears to require training" is unverified** |
| When Routing Collapses (Lai et al. 2026) | 2602.03478 | yes | abstract |
| HRBench (Ning et al. 2026) | 2605.28398 | yes | **abstract only** |
| DART (Lee et al. 2026) | 2606.23181 | yes | abstract; the draft-generation claim is in the title |
| LLMRouterBench (Li et al. 2026) | 2601.07206 | yes | abstract |
| Agent-as-a-Router (Zhou et al. 2026) | 2606.22902 | yes | **abstract only**; the CodeRouterBench column claim was verified against the released dataset (columns: task_id, split, source_split, dimension, model, score, cost_usd, input_tokens, output_tokens, total_tokens, latency_ms, cost_source; 79,992 rows) |
| Do NOT Think That Much (Chen et al. 2024) | 2412.21187 | yes | abstract |
| Stop Overthinking survey (Sui et al. 2025) | 2503.16419 | yes | abstract |
| ThoughtTerminator (Pu et al. 2025) | 2504.13367 | yes | abstract. **Correction:** the project log had recorded 2507.04023, which resolves to a different paper (Srivastava et al., "Do LLMs Overthink Basic Math Reasoning?") |
| SelfBudgeter (Li et al. 2025) | 2505.11274 | yes | abstract |
| RecurGuard (Aziz et al. 2026) | 2606.07968 | yes | abstract |
| The Silent Hyperparameter (Pape et al. 2026) | 2605.19537 | yes | abstract |
| s1 (Muennighoff et al. 2025) | 2501.19393 | yes | abstract |
| Cover & Hart 1967; Efron 1979; Kellerer et al. 2004; Dantzig 1963 | journals / books | standard references | textbook results |

Three full reads are still owed before submission: Route to Reason, HRBench and Agent-as-a-Router.
