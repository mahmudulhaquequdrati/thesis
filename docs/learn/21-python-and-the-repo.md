# Lesson 21 — Python, `uv`, and the shape of the repo

*Part 3 · about 1 hour · after lesson 20*

---

## In one sentence

> Everything runs through `uv run`, the library lives in `carr/`, the things you
> type live in `scripts/`, and about 2,000 lines of code produced every number
> in the thesis.

---

## The tools

### `uv` — the environment manager

Python projects need specific versions of specific libraries. Install them
globally and two projects fight. So each project gets a **virtual environment**:
a private folder of libraries (`.venv/`).

`uv` builds and manages that folder. Three commands are all you need:

```bash
uv sync                      # build the environment from pyproject.toml
uv run python <script.py>    # run something inside it
uv run pytest -q             # run the tests inside it
```

**Always `uv run`.** Plain `python` uses your system Python 3.14, which cannot
install `evalplus` at all.

### Why Python 3.12 is pinned

Your system has 3.14.3. The project pins `>=3.12,<3.13`, and `CLAUDE.md` says
not to "helpfully" relax it: `evalplus` and the ONNX embedding stack have no
wheels for 3.14. A **wheel** is a pre-built package; without one, installation
tries to compile from source and fails.

Pinning on day 1 avoided hitting this in week 3, mid-experiment. It is in the
decisions log for that reason.

### The dependency list is short on purpose

| Package | Why |
|---|---|
| `openai` | HTTP client. OpenRouter is OpenAI-compatible — swap `base_url`, done |
| `python-dotenv` | Loads `.env` so the API key never lands in code |
| `evalplus` | HumanEval+/MBPP+ problems **and** the grader |
| `PyYAML` | The roster and experiment config |
| `pytest` | 119 tests |
| `matplotlib` | Four figures — **the only dependency added after week 1** |

And two notable **non**-dependencies:

- **No scipy.** The convex hull is a twenty-line monotone chain; the bootstrap
  is stdlib `random`. Both are in `stats.py` and `analysis.py` with comments
  saying so.
- **No Docker.** Reversed on day 3 in favour of evalplus's own sandbox
  (lesson 06).

That restraint is worth one sentence in Chapter 3. A dependency list that is a
set of decisions reads differently from one that is an accumulation.

---

## The shape of the repository

```
thesis/
├── THESIS.md              ← source of truth: status, decisions, risks
├── CLAUDE.md              ← the working rules
├── README.md
├── config/
│   ├── models.yaml        ← THE ROSTER. Nothing else knows a model name
│   └── experiment.yaml    ← caps, temperature, max_tokens, strata, seed
├── carr/                  ← the library. Imported, never run directly
│   ├── effort.py          roster → the 10 configurations
│   ├── cost.py            tokens → dollars (25 lines)
│   ├── providers/         base.py (the contract), openrouter.py (spends money)
│   ├── extract.py         raw response → runnable Python
│   ├── execute/           verify.py (THE grader), _lcb_runner.py
│   ├── benchmarks/        livecodebench.py
│   ├── db.py              schema + never-pay-twice
│   ├── experiment.py      config + stratified sampling
│   ├── runner.py          THE paid loop, and the cost cap
│   ├── stats.py           bootstrap CIs
│   ├── analysis.py        every number in the thesis
│   ├── router.py          the router and the gap decomposition
│   └── figures.py         four PNGs
├── scripts/               ← the things you type. Thin wrappers over carr/
├── tests/                 ← 119 tests
└── data/
    ├── carr.sqlite        ← THE scientific asset. Gitignored. Back it up
    ├── backups/           ← auto-snapshots before any destructive write
    └── figures/           ← regenerated, never hand-edited
```

### The distinction that organises everything

> **`carr/` is a library — importable, testable, no side effects on import.
> `scripts/` is an interface — argument parsing, printing, and calling into
> `carr/`.**

This is why `scripts/results.py` is 219 lines while `carr/analysis.py` is 675:
the script formats, the module computes. It also means every number in the
thesis is produced by code that a test can call directly.

### ⚠️ The naming trap that cost a run

> **Never name a file in `scripts/` after a standard library module.**

Python puts a script's own directory first on `sys.path`. A file called
`scripts/inspect.py` therefore shadows the stdlib `inspect` module for **every
other script in that directory** — and the failure surfaces as a confusing
`AttributeError` deep inside a dependency, not as an import error.

