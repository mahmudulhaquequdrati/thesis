"""Grade generated code against a problem's tests. Free -- no API calls.

We delegate to evalplus's own checker rather than re-implementing it. That is a
correctness decision before it is a convenience one: pass/fail is not plain `==`.
Float results are compared with a per-problem `atol`, some MBPP tasks are graded
by set-equality, and others only assert the output is not None. Hand-rolled
grading would silently mislabel those, and a wrong label corrupts every number
downstream -- the Pareto frontier, CPC, and CARR's routing target all read from
`results.passed`.

Isolation comes from evalplus too: each check runs in a subprocess with a memory
cap and an adaptive timeout, under reliability_guard(), which disables
os.system, os.remove, os.fork, subprocess and ~40 other calls.
"""

from __future__ import annotations

import contextlib
import io
import os
from dataclasses import dataclass
from typing import Any

# MUST be set before evalplus.eval is imported.
#
# evalplus caps subprocess memory with resource.setrlimit(RLIMIT_AS/RLIMIT_DATA).
# macOS refuses to lower either, at any value -- getrlimit reports an infinite
# hard limit, and every setrlimit call raises "current limit exceeds maximum
# limit". That exception fires as the FIRST statement of reliability_guard, so
# the subprocess dies before running a single test AND before the guard disables
# os.system and friends.
#
# evalplus reports the dead subprocess as a timeout, so the failure mode is
# silent and total: every solution "fails", including evalplus's own canonical
# ones. Caught by tests/test_verify.py::test_canonical_solutions_pass.
#
# -1 makes query_maximum_memory_bytes return None, skipping the setrlimit block
# so the rest of reliability_guard actually executes. The cost is no memory cap:
# runaway allocation is then bounded only by the per-test timeout. Acceptable
# here -- these are competition-style solutions, and a broken grader is far more
# dangerous than an unbounded one.
os.environ.setdefault("EVALPLUS_MAX_MEMORY_BYTES", "-1")

from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash
from evalplus.data import get_mbpp_plus, get_mbpp_plus_hash
from evalplus.data.mbpp import mbpp_serialize_inputs  # noqa: F401  (import side effects)
from evalplus.eval import PASS
from evalplus.evaluate import check_correctness, get_groundtruth
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS

# Loading problems and computing ground truth is slow (ground truth executes
# every canonical solution against every test input), so both are cached here
# and on disk by evalplus itself.
_CACHE: dict[str, tuple[dict, dict]] = {}


def _load(dataset: str) -> tuple[dict, dict]:
    """Return (problems, expected_output) for 'humaneval' or 'mbpp'."""
    if dataset in _CACHE:
        return _CACHE[dataset]

    if dataset == "humaneval":
        problems = get_human_eval_plus()
        hashcode = get_human_eval_plus_hash()
        not_none_tasks: list[str] = []
    elif dataset == "mbpp":
        problems = get_mbpp_plus()
        hashcode = get_mbpp_plus_hash()
        not_none_tasks = MBPP_OUTPUT_NOT_NONE_TASKS
    else:
        raise ValueError(f"unknown dataset: {dataset!r}")

    # get_groundtruth prints progress; keep it out of our output.
    with contextlib.redirect_stdout(io.StringIO()):
        expected = get_groundtruth(problems, hashcode, not_none_tasks)

    _CACHE[dataset] = (problems, expected)
    return problems, expected


@dataclass
class GradeResult:
    """One row of the `results` table."""

    passed: bool           # survived BOTH base and plus tests
    base_passed: bool      # original benchmark tests only
    n_tests_passed: int    # diagnostic; pass@1 is binary, this is not the metric
    n_tests_total: int
    error_type: str | None  # None | "assertion" | "timeout" | "exception"


def _summarise(status: str, details: Any) -> tuple[bool, int, int]:
    """Turn one evalplus (status, per-test-bool-array) pair into counts."""
    ok = status == PASS
    if details is None:
        # fast_check short-circuits and returns no per-test detail.
        return ok, (1 if ok else 0), 1
    total = len(details)
    return ok, int(sum(bool(d) for d in details)), total


def grade(dataset: str, task_id: str, code: str) -> GradeResult:
    """Run `code` against `task_id`'s tests.

    `code` is the extracted solution, not the raw model response. It is executed
    in a guarded subprocess -- never trust it, and never call this on the main
    thread of anything you care about.
    """
    problems, expected = _load(dataset)
    problem = problems[task_id]

    with contextlib.redirect_stdout(io.StringIO()):
        res = check_correctness(
            dataset=dataset,
            completion_id=0,
            problem=problem,
            solution=code,
            expected_output=expected[task_id],
            fast_check=False,
        )

    base_ok, base_n, base_total = _summarise(*res["base"])
    plus_ok, plus_n, plus_total = _summarise(*res["plus"])

    passed = base_ok and plus_ok
    error_type = None
    if not passed:
        # evalplus reports timeouts as a distinct status string; anything else
        # that is not PASS means the code ran but produced wrong answers, or
        # raised. We cannot always tell those apart from the status alone, so
        # "assertion" is the honest default for a non-timeout failure.
        statuses = (res["base"][0], res["plus"][0])
        error_type = "timeout" if any("timeout" in str(s).lower() for s in statuses) else "assertion"

    return GradeResult(
        passed=passed,
        base_passed=base_ok,
        n_tests_passed=base_n + plus_n,
        n_tests_total=base_total + plus_total,
        error_type=error_type,
    )
