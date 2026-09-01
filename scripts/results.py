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

    # ...but that split is mostly a statement about COVERAGE, not about the
    # problems, and quoting it bare is the single easiest number here to lose in
    # a viva. Unanimity is trivial to reach with three voters, and 206 of the 320
    # problems saw only two or three configurations -- nearly always the cheap
    # `off` tier. Recomputed at real coverage the picture inverts.
    cov = analysis.discrimination_by_coverage(conn)
    if len(cov) > 1:
        print()
        print("  ⚠  that split is COVERAGE-DEPENDENT -- unanimity is easy with few voters")
        print(f"\n  {'coverage':20} {'n':>4} {'all':>8} {'none':>8} {'discriminating':>18}")
        for r in cov:
            mc = r["min_configs"]
            label = (f">= {mc} configs" if isinstance(mc, int)
                     else f">= {mc} config")
            print(f"  {label:20} {r['n']:>4} "
                  f"{r['all solved']:>8} {r['none solved']:>8} "
                  f"{r['discriminating']:>10} ({r['pct_discriminating']:>4.0f}%)")
        print("\n  Of the 98 'solved by nothing', 94 were never attempted by ANY")
        print("  reasoning-enabled config. At >= 6 configs, 82% discriminate.")
        print("  The per-TIER saturation above survives -- it is a pass rate, not")
        print("  a unanimity count. The problem-level '44%' does not.")

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

    # ...and 76% of that waste is a single model, so the aggregate rate is a
    # misleading thing to hand a practitioner.
    wbm = analysis.waste_by_model(conn)
    if wbm:
        print(f"\n  {'wasted by model':28} {'wasted/calls':>13} {'rate':>7} "
              f"{'mean rtok':>10} {'$ wasted':>10}")
        for r in wbm:
            rt = f"{r['avg_reasoning']:.0f}" if r["avg_reasoning"] else "-"
            print(f"  {r['model'].split('/')[1][:28]:28} "
                  f"{r['wasted']:>6}/{r['n']:<6} {r['rate_pct']:>6.1f}% "
                  f"{rt:>10} {r['wasted_usd']:>10.6f}")
        print("\n  Non-termination is a property of the small model, not of")
        print("  reasoning: expect ~a third of qwen3.5-9b's thinking calls to")
        print("  return nothing, against ~1 in 25 of deepseek-v4-flash's.")

    cens = analysis.censoring(conn)
    if cens:
        rule("⚠  CENSORING — calls stopped at max_tokens, true length unknown")
        print("  A censored call is SCORED as solving nothing (by definition --")
        print("  see analysis._WASTED), and empirically none of the 101 truncated")
        print("  rows produced code that passed either. So this biases the abort")
        print("  curve against long reasoning. Raise max_tokens if it is material.")
        print(f"\n  {'tier':22} {'n':>4} {'censored':>9} {'pct':>6}")
        for r in cens:
            print(f"  {r['tier']:22} {r['n']:>4} {r['censored']:>9} {r['pct']:>5}%")

    # --------------------------------------- the effect, per model, not per tier
    #
    # The aggregate off-vs-on rows above average over models that respond to
    # reasoning in OPPOSITE directions, so they are the wrong headline. Printed
    # before the style confound because this one reverses a sign, not a margin.
    wm = analysis.within_model_effect(conn)
    if wm:
        rule("⚠  THE EFFECT IS PER MODEL, NOT PER TIER — the aggregate hides a reversal")
        print(f"  {'tier':14} {'model':18} {'off':>14} {'high':>14} "
              f"{'delta':>7} {'cens':>6} {'rtok':>7}")
        for r in wm:
            print(f"  {r['tier']:14} {r['model'].split('/')[1][:18]:18} "
                  f"{r['off_pct']:>7.1f}% n={r['off_n']:<4} "
                  f"{r['high_pct']:>7.1f}% n={r['high_n']:<4} "
                  f"{r['delta']:>+7.1f} {r['censored_pct']:>5.0f}% {r['avg_reasoning']:>7.0f}")
        print("\n  'cens' = share of the thinking arm stopped at max_tokens, which")
        print("  cannot succeed. It separates the two failure modes:")
        print("    NON-TERMINATION  qwen3.5-9b|high censors 81% on hard -- its")
        print("      negative delta is mostly the model failing to stop.")
        print("    REAL DEGRADATION qwen3.5-9b|high censors 0% on MBPP+, reasons")
        print("      368 tokens, terminates, and still loses 24 points on the")
        print("      SAME problems. That one is not measurement.")

    # ------------------------------------------------- the style confound
    #
    # The raw off-vs-on gap above is not a like-for-like comparison on the hard
    # tier: the two arms sat different exams. See analysis.style_composition
    # for the mechanism (it is the runner's problem_id tiebreak, not a design
    # choice). Printed here, immediately under the headline it qualifies.
    comp = analysis.style_composition(conn)
    if comp:
        rule("⚠  STYLE CONFOUND — the two effort arms did not sit the same exam")
        print("  LiveCodeBench ships stdin→stdout (AtCoder) and Solution-class")
        print("  (LeetCode) problems. Run order sorts on problem_id, and numeric")
        print("  LeetCode ids sort before letter-prefixed AtCoder ids, so the")
        print("  expensive thinking arm stopped at the cap inside the LeetCode")
        print("  prefix. Compare WITHIN a style, never across.")
        print(f"\n  {'tier':8} {'style':11} {'effort':7} {'n':>5} {'passed':>7} {'pct':>7}")
        for r in comp:
            print(f"  {r['tier']:8} {r['style']:11} {r['effort']:7} "
                  f"{r['n']:>5} {r['passed']:>7} {r['pct']:>6}%")

        matched = analysis.style_matched_effect(conn)
        if matched:
            print(f"\n  {'the honest effect of reasoning, within one style':60}")
            print(f"  {'tier':8} {'style':11} {'off':>16} {'on':>16} "
                  f"{'matched':>9} {'raw':>8}")
            for m in matched:
                print(f"  {m['tier']:8} {m['style']:11} "
                      f"{m['off_pct']:>10.1f}% n={m['off_n']:<3} "
                      f"{m['high_pct']:>10.1f}% n={m['high_n']:<3} "
                      f"{m['matched_gap']:>+8.1f} {m['raw_gap']:>+7.1f}")
            print("\n  'raw' is the confounded tier-level gap reported above.")
            print("  Arms with n < 30 are dropped: hard/stdin thinking is n=8.")
            print("  Quote the MATCHED column, with its style named.")

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

        # ------------------------------------------- is that spread like-for-like?
        #
        # It is NOT, and the headline must not be quoted without this.
        #
        # `paired_problems` guarantees each row's problems have both effort arms
        # graded; it does NOT guarantee two rows share the same problems. Coverage
        # inside the paired set still runs from n=16 to n=107, and the tier mix
        # differs sharply with it -- deepseek-v4-pro|off, for instance, sits mostly
        # on the easy benchmarks. So the cheapest and dearest rows were measured on
        # DIFFERENT exams, and their ratio mixes a price difference with a
        # difficulty difference.
        #
        # Two honest re-computations, both printed so the caveat cannot be lost:
        # the same two configs over the problems they actually share, and the whole
        # spread over the largest set where every config sat the identical exam.
        shared = analysis.common_problems(
            conn, [best["config_id"], worst["config_id"]])
        if shared:
            pair = {r["config_id"]: r for r in
                    analysis.cost_per_correct(conn, shared, seed=seed,
                                              n_resamples=1500)}
            lo, hi = pair.get(best["config_id"]), pair.get(worst["config_id"])
            if lo and hi and lo["cpc_usd"] and hi["cpc_usd"]:
                print(f"\n  ^ NOT like-for-like: those two rows rest on "
                      f"n={best['n_problems']} and n={worst['n_problems']} "
                      f"DIFFERENT problems.")
                print(f"    On the {len(shared)} problems they actually share, the "
                      f"ratio is {hi['cpc_usd'] / lo['cpc_usd']:.0f}x "
                      f"(${lo['cpc_usd']:.5f} vs ${hi['cpc_usd']:.5f}).")

        like_cfgs, like_probs = analysis.frontier_subset(conn, min_problems=50)
        if len(like_cfgs) >= 3:
            like = [r for r in analysis.cost_per_correct(
                conn, like_probs, seed=seed, n_resamples=1500)
                if r["config_id"] in set(like_cfgs) and r["cpc_usd"]]
            if len(like) >= 2:
                print(f"    Over the strictest set -- {len(like_cfgs)} configs on "
                      f"the SAME {len(like_probs)} problems -- the full spread is "
                      f"{like[-1]['cpc_usd'] / like[0]['cpc_usd']:.0f}x.")
                print("    All three are large; quote whichever you can name the "
                      "denominator for.")

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

    # ...but that is a POOLED statement, and it is false for two of the five
    # models. Printed right after, because the aggregate alone gives a
    # practitioner the wrong rule.
    abm = analysis.abort_by_model(conn)
    if abm:
        print(f"\n  {'per model -- the pool hides a free threshold':58}")
        print(f"  {'model':24} {'calls':>6} {'solved':>7}   {'free threshold':<34}")
        for r in abm:
            free = (f"T={r['free_threshold']:,} saves {r['free_saving_pct']:.0f}%"
                    if r["free_threshold"] else "none -- every T costs a solution")
            print(f"  {r['model'].split('/')[1][:24]:24} {r['n_calls']:>6} "
                  f"{r['solved']:>7}   {free:<34}")
        print("\n  The free threshold exists exactly where reasoning was NOT")
        print("  earning its keep: qwen3.5-9b's delta is negative on three tiers")
        print("  and 37% of its thinking calls return nothing, so whatever it")
        print("  solved it solved early. flash gains +52.9 points on hard by")
        print("  thinking longer, so cutting it off must cost solutions.")

    print("\n  Caveat: simulated over completed calls, and the threshold must be"
          "\n  chosen on data it is not then evaluated against.\n")
    conn.close()


if __name__ == "__main__":
    main()
