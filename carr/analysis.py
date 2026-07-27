"""Turn the generations table into the thesis's results. Free -- pure SQL and arithmetic.

Four things, matching the reframed research questions:

  saturation()      RQ0  which problems can discriminate between configs at all
  reasoning_by_tier() RQ1  what predicts how long a model reasons
  waste()           RQ2  when is that reasoning wasted, and what did it cost
  abort_curve()     RQ3  what a reasoning-length abort would have saved

`abort_curve` is the headline deliverable. It is a simulation over completed
calls, and it relies on one measured fact: **aborting a stream mid-reasoning is
billed $0.00** (verified 2026-07-26 on two providers, against $0.010978 for the
same cell run to completion). So an aborted call is scored as costing nothing
and solving nothing -- not as a pro-rata saving.

Everything filters `is_mock = 0` and prefers `cost_actual_usd` over
`cost_computed_usd`, because the price table was wrong by 1.54x before
providers were pinned and only the billed number is trustworthy.
"""

from __future__ import annotations

from dataclasses import dataclass

from carr.stats import bootstrap_ci, proportion, ratio

# Actual cost where OpenRouter has told us, our estimate otherwise. Never the
# estimate alone -- see the provider-pinning finding in THESIS.md section 12.
_COST = "COALESCE(g.cost_actual_usd, g.cost_computed_usd)"
_REAL = "COALESCE(g.is_mock, 0) = 0"

# Whether a call was BILLED is what separates a model outcome from an
# infrastructure one, and the distinction is not cosmetic.
#
# A 404 from a pinned provider, or a 429 when it is overloaded, says nothing
# about the model -- but it produces a row with error set, and counting it as a
# failure understates the pass rate. It costs $0, because nothing ran.
#
# A call that burned 16,000 tokens and returned no answer also has error set,
# but it was billed in full and IS a model outcome -- the most expensive kind.
#
# So: billed and no usable answer = wasted. Not billed = infrastructure, and it
# is excluded from every rate rather than silently scored as a failure.
_INFRA = f"(g.error IS NOT NULL AND COALESCE({_COST}, 0) <= 0)"
_WASTED = (f"(COALESCE({_COST}, 0) > 0 "
           f"AND (g.finish_reason = 'length' OR g.error IS NOT NULL))")


def saturation(conn) -> list[dict]:
    """Per tier: pass rate with reasoning off vs on.

    A tier where both columns sit near 100% cannot inform any routing or abort
    decision -- every config solves everything, so there is nothing to choose.
    """
    rows = conn.execute(f"""
        SELECT COALESCE(p.difficulty, p.benchmark) AS tier,
               c.effort_label AS effort,
               COUNT(*) AS n,
               SUM(COALESCE(r.passed, 0)) AS passed,
               ROUND(100.0 * SUM(COALESCE(r.passed, 0)) / COUNT(*), 1) AS pct
        FROM generations g
        JOIN configs c  ON c.config_id = g.config_id
        JOIN problems p ON p.problem_id = g.problem_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA}
        GROUP BY tier, effort
        ORDER BY pct
    """).fetchall()
    return [dict(r) for r in rows]


def discriminating_problems(conn) -> dict[str, int]:
    """How many problems actually carry a signal.

    A problem every config solves, and a problem none solves, are equally
    useless: neither can distinguish a good decision from a bad one. Only
    problems where configs DISAGREE contribute anything.
    """
    rows = conn.execute(f"""
        WITH per_problem AS (
            SELECT g.problem_id,
                   SUM(COALESCE(r.passed, 0)) AS n_pass,
                   COUNT(*) AS n_cells
            FROM generations g
            LEFT JOIN results r ON r.gen_id = g.gen_id
            WHERE {_REAL} AND NOT {_INFRA}
            GROUP BY g.problem_id
        )
        SELECT CASE WHEN n_pass = 0        THEN 'none solved'
                    WHEN n_pass = n_cells  THEN 'all solved'
                    ELSE 'discriminating' END AS bucket,
               COUNT(*) AS n
        FROM per_problem GROUP BY bucket
    """).fetchall()
    return {r["bucket"]: r["n"] for r in rows}


