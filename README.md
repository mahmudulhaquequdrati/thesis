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

For the CARR-specific view of one problem across all 9 configs, use the terminal:

```bash
uv run python scripts/view.py --list          # every problem, one line each
uv run python scripts/view.py HumanEval/0     # all 9 configs side by side
uv run python scripts/view.py HumanEval/0 -c 3   # prompt → response → code → grade
```

`init_db.py` loads only what is real and free: 542 problems from evalplus and
the 9 verified configs. **`generations` and `results` start empty** — those rows
cost money and only the pilot can fill them.

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
