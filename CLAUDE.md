# CLAUDE.md — working rules for this repository

Undergraduate thesis: **CARR (Cost-Aware Reasoning Routing)** — measure the
cost-vs-accuracy tradeoff of open-weight reasoning models on code generation,
then build a training-free router that picks the cheapest (model, thinking-mode)
pair that still solves a given problem.

**Read [THESIS.md](THESIS.md) before doing anything.** It is the single source of
truth: current status, day-by-day plan, tech stack, DB schema, the science, and
a glossary. If a fact appears both here and in THESIS.md, **THESIS.md wins**.

---

## 1. Update the docs after every piece of work — mandatory

Every work session ends by writing down what changed. This is not optional
bookkeeping: the user picks this project up days apart, and an out-of-date
status section costs more time than the work itself saved.

**After completing any task, before reporting back, update:**

| File | What to update | When |
|---|---|---|
| **THESIS.md §1** | Stage, next action, spend to date, rows in dataset, blockers | **Every session, always** |
| **THESIS.md §1 log** | One dated line describing what was done | **Every session, always** |
| **THESIS.md §5** | Tick checkboxes: ⬜ → 🟨 → ✅ | Whenever a task starts or finishes |
| **THESIS.md §12** | A dated row for any decision made, **with its reason** | Whenever a choice was made |
| **THESIS.md §4** | The stack table | When a dependency is added or swapped |
| **THESIS.md §7** | Repo layout | When files or directories are added |
| **THESIS.md §8** | DB schema | When the schema changes — **and note the migration** |
| **THESIS.md §9** | Roster, problem counts, budget table | When the experiment design shifts |
| **THESIS.md §11** | Risk table | When a new risk appears or one is retired |
| **THESIS.md §13** | Glossary | When a new term enters the project |
| **THESIS.md §14** | `.docx` edits still owed | When code and proposal diverge |
| **THESIS.md §15** | Prior art, external datasets, novelty positioning | When a related paper or reusable dataset is found |
| **README.md** | Setup steps, layout table | When either changes |
| **CLAUDE.md** | This file | When a working rule changes |
| **`config/*.yaml`** | Roster, prices, snapshot dates | After every `verify_roster.py` run |

**Numbers must be consistent everywhere.** Budget, problem counts, config
counts, and row counts appear in several sections. Changing one means grepping
for the old value and updating all of them:

```bash
grep -n '\$50\|434\|3,906\|9 config' THESIS.md README.md CLAUDE.md
```

Exception: **§12 (decisions log) is append-only history.** Superseded values
stay there, struck through, so the reasoning behind a change survives.

Then commit. A session that changed files but left the docs stale is not done.

---

## 2. Budget discipline — $50 hard cap

Real money, and the user's own. Treat overspending as a bug, not a tradeoff.

- **Hard cap $50. Target finishing under $30.** Current spend lives in THESIS.md §1 — read it before any run and update it after.
- **Never run a paid loop without a cost cap that aborts.** Warn-and-continue is not a cap.
- **Never re-buy a generation.** The `request_hash UNIQUE` check must be verified working before any multi-hour run.
- **Estimate before spending.** Anything projected over ~$5 gets its cost stated to the user *before* it runs, not after.
- **Cheapest configs first**, always, so a blowout costs the expensive tail rather than the cheap foundation.
- **Cap `max_tokens` per config.** One runaway reasoning trace can cost more than a hundred normal calls.

---

## 3. Hard constraints

- **Python 3.12** — pinned `>=3.12,<3.13`. The system interpreter is 3.14.3; `evalplus` and the ONNX embedding stack have no wheels for it. Do not "helpfully" relax this pin.
- **Never hardcode a model name.** The roster lives in `config/models.yaml`, validated against OpenRouter's live `/models`, every row carrying a snapshot date. Model names in this repo's prose are *candidates*, not confirmed facts — the open-weight landscape moves every 6–8 weeks.
- **Never run generated code outside the Docker sandbox.** It is untrusted and will eventually contain infinite loops, `os.system`, or filesystem writes.
- **Store `raw_response` verbatim.** Code-extraction logic has bugs; keeping raw responses means re-grading offline for free instead of re-buying generations.
- **`.env` is never committed.** It is gitignored — keep it that way.
- **`data/carr.sqlite` is the scientific asset.** It costs real money to regenerate. Gitignored, but tell the user to back it up separately.
- **Fixed seeds everywhere** — sampling, splits, bootstrap. Reproducibility is a graded property of a thesis.

---

## 4. Style

- Match the surrounding code; this is a small research codebase, not a framework. No speculative abstraction layers.
- Comments explain *why*, especially where a choice protects the budget or the validity of a result. Skip comments that restate the code.
- Prefer a plain function over a class until state genuinely needs holding.
- The user is learning this stack as it is built. When introducing an unfamiliar tool or concept, say in one line what it is and why it is there.

---

## 5. Commits

- Commit at the end of each work session, after the docs are updated.
- Subject line says what changed; body says *why*, especially for cost or methodology decisions.
- End commit messages with:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

---

## 6. Reporting to the user

- **Report real outcomes.** If something failed, say so with the output. If a step was skipped, say which and why. Never describe unrun code as working.
- **Distinguish verified from assumed.** Model names, prices, and API field names in this repo have *not* been confirmed against the live API. Say which is which — a wrong price silently corrupts every CPC number in the thesis.
- **Flag methodology risks when they surface**, not at the end. The saturation risk (THESIS.md §11) is the one most likely to invalidate the headline result; if pilot data hints at it, raise it immediately.