It broke a seeding run silently. The terminal viewer is `view.py` for this
reason, and it is in `CLAUDE.md` as a permanent rule.

---

## Reading Python, if you have never read any

Four constructs cover almost everything in this codebase.

**A function** — a named piece of work:

```python
def compute_cost(prompt_tokens, completion_tokens, price_in_per_m, price_out_per_m):
    p_in = (prompt_tokens or 0) * price_in_per_m
    p_out = (completion_tokens or 0) * price_out_per_m
    return (p_in + p_out) / 1e6
```

`or 0` means "use 0 if this is missing". `1e6` is one million.

**A dataclass** — a record with named fields:

```python
@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int = 0     # `= 0` is the default
```

**A docstring** — the text right under a `def` or at the top of a file. In this
codebase, **docstrings carry the reasoning**, and they are often the most
valuable thing in the file. `carr/cost.py` is 25 lines of code and 14 lines of
docstring, and the docstring is doing more work.

**A type hint** — `x: int`, `-> float`. Documentation Python does not enforce.

That is genuinely enough. This is a small research codebase, not a framework —
`CLAUDE.md` explicitly forbids speculative abstraction, so there is no
inheritance maze to decode.

---

## How to run anything

| Want to… | Command | Costs |
|---|---|---|
| Check everything works | `uv run pytest -q` | $0 |
| See the configurations | `uv run python -m carr.effort` | $0 |
| Browse the database | `uv run python scripts/studio.py` | $0 |
| See one problem | `uv run python scripts/view.py HumanEval/0` | $0 |
| **Print the entire thesis** | `uv run python scripts/results.py` | $0 |
| Regenerate figures | `uv run python scripts/make_figures.py` | $0 |
| Check the roster is current | `uv run python scripts/verify_roster.py` | $0 |
| Price a run before it happens | `uv run python scripts/estimate_cost.py` | $0 |
| ⚠️ Buy generations | `scripts/run_one.py` / `scripts/pilot.py` | **REAL MONEY** |

Only the last row spends. Everything else is free and repeatable — which is
itself a design property: the expensive part happened once, and all analysis
runs against the stored result.

---

## Do this

**1. Confirm the environment.**

```bash
cd ~/thesis
uv sync && uv run pytest -q
```

Expect **119 passed**.

**2. Run the module that turns the roster into configurations.**

```bash
uv run python -m carr.effort
```

Ten lines, cheapest first. That `if __name__ == "__main__":` block at the bottom
of `effort.py` is a small, good habit: a module that can also demonstrate
itself.

**3. Print the whole thesis.**

```bash
uv run python scripts/results.py
```

You have run this before. Run it again now that you know all the findings — it
should read as familiar rather than cryptic. **That shift is the point of Part
2.**

**4. Look at how thin a script is.**

```bash
head -40 scripts/make_figures.py
```

39 lines. All the work is in `carr/figures.py`.

---

## Check yourself

1. Why is Python pinned to 3.12, and why must you not relax it?
2. What is the difference in purpose between `carr/` and `scripts/`?
3. Why is the terminal viewer called `view.py`?
4. Name the only dependency added after week 1, and two deliberate
   non-dependencies.
5. Which commands in this repository cost money?
6. Where does the reasoning behind a design decision live in this codebase?

<details>
<summary>Answers</summary>

1. `evalplus` and the embedding stack have no wheels for 3.14, so installation
   would fail. Pinning on day 1 avoided discovering it mid-experiment.
2. `carr/` is an importable library that computes and is directly testable;
   `scripts/` parses arguments, prints, and calls into it.
3. Because `scripts/inspect.py` would shadow the standard library's `inspect`
   module for every other script in that directory — it did, and broke a run
   silently.
4. `matplotlib`. Non-dependencies: scipy (the hull is a twenty-line monotone
   chain, the bootstrap is stdlib) and Docker (evalplus's sandbox replaced it).
5. Only `scripts/run_one.py` and `scripts/pilot.py`. Everything else is free.
6. In the docstrings. Several files have more explanation than code, and that is
   deliberate — comments explain *why*, especially where a choice protects the
   budget or the validity of a result.

</details>

---

➡️ Next: [Lesson 22 — `models.yaml`, `effort.py`, `cost.py`](22-config-and-effort.md)
