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
