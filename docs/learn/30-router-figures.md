# Lesson 30 — `router.py` and `figures.py`

*Part 3 · about 1 hour · `carr/router.py` (280 lines), `carr/figures.py` (250 lines)*

---

## In one sentence

> The router is 280 lines of free features and honest evaluation that produce a
> negative result plus its diagnosis; the figures are 250 lines whose main
> design rule is *"error bars on everything that has an interval"*.

---

## `router.py` — the cheapest possible router

### Every feature is free, and that is the claim

```python
@dataclass
class Problem:
    def features(self) -> tuple[float, ...]:
```

The docstring is emphatic:

> **Every feature here is free.** No forward pass, no draft answer, no hidden
> states, no embedding model — only what the problem statement already tells you
> before a single token is bought. That is the whole "cheapest possible router"
> claim; **a router that must first call a model to decide whether to call a
> model has already spent the money it was trying to save.**

That last sentence is the argument against DART, your nearest training-free
competitor, which must generate draft answers to route. Put it in Chapter 2.

The features: difficulty rank, test count, prompt length.

```python
DIFFICULTY_RANK = {"mbpp_plus": 0, "humaneval_plus": 1,
                   "easy": 2, "medium": 3, "hard": 4}
```

**Ordinal, not categorical**, with the reason measured: *"the easy benchmarks sit
below LiveCodeBench-easy: measured pass rates are 72–97% against 94–100%."* The
ordering is not assumed — it is derived from your own data, so a router can use
"harder than" rather than just "different from".

### Three routers, so the comparison means something

```python
def route_always(config_id):        # always the same config — the trivial baseline
def route_by_difficulty(cheap, dear, threshold=3):   # a hand-written rule
def route_knn(k=5):                 # nearest neighbours
```

Having `route_always` matters: **it is the collapse, implemented deliberately.**
When k-NN scores exactly what `route_always` scores, you can say the collapse
happened rather than inferring it.

`route_by_difficulty` is a two-line human rule — cheap below the threshold, dear
above. If a hand-written rule beats k-NN, that is worth knowing too.

### Leave-one-out, because 60 problems is small

```python
def evaluate(conn, router, config_ids, problem_ids, ...):
```

> Evaluation is leave-one-out cross-validation, because the usable set is ~60
> problems and **a single train/test split at that size measures the split more
> than the method.**

Each problem is predicted using all the others and never itself.

### The decomposition — "the most genuinely yours"

```python
def feature_ceiling(conn, config_ids, problem_ids) -> dict:
def decompose_gap(conn, config_ids, problem_ids, ...) -> dict:
```

`feature_ceiling` answers: *what is the best accuracy achievable from these
features alone?* Bucket problems by feature values, give each bucket its best
possible configuration, and see how far that gets.

`decompose_gap` splits the router→oracle gap:

| | |
|---|---|
| oracle | 98.3% |
| feature ceiling | 98.3% |
| k-NN | 65.0% |
| **feature insufficiency** | 98.3 − 98.3 = **0.0** |
| **estimation error** | 98.3 − 65.0 = **33.3** |

**The features are sufficient. The estimator is not.** That is the contribution —
THESIS.md §10.2 calls it *"the most genuinely yours"*, and it is what converts a
failure into a direction.

⚠️ The caveat is recorded in the code: the ceiling is **fitted** over 12 buckets
on 60 problems (5 each), so it is an optimistic upper bound, not an achievable
target. `tests/test_router.py` includes tests that the decomposition assigns
blame correctly — because a decomposition that could not be wrong would not be
evidence.

---

## `figures.py` — four PNGs, and a design philosophy

```
fig_effort_by_tier     when thinking helps, and where it does not
fig_reasoning_outcome  long reasoning means failure, not effort
fig_frontier           the cost-accuracy hull, the oracle, and the gap
fig_abort_curve        the honest tradeoff, with its uncertainty band
```

**One figure per claim the thesis actually makes.** Not one per interesting
query — per *claim*. That constraint is why there are four and not twelve, and it
is a good rule to keep when you are tempted to add more.

### The four design rules, and why each

