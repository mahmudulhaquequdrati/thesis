"""The pilot. COSTS MONEY -- always run --dry-run first and read the estimate.

    uv run python scripts/pilot.py --dry-run     # free: the sample and the bill
    uv run python scripts/pilot.py --yes         # buys it

The pilot's job is not to produce results. It is to measure the two numbers no
amount of estimating can supply, both of which decide the size of the grid:

  1. **Mean thinking tokens on HARD problems.** Every budget figure in
     THESIS.md rests on this. The only measurement so far, 963 tokens, came
     from HumanEval/0 -- close to the easiest problem in the pool.
  2. **The saturation rate.** The first real cell was solved by all 10 configs.
     If that holds broadly, "which config should I use" answers itself and RQ4
     has nothing to decide. This is the risk most likely to invalidate the
     headline result, so it gets measured before the grid, not after.

The sample is stratified across benchmark and difficulty (config/experiment.yaml).
A uniform draw from a pool that is 76% easy benchmarks would inherit the
saturation and answer neither question.

Everything is resumable: interrupt it, re-run it, and already-bought cells are
skipped for free.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from carr import db, runner  # noqa: E402
from carr.cost import fmt_usd  # noqa: E402
from carr.effort import load_configs  # noqa: E402
from carr.experiment import describe_sample, load_experiment, sample_problems  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="pilot", choices=["pilot", "grid"],
                    help="which strata block in config/experiment.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="show the sample and the bill. Free")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    ap.add_argument("--max-usd", type=float,
                    help="override the cap in experiment.yaml (lower only)")
    ap.add_argument("--no-reconcile", action="store_true",
                    help="skip the ground-truth cost lookup at the end")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    exp = load_experiment()
    conn = db.connect(Path(args.db) if args.db else db.DEFAULT_DB)
    db.init_schema(conn)

    configs = load_configs()
    for cfg in configs:
        db.upsert_config(conn, cfg.tier_index, cfg)
    conn.commit()

    strata = exp.pilot_strata if args.set == "pilot" else exp.grid_strata
    problem_ids = sample_problems(conn, strata, exp.seed)
    cells, skipped = runner.plan(conn, problem_ids, configs)

    already = runner.lifetime_spend(conn)
    cap = exp.budget.abort_at_usd
    if args.max_usd is not None:
        # Lower only. Raising the cap has to be a deliberate edit to the config
        # file, not a flag someone reaches for when a run stops.
        cap = min(cap, args.max_usd)

    max_tokens = exp.generation.max_tokens
    expect = sum(c.expected_usd() for c in cells)
    worst = sum(c.worst_usd(max_tokens) for c in cells)

    print("=" * 92)
    print(f"  {args.set.upper()}   seed {exp.seed}")
    print("=" * 92)
    print(f"\n  sample: {len(problem_ids)} problems x {len(configs)} configs "
          f"= {len(problem_ids) * len(configs)} cells")
    print(f"  {'benchmark':18} {'difficulty':11} {'n':>4} {'avg chars':>10} {'avg tests':>10}")
    print("  " + "-" * 58)
    for row in describe_sample(conn, problem_ids):
        print(f"  {row['benchmark']:18} {row['difficulty']:11} {row['n']:>4} "
              f"{row['avg_chars']:>10.0f} {row['avg_tests']:>10.0f}")

    if skipped:
        print(f"\n  {skipped} cell(s) already bought -- free to skip")
    if not cells:
        print("\n  nothing left to buy.\n")
        return

    print(f"\n  {len(cells)} call(s) to make")
    print(f"  expected      {fmt_usd(expect)}")
    print(f"  WORST CASE    {fmt_usd(worst)}   (max_tokens={max_tokens})")
    print(f"\n  already spent {fmt_usd(already)}")
    print(f"  cap           {fmt_usd(cap)}   (loaded balance "
          f"${exp.budget.loaded_usd:.2f})")
    print(f"  headroom      {fmt_usd(cap - already)}")

    if already + expect > cap:
        print(f"\n  NOTE: even the EXPECTED total would breach the cap. The run "
              f"would stop partway, cheapest cells first.")
    elif already + worst > cap:
        print(f"\n  NOTE: the worst case would breach the cap. The run stops "
              f"before any call that could cross it -- cheapest cells complete "
              f"first, so a stop leaves a usable foundation.")

    if args.dry_run:
        print("\n  --dry-run: no API calls made, nothing spent.\n")
        return

    if not args.yes:
        if not sys.stdin.isatty():
            sys.exit("\n  refusing to spend without --yes when not interactive.")
        if input("\n  spend it? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("  cancelled, nothing spent.")

    from carr.providers.openrouter import OpenRouterProvider

    provider = OpenRouterProvider()
    print()

    def on_row(cell, gen, result, cost, spend):
        u = gen.usage
        if result is None:
            verdict, detail = "SKIP", (gen.error or "no code")[:28]
        else:
            verdict = "PASS" if result.passed else "FAIL"
            detail = f"{result.n_tests_passed}/{result.n_tests_total}"
        print(f"  {cell.problem_id:26} {cell.config.label:42} {verdict} "
              f"{detail:>12}  think {(u.reasoning_tokens if u else 0):>6}  "
              f"{fmt_usd(cost)}  [{fmt_usd(spend)}]")

    report = runner.run(
        conn, cells, provider,
        max_tokens=max_tokens,
        abort_at_usd=cap,
        warn_at_usd=exp.budget.warn_at_usd,
        temperature=exp.generation.temperature,
        on_row=on_row,
    )

    print("\n" + "=" * 92)
    print(f"  bought {report.bought}   graded {report.graded}   "
          f"passed {report.passed}   errors {report.errors}")
    print(f"  spent this run {fmt_usd(report.spent_usd)}")
    if report.stopped_reason:
        print(f"\n  {report.stopped_reason}")
        print("  Re-run to continue -- bought cells are free to skip.")

    if not args.no_reconcile and report.generation_ids:
        updated, drift = runner.reconcile_costs(conn, provider,
                                                report.generation_ids)
        print(f"  reconciled {updated}/{len(report.generation_ids)} costs against "
              f"/generation; drift vs the price table {fmt_usd(drift)}")

    s = db.summary(conn)
    print(f"\n  lifetime spend ${s['real_spend_usd']:.6f} of "
          f"${exp.budget.loaded_usd:.2f} loaded   ({s['generations']} generations)")
    print(f"\n  next:  uv run python scripts/analyse_pilot.py\n")
    conn.close()


if __name__ == "__main__":
    main()
