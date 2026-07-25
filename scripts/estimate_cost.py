"""Project the cost of the full grid before spending anything on it.

Every number here is arithmetic over config/models.yaml plus token assumptions.
The assumptions are guesses until the pilot measures them -- rerun with the
measured values before committing to a grid size.

Run:  uv run python scripts/estimate_cost.py
      uv run python scripts/estimate_cost.py --problems 434 --think-tokens 5000
"""

import argparse
import sys
from pathlib import Path

# The repo is run in place, not installed (see pyproject.toml). pytest gets this
# from `pythonpath`; scripts invoked directly have to say it themselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr.effort import load_configs  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", type=int, default=300,
                    help="problems in the full grid")
    ap.add_argument("--subset", type=int, default=100,
                    help="problems for the held-out (RQ5) model")
    # 600 was the pre-Day-2 guess. Day 2 measured the real medians: 99 tokens
    # for HumanEval+ and 36 for MBPP+, ~6x smaller. 100 is the honest default;
    # it also means input cost is a rounding error and effectively the whole
    # budget is output plus reasoning tokens.
    ap.add_argument("--in-tokens", type=int, default=100,
                    help="mean prompt tokens per problem (measured Day 2)")
    ap.add_argument("--off-tokens", type=int, default=350,
                    help="mean completion tokens with thinking off")
    ap.add_argument("--think-tokens", type=int, default=3500,
                    help="mean completion tokens with thinking on (incl. reasoning)")
    ap.add_argument("--budget", type=float, default=4.0,
                    help="available balance in USD")
    args = ap.parse_args()

    priced = []
    for c in load_configs():
        # The held-out model runs on a subset, not the full grid: RQ5 asks
        # whether CARR transfers to an unseen model, which does not need full
        # coverage, and at $2.72/M output full coverage would cost more than
        # every other config combined.
        n = args.subset if c.held_out else args.problems
        out_tok = args.off_tokens if c.effort_label == "off" else args.think_tokens
        slug = c.model_slug + " (held-out)" if c.held_out else c.model_slug
        cost = (n * args.in_tokens * c.price_in_per_m
                + n * out_tok * c.price_out_per_m) / 1e6
        priced.append((cost, slug, c.effort_label, n, out_tok))
    # Cheapest first -- the same order runner.py must use, so that a budget
    # breach costs the expensive tail rather than the cheap foundation.
    priced.sort()

    print(f"Assumptions: {args.problems} problems, {args.in_tokens} in-tok, "
          f"{args.off_tokens} out-tok (off), {args.think_tokens} out-tok (think)\n")
    print(f"{'#':>2}  {'config':52} {'effort':6} {'probs':>6} {'cost':>8} {'cumul':>8}")
    print("-" * 90)
    total = 0.0
    for i, (cost, slug, effort, n, _) in enumerate(priced, 1):
        total += cost
        flag = "" if total <= args.budget else "  <-- OVER BUDGET"
        print(f"{i:>2}  {slug:52} {effort:6} {n:>6} {cost:>8.3f} {total:>8.3f}{flag}")

    print("-" * 90)
    print(f"{'TOTAL':>72} {total:>8.3f}")
    print(f"{'BUDGET':>72} {args.budget:>8.3f}")
    headroom = args.budget - total
    verdict = "fits" if headroom >= 0 else "DOES NOT FIT"
    print(f"{'HEADROOM':>72} {headroom:>8.3f}   {verdict}")

    if headroom < 0:
        affordable = args.problems * args.budget / total
        print(f"\n  At this budget the grid supports ~{int(affordable)} problems, "
              f"not {args.problems}.")
        print("  Alternatives: drop the held-out model, or add funds.")

    print("\n  Reminder: these are guesses. Run the pilot, then rerun this with")
    print("  --off-tokens/--think-tokens set to the measured means.")


if __name__ == "__main__":
    main()
