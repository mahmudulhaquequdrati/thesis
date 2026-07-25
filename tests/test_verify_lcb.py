"""The LiveCodeBench grader must be right before any of its rows are bought.

This file does for LCB what test_verify.py::test_canonical_solutions_pass does
for evalplus -- with one important difference. evalplus ships reference
implementations, so that test can assert "the benchmark's own answer scores
100%". **LiveCodeBench ships no canonical solutions at all.** There is nothing
to feed back through the grader as a known-good input.

So the reference solutions below are hand-written, and they are the only thing
standing between us and the LCB equivalent of the macOS setrlimit bug: a
harness that silently marks everything wrong, which would read as "all 2026
models fail every hard problem" -- absurd, but not obviously so in a table.

Both execution styles are covered, because they share no code:
  * stdin     -- AtCoder-style, program reads stdin and prints (112/175)
  * functional -- LeetCode-style, method on a Solution class (63/175)

Run:  uv run pytest tests/test_verify_lcb.py -v -s
"""

import pytest

from carr.benchmarks.livecodebench import get_livecodebench
from carr.execute.verify import grade

STDIN_TASK = "LiveCodeBench/abc387_b"     # 9x9 Sum -- easy, AtCoder
FUNC_TASK = "LiveCodeBench/3708"          # zigzagTraversal -- easy, LeetCode

# Sum of i*j over the 9x9 table, minus every cell equal to X.
STDIN_CORRECT = """
x = int(input())
total = sum(i * j for i in range(1, 10) for j in range(1, 10) if i * j != x)
print(total)
"""

# Off by one row: starts the alternation from the wrong parity.
STDIN_WRONG = """
x = int(input())
total = sum(i * j for i in range(1, 10) for j in range(1, 10))
print(total)
"""

STDIN_CRASH = """
raise ValueError("boom")
"""

STDIN_TIMEOUT = """
while True:
    pass
"""

# Serpentine order, taking every other visited cell.
FUNC_CORRECT = """
class Solution:
    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:
        order = []
        for r, row in enumerate(grid):
            order.extend(row if r % 2 == 0 else row[::-1])
        return order[::2]
"""

# Reads every row left to right -- ignores the zigzag entirely.
FUNC_WRONG = """
class Solution:
    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:
        flat = [v for row in grid for v in row]
        return flat[::2]
"""

FUNC_NO_CLASS = """
def zigzagTraversal(grid):
    return []
"""


@pytest.fixture(scope="module")
def problems():
    return get_livecodebench()


# ------------------------------------------------------- the benchmark loads


def test_dataset_shape(problems):
    assert len(problems) == 175
    assert {p["style"] for p in problems.values()} == {"stdin", "functional"}
    assert {p["difficulty"] for p in problems.values()} == {"easy", "medium", "hard"}
    # The hard tier is the entire reason LCB is here -- HumanEval+ and MBPP+
    # saturate, and RQ4 needs problems the cheap configs actually fail.
    hard = sum(p["difficulty"] == "hard" for p in problems.values())
    assert hard >= 50, f"only {hard} hard problems; the saturation fix needs more"


def test_contamination_window_is_recorded(problems):
    """Every problem carries its contest date, because we cannot filter by it.

    LCB stopped updating: the newest problem here is from 2025 and every model
    on the roster is a 2026 release. Contamination is therefore uncontrolled,
    and the date has to survive into the analysis so the exposure can be
    reported rather than assumed away.
    """
    dates = sorted(p["contest_date"] for p in problems.values())
    assert all(len(d) == 10 for d in dates)
    assert dates[0] < dates[-1]


def test_prompt_is_identical_across_configs(problems):
    """The prompt must be a pure function of the problem.

    If anything config-dependent leaked into it, the effort axis would be
    confounded and every comparison in the thesis would be invalid.
    """
    from carr.benchmarks.livecodebench import build_prompt

    raw = {"question_content": "body", "starter_code": ""}
    assert build_prompt(raw) == build_prompt(dict(raw))
    assert "body" in build_prompt(raw)


# ------------------------------------------------------------- stdin grading


def test_stdin_correct_passes(problems):
    """A hand-written correct solution must score 100%. THE critical test.

    Nothing else in this file can be trusted if this fails: a grader that marks
    correct code wrong turns every LCB row into a false negative.
    """
    r = grade("livecodebench", STDIN_TASK, STDIN_CORRECT)
    assert r.passed is True, (
        f"reference solution failed -> harness bug, not a model result "
        f"({r.n_tests_passed}/{r.n_tests_total})"
    )
    assert r.n_tests_passed == r.n_tests_total
    print(f"\n  stdin correct -> PASS {r.n_tests_passed}/{r.n_tests_total}")


def test_stdin_wrong_fails(problems):
    r = grade("livecodebench", STDIN_TASK, STDIN_WRONG)
    assert r.passed is False
    print(f"\n  stdin wrong -> FAIL {r.n_tests_passed}/{r.n_tests_total}")


def test_stdin_crash_fails_without_raising(problems):
    """A crashing program is a data point, not a reason to abort a grid run."""
    r = grade("livecodebench", STDIN_TASK, STDIN_CRASH)
    assert r.passed is False
    assert r.n_tests_passed == 0
    print(f"\n  stdin crash -> FAIL {r.n_tests_passed}/{r.n_tests_total}")


def test_stdin_infinite_loop_terminates(problems):
    """Must return. If this hangs, a 2,600-row grid run hangs with it."""
    r = grade("livecodebench", STDIN_TASK, STDIN_TIMEOUT)
    assert r.passed is False
    print(f"\n  stdin infinite loop -> FAIL, terminated cleanly")


# -------------------------------------------------------- functional grading


def test_functional_correct_passes(problems):
    """The other half of the critical test -- shares no code with the stdin path."""
    r = grade("livecodebench", FUNC_TASK, FUNC_CORRECT)
    assert r.passed is True, (
        f"reference solution failed -> harness bug "
        f"({r.n_tests_passed}/{r.n_tests_total})"
    )
    assert r.n_tests_passed == r.n_tests_total
    print(f"\n  functional correct -> PASS {r.n_tests_passed}/{r.n_tests_total}")


def test_functional_wrong_fails(problems):
    r = grade("livecodebench", FUNC_TASK, FUNC_WRONG)
    assert r.passed is False
    print(f"\n  functional wrong -> FAIL {r.n_tests_passed}/{r.n_tests_total}")


def test_functional_without_solution_class_fails(problems):
    """A bare function instead of the required class is a legitimate failure."""
    r = grade("livecodebench", FUNC_TASK, FUNC_NO_CLASS)
    assert r.passed is False
    assert r.n_tests_passed == 0


def test_starter_code_names_are_in_scope(problems):
    """The starter uses List[...] without importing it.

    The runner's prelude has to provide typing and the usual containers, or
    every functional problem fails at compile time with a NameError -- which
    would look exactly like the models being bad at LeetCode.
    """
    uses_typing = """
class Solution:
    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:
        d = defaultdict(int)
        order = []
        for r, row in enumerate(grid):
            order.extend(row if r % 2 == 0 else row[::-1])
        return order[::2]
"""
    r = grade("livecodebench", FUNC_TASK, uses_typing)
    assert r.passed is True, "prelude does not provide List/defaultdict"
