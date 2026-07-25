"""The paid loop: many problems x many configs, resumable and cost-capped.

Every safety property this project has about money lives here.

**The cap aborts, and it aborts before spending, not after.** Before each call
the runner asks: could this one call, at its worst case, push the *lifetime*
spend of the database past `abort_at_usd`? Worst case is `max_tokens` x the
output price -- not an expectation, because an expectation that is wrong is
exactly the situation a cap exists for. If the answer is yes, the run stops
having spent nothing extra. Lifetime, not per-run, because five careful runs
that each stay under their own limit still empty the account.

**Nothing is ever bought twice.** `request_hash` is checked before the call is
built. A crash, a Ctrl-C, or a cap abort costs nothing to resume from: re-run
the same command and it picks up where it stopped.

**Cheapest first.** Ordered by expected cost across the whole (problem, config)
plan, so if the cap does fire it fires on the expensive tail and leaves a
complete cheap foundation rather than a random half of everything.

Cost reconciliation is deliberately NOT per call. `/generation` needs ~10s to
settle, and 2,600 calls x 10s is over seven hours of waiting. Generation ids
are collected and reconciled in one pass at the end.
"""

from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field

from carr import db
from carr.cost import compute_cost, fmt_usd
from carr.execute.verify import grade
from carr.extract import extract_code

# Rough per-call output-token expectation. Used ONLY for ordering and for the
# printed estimate -- never for the cap, which uses the worst case.
EXPECTED_OUT = {"off": 350, "high": 3500}

# max_tokens turns out NOT to be a hard bound. On 2026-07-26 qwen3.5-9b
# returned 35,837 completion tokens against a max_tokens of 16,000 -- 2.24x --
# and then set finish_reason to "error". So "max_tokens x output price" is the
# worst case the *request* asked for, not the worst case that can be billed.
# The pre-call check multiplies by this so a single overrun cannot walk through
# a cap that looked satisfied. Actual spend is still re-read before every call,
# so an overrun self-corrects for everything after it.
WORST_CASE_SAFETY = 2.5

BENCH_DATASET = {
    "humaneval_plus": "humaneval",
    "mbpp_plus": "mbpp",
    "livecodebench": "livecodebench",
}


@dataclass
class Cell:
    """One (problem, config) pair: exactly one paid API call."""

    problem_id: str
    benchmark: str
    prompt: str
    config: object          # carr.effort.Config
    request_hash: str
    prompt_tokens: int

    def expected_usd(self) -> float:
        return compute_cost(self.prompt_tokens,
                            EXPECTED_OUT.get(self.config.effort_label, 3500),
                            self.config.price_in_per_m, self.config.price_out_per_m)

    def worst_usd(self, max_tokens: int) -> float:
        """What this call could cost if it ignores max_tokens (see the constant)."""
        return WORST_CASE_SAFETY * compute_cost(
            self.prompt_tokens, max_tokens,
            self.config.price_in_per_m, self.config.price_out_per_m)

    def requested_usd(self, max_tokens: int) -> float:
        """What it costs if the provider honours max_tokens. For reporting only."""
        return compute_cost(self.prompt_tokens, max_tokens,
                            self.config.price_in_per_m, self.config.price_out_per_m)


@dataclass
class RunReport:
    planned: int = 0
    skipped: int = 0
    bought: int = 0
    graded: int = 0
    passed: int = 0
    errors: int = 0
    spent_usd: float = 0.0
    stopped_reason: str | None = None
    generation_ids: list[str] = field(default_factory=list)