def reasoning_by_tier(conn) -> list[dict]:
    """RQ1: does the model reason longer on harder problems?"""
    rows = conn.execute(f"""
        SELECT COALESCE(p.difficulty, p.benchmark) AS tier,
               COUNT(*) AS n,
               ROUND(AVG(g.reasoning_tokens)) AS avg_reasoning,
               MIN(g.reasoning_tokens) AS min_reasoning,
               MAX(g.reasoning_tokens) AS max_reasoning
        FROM generations g
        JOIN configs c  ON c.config_id = g.config_id
        JOIN problems p ON p.problem_id = g.problem_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
              AND g.reasoning_tokens > 0
        GROUP BY tier ORDER BY avg_reasoning
    """).fetchall()
    return [dict(r) for r in rows]


def waste(conn) -> list[dict]:
    """RQ2: outcome vs reasoning length, with the bill attached.

    The expected shape, and what the pilot showed: passing calls reason least,
    calls that return nothing reason most and cost most per unit of nothing.
    """
    rows = conn.execute(f"""
        SELECT CASE WHEN {_WASTED}      THEN 'wasted (no answer)'
                    WHEN r.passed = 1   THEN 'passed'
                    WHEN r.passed = 0   THEN 'failed'
                    ELSE 'ungraded' END AS outcome,
               COUNT(*) AS n,
               ROUND(AVG(g.reasoning_tokens)) AS avg_reasoning,
               ROUND(SUM({_COST}), 6) AS total_usd
        FROM generations g
        JOIN configs c ON c.config_id = g.config_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
        GROUP BY outcome ORDER BY avg_reasoning
    """).fetchall()
    return [dict(r) for r in rows]


@dataclass
class AbortPoint:
    threshold: int
    passes_kept: int
    passes_total: int
    cost_usd: float
    baseline_usd: float
    aborted: int

    @property
    def saved_pct(self) -> float:
        if not self.baseline_usd:
            return 0.0
        return 100.0 * (1 - self.cost_usd / self.baseline_usd)

    @property
    def passes_lost(self) -> int:
        return self.passes_total - self.passes_kept

    @property
    def dominant(self) -> bool:
        """Saves money while losing nothing -- a free improvement."""
        return self.passes_lost == 0 and self.saved_pct > 0


def abort_curve(conn, thresholds=(2000, 3000, 4000, 5000, 6000, 8000,
                                  10000, 12000, 16000)) -> list[AbortPoint]:
    """RQ3: what a reasoning-length abort would have saved.

    A call whose reasoning exceeded the threshold is treated as aborted: it
    costs $0 (measured, not assumed) and solves nothing. Calls under the
    threshold are unaffected -- they had already finished thinking by then.

    Note this is a SIMULATION over calls that ran to completion. It is only
    valid because zero-cost cancellation was verified directly; if a provider
    billed for cancelled streams, every number here would be wrong.
    """
    rows = conn.execute(f"""
        SELECT COALESCE(g.reasoning_tokens, 0) AS think,
               {_COST} AS cost,
               CASE WHEN {_WASTED} THEN 0 ELSE COALESCE(r.passed, 0) END AS ok
        FROM generations g
        JOIN configs c ON c.config_id = g.config_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
    """).fetchall()
    if not rows:
        return []

    baseline_cost = sum(r["cost"] or 0 for r in rows)
    total_passes = sum(r["ok"] for r in rows)

    out = []
    for t in thresholds:
        kept = [r for r in rows if r["think"] <= t]
        out.append(AbortPoint(
            threshold=t,
            passes_kept=sum(r["ok"] for r in kept),
            passes_total=total_passes,
            cost_usd=sum(r["cost"] or 0 for r in kept),
            baseline_usd=baseline_cost,
            aborted=len(rows) - len(kept),
        ))
    return out


