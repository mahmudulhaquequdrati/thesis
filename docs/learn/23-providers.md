# Lesson 23 — The provider contract, and the file that spends money

*Part 3 · about 1 hour · `carr/providers/base.py`, `carr/providers/openrouter.py`*

---

## In one sentence

> `base.py` defines what a backend must return; `openrouter.py` is the only file
> in the project that costs money, and it is written around four things it must
> not get wrong.

---

## `base.py` — the contract (63 lines)

Three pieces.

**`Usage`** — token counts, with the trap documented in the docstring:

```python
@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int = 0        # a SUBSET of completion_tokens

    @property
    def visible_tokens(self) -> int:
        return max(0, self.completion_tokens - self.reasoning_tokens)
```

`visible_tokens` is a small piece of thoughtfulness: it makes the invisible
portion computable, which is what the thesis is about. On day 1 that would have
read 20 visible against 412 billed.

**`Generation`** — one API response, successful *or not*:

```python
@dataclass
class Generation:
    raw_response: str | None = None
    usage: Usage | None = None
    finish_reason: str | None = None      # 'stop' | 'length'
    latency_ms: int = 0
    error: str | None = None              # non-None means no usable response
    provider_gen_id: str | None = None    # for batched cost reconciliation
    is_mock: bool = False
    mock_mode: str | None = None
```

**A failure is a `Generation`, not an exception.** That single choice is what
makes a 1,373-call run survivable: one 502 does not abort a loop that has
already spent money.

**`Provider`** — a Protocol saying what a backend must implement. It exists
because there were originally two: a free `echo` provider for building the
pipeline at $0, and the real one. Everything downstream — extraction, grading,
storage, both viewers — works against `Generation` alone, so swapping the mock
for the real backend changed **one line**.

⚠️ The mock is now deleted, deliberately: it had proved the chain, the dedup and
the grader across 542 problems, and *"keeping fake rows beside real ones in the
scientific asset is a standing hazard."* Recoverable from commit `f3da6ff` if
ever needed. The `is_mock` column stays as a guard.

**That sequencing is worth a sentence in Chapter 3:** build the whole pipeline
against a fake backend for free, so the first dollar is spent on a path that
already works.

---

## `openrouter.py` — the only file that spends money (180 lines)

Its docstring lists four things it exists to get right. Learn them; they are
Chapter 3 material.

### 1. The send contract is deliberately minimal

```python
messages=[{"role": "user", "content": prompt}]
```

The benchmark prompt goes as a single user message, **unmodified**. No system
prompt. No *"you are an expert programmer"*. No *"think step by step"*.

Why: any of those would change token counts and confound the effort axis — the
one variable under study. If a system prompt made the model think more, you could
no longer attribute a difference to the thinking mode.

⚠️ **One documented exception:** LiveCodeBench stdin problems get one added
sentence about reading from standard input, because the statement alone does not
say how the program receives input, so the task is not well-posed. It is a
constant string, identical across every configuration, so it cannot confound the
effort axis — **but it is a deviation and it is recorded as one.** Say it in
Chapter 3 rather than letting someone find it.

### 2. The `reasoning` block comes verbatim from the roster

```python
extra_body={
    **dict(config.params),
    "provider": {"only": [config.provider], "allow_fallbacks": False},
},
```

`config.params` is the entire experimental manipulation, and nothing here may
invent it.

Note `"only"`, not `"order"` — the comment explains that `order` expresses a
*preference* and still fails over, while `only` is the hard restriction you
want. That distinction is exactly the sort of detail that separates "we pinned
the provider" from "we thought we pinned the provider".

### 3. `max_tokens` is a cost control, not a quality setting

Default **48,000**. A truncated answer is a legitimate failure that cost a
known, bounded amount — better than an unbounded reasoning trace.

### 4. Errors are returned, never raised

```python
except Exception as exc:
    return Generation(error=f"{type(exc).__name__}: {exc}", latency_ms=...)
```

> *A grid run that aborts on one 502 is a grid run that wastes everything before
> it.*

### Reading the usage field defensively

```python
details = getattr(u, "completion_tokens_details", None)
reasoning = getattr(details, "reasoning_tokens", None) or 0
```

`getattr(..., None)` means "if this field is missing, do not crash". The comment
says why: the field is **absent on non-reasoning models and on reasoning-off
calls**. A missing field must read as zero, not as an exception.

### Two failure modes that would have been mislabelled

This is the most instructive part of the file.

```python
if finish == "error":
    error = f"provider finish_reason=error ({len(text or '')} chars returned)"
elif not text:
    error = "empty response (no content returned)"
```

**Case 1 — the provider error that looked like a normal answer.**

> Observed 2026-07-26: `qwen3.5-9b` returned **35,837 completion tokens against
> a `max_tokens` of 16,000** — then set `finish_reason` to `"error"`. **143 KB of
> prose with no code in it.**

