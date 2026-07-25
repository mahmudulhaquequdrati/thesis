"""Day 4: one problem, real models, all the way through. COSTS MONEY.

    problem -> prompt -> OpenRouter -> raw response -> extract -> grade -> row

Everything in that chain already existed and was tested; this connects it to
the paid backend and stores the result.

    uv run python scripts/run_one.py --dry-run          # free, proves the wiring
    uv run python scripts/run_one.py --config 0 --yes   # ONE call, ~$0.0001
    uv run python scripts/run_one.py --all --yes        # one problem x 10 configs

Three cost controls, because a bigger balance is not a bigger budget:

  * A hard cap that ABORTS. Before calling anything, the worst case is computed
    as max_tokens x the output price for every cell about to run. If that
    exceeds --max-usd, nothing is sent. Worst case, not expected case -- an
    expected-case cap is not a cap.
  * `request_hash` dedup. A cell already bought is skipped, so re-running this
    is free and a crash costs nothing.
  * Cheapest-first ordering, by *expected* cost, so a surprise hits the
    expensive tail rather than the cheap foundation.

`cost_actual_usd` is left NULL. GET /generation needs ~10s to settle; costs get
reconciled in a batch later.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from carr import db  # noqa: E402
from carr.cost import compute_cost, fmt_usd  # noqa: E402
from carr.effort import load_configs  # noqa: E402
from carr.execute.verify import grade  # noqa: E402
from carr.extract import extract_code  # noqa: E402
from carr.providers.openrouter import DEFAULT_MAX_TOKENS, OpenRouterProvider  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Rough per-call output-token expectation, only for ordering and for the
# "expected" line in the estimate. The pilot replaces these with measurements.
EXPECTED_OUT = {"off": 350, "high": 3500}

BENCH_DATASET = {"humaneval_plus": "humaneval", "mbpp_plus": "mbpp",
                 "livecodebench": "livecodebench"}


def expected_cost(cfg, prompt_tokens: int) -> float:
    return compute_cost(prompt_tokens, EXPECTED_OUT.get(cfg.effort_label, 3500),
                        cfg.price_in_per_m, cfg.price_out_per_m)


def worst_cost(cfg, prompt_tokens: int, max_tokens: int) -> float:
    """Every completion token billed at the ceiling. This is what we cap on."""
    return compute_cost(prompt_tokens, max_tokens,
                        cfg.price_in_per_m, cfg.price_out_per_m)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", default="HumanEval/0")
    ap.add_argument("--config", type=int, help="one config by config_id")
    ap.add_argument("--all", action="store_true", help="every config")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--max-usd", type=float, default=0.20,
                    help="hard cap on the WORST-CASE spend of this invocation")
    ap.add_argument("--dry-run", action="store_true",
                    help="do everything except call the API. Free")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    if not args.all and args.config is None:
        sys.exit("pick one: --config N (see scripts/view.py) or --all")

    load_dotenv(ROOT / ".env")
    conn = db.connect(Path(args.db) if args.db else db.DEFAULT_DB)
    db.init_schema(conn)

    problem = db.get_problem(conn, args.problem)
    if problem is None:
        sys.exit(f"{args.problem} is not in the database. "
                 f"Run: uv run python scripts/init_db.py")

    dataset = BENCH_DATASET.get(problem["benchmark"])
    if dataset is None:
        sys.exit(f"no grader for benchmark {problem['benchmark']!r}")

    prompt = problem["prompt"]
    prompt_tokens = max(1, len(prompt) // 4)   # chars/4, same as data-spec

    configs = load_configs()
    for cfg in configs:
        db.upsert_config(conn, cfg.tier_index, cfg)
    conn.commit()

    if not args.all:
        configs = [c for c in configs if c.tier_index == args.config]
        if not configs:
            sys.exit(f"no config with id {args.config}")

    # Cheapest EXPECTED cost first. config_id stays the price_out ordering --
    # that is an identity; this is a budget policy, and they differ because
    # 'off' burns ~10x fewer tokens at the same per-token price.
    configs.sort(key=lambda c: expected_cost(c, prompt_tokens))

    todo, skipped = [], 0
    for cfg in configs:
        h = db.request_hash(cfg.model_slug, cfg.effort_label, prompt,
                            cfg.params, args.problem)
        if db.has_generation(conn, h):
            skipped += 1
            continue
        todo.append((cfg, h))

    print("=" * 92)
    print(f"  {args.problem}   {problem['entry_point']}()   "
          f"[{problem['benchmark']}]   {problem['n_tests']} tests")
    print(f"  prompt {problem['prompt_chars']} chars ~ {prompt_tokens} tokens")
    print("=" * 92)

    if skipped:
        print(f"  {skipped} cell(s) already bought -- skipping, they cost $0 again")
    if not todo:
        print("  nothing left to run.\n")
        return

    worst = sum(worst_cost(c, prompt_tokens, args.max_tokens) for c, _ in todo)
    expect = sum(expected_cost(c, prompt_tokens) for c, _ in todo)

    print(f"\n  {len(todo)} call(s) to make, cheapest expected first:")
    for cfg, _ in todo:
        print(f"    {cfg.label:44} expect {fmt_usd(expected_cost(cfg, prompt_tokens))}"
              f"   worst {fmt_usd(worst_cost(cfg, prompt_tokens, args.max_tokens))}")
    print(f"\n  expected total   {fmt_usd(expect)}")
    print(f"  WORST CASE       {fmt_usd(worst)}   (max_tokens={args.max_tokens})")
    print(f"  cap              {fmt_usd(args.max_usd)}")

    if worst > args.max_usd:
        sys.exit(f"\n  ABORTED: worst case {fmt_usd(worst)} exceeds the cap "
                 f"{fmt_usd(args.max_usd)}.\n"
                 f"  Raise --max-usd deliberately, or lower --max-tokens.")

    if args.dry_run:
        print("\n  --dry-run: no API calls made, nothing spent.\n")
        return

    if not args.yes:
        if not sys.stdin.isatty():
            sys.exit("\n  refusing to spend without --yes when not interactive.")
        if input("\n  spend it? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("  cancelled, nothing spent.")

    provider = OpenRouterProvider()
    spent = 0.0
    print()

    for cfg, req_hash in todo:
        gen = provider.complete(prompt, cfg, problem_id=args.problem,
                                max_tokens=args.max_tokens)
        code = extract_code(gen.raw_response)
        cost = compute_cost(
            gen.usage.prompt_tokens if gen.usage else 0,
            gen.usage.completion_tokens if gen.usage else 0,
            cfg.price_in_per_m, cfg.price_out_per_m,
        )
        spent += cost

        gen_id = db.insert_generation(
            conn,
            problem_id=args.problem, config_id=cfg.tier_index,
            request_hash=req_hash, openrouter_gen_id=gen.provider_gen_id,
            raw_response=gen.raw_response, extracted_code=code,
            prompt_tokens=gen.usage.prompt_tokens if gen.usage else None,
            completion_tokens=gen.usage.completion_tokens if gen.usage else None,
            reasoning_tokens=gen.usage.reasoning_tokens if gen.usage else None,
            cost_computed_usd=cost, cost_actual_usd=None,
            finish_reason=gen.finish_reason, latency_ms=gen.latency_ms,
            temperature_sent=0.0, error=gen.error, is_mock=0,
        )
        conn.commit()

        if gen_id is None:
            print(f"  {cfg.label:44} duplicate, skipped")
            continue

        if code:
            t0 = time.perf_counter()
            result = grade(dataset, args.problem, code)
            db.upsert_result(conn, gen_id, result,
                             exec_ms=int((time.perf_counter() - t0) * 1000))
            conn.commit()
            verdict = "PASS" if result.passed else "FAIL"
            detail = f"{result.n_tests_passed}/{result.n_tests_total}"
        else:
            verdict = "SKIP"
            detail = gen.error or "no code extracted"

        u = gen.usage
        print(f"  {cfg.label:44} {verdict}  {detail:>12}  "
              f"out {(u.completion_tokens if u else 0):>6}  "
              f"think {(u.reasoning_tokens if u else 0):>6}  "
              f"{fmt_usd(cost)}  {gen.latency_ms:>6}ms  {gen.finish_reason or ''}")

        # Second line of defence: the estimate could be wrong, actual spend
        # cannot be. Stop the moment it crosses the cap.
        if spent > args.max_usd:
            print(f"\n  STOPPING: actual spend {fmt_usd(spent)} reached the cap.")
            break

    print(f"\n  spent this run: {fmt_usd(spent)}")
    best = db.cheapest_passing(conn, args.problem)
    if best:
        print(f"  routing target: cheapest config that solved it = "
              f"{best['model_slug']} | {best['effort_label']} "
              f"at {fmt_usd(best['cost_computed_usd'])}")
    else:
        print("  no config has solved this problem yet")

    s = db.summary(conn)
    print(f"\n  total real spend in db: ${s['real_spend_usd']:.6f}   "
          f"({s['generations']} generations)")
    print(f"  inspect: uv run python scripts/view.py {args.problem}\n")
    conn.close()


if __name__ == "__main__":
    main()
