# Start here — learn this project from zero

About an hour, in seven steps. Each step has something to **run**, and says what
you should see. Nothing here costs money.

If you only read one other document afterwards, make it
[research-framing.md](research-framing.md) — this one teaches the machine, that
one teaches the science.

---

## Step 0 — The one-sentence version

> **Reasoning models can "think" before answering. That thinking is billed but
> invisible. When is it worth paying for?**

Everything in this repository exists to answer that with measured numbers
instead of intuition.

**The concrete thing that started it.** On day one, a trivial prompt — *"write a
Python function that reverses a string"* — came back with **412 completion
tokens, of which 392 were reasoning**. The visible answer was three lines. Price
that call from the text you can see and you understate it about twentyfold.

```bash
uv sync                    # Python 3.12 environment
uv run pytest -q           # expect: 119 passed
```

If the tests pass, everything below will work.

---

## Step 1 — The mental model: one row at a time

```
   A PROBLEM        +      A CONFIG
   (HumanEval/0)          (flash, thinking on)
                    |
                    v          ← ONE PAID API CALL
              raw response
                    |
                    v
           extract the code
                    |
                    v          ← FREE, runs the benchmark's real tests
              run the tests
                    |
                    v
   ONE ROW:  passed? tokens? reasoning tokens? dollars?
```

Do that 1,373 times and you have **the table**. The table is the thesis.

Two words you need:

- **config** = a (model, thinking-mode) pair. `flash|off` and `flash|high` are
  the *same model*, differing only in whether reasoning is enabled. There are 10.
- **reasoning tokens** = tokens the model spends thinking, billed, absent from
  the answer. This is the quantity the whole thesis is about.

```bash
uv run python scripts/view.py --list | head -20
uv run python scripts/view.py HumanEval/0        # one problem, every config
```

You should see one line per config, with cost and pass/fail, ending in the
*cheapest config that solved it*.

---

## Step 2 — Where the data lives

```bash
uv run python scripts/studio.py     # browser at 127.0.0.1:8787
```

Four tables in `data/carr.sqlite`:

| table | one row per | rebuildable? |
|---|---|---|
| `problems` | benchmark problem (884) | **yes**, free, from evalplus + LiveCodeBench |
| `configs` | model × thinking-mode (10) | **yes**, free, from `config/models.yaml` |
| `generations` | **API call (1,373)** | **NO — this cost $5.24** |
| `results` | graded generation (1,280) | **yes**, free, re-run the grader |

**Only `generations` costs money.** That is why it is gitignored, why every
destructive tool snapshots it to `data/backups/` first, and why `request_hash`
is UNIQUE — so a crashed run never re-buys what it already has.

Try this in Studio's SQL console — it is the query the whole schema exists for:

```sql
SELECT problem_id, MIN(cost_actual_usd) FROM generations
JOIN results USING (gen_id) WHERE passed = 1 GROUP BY problem_id;
```

That is "the cheapest config that solved each problem" — the routing label.

---

## Step 3 — Read the code, in this order

Roughly 2,000 lines. Read it in dependency order and each file explains itself.

**Layer 1 — what we send and what it costs**

| file | what to notice |
|---|---|
| `config/models.yaml` | The roster. Every model **pins a provider and a quantization** — read the comment saying why; it is one of the thesis's findings |
| `carr/effort.py` | Expands the roster into the 10 configs. Note `config_id` (identity) is deliberately separate from `tier_index` (run order) |
| `carr/cost.py` | 25 lines, one rule: **reasoning tokens are already inside completion tokens**. Adding them twice would corrupt every number |

**Layer 2 — buying and grading**

| file | what to notice |
|---|---|
| `carr/providers/base.py` | The contract. `Generation` carries `reasoning_tokens` and `finish_reason` |
| `carr/providers/openrouter.py` | The real backend. Sends the prompt **unmodified** — no system prompt, because that would confound the effort axis |
| `carr/extract.py` | Markdown → runnable Python. Never raises; a bad response is a data point |
| **`carr/execute/verify.py`** | **The most important file.** Grades in a sandboxed subprocess. Read the `EVALPLUS_MAX_MEMORY_BYTES` comment — that bug would have made every solution silently "fail" |
| `carr/execute/_lcb_runner.py` | LiveCodeBench needs different execution: stdin→stdout programs and `Solution`-class methods |

**Layer 3 — the loop that spends money**