> **Error bars wherever an interval exists.** A bare bar chart of these numbers
> would imply a precision the data does not have — five configuration pairs have
> overlapping CPC intervals, and the whole point of computing them was to stop
> that being invisible.

> **Greyscale-safe.** Colour carries no information that hatching, position or a
> label does not also carry.

> **Sample sizes printed on the figure.** Several panels rest on 60–107 problems
> and a reader deserves to see that without hunting for it.

> **No chart junk:** no gridlines behind bars, no 3D, no truncated y-axes on
> proportions — a bar chart of percentages starts at zero.

Every one of those is defensible out loud, which is the test for a design rule in
a thesis. Rule 1 in particular: the figures are the most-looked-at part of any
document, and a figure that overstates precision undoes the honesty of the text
around it.

### Two implementation details

```python
matplotlib.use("Agg")     # headless: no display on a build machine
```

Renders to a file without needing a window — so figures can be regenerated
anywhere, including in a script.

```python
FIGURE_DIR = ROOT / "data" / "figures"   # gitignored; regenerated, never edited
```

**Never hand-edited.** If a figure is wrong, the fix is in the code, and every
regeneration is identical. A hand-tweaked PNG is a number that no longer matches
its source — the same failure mode as a stale price table.

And `make_all` **survives one panel failing** rather than losing them all — tested,
because losing three good figures to one bad one at 2am before a deadline is a
real failure mode.

---

## Do this

**1. See the collapse implemented as a baseline.**

```bash
cd ~/thesis
sed -n '112,160p' carr/router.py
```

Read `route_always` and `route_knn` side by side. **They score the same, and that
is the finding.**

**2. Run the router tests.**

```bash
uv run pytest tests/test_router.py -v
```

Ten tests. Note which ones check leave-one-out honesty.

**3. Reproduce the decomposition.**

```bash
uv run python scripts/results.py | sed -n '/RQ4b/,/RQ3/p'
```

**4. Regenerate the figures and look at all four.**

```bash
uv run python scripts/make_figures.py && open data/figures/
```

For each one, ask: *what single claim does this figure support?* If you cannot
answer in one sentence, the figure is not earning its place — and all four
should pass that test.

**5. Check the error bars are really there.**

Open `01-effort-by-tier.png` and find the bars whose intervals overlap.
**Those overlaps are the reason the figure has error bars at all.**

---

## Check yourself

1. What makes the router "the cheapest possible", and what is the one-sentence
   argument against a router that generates drafts?
2. Why is difficulty ordinal rather than categorical, and how was the ordering
   justified?
3. Why does `route_always` exist?
4. Why leave-one-out rather than a train/test split?
5. Explain the gap decomposition and what it concludes.
6. What is the caveat on the feature ceiling?
7. Give two of the figure design rules and defend each in one sentence.

<details>
<summary>Answers</summary>

1. It uses only features computable before any token is bought — difficulty,
   test count, prompt length — with no forward pass, drafts, hidden states or
   training. The argument: a router that must first call a model to decide
   whether to call a model has already spent the money it was trying to save.
2. Because the tiers really are ordered and a router should be able to use that.
   The ordering was checked against measured pass rates: the easy benchmarks sit
   at 72–97% against LiveCodeBench-easy's 94–100%.
3. So the collapse is measurable rather than inferred: when k-NN scores exactly
   what "always pick one configuration" scores, you can state that it collapsed.
4. Because with ~60 problems a single split measures the split more than the
   method.
5. It compares the oracle (98.3%), the ceiling achievable from the features alone
   (98.3%) and what k-NN achieves (65.0%), giving 0.0 points of feature
   insufficiency and 33.3 of estimation error — the features are sufficient, the
   estimator is not.
6. It is fitted over 12 buckets on 60 problems (5 each), so it is an optimistic
   upper bound rather than an achievable target.
7. Any two: error bars wherever an interval exists (a bare chart would imply
   precision the data lacks, and five CPC pairs overlap); greyscale-safe (colour
   must never be the only carrier of information); sample sizes on the panel
   (several rest on 60–107 problems); y-axes start at zero for proportions (a
   truncated axis exaggerates differences).

</details>

---

➡️ Next: [Lesson 31 — `scripts/` and `tests/`](31-scripts-and-tests.md)
