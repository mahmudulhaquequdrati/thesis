"""Fill data/carr.sqlite with mock generations. No API calls. $0.

Every component in the chain is the real one except the API call itself:

    problem -> prompt -> [EchoProvider] -> raw response -> extract_code
            -> verify.grade  (the REAL grader, subprocess-isolated)
            -> generations + results rows

Two things this buys before any money is spent:

1. The viewers have something to show, so the shape of every column can be
   checked against what the thesis actually needs.
2. Every response in `canonical` mode is evalplus's own reference solution, so
   it MUST grade PASS. Running that over hundreds of problems across both
   benchmarks is a mass-scale version of test_canonical_solutions_pass, which
   is the check that distinguishes a harness bug from a real result. The macOS
   setrlimit bug (see carr/execute/verify.py) is exactly the class of failure
   it catches.

Run:  uv run python scripts/seed_mock.py
      uv run python scripts/seed_mock.py --problems 40 --reset
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db  # noqa: E402
from carr.cost import compute_cost  # noqa: E402
from carr.effort import load_configs  # noqa: E402
from carr.execute.verify import grade  # noqa: E402
from carr.extract import extract_code  # noqa: E402
from carr.providers.echo import EchoProvider  # noqa: E402

BENCHMARKS = {"humaneval": "humaneval_plus", "mbpp": "mbpp_plus"}


def load_pool(n_humaneval: int, n_mbpp: int):
    """Return {problem_id: (dataset, problem)} for the sampled problems.

    Problems are taken in task_id order rather than sampled randomly: this is a
    fixture, and a fixed prefix is easier to reason about than a seeded sample.
    """
    from evalplus.data import get_human_eval_plus, get_mbpp_plus

    pool = {}
    he = get_human_eval_plus()
    for task_id in list(he)[:n_humaneval]:
        pool[task_id] = ("humaneval", he[task_id])

    if n_mbpp:
        mbpp = get_mbpp_plus()
        for task_id in list(mbpp)[:n_mbpp]:
            pool[task_id] = ("mbpp", mbpp[task_id])
    return pool


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", type=int, default=40,
                    help="total problems to seed (75%% HumanEval+, 25%% MBPP+)")
    ap.add_argument("--db", default=None, help="database path")
    ap.add_argument("--reset", action="store_true",
                    help="delete the database file first")
    args = ap.parse_args()

    n_he = max(1, round(args.problems * 0.75))
    n_mbpp = max(0, args.problems - n_he)

    db_path = Path(args.db) if args.db else db.DEFAULT_DB
    if args.reset and db_path.exists():
        db_path.unlink()
        print(f"  removed {db_path}")

    print("=" * 78)
    print("SEED MOCK DATA -- no API calls, no cost")
    print("=" * 78)

    if n_mbpp:
        print("\n  Note: MBPP+ ground truth may not be cached yet. Computing it")
        print("  executes ~41,000 reference outputs and takes several minutes")
        print("  the first time. This is a one-off, and better paid now than")
        print("  in the middle of the grid run.\n")

    configs = load_configs()
    pool = load_pool(n_he, n_mbpp)
    print(f"  {len(pool)} problems x {len(configs)} configs = "
          f"{len(pool) * len(configs)} cells\n")

    conn = db.connect(db_path)
    db.init_schema(conn)

    for cfg in configs:
        db.upsert_config(conn, cfg.tier_index, cfg)

    for task_id, (dataset, problem) in pool.items():
        db.upsert_problem(
            conn,
            problem_id=task_id,
            benchmark=BENCHMARKS[dataset],
            prompt=problem["prompt"],
            entry_point=problem["entry_point"],
            n_base_tests=len(problem.get("base_input") or []),
            n_plus_tests=len(problem.get("plus_input") or []),
            difficulty="easy",
        )
    conn.commit()

    provider = EchoProvider({tid: p for tid, (_, p) in pool.items()},
                            n_configs=len(configs))

    inserted = skipped = graded = passed = 0
    started = time.time()

    for task_id, (dataset, problem) in pool.items():
        prompt = problem["prompt"]
        for cfg in configs:
            req_hash = db.request_hash(cfg.model_slug, cfg.effort_label,
                                       prompt, cfg.params)
            # The check that makes a crashed run free to restart. Verified by
            # re-running this script: the second pass must insert nothing.
            if db.has_generation(conn, req_hash):
                skipped += 1
                continue

            gen = provider.complete(prompt, cfg, problem_id=task_id)
            code = extract_code(gen.raw_response)
            cost = compute_cost(
                gen.usage.prompt_tokens if gen.usage else 0,
                gen.usage.completion_tokens if gen.usage else 0,
                cfg.price_in_per_m, cfg.price_out_per_m,
            )

            gen_id = db.insert_generation(
                conn,
                problem_id=task_id,
                config_id=cfg.tier_index,
                request_hash=req_hash,
                openrouter_gen_id=gen.provider_gen_id,
                raw_response=gen.raw_response,
                extracted_code=code,
                prompt_tokens=gen.usage.prompt_tokens if gen.usage else None,
                completion_tokens=gen.usage.completion_tokens if gen.usage else None,
                reasoning_tokens=gen.usage.reasoning_tokens if gen.usage else None,
                cost_computed_usd=cost,
                cost_actual_usd=None,   # only the real backend can fill this
                finish_reason=gen.finish_reason,
                latency_ms=gen.latency_ms,
                temperature_sent=0.0,
                error=gen.error,
                is_mock=1,
                mock_mode=gen.mock_mode,
            )
            if gen_id is None:          # lost a race with the UNIQUE index
                skipped += 1
                continue
            inserted += 1

            # An errored call has no code to grade -- it stays a generation row
            # with no result row, which is exactly how a real API failure looks.
            if code:
                t0 = time.perf_counter()
                result = grade(dataset, task_id, code)
                db.upsert_result(conn, gen_id, result,
                                 exec_ms=int((time.perf_counter() - t0) * 1000))
                graded += 1
                passed += int(result.passed)
                mark = "PASS" if result.passed else "FAIL"
                detail = f"{result.n_tests_passed}/{result.n_tests_total}"
            else:
                mark = "SKIP"
                detail = gen.error or "no code extracted"

            print(f"  {task_id:16} {cfg.label:42} {gen.mock_mode:10} "
                  f"{mark} {detail}")
        conn.commit()

    conn.commit()
    elapsed = time.time() - started

    print("\n" + "=" * 78)
    print(f"  inserted {inserted}   skipped(already present) {skipped}   "
          f"graded {graded}   passed {passed}")
    print(f"  {elapsed:.1f}s")

    # The claim this whole fixture exists to test. A canonical solution that
    # fails means the harness is broken, not that the data is interesting.
    bad = conn.execute(
        """SELECT g.problem_id, r.n_tests_passed, r.n_tests_total, r.error_type
           FROM generations g JOIN results r ON r.gen_id = g.gen_id
           WHERE g.mock_mode = 'canonical' AND r.passed = 0"""
    ).fetchall()
    if bad:
        print(f"\n  HARNESS BUG: {len(bad)} canonical solutions FAILED.")
        for row in bad[:10]:
            print(f"    {row['problem_id']}: {row['n_tests_passed']}/"
                  f"{row['n_tests_total']} ({row['error_type']})")
        sys.exit(1)
    n_canon = conn.execute(
        "SELECT COUNT(*) FROM generations WHERE mock_mode = 'canonical'"
    ).fetchone()[0]
    print(f"  canonical-solution check: {n_canon}/{n_canon} PASS")

    # Pass rate per fixture shape. A `stub` that passes means the mutation was
    # a no-op and the row is mislabelled; `near_miss` passing occasionally is
    # expected, since not every mutation changes behaviour on every input.
    print("\n  pass rate by mock mode:")
    for row in conn.execute(
        """SELECT g.mock_mode, COUNT(*) n, COALESCE(SUM(r.passed), 0) p
           FROM generations g LEFT JOIN results r ON r.gen_id = g.gen_id
           GROUP BY g.mock_mode ORDER BY g.mock_mode"""
    ):
        print(f"    {row['mock_mode']:12} {row['p']:>4}/{row['n']:<4}")

    n_stub_pass = conn.execute(
        """SELECT COUNT(*) FROM generations g JOIN results r ON r.gen_id = g.gen_id
           WHERE g.mock_mode = 'stub' AND r.passed = 1"""
    ).fetchone()[0]
    if n_stub_pass:
        print(f"\n  MOCK BUG: {n_stub_pass} stub rows graded PASS. The stub "
              f"shadow is not taking effect.")
        sys.exit(1)

    s = db.summary(conn)
    print(f"  db: {s['problems']} problems, {s['configs']} configs, "
          f"{s['generations']} generations ({s['mock_generations']} mock), "
          f"{s['results']} results")
    print(f"  real money spent: ${s['real_spend_usd']:.4f}")
    print(f"\n  Next:  uv run python scripts/view.py --list")
    print(f"         uv run python scripts/make_viewer.py")
    conn.close()


if __name__ == "__main__":
    main()