| file | what to notice |
|---|---|
| `carr/experiment.py` | Reads `config/experiment.yaml`. Note `"off"` is **quoted** — YAML parses bare `off` as `False` |
| **`carr/runner.py`** | **The cost cap.** It aborts *before* spending, on *worst case*, against *lifetime* spend. Read that docstring twice |
| `carr/db.py` | Schema. `request_hash` UNIQUE is the never-pay-twice mechanism |

**Layer 4 — turning rows into results**

| file | what to notice |
|---|---|
| `carr/stats.py` | Seeded bootstrap, stdlib only. The statistic takes the **whole resample** — required for ratios like cost-per-correct |
| `carr/analysis.py` | Every number in the thesis. Note `paired_problems()`: only 107 problems are comparable |
| `carr/router.py` | The router and the gap decomposition |
| `carr/figures.py` | Four PNGs |

---

## Step 4 — Run everything and read the output

```bash
uv run python scripts/results.py
```

This prints the entire thesis. Read it top to bottom:

- **RQ0 saturation** — which tiers can tell configs apart. Watch for
  `<- saturated, no signal`.
- **RQ1 reasoning length** — rises with difficulty, 642 → 17,547 tokens.
- **RQ2 waste** — passing calls average 7,567 reasoning tokens; calls returning
  *nothing* average **29,584**.
- **Censoring warning** — 26.3% of hard thinking calls still hit the ceiling.
- **Economics** — cost per correct answer, with intervals. Note the line saying
  *"5 adjacent pairs have OVERLAPPING intervals"*.
- **RQ4 frontier** — the hull, the oracle, and the 13.8-point gap.
- **RQ4b router** — it collapses, and the decomposition says why.
- **RQ3 abort** — the tradeoff curve, ending in *"No threshold saves money
  without losing a solved problem."*

```bash
uv run python scripts/make_figures.py && open data/figures/
```

---

## Step 5 — The three things that will surprise you

**1. The benchmarks are mostly useless for this question.** Of 320 problems, 81
are solved by *everything* and 98 by *nothing*. Only **141 discriminate**. A
problem every config solves teaches you nothing about which config to pick.

**2. The platform lies in three ways.** One model slug is served by 18 providers
at $0.87–$3.48 per M output, at quantizations from fp4 to bf16, and `/models`
reports only the cheapest — so an unpinned evaluation compares *different
models* at *unknown prices*. `reasoning: {max_tokens: 2000}` produced 13,731
tokens. `max_tokens: 48000` produced 73,037.

**3. Two headline findings were refuted by better data — both mine.** The pilot
said thinking made hard problems *worse*; with 30× more data it more than
doubles the pass rate. The pilot said a 10,000-token abort was *free*; it was an
artefact of a truncation ceiling. Both corrections are in the history on
purpose.

---

## Step 6 — The rules that keep it honest

From `CLAUDE.md`, each one paid for by a bug:

- **Never grade outside `verify.py`** — pass/fail is not `==`; floats compare
  with a tolerance and some problems have bespoke oracles.
- **Never re-buy a generation** — `request_hash` UNIQUE, proven by re-running.
- **A cost cap must abort, not warn**, and on worst case, not expectation.
- **Store `raw_response` verbatim** — re-grading is then free forever.
- **Never name a file in `scripts/` after a stdlib module** — `inspect.py` broke
  every script in that directory.
- **Fixed seeds everywhere.** Reproducibility is graded.

Verify the last one yourself:

```bash
uv run python scripts/results.py > /tmp/a.txt
uv run python scripts/results.py > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt        # must be identical
```

---

## Step 7 — Where to go next

| document | for |
|---|---|
| [**learn/**](learn/00-index.md) | **The long road.** A 40-lesson course assuming zero prior knowledge — foundations, every finding, every module, and how to write and defend the thesis. ~6 weeks at an hour a day |
| [research-framing.md](research-framing.md) | **The science.** Question, findings, contribution, what it is *not* |
| [docx-revisions.md](docx-revisions.md) | The 14 edits owed to your proposal |
| [advisor-update.md](advisor-update.md) | The one-pager to send |
| [data-spec.md](data-spec.md) | Exact send/store contract |
| [codebase-tour.md](codebase-tour.md) | Longer file-by-file walk. ⚠️ Written early; some "NOT BUILT YET" notes are now stale |
| `THESIS.md` | Source of truth: status, decisions log, risks |

**If you remember one thing:** the table is the contribution. Every rule in this
repository exists to stop that table being quietly wrong — and twice it *was*
quietly wrong, and the checks caught it.