Content came back. So the obvious rule — "has text ⇒ success" — would have
recorded a degenerate infrastructure event as a normal failed answer. It is a
provider error and is recorded as one.

**Case 2 — the expensive empty response.**

> A thinking model can spend its whole budget reasoning and return no text at
> all. **Real, paid, and empty.**

Recorded as such, rather than being allowed to look like a transport failure.

⚠️ **Why this distinction is load-bearing:** `analysis.py` treats *billed* and
*unbilled* failures differently. A 404 from a pinned provider says nothing about
the model and costs $0; a call that burned 16,000 tokens and returned nothing
*is* a model outcome — the most expensive kind. Conflating them would understate
the pass rate with infrastructure noise **and** hide lesson 15's entire finding.

### The retry rule

```python
if gen.error and "RateLimitError" in gen.error and attempt < rate_limit_retries:
    time.sleep(2 ** attempt)
    continue
```

**Only rate limits are retried, and only because they are billed $0.** Retrying
anything that produced tokens would defeat the cost cap. `2 ** attempt` is
exponential backoff — 1s, 2s, 4s.

This exists because `allow_fallbacks: false` means an overloaded pinned provider
returns 429 and the cell is otherwise lost. It is a *consequence* of pinning, and
it shows the two decisions were reasoned about together.

### Cost is not reconciled here

```python
def fetch_cost(self, generation_id) -> float | None:
```

Free — a lookup, not a generation. It returns `None` rather than raising,
because the record **404s until it settles (~10 seconds)**.

And the runner calls it *in batch afterwards*, never per call: 2,600 calls × 10s
is over seven hours of waiting.

---

## Do this

**1. Read the two docstrings.**

```bash
cd ~/thesis
sed -n '1,30p' carr/providers/openrouter.py
sed -n '1,15p' carr/providers/base.py
```

**2. Read the send contract.**

```bash
open docs/data-spec.md      # §2 is the exact send/store contract
```

**3. Find the degenerate call in your own data.**

```sql
SELECT problem_id, config_id, completion_tokens, finish_reason,
       LENGTH(raw_response) AS chars, error
FROM generations
WHERE is_mock = 0 AND error IS NOT NULL
ORDER BY completion_tokens DESC LIMIT 10;
```

Look for large `chars` with an `error` set. **Those are the calls that would have
been silently mislabelled.**

**4. Separate billed from unbilled failures.**

```sql
SELECT
  SUM(CASE WHEN completion_tokens > 0 THEN 1 ELSE 0 END) AS billed_failures,
  SUM(CASE WHEN COALESCE(completion_tokens,0) = 0 THEN 1 ELSE 0 END) AS free_failures
FROM generations WHERE is_mock = 0 AND error IS NOT NULL;
```

The first group is a model outcome. The second is infrastructure. **They must
never be added together**, and now you know why.

---

## Check yourself

1. Why is a failed call returned as a `Generation` rather than raised?
2. Why is the prompt sent completely unmodified — and what is the one documented
   exception?
3. Why `"only"` rather than `"order"` in the provider block?
4. Describe the 35,837-token incident and what the naive rule would have done.
5. Why are rate limits the only retried error?
6. Why is a billed failure different from an unbilled one, and what breaks if
   you merge them?
7. Why is cost reconciled in batch instead of per call?

<details>
<summary>Answers</summary>

1. So a single transport error cannot abort a run that has already spent money.
   The failure becomes a recorded row and the loop continues.
2. Because a system prompt or "think step by step" would change token counts and
   confound the effort axis. The exception is one constant sentence added to
   LiveCodeBench stdin problems explaining that input arrives on standard input —
   identical across configurations, and documented as a deviation.
3. `order` is only a preference and still falls back to other providers; `only`
   is a hard restriction. Pinning that can silently fail is not pinning.
4. `qwen3.5-9b` returned 35,837 completion tokens against a 16,000 ceiling,
   143 KB of prose with no code, and set `finish_reason` to `"error"`. A rule of
   "has text ⇒ success" would have recorded a provider malfunction as an ordinary
   failed answer.
5. Because a 429 is billed $0. Retrying anything that produced tokens would let
   the cost cap be bypassed. They need retrying at all because
   `allow_fallbacks: false` means an overloaded pinned provider loses the cell.
6. A billed failure is a model outcome — including the expensive
   thought-for-ages-returned-nothing case. An unbilled one is infrastructure and
   says nothing about the model. Merging them understates pass rates with noise
   and hides the waste finding.
7. Because `/generation` needs about 10 seconds to settle and 404s before then;
   blocking per call would add hours to a run.

</details>

---

➡️ Next: [Lesson 24 — Getting code out of prose](24-extract.md)
