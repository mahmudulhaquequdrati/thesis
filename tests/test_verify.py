"""The grader must be right before anything else matters.

Every downstream number -- the Pareto frontier, CPC, and CARR's routing target --
reads from `results.passed`. A grader that mislabels is worse than no grader,
because the corruption is invisible.

Run:  uv run pytest tests/test_verify.py -v -s
"""

import pytest

from carr.execute.verify import grade

TASK = "HumanEval/0"  # has_close_elements(numbers, threshold) -> bool

CORRECT = '''
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    s = sorted(numbers)
    for i in range(len(s) - 1):
        if s[i + 1] - s[i] < threshold:
            return True
    return False
'''

# Plausible-looking and wrong: only compares adjacent elements in the ORIGINAL
# order, so it misses close pairs that are far apart in the list. Exactly the
# kind of near-miss a weak model produces.
WRONG = '''
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for i in range(len(numbers) - 1):
        if abs(numbers[i + 1] - numbers[i]) < threshold:
            return True
    return False
'''

INFINITE_LOOP = '''
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    while True:
        pass
'''

SYNTAX_ERROR = '''
def has_close_elements(numbers, threshold)
    return True
'''

# The thing the sandbox exists for. If reliability_guard is working, os.system
# is None and calling it raises rather than executing.
HOSTILE = '''
import os
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    os.system("echo PWNED > /tmp/carr_pwned.txt")
    return True
'''


def test_correct_code_passes():
    r = grade("humaneval", TASK, CORRECT)
    assert r.passed is True
    assert r.error_type is None
    assert r.n_tests_passed == r.n_tests_total
    print(f"\n  correct -> PASS {r.n_tests_passed}/{r.n_tests_total}")


def test_wrong_code_fails():
    r = grade("humaneval", TASK, WRONG)
    assert r.passed is False
    print(f"\n  wrong -> FAIL ({r.error_type}) {r.n_tests_passed}/{r.n_tests_total}")


def test_infinite_loop_times_out_cleanly():
    """Must terminate. If this hangs, the 2,700-generation run would hang too."""
    r = grade("humaneval", TASK, INFINITE_LOOP)
    assert r.passed is False
    print(f"\n  infinite loop -> FAIL ({r.error_type}), terminated cleanly")


def test_syntax_error_fails_without_crashing():
    r = grade("humaneval", TASK, SYNTAX_ERROR)
    assert r.passed is False
    print(f"\n  syntax error -> FAIL ({r.error_type})")


def test_hostile_code_is_contained():
    import os
    marker = "/tmp/carr_pwned.txt"
    if os.path.exists(marker):
        os.remove(marker)
    r = grade("humaneval", TASK, HOSTILE)
    assert not os.path.exists(marker), "SANDBOX BREACH: os.system executed"
    print(f"\n  hostile os.system -> contained (passed={r.passed})")


@pytest.mark.parametrize("task", ["HumanEval/0", "HumanEval/23", "HumanEval/35"])
def test_canonical_solutions_pass(task):
    """Benchmark sanity: evalplus's own reference solutions must score ~100%.

    Anything less means our harness is broken, not that the model is bad. This
    is the check that distinguishes a grading bug from a real result.
    """
    from evalplus.data import get_human_eval_plus
    p = get_human_eval_plus()[task]
    r = grade("humaneval", task, p["prompt"] + p["canonical_solution"])
    assert r.passed is True, f"{task}: canonical solution failed -> harness bug"
    print(f"\n  {task} canonical -> PASS {r.n_tests_passed}/{r.n_tests_total}")