def best_threshold(conn) -> AbortPoint | None:
    """The cheapest threshold that loses no solved problems.

    Returns None when no such threshold exists, which is the measured outcome:
    at the 48k ceiling, 56 calls above 10,000 reasoning tokens succeeded, so
    every threshold trades solutions for money. The pilot's apparent free
    saving was an artefact of truncation at 16k -- a censored call cannot
    succeed, so the ceiling manufactured the cliff the claim depended on.

    A threshold must still be chosen on data the abort is NOT evaluated
    against, or it is fitted.
    """
    curve = [p for p in abort_curve(conn) if p.dominant]
    return min(curve, key=lambda p: p.cost_usd) if curve else None


def summary(conn) -> dict:
    return {
        "saturation": saturation(conn),
        "problems": discriminating_problems(conn),
        "reasoning_by_tier": reasoning_by_tier(conn),
        "waste": waste(conn),
        "abort_curve": abort_curve(conn),
        "best_threshold": best_threshold(conn),
    }


def censoring(conn, max_tokens: int | None = None) -> list[dict]:
    """How many thinking calls hit the ceiling, per tier.

    A call stopped at `max_tokens` gives a censored observation: its true
    reasoning length is unknown, only that it exceeded the cap. That biases
    every statistic computed from reasoning length, and it biases the abort
    curve in one specific direction -- a censored call cannot have succeeded,
    so it makes long reasoning look worse than it is.

    At the 16,000 ceiling the pilot ran under, 44% of LCB-hard thinking calls
    were censored -- and that censoring is what produced the pilot's
    now-refuted claim of a free abort threshold. At 48k it is down to ~26% on
    hard, so the right-hand end of the abort curve is still softer than the
    left. Reported alongside the results rather than left to be discovered.
    """
    rows = conn.execute(f"""
        SELECT COALESCE(p.difficulty, p.benchmark) AS tier,
               COUNT(*) AS n,
               SUM(CASE WHEN g.finish_reason = 'length' THEN 1 ELSE 0 END) AS censored,
               ROUND(100.0 * SUM(CASE WHEN g.finish_reason = 'length' THEN 1 ELSE 0 END)
                     / COUNT(*), 1) AS pct
        FROM generations g
        JOIN configs c  ON c.config_id = g.config_id
        JOIN problems p ON p.problem_id = g.problem_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
        GROUP BY tier
        HAVING censored > 0
        ORDER BY pct DESC
    """).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------- comparable statistics
#
# The grid is unbalanced: the `off` configs have 320 problems each, the `high`
# configs 51-104, and the held-out model 16-23. A cost-accuracy number computed
# per config over THAT config's own problems compares models on different exams
# and is not a frontier, however it is labelled.
#
# So everything below takes a fixed problem set and states it. `paired_problems`
# supplies the honest default: problems where both effort arms have a graded
# result, currently 107 of 320.


