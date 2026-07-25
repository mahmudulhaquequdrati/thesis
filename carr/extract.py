"""Pull runnable Python out of a raw model response.

Models return prose around their code, usually in a markdown fence, sometimes
in several fences, occasionally in none. This module is the only place that
guesses which part is the program.

It returns None rather than raising. A response we cannot parse is a data
point (a FAIL with no extracted code), not a reason to abort a grid run that
has already spent money -- the same property `verify.grade` guarantees for
code that does not compile.

Because `generations.raw_response` is stored verbatim, fixing a bug here means
re-extracting and re-grading offline for free. Never re-buy generations to fix
an extraction bug.
"""

from __future__ import annotations

import ast
import re

# ```python ... ```  /  ```py ... ```  -- the common case.
_TAGGED = re.compile(r"```(?:python|py)\s*\n(.*?)(?:```|\Z)", re.DOTALL | re.IGNORECASE)
# Any fence, tagged or not. Fallback when the model omitted the language.
_ANY_FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    return True


def extract_code(response: str | None) -> str | None:
    """Best-effort Python source from a raw response, or None.

    Order: a ```python fence, then any fence, then the whole response if it is
    itself valid Python. Among multiple fenced blocks the LONGEST is chosen --
    models often show a short usage example after the real solution, and the
    solution is essentially always the longer block.

    Note the regexes accept an unterminated fence (`\\Z`). A response truncated
    by max_tokens opens a fence and never closes it; taking what we got means a
    truncated answer is graded as the broken code it is, rather than silently
    becoming "no code at all".
    """
    if not response or not response.strip():
        return None

    for pattern in (_TAGGED, _ANY_FENCE):
        blocks = [m.group(1).strip() for m in pattern.finditer(response)]
        blocks = [b for b in blocks if b]
        if blocks:
            valid = [b for b in blocks if _parses(b)]
            # Prefer a block that compiles; if none does, still return the
            # longest so the grader records a real syntax failure.
            pool = valid or blocks
            return max(pool, key=len)

    stripped = response.strip()
    if _parses(stripped):
        return stripped

    return None
