"""Create data/carr.sqlite and load everything that is real and free.

Two of the four tables cost nothing and can be rebuilt at any time:

    problems  <- evalplus (HumanEval+ 164, MBPP+ 378)
    configs   <- config/models.yaml (the 9 verified model x effort pairs)

The other two are left EMPTY on purpose. `generations` is the money table --
the only way to fill it is to buy the rows -- and `results` is derived from it.
An empty grid here is the honest state of the project, not a failure.

Safe to re-run: both loaders upsert, so this never duplicates and never
touches generations or results.

Run:  uv run python scripts/init_db.py
      uv run python scripts/init_db.py --benchmarks humaneval
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db  # noqa: E402
from carr.effort import load_configs  # noqa: E402

# evalplus loader -> the `benchmark` value stored on each row.
LOADERS = {
    "humaneval": ("humaneval_plus", "get_human_eval_plus"),
    "mbpp": ("mbpp_plus", "get_mbpp_plus"),
}
# LiveCodeBench is loaded separately: different source, different record shape,
# and it carries a real difficulty label and a contest date that the other two
# do not have.
LCB_BENCHMARK = "livecodebench"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--benchmarks", nargs="*",
                    default=["humaneval", "mbpp", "livecodebench"],
                    choices=[*LOADERS, LCB_BENCHMARK],
                    help="which pools to load")
    ap.add_argument("--reset", action="store_true",
                    help="delete the database file first -- DESTROYS generations")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else db.DEFAULT_DB

    if args.reset and db_path.exists():
        conn = db.connect(db_path)
        try:
            paid = conn.execute(
                "SELECT COUNT(*) FROM generations WHERE COALESCE(is_mock, 0) = 0"
            ).fetchone()[0]
        except Exception:
            paid = 0
        conn.close()
        if paid:
            sys.exit(f"refusing --reset: {db_path} holds {paid} paid generations.\n"
                     f"Those cost real money and cannot be rebuilt. Back the file "
                     f"up and delete it by hand if you really mean it.")
        db_path.unlink()
        print(f"  removed {db_path}")

    conn = db.connect(db_path)
    db.init_schema(conn)

    configs = load_configs()
    for cfg in configs:
        db.upsert_config(conn, cfg.config_id, cfg)
    conn.commit()
    print(f"  configs   {len(configs):>5}   from config/models.yaml")

    # Idempotent: brings already-bought rows onto the current request_hash
    # formula so they are still recognised as bought and never re-purchased.
    # Both idempotent. They bring an existing database onto the current
    # request_hash formula and the current (stable) config_id scheme, so
    # already-bought rows stay recognised and correctly attributed.
    n_cfg, moved = db.repair_config_ids(conn)
    if moved:
        print(f"  repaired  {moved:>5}   generations re-pointed at the right config")
    changed = db.migrate_request_hashes(conn)
    if changed:
        print(f"  migrated  {changed:>5}   request_hash values (no re-purchase)")

    import evalplus.data as ep

    total = 0
    if LCB_BENCHMARK in args.benchmarks:
        from carr.benchmarks.livecodebench import get_livecodebench

        lcb = get_livecodebench()
        for task_id, p in lcb.items():
            db.upsert_problem(
                conn,
                problem_id=task_id,
                benchmark=LCB_BENCHMARK,
                prompt=p["prompt"],
                entry_point=p["entry_point"],   # "" for stdin-style problems
                n_base_tests=len(p["base_input"]),
                n_plus_tests=len(p["plus_input"]),
                difficulty=p["difficulty"],     # real labels, unlike HE+/MBPP+
                # Stored so contamination exposure can be REPORTED. It cannot be
                # filtered: LCB stopped updating in 2025 and every model on the
                # roster is a 2026 release. See the loader's docstring.
                release_date=p["contest_date"],
            )
        conn.commit()
        total += len(lcb)
        print(f"  problems  {len(lcb):>5}   {LCB_BENCHMARK}   "
              f"(hard tier; contamination UNCONTROLLED -- see THESIS.md section 11)")

    for key in args.benchmarks:
        if key == LCB_BENCHMARK:
            continue
        benchmark, fn_name = LOADERS[key]
        problems = getattr(ep, fn_name)()
        for task_id, p in problems.items():
            db.upsert_problem(
                conn,
                problem_id=task_id,
                benchmark=benchmark,
                prompt=p["prompt"],
                entry_point=p["entry_point"],
                n_base_tests=len(p.get("base_input") or []),
                n_plus_tests=len(p.get("plus_input") or []),
                # HumanEval+ and MBPP+ ship no difficulty label; only
                # LiveCodeBench does. Recording 'easy' would be an invention.
                difficulty=None,
            )
        conn.commit()
        total += len(problems)
        print(f"  problems  {len(problems):>5}   {benchmark}")

    s = db.summary(conn)
    print(f"\n  {total} problems, {s['configs']} configs loaded.")
    note = "" if s["generations"] else "   (empty until the pilot buys them)"
    print(f"  generations {s['generations']}   results {s['results']}{note}")
    if s["generations"]:
        print(f"  real spend so far: ${s['real_spend_usd']:.6f}")
    print(f"\n  {db_path}")
    print(f"  browse it:  uv run python scripts/studio.py")
    conn.close()


if __name__ == "__main__":
    main()
