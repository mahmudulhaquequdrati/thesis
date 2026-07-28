# Lesson 29 — `stats.py` and `analysis.py`: every number in the thesis

*Part 3 · about 1.5 hours · `carr/stats.py` (120 lines), `carr/analysis.py` (675 lines)*

---

## In one sentence

> `analysis.py` is pure SQL and arithmetic over the purchased table, `stats.py`
> puts an interval on everything, and between them they produce every number you
> will write down.

---

## `stats.py` — 120 lines, stdlib only

The whole bootstrap:

```python
rng = random.Random(seed)
values = []
for _ in range(n_resamples):
    resample = [items[rng.randrange(n)] for _ in range(n)]
    value = statistic(resample)
    if value is not None:
        values.append(value)

values.sort()
alpha = (1.0 - confidence) / 2.0
return (_percentile(values, alpha), _percentile(values, 1.0 - alpha))
```

That is lesson 09 in seven lines: draw `n` items **with replacement**, recompute
the statistic, repeat 10,000 times, take the 2.5th and 97.5th percentiles.

Four design points, each defended in the source:

**1. `items` are always PROBLEMS.**

> `items` are the independent units being resampled — for this project that is
> always PROBLEMS, never individual cells, because two cells on the same problem
> are not independent observations of difficulty.

**2. The statistic receives the whole resample.**

```python
def ratio(numerator, denominator):
    def stat(sample):
        den = sum(denominator(x) for x in sample)
        if den <= 0:
            return None
        return sum(numerator(x) for x in sample) / den
    return stat
```

Sum of costs ÷ sum of solved — **not** the average of per-problem ratios. The
docstring names it as *"the specific mistake section 10.2 warns about"* and
points at the test that pins it:
`tests/test_stats.py::test_ratio_is_not_the_mean_of_ratios`.

**3. Degenerate cases say so rather than pretending.**

```python
if n == 1:
    # One observation carries no information about spread.
    value = statistic(items)
    return (math.nan, math.nan) if value is None else (value, value)
```

And `ci_str` renders `nan` as **blank** rather than as the string `"nan"` — a
missing interval should look missing, not look like a number.

**4. `None` is meaningful.** `ratio` returns `None` when the denominator is
zero, because *"a config that solved nothing has no cost-per-correct, and that is
a real outcome on the hard tier rather than an error."* `bootstrap_ci` drops
those resamples.

Why no scipy: the docstring says the reason plainly, and the same judgement
appears for the convex hull. A dependency should earn its place.

---

## `analysis.py` — the two constants that shape everything

At the top, two SQL fragments reused in nearly every query:

```python
_COST = "COALESCE(g.cost_actual_usd, g.cost_computed_usd)"
_REAL = "COALESCE(g.is_mock, 0) = 0"
```

**Actual cost where OpenRouter told you, your estimate otherwise — never the
estimate alone**, *"because the price table was wrong by 1.54× before providers
were pinned and only the billed number is trustworthy."*

And then the distinction that lesson 23 set up, made operational:

```python
_INFRA  = f"(g.error IS NOT NULL AND COALESCE({_COST}, 0) <= 0)"
_WASTED = (f"(COALESCE({_COST}, 0) > 0 "
           f"AND (g.finish_reason = 'length' OR g.error IS NOT NULL))")
```

> A 404 from a pinned provider, or a 429 when it is overloaded, says nothing
> about the model — but it produces a row with `error` set, and counting it as a
> failure **understates the pass rate**. It costs $0, because nothing ran.
>
> A call that burned 16,000 tokens and returned no answer also has `error` set,
> but it **was billed in full and IS a model outcome** — the most expensive kind.
>
> So: billed and no usable answer = **wasted**. Not billed = **infrastructure**,
> and it is excluded from every rate rather than silently scored as a failure.

**Whether a call was billed is what separates a model outcome from an
infrastructure one.** Every pass rate in the thesis depends on that line being
right. Merging the two would simultaneously depress every pass rate with network
noise *and* dilute the waste finding.

---

## The functions, grouped by which lesson they produce

| Function | Produces | Lesson |
|---|---|---|
| `saturation()` | pass rate off vs on, per tier | 13 |
| `discriminating_problems()` | 81 / 98 / 141 | 13 |
| `reasoning_by_tier()` | 642 → 17,547 mean reasoning tokens | 15 |
| `waste()` | the three-way outcome table | 15 |
| `censoring()` | 26.3% truncation | 14, 16, 20 |
| `abort_curve()`, `best_threshold()`, `abort_curve_ci()` | the tradeoff curve; `None` | 16 |
| `paired_problems()` | **107** | 8, 14 |
| `cost_per_correct()`, `pass_rate_ci()` | CPC/TPC with intervals | 9, 10 |
| `frontier_subset()`, `frontier()` | the 6 × 60 set and its points | 17 |
| `pareto_front()`, `upper_hull()`, `hull_accuracy_at()` | dominance, the two vertices | 17 |
| `oracle()` | 98.3% at $0.00111 | 17 |

Read that table as a map: **each row is a paragraph of your results chapters,
and the function is where its number comes from.**

### `paired_problems()` — the comparability fix

```sql
GROUP BY g.problem_id
HAVING SUM(CASE WHEN c.effort_label  = 'off' THEN 1 ELSE 0 END) > 0
   AND SUM(CASE WHEN c.effort_label != 'off' THEN 1 ELSE 0 END) > 0
```

"Keep problems that have at least one `off` row **and** at least one thinking
row." That is the 107.

Two details:

- Infrastructure failures are excluded, so *"a problem whose only thinking row
  was a 429 does not count as paired: nothing ran, so there is nothing to
  compare."*
