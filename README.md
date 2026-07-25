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

Everything below is **free and offline** — no API key, no network, no cost. The
rows are mock generations produced by `carr/providers/echo.py`, but they are
graded by the real grader, so the pipeline they exercise is the real one.

```bash
uv run python scripts/seed_mock.py            # fill data/carr.sqlite ($0)
uv run python scripts/view.py --list          # every problem, one line each
uv run python scripts/view.py HumanEval/0     # all 9 configs for one problem
uv run python scripts/view.py HumanEval/0 -c 3   # one cell: prompt → response → code → grade

uv run python scripts/make_viewer.py          # → data/viewer.html
open data/viewer.html                          # browse it, self-contained, no server
```

Mock rows carry `is_mock = 1` and are excluded from every spend and result
number. Re-running `seed_mock.py` inserts nothing: `request_hash` is UNIQUE, so
a crashed run is free to restart.

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
| `carr/` | The harness package. Built: `db`, `effort`, `extract`, `cost`, `execute/verify`, `providers/{base,echo}` |
| `config/` | Model roster, benchmarks, experiment grid — never hardcoded |
| `data/` | `carr.sqlite`, the dataset. Gitignored; back it up separately. `viewer.html` is regenerated, never edited |