def plan(conn, problem_ids: list[str], configs: list) -> tuple[list[Cell], int]:
    """Build the work list, cheapest expected first, skipping bought cells.

    Returns (cells_to_run, already_bought_count).
    """
    cells: list[Cell] = []
    skipped = 0

    for problem_id in problem_ids:
        problem = db.get_problem(conn, problem_id)
        if problem is None:
            raise ValueError(f"{problem_id} is not in the database")
        prompt = problem["prompt"]
        prompt_tokens = max(1, len(prompt) // 4)   # chars/4, as in data-spec

        for cfg in configs:
            h = db.request_hash(cfg.model_slug, cfg.effort_label, prompt,
                                cfg.params, problem_id)
            if db.has_generation(conn, h):
                skipped += 1
                continue
            cells.append(Cell(problem_id, problem["benchmark"], prompt, cfg, h,
                              prompt_tokens))

    # Global cheapest-first: every `off` config across every problem runs before
    # any `high` one, so a cap abort leaves the cheap half of the grid complete.
    cells.sort(key=lambda c: (c.expected_usd(), c.problem_id))
    return cells, skipped


def lifetime_spend(conn) -> float:
    """Everything ever bought into this database. Actual cost wins over computed."""
    return conn.execute(
        "SELECT COALESCE(SUM(COALESCE(cost_actual_usd, cost_computed_usd)), 0) "
        "FROM generations WHERE COALESCE(is_mock, 0) = 0"
    ).fetchone()[0]


def _store(conn, cell, gen, temperature: float) -> tuple[int | None, float]:
    """Write one generation row. Returns (gen_id, cost). Main thread only."""
    cost = compute_cost(
        gen.usage.prompt_tokens if gen.usage else 0,
        gen.usage.completion_tokens if gen.usage else 0,
        cell.config.price_in_per_m, cell.config.price_out_per_m,
    )
    gen_id = db.insert_generation(
        conn,
        problem_id=cell.problem_id, config_id=cell.config.tier_index,
        request_hash=cell.request_hash, openrouter_gen_id=gen.provider_gen_id,
        raw_response=gen.raw_response,
        extracted_code=extract_code(gen.raw_response),
        prompt_tokens=gen.usage.prompt_tokens if gen.usage else None,
        completion_tokens=gen.usage.completion_tokens if gen.usage else None,
        reasoning_tokens=gen.usage.reasoning_tokens if gen.usage else None,
        cost_computed_usd=cost, cost_actual_usd=None,
        finish_reason=gen.finish_reason, latency_ms=gen.latency_ms,
        temperature_sent=temperature, error=gen.error, is_mock=0,
    )
    conn.commit()
    return gen_id, cost


def buy(conn, cells: list[Cell], provider, *, max_tokens: int,
        abort_at_usd: float, warn_at_usd: float | None = None,
        temperature: float = 0.0, concurrency: int = 1,
        on_row=None) -> RunReport:
    """Phase 1: purchase generations. No grading -- that is free and separate.

    API calls are I/O-bound and independent, so they run `concurrency` at a
    time. The cost cap survives that because dispatch happens in waves: before
    a wave is sent, the whole wave's worst case must fit the remaining
    headroom. Nothing is fired that has not already been paid for in the
    accounting, so concurrency cannot slip a call past the cap.

    Grading is deliberately NOT interleaved. It is free, CPU-bound and slow
    (an LCB problem runs 43 tests twice), and mixing it in serialised the paid
    calls behind it -- the pilot was spending a minute per cell mostly waiting
    on the grader.
    """
    report = RunReport(planned=len(cells))
    spend = lifetime_spend(conn)
    warned = False
    i = 0
    inflight: dict = {}          # future -> (cell, reserved_usd)
    reserved = 0.0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        while True:
            # Top the pool up continuously rather than in fixed waves. A wave
            # only advances when its SLOWEST call returns, so one 180s
            # straggler idles every other worker; measured latency on identical
            # prompts already varied 2.5s-12.8s, and thinking calls are far
            # worse. Continuous dispatch keeps every slot busy.
            while i < len(cells) and len(inflight) < max(1, concurrency):
                nxt = cells[i]
                w = nxt.worst_usd(max_tokens)
                # Reserve the worst case up front, so a call is never dispatched
                # on budget that another in-flight call might already be using.
                if spend + reserved + w > abort_at_usd:
                    break
                fut = pool.submit(provider.complete, nxt.prompt, nxt.config,
                                  problem_id=nxt.problem_id,
                                  max_tokens=max_tokens, temperature=temperature)
                inflight[fut] = (nxt, w)
                reserved += w
                i += 1

            if not inflight:
                if i < len(cells):
                    blocker = cells[i]
                    report.stopped_reason = (
                        f"stopped before {blocker.config.label} on "
                        f"{blocker.problem_id}: lifetime spend {fmt_usd(spend)} + "
                        f"worst case {fmt_usd(blocker.worst_usd(max_tokens))} "
                        f"would exceed the cap {fmt_usd(abort_at_usd)}"
                    )
                break

            done, _ = wait(list(inflight), return_when=FIRST_COMPLETED)
            for fut in done:
                cell, w = inflight.pop(fut)
                reserved -= w
                try:
                    gen = fut.result()
                except Exception as exc:                       # noqa: BLE001
                    from carr.providers.base import Generation
                    gen = Generation(error=f"{type(exc).__name__}: {exc}")

                gen_id, cost = _store(conn, cell, gen, temperature)
                spend += cost
                report.spent_usd += cost
                if gen_id is None:
                    report.skipped += 1
                    continue
                report.bought += 1
                if gen.provider_gen_id:
                    report.generation_ids.append(gen.provider_gen_id)
                if gen.error:
                    report.errors += 1
                if on_row:
                    on_row(cell, gen, None, cost, spend)

            if warn_at_usd and not warned and spend >= warn_at_usd:
                warned = True
                print(f"\n  ** lifetime spend has passed {fmt_usd(warn_at_usd)} "
                      f"(cap {fmt_usd(abort_at_usd)}) **\n", flush=True)

    return report


def grade_pending(conn, *, concurrency: int = 4, on_graded=None) -> tuple[int, int]:
    """Phase 2: grade every generation that has code but no result yet. FREE.

    Separate from buying so it can be re-run at any time -- fixing an
    extraction bug means re-grading, never re-purchasing. Threads are fine
    despite the GIL because grade() spends its time waiting on subprocesses.
    """
    rows = conn.execute(
        """SELECT g.gen_id, g.problem_id, g.extracted_code, p.benchmark
           FROM generations g
           JOIN problems p ON p.problem_id = g.problem_id
           LEFT JOIN results r ON r.gen_id = g.gen_id
           WHERE r.gen_id IS NULL AND g.extracted_code IS NOT NULL
           ORDER BY g.gen_id"""
    ).fetchall()
    if not rows:
        return 0, 0

    def work(row):
        t0 = time.perf_counter()
        try:
            res = grade(BENCH_DATASET[row["benchmark"]], row["problem_id"],
                        row["extracted_code"])
            return row, res, int((time.perf_counter() - t0) * 1000), None
        except Exception as exc:                               # noqa: BLE001
            return row, None, 0, exc

    graded = passed = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        for row, res, ms, exc in pool.map(work, rows):
            if exc is not None:
                print(f"    grader raised on {row['problem_id']}: "
                      f"{type(exc).__name__}: {exc}", flush=True)
                continue
            db.upsert_result(conn, row["gen_id"], res, exec_ms=ms)
            conn.commit()
            graded += 1
            passed += int(res.passed)
            if on_graded:
                on_graded(row, res)
    return graded, passed


def run(conn, cells: list[Cell], provider, *, max_tokens: int,
        abort_at_usd: float, warn_at_usd: float | None = None,
        temperature: float = 0.0, concurrency: int = 1,
        grade_concurrency: int = 4, on_row=None) -> RunReport:
    """Buy everything, then grade everything. Convenience wrapper over the two."""
    report = buy(conn, cells, provider, max_tokens=max_tokens,
                 abort_at_usd=abort_at_usd, warn_at_usd=warn_at_usd,
                 temperature=temperature, concurrency=concurrency, on_row=on_row)
    graded, passed = grade_pending(conn, concurrency=grade_concurrency)
    report.graded, report.passed = graded, passed
    return report


def reconcile_costs(conn, provider, generation_ids: list[str],
                    settle_seconds: float = 12.0) -> tuple[int, float]:
    """Fill cost_actual_usd from OpenRouter's ground truth, in one pass.

    Returns (rows_updated, total_drift). Drift is actual minus computed; a
    consistent non-zero drift means config/models.yaml has gone stale, which is
    exactly the silent failure `cost_computed_usd` exists to detect.
    """
    if not generation_ids:
        return 0, 0.0

    # /generation 404s until the record settles (~10s). Wait once for the batch
    # rather than once per call, which is the whole point of batching.
    print(f"  waiting {settle_seconds:.0f}s for cost records to settle...")
    time.sleep(settle_seconds)

    updated, drift = 0, 0.0
    for gen_id in generation_ids:
        actual = provider.fetch_cost(gen_id)
        if actual is None:
            continue
        row = conn.execute(
            "SELECT gen_id, cost_computed_usd FROM generations "
            "WHERE openrouter_gen_id = ?", (gen_id,)
        ).fetchone()
        if row is None:
            continue
        conn.execute("UPDATE generations SET cost_actual_usd = ? WHERE gen_id = ?",
                     (actual, row["gen_id"]))
        drift += actual - (row["cost_computed_usd"] or 0.0)
        updated += 1
    conn.commit()

    # A gap between the price table and the bill is how a stale or wrong roster
    # announces itself, and it is otherwise invisible. On 2026-07-26 an unpinned
    # run came back 1.54x over, because OpenRouter routed one slug across nine
    # providers whose prices span 4x while config/models.yaml recorded only the
    # cheapest. Providers are pinned now, so any gap here means the pin broke or
    # a price moved -- stop and re-run verify_roster.py before spending more.
    if updated:
        computed = sum(
            r[0] or 0.0 for r in conn.execute(
                "SELECT cost_computed_usd FROM generations "
                "WHERE cost_actual_usd IS NOT NULL")
        )
        actual = computed + drift
        if computed > 0 and abs(actual / computed - 1.0) > 0.05:
            print(f"\n  !! PRICE TABLE IS WRONG: billed {fmt_usd(actual)} against "
                  f"a predicted {fmt_usd(computed)} ({actual / computed:.2f}x).\n"
                  f"     The cost cap is enforced on the predicted number, so it "
                  f"is not protecting you.\n"
                  f"     Run: uv run python scripts/verify_roster.py\n",
                  flush=True)
    return updated, drift
