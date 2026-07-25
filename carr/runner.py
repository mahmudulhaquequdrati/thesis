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
from dataclasses import dataclass, field

from carr import db
from carr.cost import compute_cost, fmt_usd
from carr.execute.verify import grade
from carr.extract import extract_code

# Rough per-call output-token expectation. Used ONLY for ordering and for the
# printed estimate -- never for the cap, which uses the worst case.
EXPECTED_OUT = {"off": 350, "high": 3500}

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


def run(conn, cells: list[Cell], provider, *, max_tokens: int,
        abort_at_usd: float, warn_at_usd: float | None = None,
        temperature: float = 0.0, on_row=None) -> RunReport:
    """Buy and grade each cell. Stops the moment the next call could breach."""
    report = RunReport(planned=len(cells))
    spend = lifetime_spend(conn)
    warned = False

    for cell in cells:
        worst = cell.worst_usd(max_tokens)
        if spend + worst > abort_at_usd:
            report.stopped_reason = (
                f"stopped before {cell.config.label} on {cell.problem_id}: "
                f"lifetime spend {fmt_usd(spend)} + worst case {fmt_usd(worst)} "
                f"would exceed the cap {fmt_usd(abort_at_usd)}"
            )
            break

        gen = provider.complete(cell.prompt, cell.config,
                                problem_id=cell.problem_id,
                                max_tokens=max_tokens, temperature=temperature)

        cost = compute_cost(
            gen.usage.prompt_tokens if gen.usage else 0,
            gen.usage.completion_tokens if gen.usage else 0,
            cell.config.price_in_per_m, cell.config.price_out_per_m,
        )
        spend += cost
        report.spent_usd += cost

        code = extract_code(gen.raw_response)
        gen_id = db.insert_generation(
            conn,
            problem_id=cell.problem_id, config_id=cell.config.tier_index,
            request_hash=cell.request_hash, openrouter_gen_id=gen.provider_gen_id,
            raw_response=gen.raw_response, extracted_code=code,
            prompt_tokens=gen.usage.prompt_tokens if gen.usage else None,
            completion_tokens=gen.usage.completion_tokens if gen.usage else None,
            reasoning_tokens=gen.usage.reasoning_tokens if gen.usage else None,
            cost_computed_usd=cost, cost_actual_usd=None,
            finish_reason=gen.finish_reason, latency_ms=gen.latency_ms,
            temperature_sent=temperature, error=gen.error, is_mock=0,
        )
        conn.commit()

        if gen_id is None:            # lost a race with the UNIQUE index
            report.skipped += 1
            continue
        report.bought += 1
        if gen.provider_gen_id:
            report.generation_ids.append(gen.provider_gen_id)
        if gen.error:
            report.errors += 1

        result = None
        if code:
            dataset = BENCH_DATASET[cell.benchmark]
            t0 = time.perf_counter()
            # Grading is free but slow, and it runs untrusted code. A crash
            # here must not lose the generation we just paid for -- the row is
            # already committed above.
            try:
                result = grade(dataset, cell.problem_id, code)
                db.upsert_result(conn, gen_id, result,
                                 exec_ms=int((time.perf_counter() - t0) * 1000))
                conn.commit()
                report.graded += 1
                report.passed += int(result.passed)
            except Exception as exc:                          # noqa: BLE001
                print(f"    grader raised on {cell.problem_id}: "
                      f"{type(exc).__name__}: {exc}")

        if on_row:
            on_row(cell, gen, result, cost, spend)

        if warn_at_usd and not warned and spend >= warn_at_usd:
            warned = True
            print(f"\n  ** lifetime spend has passed {fmt_usd(warn_at_usd)} "
                  f"(cap {fmt_usd(abort_at_usd)}) **\n")

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
    return updated, drift
