"""Subprocess entry point for grading LiveCodeBench code. Never import this.

`carr/execute/verify.py` owns it and invokes it with `python -m`; it exists as
a separate file only because untrusted code has to run in its own process.
Grading logic lives here and nowhere else -- CLAUDE.md section 3.

The order of operations is load-bearing:

  1. read the payload  (reliability_guard sets builtins.open to None, so every
     file read has to happen first)
  2. capture the real stdout (the guard does not touch it, but the stdin-style
     loop reassigns sys.stdout and needs a way back)
  3. reliability_guard(None) -- None skips the setrlimit block that macOS
     refuses, the same fix documented in verify.py
  4. only then execute anything the model wrote

Results go to the real stdout after a sentinel, because a stdin-style solution
prints to stdout as its normal output and the two have to be separable.
"""

import io
import json
import os
import sys

# Same macOS fix as verify.py: without it setrlimit raises as the first
# statement of reliability_guard and the process dies before running anything.
os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")

SENTINEL = "__CARR_LCB_RESULT__"

# LeetCode starter code says `def f(self, grid: List[List[int]])` without
# importing List, so the names have to be in scope before the model's code is
# compiled. This mirrors what LiveCodeBench's own harness provides.
PRELUDE = """
import math, re, sys, string, bisect, heapq, itertools, functools, collections
from typing import List, Dict, Tuple, Optional, Set, Any, Union
from collections import defaultdict, deque, Counter, OrderedDict
from functools import lru_cache, cache, reduce
from itertools import permutations, combinations, accumulate, product
from heapq import heappush, heappop, heapify
from bisect import bisect_left, bisect_right
"""


def run_stdin(compiled, tests, real_stdout):
    """Each test re-runs the whole program with a different stdin.

    A fresh globals dict per test so state cannot leak between them. SystemExit
    is success -- competitive programs call sys.exit() routinely.
    """
    out = []
    original_stdin = sys.stdin
    for t in tests:
        buf = io.StringIO()
        sys.stdin = io.StringIO(t["input"])
        sys.stdout = buf
        try:
            exec(compiled, {"__name__": "__main__"})
            out.append(buf.getvalue())
        except SystemExit:
            out.append(buf.getvalue())
        except BaseException:
            out.append(None)          # crashed: no output, counts as a failure
        finally:
            sys.stdout = real_stdout
            sys.stdin = original_stdin
    return out


def run_functional(compiled, tests, entry_point, real_stdout):
    """Call `Solution().<entry_point>(*args)` once per test.

    The input field is newline-separated JSON, one value per argument.
    """
    scope = {"__name__": "__main__"}
    buf = io.StringIO()
    sys.stdout = buf                  # solutions sometimes print while defining
    try:
        exec(compile(PRELUDE, "prelude", "exec"), scope)
        exec(compiled, scope)
    except BaseException:
        sys.stdout = real_stdout
        return [None] * len(tests)
    finally:
        sys.stdout = real_stdout

    solution_cls = scope.get("Solution")
    if solution_cls is None:
        return [None] * len(tests)

    out = []
    for t in tests:
        buf = io.StringIO()
        sys.stdout = buf
        try:
            args = [json.loads(line) for line in t["input"].split("\n") if line.strip()]
            value = getattr(solution_cls(), entry_point)(*args)
            out.append(json.dumps(value))
        except BaseException:
            out.append(None)
        finally:
            sys.stdout = real_stdout
    return out


def main() -> None:
    with open(sys.argv[1]) as f:      # before the guard disables open()
        payload = json.load(f)

    real_stdout = sys.stdout
    from evalplus.eval.utils import reliability_guard

    reliability_guard(None)

    try:
        compiled = compile(payload["code"], "solution", "exec")
    except BaseException:
        # Does not even parse. Every test fails, and that is a real result.
        print(SENTINEL + json.dumps([None] * len(payload["tests"])), file=real_stdout)
        return

    tests = payload["tests"]
    if payload["style"] == "stdin":
        produced = run_stdin(compiled, tests, real_stdout)
    else:
        produced = run_functional(compiled, tests, payload["entry_point"], real_stdout)

    print(SENTINEL + json.dumps(produced), file=real_stdout)


if __name__ == "__main__":
    main()
