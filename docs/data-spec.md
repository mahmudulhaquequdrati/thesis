# Data specification

Exactly what we send to a model, exactly what comes back, exactly what we store.
This is the contract the harness implements. Verified against real evalplus data
on 2026-07-25.

---

## 1. What a benchmark problem is

Three fields matter. Everything else is metadata.

| Field | Example (`HumanEval/0`) | Sent to model? |
|---|---|---|
| `prompt` | function signature + docstring, ~396 chars | **YES, verbatim** |
| `entry_point` | `has_close_elements` | No — the grader needs it |
| `base_input` + `plus_input` | 7 + 999 = **1,006 test cases** | **NEVER** — leaking tests would invalidate everything |

```python
# HumanEval/0 prompt -- this exact text is the user message
from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
```

**Measured prompt sizes** (chars ÷ 4 ≈ tokens):

| Benchmark | n | median tokens | max tokens |
|---|---|---|---|
| HumanEval+ | 164 | **99** | 340 |
| MBPP+ | 378 | **36** | 121 |
| LiveCodeBench | ~150 | not yet measured — expect 500–1,500 |

> **Consequence:** input cost is negligible. At $0.10–0.44/M input, 300 problems
> × 200 tokens is under 3 cents across the entire roster. **Effectively 100% of
> the budget is output and reasoning tokens.** Cost control therefore means
> controlling thinking, not prompt engineering.

---

## 2. What we send

One request per (problem × config). No system prompt — it would be a confound we
did not design for, and it changes token counts.

```python
{
  "model": "deepseek/deepseek-v4-flash",        # from config/models.yaml
  "messages": [{"role": "user", "content": PROMPT}],   # the raw prompt, unmodified
  "temperature": 0,                              # determinism; halves cost via n=1
  "max_tokens": 16000,                           # runaway-trace guard
  "reasoning": {"effort": "high"},               # or {"enabled": false} -- the effort axis
}
```

**Three rules:**

1. **The prompt is sent unmodified.** No "you are an expert programmer", no
   few-shot examples, no "think step by step". Any of those would change token
   counts and confound the effort axis, which is the variable under study.
2. **`max_tokens` is a cost control**, not a quality setting. A truncated
   response is a legitimate ❌ that cost a known, bounded amount.
3. **`reasoning` is the entire experimental manipulation.** Everything else is
   held constant across configs.

---

## 3. What comes back

Measured on a real call (`qwen/qwen3-8b`, "reverse a string"):

```
prompt_tokens      23
completion_tokens  412      <- billed
reasoning_tokens   392      <- 95% of it, and INVISIBLE in the text
```

The visible answer was three lines. **Deriving cost from response length would
have understated this call by 20×.** Read
`usage.completion_tokens_details.reasoning_tokens`, always.

Ground truth is available from `GET /api/v1/generation?id=<id>`, which returns
`total_cost` and `native_tokens_reasoning`. **It takes ~10 seconds to settle**
(404 before then), so the runner collects generation IDs and reconciles in a
batch after the run — never blocking per call.

---

## 4. Extraction

The model returns markdown, not code:

````
```python
def has_close_elements(numbers, threshold):
    ...
```
````

