"""Day 2: look at what a benchmark problem actually is. No API calls, no cost.

A benchmark problem turns out to be three things: a prompt we send verbatim,
a blob of test code we never send, and the name of the function the tests will
call. Seeing that concretely is what makes the rest of the harness obvious.

Run:  uv run python scripts/day2_inspect_problems.py
      uv run python scripts/day2_inspect_problems.py --task HumanEval/23
"""

import argparse
import textwrap

from evalplus.data import get_human_eval_plus, get_mbpp_plus


def rule(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def show(problem: dict, name: str) -> None:
    rule(f"{name}  --  task_id = {problem['task_id']}")

    print("\n--- prompt (THIS IS WHAT WE SEND TO THE MODEL, VERBATIM) ---")
    print(problem["prompt"])

    print("--- entry_point (the function the tests will call) ---")
    print(f"    {problem['entry_point']}")

    print("\n--- canonical_solution (ground truth; NEVER sent, used to sanity-check the grader) ---")
    print(textwrap.indent(problem["canonical_solution"].rstrip(), "    "))

    n_base = len(problem.get("base_input") or [])
    n_plus = len(problem.get("plus_input") or [])
    print(f"\n--- test inputs (NEVER sent to the model) ---")
    print(f"    base_input : {n_base:>5}   (original benchmark tests)")
    print(f"    plus_input : {n_plus:>5}   (evalplus's extra tests -- the '+' in HumanEval+)")
    print(f"    TOTAL      : {n_base + n_plus:>5}   assertions the generated code must survive")

    if n_base:
        print(f"\n    first base input: {str(problem['base_input'][0])[:120]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", help="specific task_id, e.g. HumanEval/23")
    args = ap.parse_args()

    he = get_human_eval_plus()
    mbpp = get_mbpp_plus()

    if args.task:
        pool = he if args.task.startswith("HumanEval") else mbpp
        show(pool[args.task], "REQUESTED")
        return

    show(he["HumanEval/0"], "HUMANEVAL+ EXAMPLE")
    show(mbpp[list(mbpp)[0]], "MBPP+ EXAMPLE")

    rule("POOL SIZES")
    print(f"  HumanEval+ : {len(he):>4} problems")
    print(f"  MBPP+      : {len(mbpp):>4} problems   (evalplus drops broken ones; not 500)")
    print(f"  LiveCodeBench: loaded separately -- the hard tier")

    tests = [len(p.get('base_input') or []) + len(p.get('plus_input') or [])
             for p in he.values()]
    tests.sort()
    rule("TEST COUNT DISTRIBUTION (HumanEval+)")
    print(f"  min {tests[0]}   median {tests[len(tests) // 2]}   max {tests[-1]}")
    print("\n  Test count is a CARR feature (section 5.2 of the proposal): more tests")
    print("  tends to mean more edge cases, which tends to mean a harder problem.")


if __name__ == "__main__":
    main()