- The docstring notes that requiring **all ten** configurations leaves only
  **5** problems — which is why the frontier work uses six.

### `_per_problem_config()` — why the shape is what it is

```python
"""One row per (config, problem) so the bootstrap can resample PROBLEMS."""
```

The data is deliberately materialised **problem-wise** so that `bootstrap_ci`
can resample the right unit. The statistical requirement from lesson 09 shows up
here as a *data structure* decision — which is usually where such requirements
have to be enforced, because by the time you are inside the resampling loop it is
too late.

Note also:

```sql
CASE WHEN {_WASTED} THEN 0 ELSE COALESCE(r.passed, 0) END AS solved
```

A wasted call counts as **not solved** even if a stray grade exists. Cost counted,
credit not.

### `upper_hull()` — twenty lines instead of scipy

```python
def cross(o, a, b) -> float:
```

A monotone chain: sort by cost, then walk the points keeping only those that
turn the right way. The cross product tells you which way three points turn.

Adding scipy for this would have pulled in a large numerical stack to save
twenty lines. **Knowing when not to add a dependency is a judgement worth one
sentence in Chapter 3.**

### `abort_curve()` — a simulation resting on a measured fact

The module docstring flags it:

> `abort_curve` is the headline deliverable. It is a **simulation** over
> completed calls, and it relies on one measured fact: **aborting a stream
> mid-reasoning is billed $0.00** (verified 2026-07-26 on two providers, against
> $0.010978 for the same cell run to completion). So an aborted call is scored as
> costing **nothing** and solving nothing — not as a pro-rata saving.

Two things to take from this:

1. **Be explicit that it is a simulation.** You did not run the grid twice with
   an abort enabled; you replayed completed calls under an abort rule. Say so in
   Chapter 7.
2. **The simulation is only valid because of a measurement.** If cancellation
   were billed pro-rata, every number in the curve would be wrong. The measured
   fact is load-bearing, and it is cited at the point of use.

---

## Do this

**1. Read the module docstring.**

```bash
cd ~/thesis
sed -n '1,47p' carr/analysis.py
```

Lines 26–46 are the billed/unbilled argument. That is Chapter 3 material.

**2. Call the functions directly.**

```bash
uv run python -c "
from carr import db, analysis
conn = db.connect()
print('discriminating:', analysis.discriminating_problems(conn))
print('paired problems:', len(analysis.paired_problems(conn)))
print('frontier subset:', analysis.frontier_subset(conn))
"
```

You should see 141 discriminating, 107 paired, and a (configs, problems) pair
near 6 and 60. **You just produced three of the thesis's headline denominators
in one command.**

**3. Prove the ratio rule matters.**

```bash
uv run pytest tests/test_stats.py -v -k ratio
```

**4. Watch a bootstrap being reproducible.**

```bash
uv run python -c "
from carr.stats import bootstrap_ci, proportion
items = [1,1,0,1,0,1,1,0,1,1]
f = proportion(lambda x: x == 1)
print(bootstrap_ci(items, f, seed=0))
print(bootstrap_ci(items, f, seed=0))   # identical
print(bootstrap_ci(items, f, seed=1))   # different
"
```

Same seed, same interval. **That is reproducibility, demonstrated in four
lines.**

**5. Count infrastructure failures excluded from your rates.**

```sql
SELECT COUNT(*) FROM generations
WHERE is_mock = 0 AND error IS NOT NULL
  AND COALESCE(cost_actual_usd, cost_computed_usd, 0) <= 0;
```

Every one is excluded from every pass rate — correctly, because nothing ran.

---

## Check yourself

1. Why does `bootstrap_ci` resample problems rather than cells, and where is
   that requirement enforced?
2. Why must a ratio statistic receive the whole resample?
3. What is the difference between `_INFRA` and `_WASTED`, and what breaks if you
   merge them?
4. Why does `_COST` prefer `cost_actual_usd`?
5. How does `paired_problems()` produce 107, and why do only 5 problems have all
   ten configurations?
6. Why is `abort_curve` described as a simulation, and which measurement makes
   it valid?
7. Why no scipy for the convex hull?

<details>
<summary>Answers</summary>

1. Because cells on the same problem share that problem's difficulty and are not
   independent; resampling cells would make every interval too narrow. It is
   enforced by the shape of the data — `_per_problem_config()` materialises one
   row per (config, problem) so problems are the resampling unit.
2. Because CPC is a ratio of sums — total cost ÷ total solved — not a mean of
   per-problem ratios. Those are different quantities, and a test pins the
   distinction.
3. `_INFRA` is a failure that was never billed (a 429 or 404) and says nothing
   about the model, so it is excluded from every rate. `_WASTED` is a billed call
   that returned nothing usable — a genuine, expensive model outcome. Merging
   them would depress every pass rate with network noise and dilute the waste
   finding.
4. Because the price table was wrong by 1.54× before providers were pinned, so
   only the billed number is trustworthy. The computed cost is a fallback and a
   drift detector.
5. It keeps problems having at least one `off` row and at least one thinking row,
   excluding infrastructure failures. Requiring all ten configurations leaves 5
   problems, because the thinking arms ran on far fewer problems than the `off`
   arms.
6. Because it replays already-completed calls under a hypothetical abort rule
   rather than re-running the grid. It is valid because cancelling a stream
   mid-reasoning was measured to be billed $0.00 on two providers — otherwise an
   aborted call would need pro-rata costing and every number would change.
7. Because a 2D upper hull is a twenty-line monotone chain, and pulling in a
   large numerical stack to save twenty lines is not a good trade.

</details>

---

➡️ Next: [Lesson 30 — `router.py` and `figures.py`](30-router-figures.md)
