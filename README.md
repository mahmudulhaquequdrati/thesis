# CARR — Cost-Aware Reasoning Routing

Undergraduate thesis: measuring the cost-vs-accuracy tradeoff of open-weight
reasoning models on code generation, and building a training-free router that
picks the cheapest (model, thinking-mode) pair that still solves the problem.

**Read [THESIS.md](THESIS.md) first** — it is the single source of truth for
what this is, how it is built, what is done, and what comes next.

## Setup

```bash
uv sync                       # creates .venv on Python 3.12
cp .env.example .env          # then paste your OpenRouter key into .env
uv run python scripts/day1_hello.py
```

## See the data

```bash
uv run python scripts/init_db.py     # build data/carr.sqlite from evalplus + the roster
uv run python scripts/studio.py      # browse it at http://127.0.0.1:8787
```

**Studio** is a local database browser — tables, columns, sorting, search,
pagination, a read-only SQL console, and row editing and deletion. It reads the
schema at request time, so it works on whatever the file contains; add a table
and it appears. It binds to loopback only and uses nothing outside the standard
library.

Everything it can change is reversible: the whole database is snapshotted to
`data/backups/` before the first write of each session. Start it with
`--read-only` to disable writing entirely.

For the CARR-specific view of one problem across all 10 configs, use the terminal:

```bash
uv run python scripts/view.py --list          # every problem, one line each
uv run python scripts/view.py HumanEval/0     # all 10 configs side by side
uv run python scripts/view.py HumanEval/0 -c 3   # prompt → response → code → grade
```

`init_db.py` loads only what is real and free: **884 problems** (HumanEval+ 164,
MBPP+ 378, LiveCodeBench 342) and the 10 verified configs. `generations` and
`results` start empty — those rows cost money.

LiveCodeBench is the hard tier: **154 of its 342 problems are `hard`** and 104
`medium`. The pilot showed those are the *only* tiers that discriminate —
HumanEval+, MBPP+ and LCB-easy all pass 90–100% whether reasoning is on or off. ⚠️ It is
**not** a contamination control here — it stopped updating in 2025 and every
model on the roster is a 2026 release. See THESIS.md §9.

## Run the pilot (this spends real money)

```bash
uv run python scripts/pilot.py --dry-run    # free: the sample and the bill
uv run python scripts/pilot.py --yes        # ~$0.29 expected
```

15 problems stratified across benchmark and difficulty × 10 configs. Its job is
to measure the two numbers that decide the grid's size: mean thinking tokens on
**hard** problems, and the saturation rate.

The cap in `config/experiment.yaml` **aborts before spending** — it refuses any
call whose worst case (`max_tokens` × output price) would push *lifetime* spend
past `abort_at_usd`. Interrupt it and re-run; bought cells are skipped for free.

## Buy a single row

```bash
uv run python scripts/run_one.py --all --dry-run          # free; shows the bill first
uv run python scripts/run_one.py --config 1 --yes         # one call, ~$0.0001
uv run python scripts/run_one.py --all --yes              # 10 configs, ~$0.02
```

It refuses to send anything if the **worst case** — `max_tokens` × the output
price, summed over every cell — exceeds `--max-usd` (default $0.20). Cells
already bought are skipped via `request_hash`, so re-running costs nothing.

Other free checks:

```bash
uv run python scripts/verify_roster.py        # roster vs OpenRouter's live /models
uv run python scripts/estimate_cost.py        # price the grid before running it
uv run pytest                                  # 32 tests
```

## Layout

| Path | What |
|---|---|
| `THESIS.md` | Master document — status, plan, schema, science, glossary |
| `CLAUDE.md` | Working rules, incl. the mandatory doc-update ritual and the $50 budget cap |
| `docs/codebase-tour.md` | **Learn the code here** — every file explained, in order |
| `docs/data-spec.md` | Exact contract: what we send, what we store, every column |
| `Thesis_Project_Proposal.docx` | The submitted proposal (Revision 2) |
| `scripts/` | Runnable entry points. **`view.py`, not `inspect.py`** — that name shadows the stdlib module and breaks every other script here |
| `carr/` | The harness package. Built: `db`, `effort`, `extract`, `cost`, `execute/verify`, `providers/base` |
| `config/` | Model roster, benchmarks, experiment grid — never hardcoded |
| `data/` | `carr.sqlite`, the dataset. Gitignored; back it up separately. `backups/` holds automatic pre-write snapshots |
