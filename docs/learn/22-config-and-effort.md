# Lesson 22 — The roster, the configurations, and the money

*Part 3 · about 1 hour · `config/models.yaml`, `carr/effort.py`, `carr/cost.py`*

---

## In one sentence

> One YAML file knows every model name and price; one module expands it into the
> 10 configurations with a **stable** identity; and one 25-line module turns
> tokens into dollars without double-counting reasoning.

---

## `config/models.yaml` — the only file that knows a model name

`CLAUDE.md` §3: **never hardcode a model name.** The open-weight landscape moves
every 6–8 weeks; one file being wrong is recoverable, twenty is not.

Each entry carries what you need to reproduce a call *and* to defend it:

```yaml
- slug: deepseek/deepseek-v4-flash
  provider: baidu/fp8            # pins provider AND quantization
  quantization: fp8              # held constant across the roster
  provider_uptime_30m: 100.0
  family: deepseek
  price_in_per_m: 0.091
  price_out_per_m: 0.182
  context_length: 1048576
  efforts:
    - label: "off"
      mechanism: native_toggle
      params: {reasoning: {enabled: false}}
    - label: "high"
      mechanism: native_toggle
      params: {reasoning: {effort: "high"}}
```

Five things to notice:

1. **`provider` pins provider *and* precision in one field** — `baidu/fp8`.
   Lesson 19's entire chapter is enforced by that one string.
2. **`params` is the experimental manipulation**, stored as data. `openrouter.py`
   sends it verbatim and is forbidden from constructing it.
3. **`mechanism`** distinguishes a native thinking toggle from prompt-based
   budget forcing. They are not equivalent, so results must be splittable by it.
   Every entry is `native_toggle` today; the column exists so a future mixed
   roster cannot silently confound them.
4. **Exact prices, not rounded** — `0.091`, not `0.09`. `cost_computed_usd` is
   compared against `cost_actual_usd` to detect price drift, and a 0.2% rounding
   error would read as permanent drift.
5. **`uptime` is recorded** because `allow_fallbacks` is off: a provider outage
   means failed calls, so the choice of provider is partly an availability bet.

And two sections most projects would not have:

- **`held_out:`** — Kimi, `subset_only: true`, with a comment explaining that
  `subset_only` cuts *problems*, never the effort axis, because a single effort
  level would leave it with one point on the cost-accuracy plane.
- **`rejected:`** — models considered and turned down, **with reasons**. That is
  a small, excellent habit: it stops you re-litigating the same decision in six
  weeks, and it is a ready-made paragraph for Chapter 3.

---

## `carr/effort.py` — roster → 10 configurations

127 lines. It reads the YAML and produces a list of `Config` records.

### The one thing to understand: two different orderings

```python
# Identity first, on a key that prices cannot move.
configs.sort(key=lambda c: (c.model_slug, c.effort_label))
for i, c in enumerate(configs):
    c.config_id = i

# Then run order, which prices are expected to move.
configs.sort(key=lambda c: (c.price_out_per_m, c.model_slug, c.effort_label))
for i, c in enumerate(configs):
    c.tier_index = i
```

Two sorts, two fields, and they answer different questions:

| Field | Sorted by | Purpose | May it change? |
|---|---|---|---|
| `config_id` | **alphabetical** (slug, effort) | **Identity.** Goes in the database; every generation points at it | **Never** |
| `tier_index` | **price** | **Run order.** Cheapest first, so a cap abort costs the expensive tail | Freely |

### ⚠️ The bug this shape exists to prevent

Read the comment in the source — it is the best single comment in the repository:

> `config_id` *was previously the cheapest-first position, which was a bug:
> changing a price re-sorted the list, so `config_id` 4 meant `deepseek-v4-pro`
> one day and `qwen3.6-35b-a3b` the next. **Eight already-bought rows ended up
> attributed to the wrong model.** An identity must not depend on a value that is
> expected to move.*

How it was caught: not by a test, but by a `UNIQUE` constraint failing during an
**unrelated** migration. Otherwise every per-model number in the thesis would
have been quietly wrong.

How it was repaired: using `request_hash` as ground truth — the hash contains the
model slug, so each affected row could be resolved back to the model that
actually produced it. **All 149 rows resolved exactly, none guessed**, and the
repair was verified to change no conclusions.

Three lessons worth carrying out of this project entirely:

1. **An identifier must never encode a mutable property.**
2. **Store enough redundancy to repair.** Because `request_hash` existed, the
   damage was recoverable rather than fatal.
3. **A constraint that fires is cheaper than a number that is quietly wrong.**

### One more subtlety

```python
subset_only=bool(entry.get("subset_only", False)),
```

with the comment: *read the flag rather than inferring it from which YAML key the
model sat under — the two happen to agree today, and silently disagreeing later
is exactly the kind of bug that costs money.*

