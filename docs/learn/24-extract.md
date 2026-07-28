# Lesson 24 — Getting code out of prose

*Part 3 · about 30 minutes · `carr/extract.py` (66 lines)*

---

## In one sentence

> Sixty-six lines that turn a chatty model response into runnable Python — and
> whose most important property is that they **never raise**.

---

## The problem

A model does not return bare Python. It returns:

````
Here's my solution:

```python
def has_close_elements(numbers, threshold):
    for i, a in enumerate(numbers):
        for b in numbers[i+1:]:
            if abs(a - b) < threshold:
                return True
    return False
```

For example:

```python
has_close_elements([1.0, 2.0], 0.5)   # False
```

This runs in O(n²) time.
````

Two code blocks. One is the solution; one is a usage example. Grade the wrong
one and you record a `FAIL` that the model did not earn.

---

## The strategy

```python
for pattern in (_TAGGED, _ANY_FENCE):
    blocks = [m.group(1).strip() for m in pattern.finditer(response)]
    blocks = [b for b in blocks if b]
    if blocks:
        valid = [b for b in blocks if _parses(b)]
        pool = valid or blocks
        return max(pool, key=len)

stripped = response.strip()
if _parses(stripped):
    return stripped

return None
```

Four rules, in order:

| Rule | Why |
|---|---|
| Prefer a ` ```python ` fence | The common case, and unambiguous |
| Fall back to **any** fence | Models sometimes omit the language tag |
| Fall back to the whole response | Some responses are bare code with no prose |
| Otherwise `None` | Nothing usable — a data point, not an error |

And two selection rules inside that:

**Prefer blocks that parse.** `_parses()` runs Python's own `ast.parse` — a
syntax check that never executes anything. Safe on hostile input.

**Among candidates, take the longest.** The comment gives the reason:

> *Models often show a short usage example after the real solution, and the
> solution is essentially always the longer block.*

A heuristic, honestly labelled as one. It is the right kind: simple, justified,
and cheap to revisit — because `raw_response` is stored verbatim, so re-extracting
everything costs $0.

---

## The two properties that matter

### 1. It never raises

```python
It returns None rather than raising. A response we cannot parse is a data
point (a FAIL with no extracted code), not a reason to abort a grid run that
has already spent money.
```

Same discipline as `openrouter.py` returning errors instead of throwing. **A
pipeline spending real money must treat unusual input as data, not as an
emergency.**

### 2. Truncated fences are handled deliberately

Look at the regex:

```python
_TAGGED = re.compile(r"```(?:python|py)\s*\n(.*?)(?:```|\Z)", re.DOTALL | re.IGNORECASE)
```

`(?:```|\Z)` means "closing fence **or end of string**".

The docstring explains why:

> *A response truncated by `max_tokens` opens a fence and never closes it;
> taking what we got means a truncated answer is graded as the broken code it
> is, rather than silently becoming "no code at all".*

Think about what the alternative would do. Requiring a closing fence would map
every truncated response to `None`. `None` looks like "the model said nothing".
But the model *did* say something — it said half a program, expensively, and then
hit your ceiling.

**That distinction is lesson 15's finding.** If extraction had quietly discarded
truncated responses, the "billed, no answer at all" category would have been
polluted by "produced partial code that was thrown away", and the 29,584-token
result would have been about your regex rather than about the models.

Two small design choices, one in `openrouter.py` and one here, are what keep that
category clean.

---

## Why `raw_response` is stored verbatim

`CLAUDE.md` §3:

> **Store `raw_response` verbatim.** Code-extraction logic has bugs; keeping raw
> responses means re-grading offline for free instead of re-buying generations.

Extraction is heuristic, so it *will* be wrong sometimes. The question is only
whether being wrong costs $0 or $5.24.

This is the single best cost-of-mistakes decision in the project, and it belongs
in Chapter 3 as a general principle: **store the rawest thing you paid for, and
derive everything else.** Derivations are free to redo; purchases are not.

---

## Do this

**1. Read the whole file.**

```bash
cd ~/thesis
cat carr/extract.py
```

66 lines. Read it top to bottom — this is the first file in the project you can
fully understand in one sitting.

**2. Run the tests and read their names.**

```bash
uv run pytest tests/test_extract.py -v
```

Eleven tests. They enumerate the ways this can go wrong: multiple fences,
untagged fences, no fence, truncated fence, empty response, prose that looks like
code.

**3. Try it on a real stored response.**

```bash
uv run python -c "
from carr import db
from carr.extract import extract_code
conn = db.connect()
row = conn.execute('''SELECT raw_response FROM generations
                      WHERE raw_response IS NOT NULL AND is_mock = 0
                      ORDER BY LENGTH(raw_response) DESC LIMIT 1''').fetchone()
raw = row['raw_response']
print('RAW length:', len(raw))
code = extract_code(raw)
print('EXTRACTED length:', len(code) if code else None)
print((code or '')[:400])
"
```

You just re-ran extraction on a purchased response, for free. **That is the
property `raw_response` buys you.**

**4. Count what extraction could not handle.**

```sql
SELECT COUNT(*) FROM generations
WHERE is_mock = 0 AND raw_response IS NOT NULL
  AND (extracted_code IS NULL OR extracted_code = '');
```

Every one of those is a paid response with no usable code — a data point, not a
crash.

---

## Check yourself

1. Why is picking the *longest* code block the right heuristic, and what kind of
   rule is it?
2. Why does `extract_code` return `None` instead of raising?
3. Why do the regexes accept an unterminated fence, and which finding depends on
   that?
4. Why is `ast.parse` safe to run on model-written code?
5. What does storing `raw_response` verbatim buy you, and state it as a general
   principle.

<details>
<summary>Answers</summary>

1. Models frequently follow the solution with a short usage example, and the
   solution is almost always longer. It is a heuristic, labelled as one, and safe
   to revisit because re-extraction costs nothing.
2. Because an unparseable response is a legitimate data point — a failure with no
   code — and raising would abort a run that has already spent money.
3. Because a response truncated by `max_tokens` opens a fence and never closes
   it. Taking what arrived means it is graded as the broken code it is, rather
   than being recorded as "no code at all" — which keeps lesson 15's
   "billed, no answer" category clean.
4. It only parses; it never executes. It is a syntax check, so hostile code
   cannot do anything during it.
5. Free re-grading forever instead of re-buying generations. Generally: **store
   the rawest thing you paid for and derive everything else**, because
   derivations can be redone at no cost and purchases cannot.

</details>

---

➡️ Next: [Lesson 25 — `verify.py`, the most important file](25-verify.md)
