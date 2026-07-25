"""Project the cost of the full grid before spending anything on it.

Every number here is arithmetic over config/models.yaml plus token assumptions.
The assumptions are guesses until the pilot measures them -- rerun with the
measured values before committing to a grid size.

Run:  uv run python scripts/estimate_cost.py
      uv run python scripts/estimate_cost.py --problems 434 --think-tokens 5000
"""

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", type=int, default=300,
                    help="problems in the full grid")
    ap.add_argument("--subset", type=int, default=100,
                    help="problems for the held-out (RQ5) model")
    ap.add_argument("--in-tokens", type=int, default=600,
                    help="mean prompt tokens per problem")
    ap.add_argument("--off-tokens", type=int, default=350,
                    help="mean completion tokens with thinking off")
    ap.add_argument("--think-tokens", type=int, default=3500,
                    help="mean completion tokens with thinking on (incl. reasoning)")
    ap.add_argument("--budget", type=float, default=4.0,
                    help="available balance in USD")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())

    rows = []
    for model in cfg["models"]:
        for effort in model["efforts"]:
            out_tok = args.off_tokens if effort["label"] == "off" else args.think_tokens
            rows.append((model["slug"], effort["label"], model["price_in_per_m"],
                         model["price_out_per_m"], args.problems, out_tok))
    for model in cfg.get("held_out", []):
        for effort in model["efforts"]:
            out_tok = args.off_tokens if effort["label"] == "off" else args.think_tokens
            rows.append((model["slug"] + " (held-out)", effort["label"],
                         model["price_in_per_m"], model["price_out_per_m"],
                         args.subset, out_tok))

    priced = []
    for slug, effort, p_in, p_out, n, out_tok in rows:
        cost = (n * args.in_tokens * p_in + n * out_tok * p_out) / 1e6
        priced.append((cost, slug, effort, n, out_tok))
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
