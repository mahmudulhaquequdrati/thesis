"""Look at the dataset: what we sent, what came back, what it cost, did it pass.

This is the row the whole project is built to produce, made visible:

    problem -> prompt sent -> raw response -> extracted code -> grade

Three views:

    uv run python scripts/view.py --list             every problem, one line each
    uv run python scripts/view.py HumanEval/0        all 10 configs for one problem
    uv run python scripts/view.py HumanEval/0 -c 3   one cell, in full

The per-problem view ends with the cheapest config that solved it. That single
line is CARR's routing target -- the label the router is trained to predict --
so this view is the thesis in miniature.
"""

import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db  # noqa: E402
from carr.cost import fmt_usd  # noqa: E402

W = 100

# Plain ANSI rather than a table library: `rich` is not a dependency and one
# viewer does not justify making it one.
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, RED, YELLOW = "\033[32m", "\033[31m", "\033[33m"


def rule(title: str = "") -> None:
    print(f"\n{BOLD}{'=' * W}{RESET}")
    if title:
        print(f"{BOLD}{title}{RESET}")
        print(f"{BOLD}{'=' * W}{RESET}")


def section(title: str) -> None:
    print(f"\n{BOLD}--- {title} {'-' * max(0, W - len(title) - 5)}{RESET}")


def verdict(row) -> str:
    if row["passed"] is None:
        return f"{YELLOW}SKIP{RESET}"
    return f"{GREEN}PASS{RESET}" if row["passed"] else f"{RED}FAIL{RESET}"


def show_list(conn) -> None:
    rows = db.list_problems(conn)
    rule(f"PROBLEMS ({len(rows)})")
    print(f"  {'problem_id':16} {'benchmark':15} {'tests':>7} {'chars':>6} "
          f"{'solved':>8}  cheapest pass")
    print(f"  {'-' * (W - 2)}")
    for r in rows:
        solved = f"{r['n_passed']}/{r['n_gens']}"
        print(f"  {r['problem_id']:16} {r['benchmark']:15} {r['n_tests']:>7} "
              f"{r['prompt_chars']:>6} {solved:>8}  "
              f"{fmt_usd(r['cheapest_pass_usd'])}")

    s = db.summary(conn)
    print(f"\n  {s['generations']} generations ({s['mock_generations']} MOCK), "
          f"{s['results']} graded, {s['passed']} passed")
    print(f"  real money spent: ${s['real_spend_usd']:.4f}")


def show_problem(conn, problem_id: str) -> None:
    problem = db.get_problem(conn, problem_id)
    if problem is None:
        sys.exit(f"no such problem in the database: {problem_id}")

    rule(f"{problem_id}   {problem['entry_point']}()   [{problem['benchmark']}]")
    print(f"  {problem['n_base_tests']} base + {problem['n_plus_tests']} plus "
          f"= {problem['n_tests']} test inputs   |   "
          f"prompt {problem['prompt_chars']} chars")

    section("PROMPT SENT TO THE MODEL (verbatim)")
    print(textwrap.indent(problem["prompt"].rstrip(), "  |"))

    rows = db.rows_for_problem(conn, problem_id)
    if not rows:
        print("\n  no generations yet for this problem")
        return

    section("CONFIGS")
    print(f"  {'#':>2} {'model':30} {'eff':5} {'out':>7} {'think':>7} "
          f"{'cost':>11} {'ms':>7}  grade  tests")
    print(f"  {'-' * (W - 2)}")
    for i, r in enumerate(rows):
        tests = (f"{r['n_tests_passed']}/{r['n_tests_total']}"
                 if r["passed"] is not None else (r["error"] or "no code"))
        mock = f" {DIM}[{r['mock_mode']}]{RESET}" if r["mock_mode"] else ""
        print(f"  {i:>2} {r['model_slug']:30} {r['effort_label']:5} "
              f"{r['completion_tokens'] or 0:>7} {r['reasoning_tokens'] or 0:>7} "
              f"{fmt_usd(r['cost_computed_usd']):>11} {r['latency_ms'] or 0:>7}  "
              f"{verdict(r)}  {tests}{mock}")

    best = db.cheapest_passing(conn, problem_id)
    print()
    if best:
        print(f"  {BOLD}routing target{RESET}: cheapest config that solved this "
              f"= {GREEN}{best['model_slug']} | {best['effort_label']}{RESET} "
              f"at {fmt_usd(best['cost_computed_usd'])}")
    else:
        # Not a bug. A problem no config solves carries no routing label and is
        # excluded from the router's training set.
        print(f"  {YELLOW}no config solved this problem -- no routing label{RESET}")