def paired_problems(conn, config_ids: list[int] | None = None) -> list[str]:
    """Problems where EVERY named config has a graded, billed result.

    Defaults to requiring both effort arms (at least one `off` and one `high`),
    which is the comparison the thesis turns on. Pass explicit `config_ids` to
    require a specific set -- but note only 5 problems have all ten.

    Infrastructure failures are excluded via _INFRA, so a problem whose only
    thinking row was a 429 does not count as paired: nothing ran, so there is
    nothing to compare.
    """
    if config_ids:
        marks = ",".join("?" * len(config_ids))
        rows = conn.execute(f"""
            SELECT g.problem_id
            FROM generations g
            JOIN results r ON r.gen_id = g.gen_id
            WHERE {_REAL} AND NOT {_INFRA} AND g.config_id IN ({marks})
            GROUP BY g.problem_id
            HAVING COUNT(DISTINCT g.config_id) = ?
            ORDER BY g.problem_id
        """, [*config_ids, len(config_ids)]).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT g.problem_id
            FROM generations g
            JOIN configs c ON c.config_id = g.config_id
            JOIN results r ON r.gen_id = g.gen_id
            WHERE {_REAL} AND NOT {_INFRA}
            GROUP BY g.problem_id
            HAVING SUM(CASE WHEN c.effort_label = 'off' THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN c.effort_label != 'off' THEN 1 ELSE 0 END) > 0
            ORDER BY g.problem_id
        """).fetchall()
    return [r[0] for r in rows]


def _per_problem_config(conn, problem_ids: list[str]) -> dict[int, list[dict]]:
    """{config_id: [one row per problem]} restricted to `problem_ids`.

    One row per (config, problem) so the bootstrap can resample PROBLEMS. Cells
    on the same problem are not independent observations of difficulty, so
    resampling cells rather than problems would understate every interval.
    """
    if not problem_ids:
        return {}
    marks = ",".join("?" * len(problem_ids))
    rows = conn.execute(f"""
        SELECT g.config_id, g.problem_id,
               {_COST} AS cost,
               COALESCE(g.completion_tokens, 0) AS tokens,
               CASE WHEN {_WASTED} THEN 0 ELSE COALESCE(r.passed, 0) END AS solved
        FROM generations g
        JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND g.problem_id IN ({marks})
    """, problem_ids).fetchall()

    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["config_id"], []).append(
            {"problem_id": r["problem_id"], "cost": r["cost"] or 0.0,
             "tokens": r["tokens"] or 0, "solved": int(r["solved"])})
    return out


def _config_names(conn) -> dict[int, tuple[str, str]]:
    """{config_id: (model_slug, effort_label)} -- labels for reporting."""
    return {r["config_id"]: (r["model_slug"], r["effort_label"])
            for r in conn.execute(
                "SELECT config_id, model_slug, effort_label FROM configs")}


def cost_per_correct(conn, problem_ids: list[str] | None = None, *,
                     seed: int = 0, n_resamples: int = 2000) -> list[dict]:
    """CPC and TPC per config, over ONE fixed problem set, with intervals.

    CPC is total dollars divided by number solved (THESIS.md section 13: "the
    headline economic metric"). TPC is the same, token-denominated.

    Both are ratios of sums, so the bootstrap recomputes sum/sum on each
    resample rather than averaging per-problem ratios -- those are different
    quantities and the second one is wrong.

    `n_resamples` is lower than the stats default because this runs once per
    config in an interactive report; the intervals are stable well below 10,000.
    """
    ids = problem_ids if problem_ids is not None else paired_problems(conn)
    by_config = _per_problem_config(conn, ids)
    names = _config_names(conn)

    out = []
    for config_id, rows in by_config.items():
        solved = sum(r["solved"] for r in rows)
        total_usd = sum(r["cost"] for r in rows)
        total_tok = sum(r["tokens"] for r in rows)
        slug, effort = names.get(config_id, ("?", "?"))

        cpc = total_usd / solved if solved else None
        tpc = total_tok / solved if solved else None
        if solved:
            cpc_lo, cpc_hi = bootstrap_ci(
                rows, ratio(lambda r: r["cost"], lambda r: r["solved"]),
                seed=seed, n_resamples=n_resamples)
            tpc_lo, tpc_hi = bootstrap_ci(
                rows, ratio(lambda r: r["tokens"], lambda r: r["solved"]),
                seed=seed, n_resamples=n_resamples)
        else:
            cpc_lo = cpc_hi = tpc_lo = tpc_hi = float("nan")

        out.append({
            "config_id": config_id, "model_slug": slug, "effort_label": effort,
            "n_problems": len(rows), "solved": solved,
            "total_usd": total_usd, "cpc_usd": cpc, "cpc_lo": cpc_lo, "cpc_hi": cpc_hi,
            "total_tokens": total_tok, "tpc": tpc, "tpc_lo": tpc_lo, "tpc_hi": tpc_hi,
        })
    out.sort(key=lambda r: (r["cpc_usd"] is None, r["cpc_usd"] or 0))
    return out


def pass_rate_ci(conn, problem_ids: list[str] | None = None, *,
                 seed: int = 0, n_resamples: int = 2000) -> list[dict]:
    """Per-config pass rate over a fixed problem set, with an interval."""
    ids = problem_ids if problem_ids is not None else paired_problems(conn)
    by_config = _per_problem_config(conn, ids)
    names = _config_names(conn)
    out = []
    for config_id, rows in by_config.items():
        slug, effort = names.get(config_id, ("?", "?"))
        lo, hi = bootstrap_ci(rows, proportion(lambda r: r["solved"] == 1),
                              seed=seed, n_resamples=n_resamples)
        out.append({"config_id": config_id, "model_slug": slug,
                    "effort_label": effort, "n": len(rows),
                    "solved": sum(r["solved"] for r in rows),
                    "pct": 100.0 * sum(r["solved"] for r in rows) / max(1, len(rows)),
                    "lo": lo, "hi": hi})
    out.sort(key=lambda r: -r["pct"])
    return out


def abort_curve_ci(conn, thresholds=(2000, 4000, 6000, 8000, 10000, 12000, 16000),
                   *, seed: int = 0, n_resamples: int = 2000) -> list[dict]:
    """The abort curve with intervals on both axes, resampled by PROBLEM.

    The headline deliverable, and the one whose sample is thinnest -- the
    10k-20k band rests on ~58 observations. An interval here is the difference
    between a claim and a guess.
    """
    rows = conn.execute(f"""
        SELECT g.problem_id,
               COALESCE(g.reasoning_tokens, 0) AS think,
               {_COST} AS cost,
               CASE WHEN {_WASTED} THEN 0 ELSE COALESCE(r.passed, 0) END AS solved
        FROM generations g
        JOIN configs c ON c.config_id = g.config_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
    """).fetchall()
    if not rows:
        return []

    # Group by problem: the resampling unit is the problem, not the cell.
    by_problem: dict[str, list[dict]] = {}
    for r in rows:
        by_problem.setdefault(r["problem_id"], []).append(
            {"think": r["think"] or 0, "cost": r["cost"] or 0.0,
             "solved": int(r["solved"])})
    problems = list(by_problem.values())

    baseline = sum(c["cost"] for cells in problems for c in cells)
    total_solved = sum(c["solved"] for cells in problems for c in cells)

    out = []
    for t in thresholds:
        kept = [c for cells in problems for c in cells if c["think"] <= t]
        saved_stat = lambda sample, t=t: (                       # noqa: E731
            None if (b := sum(c["cost"] for cells in sample for c in cells)) <= 0
            else 100.0 * (1 - sum(c["cost"] for cells in sample for c in cells
                                  if c["think"] <= t) / b))
        kept_stat = lambda sample, t=t: (                        # noqa: E731
            None if (tot := sum(c["solved"] for cells in sample for c in cells)) <= 0
            else 100.0 * sum(c["solved"] for cells in sample for c in cells
                             if c["think"] <= t) / tot)
        s_lo, s_hi = bootstrap_ci(problems, saved_stat, seed=seed,
                                  n_resamples=n_resamples)
        k_lo, k_hi = bootstrap_ci(problems, kept_stat, seed=seed,
                                  n_resamples=n_resamples)
        cost = sum(c["cost"] for c in kept)
        out.append({
            "threshold": t,
            "passes_kept": sum(c["solved"] for c in kept),
            "passes_total": total_solved,
            "kept_pct": 100.0 * sum(c["solved"] for c in kept) / max(1, total_solved),
            "kept_lo": k_lo, "kept_hi": k_hi,
            "cost_usd": cost,
            "saved_pct": 100.0 * (1 - cost / baseline) if baseline else 0.0,
            "saved_lo": s_lo, "saved_hi": s_hi,
            "n_problems": len(problems),
        })
    return out


# ------------------------------------------------- the frontier and its hull
#
# THESIS.md section 10.1, which is the honest bar for RQ4:
#
#   Each config is a point (cost c_i, accuracy a_i). If you may randomize --
#   send fraction p_i of problems to config i -- the achievable set is the
#   CONVEX HULL of those points. [...] "CARR beats the best single model" is
#   nearly free and proves little. The honest bar: CARR must beat the convex
#   hull -- and it can, because the hull is blind to the problem while CARR
#   reads its features.
#
# No scipy. A 2D upper hull is a monotone chain in twenty lines, and adding a
# heavyweight dependency for that would be silly.
#
# Every function here takes ONE problem set shared by every config being
# compared. Comparing configs measured on different problems is not a frontier
# however it is drawn -- see common_problems().


def common_problems(conn, config_ids: list[int]) -> list[str]:
    """Problems where every one of `config_ids` has a graded, billed result."""
    if not config_ids:
        return []
    marks = ",".join("?" * len(config_ids))
    rows = conn.execute(f"""
        SELECT g.problem_id FROM generations g
        JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND g.config_id IN ({marks})
        GROUP BY g.problem_id
        HAVING COUNT(DISTINCT g.config_id) = ?
        ORDER BY g.problem_id
    """, [*config_ids, len(config_ids)]).fetchall()
    return [r[0] for r in rows]


def frontier_subset(conn, min_problems: int = 50) -> tuple[list[int], list[str]]:
    """Pick the largest config set that still shares `min_problems` problems.

    The grid is unbalanced, so this is a genuine trade: all ten configs share
    only 5 problems, which is useless, while six share 60, which is a frontier.
    Configs are added widest-coverage-first and the set stops growing when the
    intersection would fall below the floor.

    Returns (config_ids, problem_ids) so a caller can report both.
    """
    coverage = {}
    for r in conn.execute(f"""
            SELECT g.config_id, COUNT(DISTINCT g.problem_id) AS n
            FROM generations g JOIN results r ON r.gen_id = g.gen_id
            WHERE {_REAL} AND NOT {_INFRA} GROUP BY g.config_id"""):
        coverage[r["config_id"]] = r["n"]

    chosen: list[int] = []
    problems: list[str] = []
    for config_id in sorted(coverage, key=lambda c: -coverage[c]):
        candidate = [*chosen, config_id]
        shared = common_problems(conn, candidate)
        if len(shared) < min_problems and chosen:
            continue                     # this config would cost too much overlap
        chosen, problems = candidate, shared
    return chosen, problems


def frontier(conn, config_ids: list[int] | None = None,
             problem_ids: list[str] | None = None, *,
             seed: int = 0, n_resamples: int = 1500) -> list[dict]:
    """One (mean cost, accuracy) point per config over ONE shared problem set.

    Cost is mean dollars per problem, not per solved problem -- the frontier is
    "what does a fixed strategy buy", so the denominator has to be every problem
    it was asked, including the ones it failed.
    """
    if config_ids is None:
        config_ids, problem_ids = frontier_subset(conn)
    if problem_ids is None:
        problem_ids = common_problems(conn, config_ids)

    by_config = _per_problem_config(conn, problem_ids)
    names = _config_names(conn)
    points = []
    for config_id in config_ids:
        rows = [r for r in by_config.get(config_id, [])
                if r["problem_id"] in set(problem_ids)]
        if not rows:
            continue
        slug, effort = names.get(config_id, ("?", "?"))
        acc_lo, acc_hi = bootstrap_ci(
            rows, proportion(lambda r: r["solved"] == 1),
            seed=seed, n_resamples=n_resamples)
        points.append({
            "config_id": config_id, "model_slug": slug, "effort_label": effort,
            "n": len(rows),
            "cost": sum(r["cost"] for r in rows) / len(rows),
            "accuracy": 100.0 * sum(r["solved"] for r in rows) / len(rows),
            "acc_lo": acc_lo, "acc_hi": acc_hi,
        })
    points.sort(key=lambda p: p["cost"])
    return points


def pareto_front(points: list[dict]) -> list[dict]:
    """Points no other point beats on BOTH cost and accuracy.

    Everything else is dominated -- strictly worse on both axes, so no rational
    strategy would ever pick it (THESIS.md section 13).
    """
    out = []
    for p in points:
        if not any(q["cost"] <= p["cost"] and q["accuracy"] >= p["accuracy"]
                   and (q["cost"] < p["cost"] or q["accuracy"] > p["accuracy"])
                   for q in points):
            out.append(p)
    return sorted(out, key=lambda p: p["cost"])


def upper_hull(points: list[dict]) -> list[dict]:
    """Upper convex hull of (cost, accuracy) -- the randomised-strategy bound.

    Monotone chain. A point strictly inside the hull is beaten by MIXING two
    hull vertices, so the hull, not the best single config, is what a
    problem-blind strategy can actually achieve.
    """
    pts = sorted(points, key=lambda p: (p["cost"], p["accuracy"]))
    if len(pts) < 3:
        return pts

    def cross(o, a, b) -> float:
        return ((a["cost"] - o["cost"]) * (b["accuracy"] - o["accuracy"])
                - (a["accuracy"] - o["accuracy"]) * (b["cost"] - o["cost"]))

    hull: list[dict] = []
    for p in pts:
        # Pop while the last turn is not clockwise: those points sit below the
        # line between their neighbours, so a mixture dominates them.
        while len(hull) >= 2 and cross(hull[-2], hull[-1], p) >= 0:
            hull.pop()
        hull.append(p)
    return hull


def hull_accuracy_at(hull: list[dict], budget: float) -> float | None:
    """Best accuracy a problem-BLIND randomised strategy reaches at `budget`.

    Section 10.1's proposition: the optimum randomises between at most two
    configurations, so it is a linear interpolation between adjacent hull
    vertices. Below the cheapest config nothing is affordable; above the
    dearest, the dearest is the ceiling.
    """
    if not hull:
        return None
    if budget < hull[0]["cost"]:
        return None
    if budget >= hull[-1]["cost"]:
        return hull[-1]["accuracy"]
    for a, b in zip(hull, hull[1:]):
        if a["cost"] <= budget <= b["cost"]:
            span = b["cost"] - a["cost"]
            if span <= 0:
                return max(a["accuracy"], b["accuracy"])
            w = (budget - a["cost"]) / span
            return a["accuracy"] * (1 - w) + b["accuracy"] * w
    return hull[-1]["accuracy"]


def oracle(conn, config_ids: list[int], problem_ids: list[str]) -> dict:
    """The cheat that always picks the cheapest config that solves each problem.

    This is the MCKP integer optimum of section 10.2, not an ad-hoc ceiling. It
    is not achievable -- it needs the answer in advance -- but the gap between
    it and the hull is exactly the value of problem-level information, which is
    the sharp version of RQ4.
    """
    by_config = _per_problem_config(conn, problem_ids)
    wanted = set(problem_ids)
    per_problem: dict[str, list[tuple[float, int]]] = {}
    for config_id in config_ids:
        for r in by_config.get(config_id, []):
            if r["problem_id"] in wanted:
                per_problem.setdefault(r["problem_id"], []).append(
                    (r["cost"], r["solved"]))

    total_cost = 0.0
    solved = 0
    for _, cells in per_problem.items():
        winners = [c for c, ok in cells if ok]
        if winners:
            total_cost += min(winners)      # cheapest config that solved it
            solved += 1
        else:
            # Nothing solved it. The oracle still pays the cheapest attempt --
            # pretending it pays nothing would flatter it for free.
            total_cost += min(c for c, _ in cells)
    n = len(per_problem)
    return {
        "n": n,
        "solved": solved,
        "accuracy": 100.0 * solved / n if n else 0.0,
        "cost": total_cost / n if n else 0.0,
    }
