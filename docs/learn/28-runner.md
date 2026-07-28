# Lesson 28 — The paid loop and the cost cap

*Part 3 · about 1.5 hours · `carr/experiment.py`, `carr/runner.py` (414 lines)*

**Every safety property this project has about money lives in `runner.py`. Read
its docstring twice.**

---

## In one sentence

> Before each call the runner asks *"could this one call, at its worst case, push
> the **lifetime** spend past the cap?"* — and if so it stops, having spent
> nothing extra.

---

## `experiment.py` first — the settings and the sample

Two jobs, both required to be reproducible.

**The budget object:**

```python
@dataclass
class Budget:
    max_spend_usd: float
    loaded_usd: float
    abort_at_usd: float
    warn_at_usd: float
    run_headroom: float = 1.25
```

`run_headroom` has the best comment in the file:

> **A bigger account balance is not a bigger budget**; this keeps each run close
> to what the work actually needs even when the lifetime cap has plenty of room.

Two ceilings, and a run obeys whichever binds first:

| | | |
|---|---|---|
| **Lifetime** | `abort_at_usd: 6.00` | total across every run ever |
| **Per run** | `run_headroom: 1.25` | 1.25 × *that run's own* estimate |

The per-run ceiling operationalises the rule *"if it can be done for $2, never
spend $2.20"*. It matters because the lifetime cap having room is not a reason
for a single run to drift.

**Stratified sampling**, with the reason stated in the docstring:

> The first real grid cell — `HumanEval/0` across all 10 configurations — came
> back **10/10 PASS**. A sample drawn uniformly from a pool that is 76% easy
> benchmarks would inherit that, report a near-100% pass rate everywhere, and
> **answer none of the questions the pilot exists to ask.**

⚠️ And the YAML trap: `"off"` must be **quoted**. YAML parses bare `off` as the
boolean `False`, so an unquoted key silently becomes the wrong thing.

---

## `runner.py` — the four properties

### 1. The cap aborts, before spending, on worst case, against lifetime spend

Four adjectives, each load-bearing:

**Aborts** — it stops. It does not warn and continue. (There *is* a warn
threshold, but it is additional, not instead.)

**Before spending** — the check happens before the request is dispatched:

```python
w = nxt.worst_usd(max_tokens)
if spend + reserved + w > abort_at_usd:
    break
```

**On worst case** —

> Worst case is `max_tokens × the output price` — **not an expectation, because
> an expectation that is wrong is exactly the situation a cap exists for.**

**Against lifetime spend** —

```python
def lifetime_spend(conn) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(COALESCE(cost_actual_usd, cost_computed_usd)), 0) "
        "FROM generations WHERE COALESCE(is_mock, 0) = 0").fetchone()[0]
```

> Lifetime, not per-run, because **five careful runs that each stay under their
> own limit still empty the account.**

Note the query itself: actual cost wins over computed, and mock rows are
excluded. The cap reads the same numbers the analysis does.

### ⚠️ 2. The worst case is not the worst case

```python
WORST_CASE_SAFETY = 2.5
```

> `max_tokens` turns out **NOT to be a hard bound**. On 2026-07-26 `qwen3.5-9b`
> returned 35,837 completion tokens against a `max_tokens` of 16,000 — 2.24× —
> and then set `finish_reason` to `"error"`. So "max_tokens × output price" is
> the worst case the *request* asked for, not the worst case that can be billed.

So the pre-call check multiplies by 2.5, chosen above the observed 2.24×, *"so a
single overrun cannot walk through a cap that looked satisfied."*

And a second layer: **actual spend is re-read before every call**, so an overrun
self-corrects for everything after it.

This is a small masterclass in defensive design. The platform violated its own
contract; the response was not to trust it harder but to add a margin **and** a
feedback loop.

### 3. Nothing is ever bought twice

```python
h = db.request_hash(...)
if db.has_generation(conn, h):
    skipped += 1
    continue
```

Checked in `plan()`, **before the work list is even built**. A crash, a Ctrl-C or
a cap abort costs nothing to resume from.

### 4. Cheapest first — with a second mode that exists for a reason

```python
if order == "problem":
    cells.sort(key=lambda c: (c.problem_id, c.expected_usd()))
else:
    cells.sort(key=lambda c: (c.expected_usd(), c.problem_id))
```

| Mode | Behaviour | When it is right |
|---|---|---|
| `cheapest` (default) | every `off` configuration across every problem, then the `high` ones | Filling a grid whose rows are independent — a cap abort leaves the cheap half complete |
| `problem` | finish every configuration for one problem before starting the next | **An effort-axis comparison** — a cap abort leaves *complete* rows for a prefix of problems |

The comment explains the tension precisely: cheapest-first *"completes the cheap
configs across every problem and cuts the expensive ones, so no problem ends up
with a full set."*

**That is the imbalance from lesson 08, anticipated in the code.** Two orderings,
each optimal for a different question, with a comment saying which is which.

---

## Buying and grading are separate phases

```python
def buy(conn, cells, provider, ...):     # phase 1: costs money
def grade_pending(conn, ...):            # phase 2: FREE
```

