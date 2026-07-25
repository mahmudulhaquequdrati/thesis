"""Grade generated code against a problem's tests. Free -- no API calls.

We delegate to evalplus's own checker rather than re-implementing it. That is a
correctness decision before it is a convenience one: pass/fail is not plain `==`.
Float results are compared with a per-problem `atol`, some MBPP tasks are graded
by set-equality, and others only assert the output is not None. Hand-rolled
grading would silently mislabel those, and a wrong label corrupts every number
downstream -- the Pareto frontier, CPC, and CARR's routing target all read from
`results.passed`.

Isolation comes from evalplus too: each check runs in a subprocess under an
adaptive timeout and reliability_guard(), which disables os.system, os.remove,
os.fork, subprocess and ~40 other calls. There is deliberately NO memory cap --
see the comment on EVALPLUS_MAX_MEMORY_BYTES below; runaway allocation is
bounded by the timeout instead.

Note what this is not: evalplus's own docstring for reliability_guard says it
"is NOT a security sandbox". It contains accidents and casual hostility, which
is the threat model for benchmark solutions, not a determined adversary.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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

from carr.execute._lcb_runner import SENTINEL as _SENTINEL

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
    if dataset == "livecodebench":
        # A genuinely different execution model, not a variant of the same one:
        # LCB problems are stdin->stdout programs or method calls on a Solution
        # class, and evalplus's checker only knows how to compare the return
        # value of a free function. See _grade_lcb.
        return _grade_lcb(task_id, code)

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


# --------------------------------------------------------------- LiveCodeBench
#
# Separate from the evalplus path above because nothing is shared: LCB has no
# canonical solutions to derive expected outputs from (they ship with the tests
# instead), no `atol`, no special oracles, and two execution styles neither of
# which is "call a function and compare the return value".
#
# The comparison is string equality after normalisation, which is what the
# judges these problems came from do. There is no float tolerance, because
# these problems are integer/string answers -- if a future release adds
# floating-point answers this will need an `atol` equivalent and will silently
# mark correct solutions wrong until it gets one.

_LCB_MIN_TIMEOUT = 15.0
_LCB_PER_TEST = 0.4
_LCB_MAX_TIMEOUT = 90.0


def _normalise_stdout(text: str) -> str:
    """Trailing whitespace per line, and trailing blank lines, are not answers."""
    return "\n".join(line.rstrip() for line in text.strip().split("\n")).strip()


def _lcb_matches(produced: str | None, expected: str, style: str) -> bool:
    if produced is None:          # crashed, timed out, or never ran
        return False
    if style == "stdin":
        return _normalise_stdout(produced) == _normalise_stdout(expected)

    # Functional: compare parsed values so [1,2] and [1, 2] agree. Falling back
    # to string comparison keeps a non-JSON answer gradeable rather than
    # crashing the whole problem.
    try:
        return json.loads(produced) == json.loads(expected)
    except (json.JSONDecodeError, TypeError):
        return produced.strip() == expected.strip()


def _run_lcb(problem: dict, code: str, tests: list[dict]) -> list[str | None]:
    """One subprocess for the whole test set. Returns per-test stdout, or None.

    One process rather than one per test: 175 problems x ~43 tests x 10 configs
    would otherwise be 75,000 interpreter startups. The cost of batching is that
    a single non-terminating test times out the whole problem -- which is the
    same behaviour evalplus's per-task timeout already has.
    """
    if not tests:
        return []

    payload = {
        "code": code,
        "tests": tests,
        "style": problem["style"],
        "entry_point": problem["entry_point"],
    }
    timeout = min(_LCB_MAX_TIMEOUT, _LCB_MIN_TIMEOUT + _LCB_PER_TEST * len(tests))

    with tempfile.TemporaryDirectory() as tmp:
        payload_path = os.path.join(tmp, "payload.json")
        with open(payload_path, "w") as f:
            json.dump(payload, f)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "carr.execute._lcb_runner", payload_path],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(_REPO_ROOT),
                # A solution that reads stdin outside the harness must not
                # inherit ours and block forever.
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return [None] * len(tests)

    marker = proc.stdout.rfind(_SENTINEL)
    if marker == -1:
        return [None] * len(tests)
    try:
        produced = json.loads(proc.stdout[marker + len(_SENTINEL):])
    except json.JSONDecodeError:
        return [None] * len(tests)
    if len(produced) != len(tests):
        return [None] * len(tests)
    return produced


def _grade_lcb(task_id: str, code: str) -> GradeResult:
    from carr.benchmarks.livecodebench import get_livecodebench

    problem = get_livecodebench()[task_id]
    style = problem["style"]

    def run(tests: list[dict]) -> tuple[bool, int, int]:
        produced = _run_lcb(problem, code, tests)
        n_ok = sum(
            _lcb_matches(p, t["output"], style) for p, t in zip(produced, tests)
        )
        return n_ok == len(tests), n_ok, len(tests)

    # Same split as evalplus: `base` is the examples printed in the problem
    # statement, `plus` is the hidden set. Public tests run first so an obvious
    # failure costs one short subprocess instead of a long one.
    base_ok, base_n, base_total = run(problem["base_input"])
    plus_ok, plus_n, plus_total = run(problem["plus_input"])

    passed = base_ok and plus_ok
    return GradeResult(
        passed=passed,
        base_passed=base_ok,
        n_tests_passed=base_n + plus_n,
        n_tests_total=base_total + plus_total,
        # LCB gives us no way to tell a wrong answer from a crash from a
        # timeout: all three arrive as "no matching output". Reporting
        # "assertion" is the honest floor, same reasoning as the evalplus path.
        error_type=None if passed else "assertion",
    )
