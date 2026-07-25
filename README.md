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

## Layout

| Path | What |
|---|---|
| `THESIS.md` | Master document — status, plan, schema, science, glossary |
| `CLAUDE.md` | Working rules, incl. the mandatory doc-update ritual and the $50 budget cap |
| `docs/codebase-tour.md` | **Learn the code here** — every file explained, in order |
| `docs/data-spec.md` | Exact contract: what we send, what we store, every column |
| `Thesis_Project_Proposal.docx` | The submitted proposal (Revision 2) |
| `scripts/` | Runnable entry points |
| `carr/` | The harness package (built out from Week 2) |
| `config/` | Model roster, benchmarks, experiment grid — never hardcoded |
| `data/` | `carr.sqlite`, the dataset. Gitignored; back it up separately |