There was already a related bug: `subset_only` was **stored but never honoured**,
so the runner planned Kimi over the whole grid at $3.40/M. Fixing it cut the grid
cost from **$7.51 to $4.59** — which is what made it fit under the $6 cap.

---

## `carr/cost.py` — 25 lines that could invalidate everything

```python
def compute_cost(prompt_tokens, completion_tokens, price_in_per_m, price_out_per_m):
    p_in = (prompt_tokens or 0) * price_in_per_m
    p_out = (completion_tokens or 0) * price_out_per_m
    return (p_in + p_out) / 1e6
```

**Reasoning tokens do not appear.** That is the entire point.

> `completion_tokens` is the billed total; `reasoning_tokens` is a **subset** of
> it. Adding the two double-charges every thinking configuration — inflating
> exactly the configurations the thesis is about, silently, by roughly 2×.

The file is 25 lines of code and 14 lines of docstring, and the docstring is
carrying the weight. That ratio is correct here: the code is obvious and the
*reason* is not.

### The two-cost design

`compute_cost` produces `cost_computed_usd` — an estimate. Ground truth is
`cost_actual_usd`, fetched from OpenRouter's `/generation` endpoint.

Both are stored on every row. Why keep an estimate you know is inferior?

> **Because their disagreement is the only detector of silent price drift.**

`runner.reconcile_costs()` acts on it, and the message it prints when they
diverge by more than 5% is worth reading in full:

> `!! PRICE TABLE IS WRONG: billed $X against a predicted $Y (1.54x).`
> `The cost cap is enforced on the predicted number, so it is not protecting
> you.`

That second line is the real point. **The cap is computed from the price table,
so a wrong price table does not merely mis-report cost — it disables the safety
mechanism.** That is the kind of second-order reasoning worth pointing at in
Chapter 3.

The 1.54× in that comment is not hypothetical: it is what an unpinned run
actually billed.

---

## Do this

**1. Print the configurations.**

```bash
cd ~/thesis
uv run python -m carr.effort
```

**2. See both orderings.**

```bash
uv run python -c "
from carr.effort import load_configs
for c in sorted(load_configs(), key=lambda c: c.config_id):
    print(f'id={c.config_id}  tier={c.tier_index}  {c.label}')
"
```

`config_id` is alphabetical; `tier_index` is by price. **They disagree, and that
disagreement is the fix for the bug.**

**3. Read the comment that documents the bug.**

```bash
sed -n '43,55p' carr/effort.py
```

**4. Read the whole of `cost.py`.**

```bash
cat carr/cost.py
```

37 lines including blanks. You can hold all of it in your head — which is what
you want from the file that converts tokens into every dollar in the thesis.

**5. Check for price drift in your own data.**

```sql
SELECT ROUND(SUM(cost_actual_usd) / SUM(cost_computed_usd), 4) AS drift_ratio
FROM generations
WHERE is_mock = 0 AND cost_actual_usd IS NOT NULL;
```

Near 1.0 means the price table matches the bill.

---

## Check yourself

1. Why may no model name appear anywhere except `models.yaml`?
2. What does the `provider` field pin, and why does that matter twice over?
3. What is the difference between `config_id` and `tier_index`?
4. Describe the `config_id` bug, how it was caught, and how it was repaired.
5. Why are prices stored unrounded?
6. Why does `compute_cost` never mention reasoning tokens?
7. Why store a computed cost when you have the actual one — and what does a
   divergence disable?

<details>
<summary>Answers</summary>

1. Because the roster changes every 6–8 weeks; a single source means one edit,
   and it keeps prices, snapshot dates and pinning together with the name.
2. The provider *and* the quantization (`baidu/fp8`). It fixes the price (up to
   4× variation) and the model's precision, so a failure is attributable to the
   model rather than to compression.
3. `config_id` is a stable, alphabetical identity stored in the database.
   `tier_index` is a price-based run order, expected to change.
4. `config_id` used to be a price-sorted position, so repricing a model reassigned
   ids and 8 purchased rows were attributed to the wrong model. It surfaced as a
   `UNIQUE` failure during an unrelated migration, and was repaired using
   `request_hash` — which contains the slug — resolving all 149 rows exactly.
5. Because computed cost is compared against actual cost to detect price drift,
   and rounding would produce a permanent false drift signal.
6. Because reasoning tokens are already inside `completion_tokens`. Adding them
   would double-charge every thinking configuration by about 2×, silently.
7. Their disagreement is the only way to detect a silent price change. And since
   the cost cap is computed from the price table, a wrong table means the cap is
   no longer protecting you.

</details>

---

➡️ Next: [Lesson 23 — The provider contract, and the file that spends money](23-providers.md)
