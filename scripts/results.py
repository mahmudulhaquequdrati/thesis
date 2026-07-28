"""Print the thesis's results from whatever is in the database. Free.

    uv run python scripts/results.py

Reads only; makes no API calls and changes nothing. Safe to run mid-grid --
the numbers just firm up as more rows arrive.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import analysis, db  # noqa: E402
from carr.experiment import load_experiment  # noqa: E402
from carr.stats import ci_str  # noqa: E402


def rule(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")
    print("-" * 78)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    path = Path(args.db) if args.db else db.DEFAULT_DB
    if not path.exists():
        sys.exit(f"no database at {path}\nrun: uv run python scripts/init_db.py")
    conn = db.connect(path)

    s = db.summary(conn)
    print("=" * 78)
    print(f"  {s['generations']} generations, {s['results']} graded, "
          f"${s['real_spend_usd']:.4f} spent")
    print("=" * 78)

    rule("RQ0  Can these problems tell configs apart?")
    print(f"  {'tier':22} {'effort':7} {'n':>4} {'passed':>7} {'pct':>6}")
    for r in analysis.saturation(conn):
        flag = "   <- saturated, no signal" if r["pct"] >= 90 else ""
        print(f"  {r['tier']:22} {r['effort']:7} {r['n']:>4} {r['passed']:>7} "
              f"{r['pct']:>5}%{flag}")
    buckets = analysis.discriminating_problems(conn)
    print()
    for k in ("discriminating", "all solved", "none solved"):
        if k in buckets:
            print(f"  {k:18} {buckets[k]:>4} problems"
                  + ("   <- the only useful ones" if k == "discriminating" else ""))

    rule("RQ1  What predicts how long the model reasons?")
    print(f"  {'tier':22} {'n':>4} {'mean':>8} {'min':>8} {'max':>8}")
    for r in analysis.reasoning_by_tier(conn):
        print(f"  {r['tier']:22} {r['n']:>4} {r['avg_reasoning']:>8.0f} "
              f"{r['min_reasoning']:>8} {r['max_reasoning']:>8}")

    rule("RQ2  When is that reasoning wasted?")
    print(f"  {'outcome':22} {'n':>4} {'mean reasoning':>15} {'cost':>11}")
    for r in analysis.waste(conn):
        print(f"  {r['outcome']:22} {r['n']:>4} {r['avg_reasoning'] or 0:>15.0f} "
              f"${r['total_usd'] or 0:>10.6f}")

    cens = analysis.censoring(conn)
    if cens:
        rule("⚠  CENSORING — calls stopped at max_tokens, true length unknown")
        print("  A censored call CANNOT have succeeded, so this biases the abort")
        print("  curve against long reasoning. Raise max_tokens if it is material.")
        print(f"\n  {'tier':22} {'n':>4} {'censored':>9} {'pct':>6}")
        for r in cens:
            print(f"  {r['tier']:22} {r['n']:>4} {r['censored']:>9} {r['pct']:>5}%")

    # ---------------------------------------------------------- economics
    seed = load_experiment().seed
    paired = analysis.paired_problems(conn)
    rule(f"ECONOMICS  cost per correct answer  (n={len(paired)} paired problems)")
    print("  Only problems with BOTH a reasoning-off and a reasoning-on graded")
    print("  result are comparable at all. Per-config coverage still varies")
    print("  within that set -- read the n column before comparing two rows.")
    print(f"\n  {'config':32} {'n':>4} {'solved':>7} {'CPC $':>10} "
          f"{'95% CI':>22} {'TPC':>9}")
    econ = analysis.cost_per_correct(conn, paired, seed=seed, n_resamples=1500)
    for r in econ:
        cpc = f"{r['cpc_usd']:.5f}" if r["cpc_usd"] is not None else "  never"
        tpc = f"{r['tpc']:.0f}" if r["tpc"] is not None else "-"
        print(f"  {r['model_slug'] + '|' + r['effort_label']:32} {r['n_problems']:>4} "
              f"{r['solved']:>7} {cpc:>10} "
              f"{ci_str(r['cpc_lo'], r['cpc_hi'], places=5):>22} {tpc:>9}")

    usable = [r for r in econ if r["cpc_usd"] is not None]
    if len(usable) >= 2:
        best, worst = usable[0], usable[-1]
        print(f"\n  cheapest per correct answer: {best['model_slug']}|"
              f"{best['effort_label']}  at ${best['cpc_usd']:.5f}")
        print(f"  dearest:                     {worst['model_slug']}|"
              f"{worst['effort_label']}  at ${worst['cpc_usd']:.5f}"
              f"   ({worst['cpc_usd'] / best['cpc_usd']:.0f}x)")
        # Overlapping intervals mean the ordering between two configs is not
        # established, however different the point estimates look.
        overlaps = [(a, b) for a, b in zip(usable, usable[1:])
                    if a["cpc_hi"] >= b["cpc_lo"]]
        if overlaps:
            print(f"\n  {len(overlaps)} adjacent pair(s) have OVERLAPPING intervals "
                  f"-- their order is not established:")
            for a, b in overlaps[:4]:
                print(f"    {a['model_slug']}|{a['effort_label']} vs "
                      f"{b['model_slug']}|{b['effort_label']}")

    # ------------------------------------------------ frontier and its hull
    cfg_ids, front_probs = analysis.frontier_subset(conn, min_problems=50)
    if len(cfg_ids) >= 3 and len(front_probs) >= 20:
        rule(f"RQ4  Cost-accuracy frontier  ({len(cfg_ids)} configs x "
             f"{len(front_probs)} shared problems)")
        print("  Only configs measured on the SAME problems can be compared. All")
        print("  ten share just 5 problems, so this is the largest usable set.")
        pts = analysis.frontier(conn, cfg_ids, front_probs, seed=seed,
                                n_resamples=1200)
        front = analysis.pareto_front(pts)
        hull = analysis.upper_hull(front)
        hull_ids = {p["config_id"] for p in hull}
        front_ids = {p["config_id"] for p in front}
        print(f"\n  {'config':32} {'cost/problem':>13} {'accuracy':>9} "
              f"{'95% CI':>12}  {'':6}")
        for p in pts:
            tag = ("HULL" if p["config_id"] in hull_ids
                   else "pareto" if p["config_id"] in front_ids
                   else "dominated")
            print(f"  {p['model_slug'] + '|' + p['effort_label']:32} "
                  f"${p['cost']:>12.5f} {p['accuracy']:>8.1f}% "
                  f"{ci_str(p['acc_lo'], p['acc_hi'], pct=True):>12}  {tag}")

        orc = analysis.oracle(conn, cfg_ids, front_probs)
        blind = analysis.hull_accuracy_at(hull, orc["cost"])
        print(f"\n  ORACLE (cheapest config that solves each problem):")
        print(f"    {orc['accuracy']:.1f}% at ${orc['cost']:.5f}/problem")
        if blind is not None:
            print(f"  CONVEX HULL at the same budget (problem-blind mixing):")
            print(f"    {blind:.1f}%")
            print(f"\n  VALUE OF PROBLEM-LEVEL INFORMATION: "
                  f"{orc['accuracy'] - blind:+.1f} percentage points")
            print("    This is the headroom any router has to play for. The hull")
            print("    is the honest baseline -- beating the best SINGLE config")
            print("    is nearly free, because mixing two already beats it.")

    # ------------------------------------------------- RQ4b: does a router help
    if len(cfg_ids) >= 3 and len(front_probs) >= 20:
        from carr import router as rt

        grid = rt.outcome_grid(conn, cfg_ids, front_probs)
        costs = {c: sum(g[c]["cost"] for g in grid.values() if c in g)
                 for c in cfg_ids}
        cheap, dear = min(costs, key=costs.get), max(costs, key=costs.get)

        rule("RQ4b  Can a free-feature router beat the hull?")
        print("  Features are free: difficulty tier, test count, prompt length.")
        print("  No forward pass, no draft answer. Leave-one-out CV.\n")
        print(f"  {'strategy':26} {'accuracy':>9} {'cost/problem':>14} {'configs used':>13}")
        for label, r in (("always cheapest", rt.route_always(cheap)),
                         ("always dearest", rt.route_always(dear)),
                         ("rule: think if hard", rt.route_by_difficulty(cheap, dear)),
                         ("k-NN (k=5)", rt.route_knn(5))):
            e = rt.evaluate(conn, r, cfg_ids, front_probs, fallback=cheap)
            print(f"  {label:26} {e['accuracy']:>8.1f}% ${e['cost']:>13.5f} "
                  f"{e['distinct_configs_used']:>13}")

        d = rt.decompose_gap(conn, cfg_ids, front_probs, k=5)
        print(f"\n  GAP DECOMPOSITION (section 10.2)")
        print(f"    oracle, needs the answers          {d['oracle']['accuracy']:>6.1f}%")
        print(f"    ceiling from these features alone  "
              f"{d['feature_ceiling']['accuracy']:>6.1f}%   "
              f"({d['feature_ceiling']['buckets']} buckets, "
              f"{d['feature_ceiling']['problems_per_bucket']:.1f} problems each)")
        print(f"    k-NN actually achieves             {d['router']['accuracy']:>6.1f}%")
        print(f"\n    feature insufficiency  {d['feature_insufficiency']:>6.1f} points"
              f"   -> better FEATURES needed")
        print(f"    estimation error       {d['estimation_error']:>6.1f} points"
              f"   -> better METHOD needed")
        if d["router_minus_hull"] is not None:
            print(f"    router minus hull      {d['router_minus_hull']:>+6.1f} points"
                  f"   -> value the router adds")
        if d["router"]["distinct_configs_used"] == 1:
            print("\n    The router COLLAPSED to a single configuration. The")
            print("    cheapest-solving label is dominated by one config, so a")
            print("    nearest-neighbour vote predicts it everywhere. This is the")
            print("    degenerate outcome 'When Routing Collapses' describes, and")
            print("    the decomposition says the cause is the ESTIMATOR, not the")
            print("    features -- they are sufficient to reach the oracle.")

    rule("RQ3  What would a reasoning-length abort have saved?")
    print("  (an aborted call is billed $0 -- measured, not assumed)")
    curve = analysis.abort_curve_ci(conn, seed=seed, n_resamples=1500)
    print(f"  intervals bootstrap over PROBLEMS (n={curve[0]['n_problems'] if curve else 0}), "
          f"not cells -- two cells on one problem are not independent\n")
    print(f"  {'abort at':>9} {'solutions kept':>16} {'95% CI':>14} "
          f"{'cost':>10} {'saved':>7} {'95% CI':>14}")
    for c in curve:
        print(f"  {c['threshold']:>9} "
              f"{c['passes_kept']:>5}/{c['passes_total']:<4} {c['kept_pct']:>4.0f}% "
              f"{ci_str(c['kept_lo'], c['kept_hi'], pct=True):>14} "
              f"${c['cost_usd']:>9.4f} {c['saved_pct']:>6.0f}% "
              f"{ci_str(c['saved_lo'], c['saved_hi'], pct=True):>14}")

    best = analysis.best_threshold(conn)
    print()
    if best:
        print(f"  \033[1mHEADLINE\033[0m: abort at {best.threshold:,} reasoning tokens — "
              f"keeps all {best.passes_total} solved problems, "
              f"cuts thinking spend {best.saved_pct:.0f}%")
    else:
        print("  No threshold saves money without losing a solved problem.")
    print("\n  Caveat: simulated over completed calls, and the threshold must be"
          "\n  chosen on data it is not then evaluated against.\n")
    conn.close()


if __name__ == "__main__":
    main()