`extract_code()` takes the first ```` ```python ```` fenced block, or the whole
response if there is no fence. **Store `raw_response` verbatim regardless** —
extraction logic has bugs, and keeping the raw text means re-parsing offline for
free instead of re-buying 2,600 generations.

---

## 5. Grading

```
extracted_code + evalplus test inputs  ->  Docker container  ->  passed: bool
```

No network, memory cap, ~10s per-test timeout. `HumanEval/0` alone has 1,006
assertions, so grading is CPU-bound and slow — but it is **free**, unlike
generation. Grade offline from stored responses; never re-call the API to re-grade.

`passed` = every assertion survives. Partial credit is recorded in
`n_tests_passed` but is not the metric — pass@1 is binary.

---

## 6. The tables

### `problems` — one row per problem, populated once, free

| Column | Type | Source |
|---|---|---|
| `problem_id` | TEXT PK | `task_id`, e.g. `HumanEval/0` |
| `benchmark` | TEXT | `humaneval_plus` / `mbpp_plus` / `livecodebench` |
| `difficulty` | TEXT | `easy` / `medium` / `hard` — LCB only. NULL for HE+/MBPP+, which ship no difficulty label; recording 'easy' would be an invention |
| `prompt` | TEXT | Sent verbatim |
| `entry_point` | TEXT | Function name the tests call |
| `tests_blob` | BLOB | Pickled base+plus inputs. **Never sent** |
| `n_tests` | INTEGER | Test count — **a CARR feature** |
| `prompt_chars` | INTEGER | **A CARR feature** |
| `release_date` | TEXT | LCB only — contamination filtering |

### `configs` — one row per (model × effort), 10 rows

| Column | Type | Source |
|---|---|---|
| `config_id` | INTEGER PK | |
| `model_slug` | TEXT | `config/models.yaml` |
| `family` | TEXT | `qwen` / `deepseek` / `moonshot` — for within- vs cross-family analysis |
| `effort_label` | TEXT | `off` / `high` |
| `effort_mechanism` | TEXT | `native_toggle` / `budget_forcing` — **these are not equivalent; results must split by it** |
| `params_json` | TEXT | The exact `reasoning` block sent |
| `price_in_per_m` | REAL | Verified price, snapshot-dated |
| `price_out_per_m` | REAL | Verified price |
| `snapshot_date` | TEXT | Reproducibility |

### `generations` — one row per API call, **~2,600 rows. This is the money table.**

| Column | Type | Source |
|---|---|---|
| `gen_id` | INTEGER PK | |
| `problem_id` | TEXT FK | |
| `config_id` | INTEGER FK | |
| `request_hash` | TEXT **UNIQUE** | sha256(model+effort+prompt+params). **Checked before every call — this is what stops us paying twice** |
| `openrouter_gen_id` | TEXT | For batch cost reconciliation |
| `raw_response` | TEXT | Verbatim. Enables free re-grading |
| `extracted_code` | TEXT | What actually gets executed |
| `prompt_tokens` | INTEGER | `usage` |
| `completion_tokens` | INTEGER | `usage` |
| `reasoning_tokens` | INTEGER | `usage.completion_tokens_details` — **the field everyone misses** |
| `cost_computed_usd` | REAL | tokens × price table |
| `cost_actual_usd` | REAL | `/generation.total_cost` — ground truth |
| `finish_reason` | TEXT | `stop` / `length`. `length` = hit `max_tokens` |
| `latency_ms` | INTEGER | |
| `temperature_sent` | REAL | Some endpoints override it silently — log what we sent |
| `error` | TEXT | NULL on success |
| `created_at` | TEXT | |

### `results` — one row per graded generation, free to regenerate

| Column | Type | Source |
|---|---|---|
| `gen_id` | INTEGER PK FK | |
| `passed` | INTEGER | 1 only if **both** base and plus tests survive |
| `base_passed` | INTEGER | Original benchmark tests only. Added 2026-07-26 — `GradeResult` already produced it, and the §11 saturation check needs it |
| `n_tests_passed` | INTEGER | Diagnostic, not the metric |
| `n_tests_total` | INTEGER | |
| `error_type` | TEXT | **`assertion` or `timeout` only**, enforced by a CHECK constraint. Narrowed 2026-07-26: `grade()` never emits `syntax` or `exception`, and a documented-but-impossible value is a trap for anyone writing a query against it |
| `exec_ms` | INTEGER | |

Implemented in [`carr/db.py`](../carr/db.py); that file is authoritative.

---

## 7. One problem, end to end

```
problems       HumanEval/0 | humaneval_plus | easy | 1006 tests | 396 chars
                     |
                     |  x 10 configs
                     v
generations    gen 1: qwen3.5-9b      off  | 99 in |   180 out |    0 reasoning | $0.000037
               gen 2: qwen3.5-9b      high | 99 in | 3,200 out | 3,050 reasoning | $0.000490
               gen 3: v4-flash        off  | 99 in |   210 out |    0 reasoning | $0.000049
               ...
               gen 9: kimi-k2.6       high | 99 in | 4,100 out | 3,900 reasoning | $0.011216
                     |
                     |  grade in Docker (free)
                     v
results        gen 1: PASS  1006/1006
               gen 2: PASS  1006/1006
               ...
                     |
                     v
CARR label     cheapest config that PASSED = qwen3.5-9b/off  ($0.000037)
               vs. always-best-model                          ($0.011216)
               -> 303x overpayment avoided on this problem
```

**That last line is the thesis.** `cheapest_passing_config` is computed per
problem by a SQL query over `generations ⋈ results` — which is why every problem
must run through **every** config. A sparse grid makes this label uncomputable.

---

## 8. Row counts and cost

| Table | Rows | Cost to build | Cost to rebuild |
|---|---|---|---|
| `problems` | ~300 | free | free |
| `configs` | 9 | free | free |
| `generations` | **~2,600** | **$3.60** | **$3.60 — never do this** |
| `results` | ~2,600 | free (CPU) | free |
| `features` | ~300 | free (local embeddings) | free |

Only one table costs money. It is also the only one that cannot be regenerated
from the others. Back up `data/carr.sqlite` separately, outside git.
