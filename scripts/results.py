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

    rule("RQ3  What would a reasoning-length abort have saved?")
    print("  (an aborted call is billed $0 -- measured, not assumed)")
    print(f"\n  {'abort at':>9} {'passes kept':>13} {'cost':>11} {'saved':>7} {'aborted':>8}")
    for p in analysis.abort_curve(conn):
        mark = "  <- free saving" if p.dominant else ""
        print(f"  {p.threshold:>9} {p.passes_kept:>6}/{p.passes_total:<6} "
              f"${p.cost_usd:>10.6f} {p.saved_pct:>6.0f}% {p.aborted:>8}{mark}")

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