Why not interleave them?

> Grading is deliberately NOT interleaved. It is free, CPU-bound and slow (an LCB
> problem runs 43 tests twice), and mixing it in serialised the paid calls behind
> it — **the pilot was spending a minute per cell mostly waiting on the grader.**

And the deeper reason: `grade_pending` finds every generation that has code but
no result, so it *"can be re-run at any time — fixing an extraction bug means
re-grading, never re-purchasing."*

That is the `raw_response` principle from lesson 24, expressed as program
structure: **the paid phase and the free phase are separable, so the free one can
be repeated.**

---

## Concurrency without breaking the cap

API calls are I/O-bound and independent, so they run several at a time. But
concurrency plus a budget is a classic way to leak money — three calls in flight
can each individually fit the remaining headroom and collectively exceed it.

The solution is **reservation**:

```python
if spend + reserved + w > abort_at_usd:
    break
...
reserved += w        # reserve the worst case up front
```

> Reserve the worst case up front, so a call is never dispatched on budget that
> another in-flight call might already be using.

And the dispatch pattern is continuous rather than in waves:

> A wave only advances when its **slowest** call returns, so one 180s straggler
> idles every other worker; measured latency on identical prompts already varied
> **2.5s–12.8s**, and thinking calls are far worse.

Note that the argument is made with *measured* numbers, not intuition.

---

## Cost reconciliation, and the alarm

```python
def reconcile_costs(conn, provider, generation_ids, settle_seconds=12.0):
```

Waits **once** for the batch (not once per call), then fills `cost_actual_usd`
and computes drift.

And then the check that matters:

```python
if computed > 0 and abs(actual / computed - 1.0) > 0.05:
    print("!! PRICE TABLE IS WRONG: billed $X against a predicted $Y (1.54x).")
    print("   The cost cap is enforced on the predicted number, so it is not "
          "protecting you.")
```

Read the second line again. **A wrong price table does not merely mis-report
cost — it disables the safety mechanism**, because the cap is computed from the
price table. The alarm says so explicitly and tells you what to run next
(`verify_roster.py`).

The 1.54× in the comment is the real measurement from the unpinned run.

---

## Do this

**1. Read the docstring.**

```bash
cd ~/thesis
sed -n '1,25p' carr/runner.py
```

**2. Run the 16 tests on the cap alone.**

```bash
uv run pytest tests/test_runner.py -v
```

Look for the tests proving a zero-headroom cap buys **literally nothing**, and
that a mid-run stop is resumable.

**3. Price a run without running it.**

```bash
uv run python scripts/pilot.py --dry-run
```

Free. It prints an expected and a worst case. **That is the discipline: never
launch a paid loop you have not priced.**

**4. Check the actual spend the cap was reading.**

```bash
uv run python -c "
from carr import db, runner
conn = db.connect()
print('lifetime spend: \$%.4f' % runner.lifetime_spend(conn))
"
```

Should be about $5.25 — against a $6.00 cap that was never breached.

---

## Check yourself

1. Give the four adjectives describing the cap, and why each matters.
2. What is `WORST_CASE_SAFETY` and what real event caused it?
3. Why is the cap checked against lifetime spend rather than per-run?
4. What does `run_headroom` add that the lifetime cap does not?
5. Why are buying and grading separate phases? Give both reasons.
6. Why must concurrent calls reserve their worst case before dispatch?
7. What is the deeper consequence of a wrong price table, beyond wrong numbers?

<details>
<summary>Answers</summary>

1. **Aborts** (it stops rather than warning); **before spending** (checked prior
   to dispatch, so a refusal costs nothing); **on worst case** (an expectation
   that is wrong is exactly the situation a cap exists for); **against lifetime
   spend** (five runs each within their own limit still empty the account).
2. A 2.5× multiplier on the computed worst case, because `max_tokens` is not a
   hard bound — `qwen3.5-9b` returned 35,837 tokens against a 16,000 ceiling
   (2.24×). It ensures a single overrun cannot slip past a cap that looked
   satisfied.
3. Because a per-run cap permits unlimited runs. Lifetime spend is read from the
   database before every call, so the limit is on the account, not on any one
   invocation.
4. It keeps a single run near its *own* estimate (1.25×) even when the lifetime
   cap has plenty of room — the "if it can be done for $2, never spend $2.20"
   rule made mechanical.
5. Practically: grading is slow and CPU-bound, and interleaving serialised the
   paid calls behind it — about a minute per cell in the pilot. Structurally:
   grading can then be re-run any time for free, so an extraction bug means
   re-grading rather than re-purchasing.
6. Because several in-flight calls can each individually fit the remaining
   headroom while collectively exceeding it. Reserving worst case at dispatch
   makes the accounting sound.
7. The cost cap is computed from the price table, so a wrong table means the cap
   is not protecting you at all — the failure is a disabled safety mechanism, not
   just a reporting error.

</details>

---

➡️ Next: [Lesson 29 — `stats.py` and `analysis.py`: every number in the thesis](29-analysis-code.md)