def show_cell(conn, problem_id: str, index: int) -> None:
    rows = db.rows_for_problem(conn, problem_id)
    if not rows:
        sys.exit(f"no generations for {problem_id}")
    if not 0 <= index < len(rows):
        sys.exit(f"--config must be 0..{len(rows) - 1}")
    r = rows[index]
    problem = db.get_problem(conn, problem_id)

    rule(f"{problem_id}   {r['model_slug']} | {r['effort_label']}")
    if r["is_mock"]:
        print(f"  {YELLOW}*** MOCK ROW -- generated offline, not purchased "
              f"(mode: {r['mock_mode']}) ***{RESET}")

    section("1. PROMPT SENT (verbatim)")
    print(textwrap.indent(problem["prompt"].rstrip(), "  |"))

    section("2. RAW RESPONSE (stored verbatim, so re-grading is free)")
    if r["error"]:
        print(f"  {RED}error: {r['error']}{RESET}")
    else:
        print(textwrap.indent((r["raw_response"] or "").rstrip(), "  |"))

    section("3. EXTRACTED CODE (what actually gets executed)")
    if r["extracted_code"]:
        print(textwrap.indent(r["extracted_code"].rstrip(), "  |"))
    else:
        print(f"  {YELLOW}nothing extractable from the response{RESET}")

    section("4. USAGE AND COST")
    reasoning = r["reasoning_tokens"] or 0
    completion = r["completion_tokens"] or 0
    print(f"  prompt tokens      {r['prompt_tokens'] or 0:>8}")
    print(f"  completion tokens  {completion:>8}")
    # The number the whole thesis turns on: billed, and invisible in the text.
    print(f"    of which reasoning {reasoning:>6}   "
          f"({100 * reasoning / completion if completion else 0:.0f}% of "
          f"completion, billed but not shown above)")
    print(f"  finish_reason      {str(r['finish_reason']):>8}"
          f"{'   <-- truncated at max_tokens' if r['finish_reason'] == 'length' else ''}")
    print(f"  cost (computed)    {fmt_usd(r['cost_computed_usd']):>8}   "
          f"@ ${r['price_in_per_m']}/${r['price_out_per_m']} per M")
    print(f"  cost (actual)      {fmt_usd(r['cost_actual_usd']):>8}   "
          f"{DIM}ground truth from /generation; NULL until reconciled{RESET}")
    print(f"  latency            {r['latency_ms'] or 0:>8} ms")

    section("5. GRADE")
    if r["passed"] is None:
        print(f"  {YELLOW}not graded -- no code to run{RESET}")
    else:
        print(f"  verdict            {verdict(r)}")
        print(f"  base tests         "
              f"{'pass' if r['base_passed'] else 'fail'}   (original benchmark)")
        print(f"  tests passed       {r['n_tests_passed']}/{r['n_tests_total']}"
              f"   (diagnostic -- pass@1 is binary)")
        print(f"  error_type         {r['error_type'] or '-'}")
        print(f"  exec               {r['exec_ms'] or 0} ms")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("problem_id", nargs="?", help="e.g. HumanEval/0")
    ap.add_argument("-c", "--config", type=int,
                    help="row number from the config table, for full detail")
    ap.add_argument("--list", action="store_true", help="list every problem")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else db.DEFAULT_DB
    if not db_path.exists():
        sys.exit(f"no database at {db_path}\n"
                 f"run:  uv run python scripts/seed_mock.py")

    conn = db.connect(db_path)
    if args.problem_id and args.config is not None:
        show_cell(conn, args.problem_id, args.config)
    elif args.problem_id:
        show_problem(conn, args.problem_id)
    else:
        show_list(conn)
    print()
    conn.close()


if __name__ == "__main__":
    main()
