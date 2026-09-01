"""Turn the generations table into the thesis's results. Free -- pure SQL and arithmetic.

Four things, matching the reframed research questions:

  saturation()      RQ0  which problems can discriminate between configs at all
  reasoning_by_tier() RQ1  what predicts how long a model reasons
  waste()           RQ2  when is that reasoning wasted, and what did it cost
  abort_curve()     RQ3  what a reasoning-length abort would have saved

`abort_curve` is the headline deliverable. It is a simulation over completed
calls, and it relies on one measured fact: **aborting a stream mid-reasoning is
billed $0.00** (verified 2026-07-26 on two providers). So an aborted call is
scored as costing nothing and solving nothing -- not as a pro-rata saving.

The often-quoted "$0.010978 for the same cell run to completion" is NOT
reproducible from this database: the abort test was an exploratory call made
outside the runner and never stored, and the only row carrying that exact cost
is qwen3.6-35b-a3b|high on LiveCodeBench/3697, a different model from the one
the log attributes the test to. Use the stored grid instead -- a completed
deepseek-v4-pro|high call averages $0.012165 (n=73), kimi|high $0.057706 (n=23)
-- which makes the same point and is checkable.

Everything filters `is_mock = 0` and prefers `cost_actual_usd` over
`cost_computed_usd`, because the price table was wrong by 1.54x before
providers were pinned and only the billed number is trustworthy.

⚠️ But know how far that preference actually reaches: `cost_actual_usd` is
populated on **139 of 1,373 rows, all of them the 2026-07-25 pilot**. The
1,224-call grid was never reconciled, so in practice almost every dollar these
functions return is `cost_computed_usd` -- token counts times the price table.
That is defensible because the grid pins one provider per model with
`allow_fallbacks: false`, making the endpoint's price contractual rather than a
routing lottery; it is not the same as having checked. On the 139 rows where it
could be checked, billed ran 1.354x computed (2.16-2.51x on deepseek-v4-pro),
which is evidence for the pinning finding rather than against the grid, since
the pilot pre-dates pinning.

`runner.reconcile_costs()` can still close this: 1,207 of the 1,224 grid rows
carry an `openrouter_gen_id` and `GET /generation` is free.
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

# "Wasted" means BILLED AND NO USABLE ANSWER.
#
# ⚠️ Note what this does NOT depend on: the grader. A billed row with
# finish_reason='length' is scored as solving nothing *whatever `passed` says*,
# which is a deliberate decision (see
# tests/test_analysis.py::test_a_truncated_call_is_never_counted_as_a_pass) and
# is coherent with the abort simulation, where an aborted call also solves
# nothing. A response cut off mid-stream is not an answer you could ship.
#
# ⚠️ But it has a consequence for how the result may be WORDED. "A censored call
# cannot have succeeded" is true here partly by construction, so it is not
# evidence about the models on its own. The independent, empirical version is:
#
#     ZERO of the 101 truncated rows produced extracted code that passed.
#     (Checked 2026-09-01: billed AND truncated-or-errored AND passed = 0 rows.)
#
# Quote that sentence, not the definitional one. Re-check it whenever new rows
# land, because the two statements will stop agreeing the moment a truncated
# response closes its code fence in time -- extract.py deliberately accepts an
# unterminated fence, so such a row is gradeable and would then be scored 0 here
# while the grader says 1.
_WASTED = (f"(COALESCE({_COST}, 0) > 0 "
           f"AND (g.finish_reason = 'length' OR g.error IS NOT NULL))")

# LiveCodeBench ships two kinds of problem and they are not equally hard for a
# model: AtCoder tasks are stdin->stdout programs, LeetCode tasks are a method
# body to fill in on a `Solution` class. Only the second has an entry point.
#
# This is a CONFOUND, not a curiosity, because coverage of the two is wildly
# uneven -- see style_composition(). Reported next to every tier so the effect
# of reasoning can never again be read off arms that sat different exams.
_STYLE = ("CASE WHEN p.benchmark != 'livecodebench' THEN 'n/a' "
          "WHEN p.entry_point IS NULL OR p.entry_point = '' THEN 'stdin' "
          "ELSE 'functional' END")


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


def discriminating_problems(conn, min_configs: int = 1) -> dict[str, int]:
    """How many problems actually carry a signal.

    A problem every config solves, and a problem none solves, are equally
    useless: neither can distinguish a good decision from a bad one. Only
    problems where configs DISAGREE contribute anything.

    ⚠️ `min_configs` is not a convenience knob -- READ discrimination_by_coverage
    before quoting this. Unanimity is trivially easier to reach with fewer
    voters, and coverage here runs from 2 cells to 10: 206 of 320 problems saw
    only 2-3 configurations, nearly always the three cheap `off` ones. Counting
    those beside the 73 problems that saw six or more mixes a property of the
    problems with a property of the budget.
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
            HAVING COUNT(*) >= ?
        )
        SELECT CASE WHEN n_pass = 0        THEN 'none solved'
                    WHEN n_pass = n_cells  THEN 'all solved'
                    ELSE 'discriminating' END AS bucket,
               COUNT(*) AS n
        FROM per_problem GROUP BY bucket
    """, (min_configs,)).fetchall()
    return {r["bucket"]: r["n"] for r in rows}


def discrimination_by_coverage(conn,
                               cuts: tuple[int, ...] = (1, 4, 6)) -> list[dict]:
    """The same split, recomputed at increasing coverage. The honest version.

    ⚠️ The headline "only 141 of 320 problems discriminate" is substantially a
    COVERAGE artefact, and this is the function that says so.

    A problem is called unanimous when every configuration that ran on it agreed.
    With ten configurations that is a real statement about the problem. With
    three -- all of them the cheap no-reasoning tier, which is what 206 of the
    320 problems got -- it mostly says nobody capable was asked.

    Measured:

        coverage            n     all-solved   none-solved   discriminating
        >= 1 config       320      81 (25%)      98 (31%)       141 (44%)
        >= 1 thinking     108      33 (31%)       4 ( 4%)        71 (66%)
        >= 6 configs       73      11 (15%)       2 ( 3%)        60 (82%)

    So of the 98 problems "solved by nothing", **94 were never attempted by a
    single reasoning-enabled configuration** -- they saw only the three cheap
    `off` configs. Read at proper coverage the picture inverts: on the problems
    actually measured across six or more configurations, **82% discriminate**.

    What survives unchanged is the per-TIER saturation result, because that is a
    pass rate rather than a unanimity count: HumanEval+, MBPP+ and LCB-easy sit
    at 72-100% whichever effort arm you read. The easy benchmarks really are
    saturated. What does not survive is the problem-level claim that three
    quarters of the pool carries no signal.
    """
    out = []
    for cut in cuts:
        counts = discriminating_problems(conn, min_configs=cut)
        n = sum(counts.values())
        out.append({
            "min_configs": cut, "n": n,
            "all solved": counts.get("all solved", 0),
            "none solved": counts.get("none solved", 0),
            "discriminating": counts.get("discriminating", 0),
            "pct_discriminating": 100.0 * counts.get("discriminating", 0) / n if n else 0.0,
        })

    # The cut that matters most is not a cell count but whether anything capable
    # ran at all, so report it explicitly rather than leaving it to be inferred.
    rows = conn.execute(f"""
        WITH per_problem AS (
            SELECT g.problem_id,
                   SUM(COALESCE(r.passed, 0)) AS n_pass,
                   COUNT(*) AS n_cells,
                   SUM(CASE WHEN c.effort_label != 'off' THEN 1 ELSE 0 END) AS n_think
            FROM generations g
            JOIN configs c ON c.config_id = g.config_id
            LEFT JOIN results r ON r.gen_id = g.gen_id
            WHERE {_REAL} AND NOT {_INFRA}
            GROUP BY g.problem_id
        )
        SELECT CASE WHEN n_pass = 0       THEN 'none solved'
                    WHEN n_pass = n_cells THEN 'all solved'
                    ELSE 'discriminating' END AS bucket,
               COUNT(*) AS n
        FROM per_problem WHERE n_think >= 1 GROUP BY bucket
    """).fetchall()
    counts = {r["bucket"]: r["n"] for r in rows}
    n = sum(counts.values())
    out.insert(1, {
        "min_configs": "1 thinking", "n": n,
        "all solved": counts.get("all solved", 0),
        "none solved": counts.get("none solved", 0),
        "discriminating": counts.get("discriminating", 0),
        "pct_discriminating": 100.0 * counts.get("discriminating", 0) / n if n else 0.0,
    })
    return out


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


def abort_by_model(conn, thresholds=(2000, 4000, 6000, 8000, 10000,
                                     12000, 16000, 20000, 24000, 32000)) -> list[dict]:
    """The abort tradeoff per MODEL, and the free threshold the pool hides.

    ⚠️ `best_threshold()` returns None, and the thesis reports "no threshold
    saves money without losing a solved problem". That is true of the **pooled**
    roster and FALSE for two of the five models taken individually:

        model               free threshold      saving   solutions kept
        qwen3.5-9b          10,000 tokens        88%      46/46
        qwen3.6-35b-a3b     16,000 tokens        13%      43/43
        deepseek-v4-flash   none -- every threshold costs a solution
        deepseek-v4-pro     none
        kimi-k2.6           none

    And the pattern is coherent rather than noise: **the free threshold exists
    exactly where reasoning was not earning its keep.** qwen3.5-9b is the model
    whose reasoning delta is negative on three tiers of four
    (within_model_effect) and which wastes 37% of its thinking calls
    (waste_by_model) -- so everything it solved, it solved early, and everything
    long was already doomed. deepseek-v4-flash gains +52.9 points on hard
    problems by thinking longer, so cutting it off necessarily costs solutions.

    This refines the refuted pilot claim rather than restoring it. The pilot said
    a free threshold existed *for the roster*; that remains false, and the 16k
    ceiling really did manufacture part of it. What is true is narrower and more
    useful:

        Whether a reasoning-length abort is free is a property of the model.
        Where long reasoning rarely succeeds it is free money -- 88% of
        qwen3.5-9b's thinking spend, losing nothing. Where long reasoning
        genuinely solves hard problems, every threshold costs solutions.

    `free_threshold` is the cheapest threshold keeping EVERY solved problem, or
    None. Same simulation and the same caveats as abort_curve(): it runs over
    completed calls, it relies on the measured $0.00 cancellation, and a
    threshold chosen here is fitted unless it is evaluated on held-out data.
    """
    rows = conn.execute(f"""
        SELECT c.model_slug AS model,
               COALESCE(g.reasoning_tokens, 0) AS think,
               {_COST} AS cost,
               CASE WHEN {_WASTED} THEN 0 ELSE COALESCE(r.passed, 0) END AS ok
        FROM generations g
        JOIN configs c ON c.config_id = g.config_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
    """).fetchall()

    by_model: dict[str, list] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    out = []
    for model, rs in by_model.items():
        total = sum(r["ok"] for r in rs)
        baseline = sum(r["cost"] or 0 for r in rs)
        free_t = free_saving = None
        for t in thresholds:
            kept = sum(r["ok"] for r in rs if r["think"] <= t)
            cost = sum(r["cost"] or 0 for r in rs if r["think"] <= t)
            if kept == total and cost < baseline:
                free_t = t
                free_saving = 100.0 * (1 - cost / baseline) if baseline else 0.0
                break
        out.append({
            "model": model, "n_calls": len(rs), "solved": total,
            "baseline_usd": baseline,
            "free_threshold": free_t, "free_saving_pct": free_saving,
        })
    out.sort(key=lambda r: (r["free_threshold"] is None, -(r["free_saving_pct"] or 0)))
    return out


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


def style_composition(conn, tiers: tuple[str, ...] = ("hard", "medium")) -> list[dict]:
    """Pass rate per (tier, LiveCodeBench style, effort). The matched comparison.

    ⚠️ This exists because the headline effort comparison is CONFOUNDED BY
    PROBLEM STYLE, and the cause is mechanical rather than scientific.

    `runner.plan` orders cells by `(expected_usd, problem_id)`. Within one
    config every cell has the same expected cost, so the tiebreak is the problem
    id -- as a STRING. LiveCodeBench's LeetCode ids are numeric
    ("LiveCodeBench/3487") and its AtCoder ids start with letters
    ("LiveCodeBench/abc374_a"), and digits sort before letters in ASCII. So all
    125 functional problems ran before any of the 217 stdin ones, and the
    expensive thinking arm -- which runs last under cheapest-first -- stopped at
    the cost cap while still inside the functional prefix.

    The result is that the two effort arms sat different exams on the hard tier:
    the `off` arm is 348 stdin / 114 functional, the `high` arm is 8 / 110. And
    the styles are not equally hard, so a raw off-vs-on difference on that tier
    mixes a reasoning effect with a composition effect.

    Restricting to one style is the honest comparison, and it is free -- a
    re-analysis of rows already bought, not a re-purchase. It costs the raw hard
    gap about 3.6 points (29.3 -> 25.7) and it makes the medium gap LARGER
    (23.1 -> 28.9), so the finding survives; the raw pair simply overstates it
    on one tier and understates it on the other.

    Every set derived from the frontier subset inherits this too: those 60
    problems are 51 functional and 2 stdin, so the frontier, hull, oracle and
    router numbers describe function-style problems, not the hard tier at large.
    """
    marks = ",".join("?" * len(tiers))
    rows = conn.execute(f"""
        SELECT COALESCE(p.difficulty, p.benchmark) AS tier,
               {_STYLE} AS style,
               c.effort_label AS effort,
               COUNT(*) AS n,
               SUM(COALESCE(r.passed, 0)) AS passed,
               ROUND(100.0 * SUM(COALESCE(r.passed, 0)) / COUNT(*), 1) AS pct
        FROM generations g
        JOIN configs c  ON c.config_id = g.config_id
        JOIN problems p ON p.problem_id = g.problem_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA}
          AND COALESCE(p.difficulty, '') IN ({marks})
        GROUP BY tier, style, effort
        ORDER BY tier, style, effort
    """, list(tiers)).fetchall()
    return [dict(r) for r in rows]


def style_matched_effect(conn, min_n: int = 30) -> list[dict]:
    """The off-vs-on gap within a single style, beside the confounded raw gap.

    `min_n` drops arms too thin to compare -- the hard/stdin thinking arm is
    n=8, which supports nothing and would otherwise print a 12.5% that reads
    like a finding.
    """
    comp = style_composition(conn)
    by: dict[tuple[str, str], dict[str, dict]] = {}
    for r in comp:
        by.setdefault((r["tier"], r["style"]), {})[r["effort"]] = r

    raw: dict[str, dict[str, list[dict]]] = {}
    for r in comp:
        raw.setdefault(r["tier"], {}).setdefault(r["effort"], []).append(r)

    out = []
    for (tier, style), arms in sorted(by.items()):
        off, high = arms.get("off"), arms.get("high")
        if not off or not high or off["n"] < min_n or high["n"] < min_n:
            continue
        rows = raw[tier]
        raw_off = sum(x["passed"] for x in rows.get("off", []))
        raw_off_n = sum(x["n"] for x in rows.get("off", []))
        raw_hi = sum(x["passed"] for x in rows.get("high", []))
        raw_hi_n = sum(x["n"] for x in rows.get("high", []))
        out.append({
            "tier": tier, "style": style,
            "off_pct": off["pct"], "off_n": off["n"],
            "high_pct": high["pct"], "high_n": high["n"],
            "matched_gap": high["pct"] - off["pct"],
            "raw_off_pct": 100.0 * raw_off / raw_off_n if raw_off_n else 0.0,
            "raw_high_pct": 100.0 * raw_hi / raw_hi_n if raw_hi_n else 0.0,
            "raw_gap": ((100.0 * raw_hi / raw_hi_n) if raw_hi_n else 0.0)
                       - ((100.0 * raw_off / raw_off_n) if raw_off_n else 0.0),
        })
    return out


def waste_by_model(conn) -> list[dict]:
    """Which model burned the money that bought nothing. RQ2, disaggregated.

    ⚠️ "15% of reasoning spend bought no answer" is a real number and a
    misleading headline, because the waste is not spread across the roster:

        model               wasted / thinking calls    rate    mean reasoning
        qwen3.5-9b                    37 / 99          37.4%      30,411
        qwen3.6-35b-a3b                7 / 74           9.5%      16,635
        deepseek-v4-flash              3 / 73           4.1%      48,000
        deepseek-v4-pro                2 / 72           2.8%      31,999
        kimi-k2.6                      0 / 22           0.0%           -

    **76% of the wasted calls are one model.** Non-termination is a property of
    the small model rather than of reasoning in general, which is the same story
    within_model_effect() tells about the sign reversal -- and it makes the
    practitioner advice far more useful: *expect roughly a third of a small
    model's thinking calls to return nothing, and about one in twenty-five of a
    capable one's.*
    """
    rows = conn.execute(f"""
        SELECT c.model_slug AS model,
               COUNT(*) AS n,
               SUM(CASE WHEN {_WASTED} THEN 1 ELSE 0 END) AS wasted,
               ROUND(AVG(CASE WHEN {_WASTED} THEN g.reasoning_tokens END)) AS avg_reasoning,
               ROUND(SUM(CASE WHEN {_WASTED} THEN {_COST} ELSE 0 END), 6) AS wasted_usd,
               ROUND(SUM({_COST}), 6) AS total_usd
        FROM generations g
        JOIN configs c ON c.config_id = g.config_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA} AND c.effort_label != 'off'
        GROUP BY model
        ORDER BY 1.0 * SUM(CASE WHEN {_WASTED} THEN 1 ELSE 0 END) / COUNT(*) DESC
    """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["rate_pct"] = 100.0 * r["wasted"] / r["n"] if r["n"] else 0.0
        out.append(d)
    return out


def within_model_effect(conn, min_n: int = 15) -> list[dict]:
    """The effect of reasoning per (tier, MODEL), with censoring attached.

    ⚠️ This is the table the results chapter should lead with, because the
    aggregate off-vs-on comparison averages over models whose responses to
    reasoning point in OPPOSITE directions.

    Measured:

        tier       model               off            high          delta
        hard       deepseek-v4-flash   29.2% n=154    82.1% n=28    +52.9
        hard       qwen3.6-35b-a3b     22.1% n=154    27.6% n=29     +5.5
        hard       qwen3.5-9b          22.1% n=145     3.8% n=26    -18.2
        medium     deepseek-v4-flash   62.5% n=104    94.4% n=36    +31.9
        medium     qwen3.6-35b-a3b     52.9% n=104    72.2% n=36    +19.3
        medium     qwen3.5-9b          43.6% n=101    38.7% n=31     -4.9
        mbpp_plus  qwen3.5-9b          80.0% n=20     55.6% n=18    -24.4
        humaneval  qwen3.5-9b          90.5% n=21     94.7% n=19     +4.3

    So the headline "+29.3 points on hard" is an average over **+52.9 on one
    model and -18.2 on another**. Reasoning is not a property of the tier; it is
    a property of the (model, tier) pair.

    `censored_pct` and `nocode_pct` are carried on every row because they
    separate the two failure modes, and the separation is the finding:

    * **Non-termination.** `qwen3.5-9b|high` hits the 48,000-token ceiling on
      **81% of hard calls** and returns no code at all on 77%, averaging 24,826
      reasoning tokens. Its -18.2 is mostly the model failing to stop, not the
      model reasoning badly. `deepseek-v4-flash|high` censors at 11% on the same
      tier. A ceiling censors the small model far harder than the large one, so
      "reasoning hurts small models on hard problems" is partly a statement
      about our ceiling.

    * **Genuine degradation.** On MBPP+, `qwen3.5-9b|high` censors **0%**,
      reasons for a mean of 368 tokens, terminates normally, and still drops
      from 16/20 to 10/18 on the SAME problems. Every failure produced extracted
      code and failed on assertions. That one is not measurement: enabling
      reasoning made an easy problem harder for it.

    Both matter, and they need different sentences in the write-up.
    """
    rows = conn.execute(f"""
        SELECT COALESCE(p.difficulty, p.benchmark) AS tier,
               c.model_slug AS model,
               c.effort_label AS effort,
               COUNT(*) AS n,
               SUM(COALESCE(r.passed, 0)) AS passed,
               SUM(CASE WHEN g.finish_reason = 'length' THEN 1 ELSE 0 END) AS censored,
               SUM(CASE WHEN LENGTH(COALESCE(g.extracted_code, '')) = 0
                        THEN 1 ELSE 0 END) AS nocode,
               ROUND(AVG(COALESCE(g.reasoning_tokens, 0))) AS avg_reasoning
        FROM generations g
        JOIN configs c  ON c.config_id = g.config_id
        JOIN problems p ON p.problem_id = g.problem_id
        LEFT JOIN results r ON r.gen_id = g.gen_id
        WHERE {_REAL} AND NOT {_INFRA}
        GROUP BY tier, model, effort
    """).fetchall()

    arms: dict[tuple[str, str], dict[str, dict]] = {}
    for r in rows:
        arms.setdefault((r["tier"], r["model"]), {})[r["effort"]] = dict(r)

    out = []
    for (tier, model), by_effort in arms.items():
        off, high = by_effort.get("off"), by_effort.get("high")
        if not off or not high or off["n"] < min_n or high["n"] < min_n:
            continue
        off_pct = 100.0 * off["passed"] / off["n"]
        high_pct = 100.0 * high["passed"] / high["n"]
        out.append({
            "tier": tier, "model": model,
            "off_n": off["n"], "off_pct": off_pct,
            "high_n": high["n"], "high_pct": high_pct,
            "delta": high_pct - off_pct,
            "censored_pct": 100.0 * high["censored"] / high["n"],
            "nocode_pct": 100.0 * high["nocode"] / high["n"],
            "avg_reasoning": high["avg_reasoning"] or 0,
        })
    out.sort(key=lambda r: (r["tier"], -r["delta"]))
    return out


# ------------------------------------------------------- comparable statistics
#
# The grid is unbalanced: the `off` configs have 320 problems each, the `high`
# configs 73-104, and the held-out model 16-23. Note the `off` arm is NOT
# uniformly 320: deepseek-v4-pro|off ran only 51 problems and kimi|off 16, so
# "51" is an OFF config, not a thinking one. A cost-accuracy number computed
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
