"""Read config/experiment.yaml, and sample problems from the pools.

Two jobs that both have to be reproducible: the budget/generation settings the
runner obeys, and the stratified problem sample it runs over.

The sampling is stratified rather than random for a measured reason. The first
real grid cell -- HumanEval/0 across all 10 configs -- came back 10/10 PASS.
A sample drawn uniformly from a 717-problem pool that is 76% easy benchmarks
would inherit that, report a near-100% pass rate everywhere, and answer none of
the questions the pilot exists to ask.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "experiment.yaml"


@dataclass
class Budget:
    max_spend_usd: float
    loaded_usd: float
    abort_at_usd: float
    warn_at_usd: float
    # Per-run ceiling as a multiple of that run's own estimate. A bigger
    # account balance is not a bigger budget; this keeps each run close to what
    # the work actually needs even when the lifetime cap has plenty of room.
    run_headroom: float = 1.25


@dataclass
class GenerationSettings:
    temperature: float
    n: int
    max_tokens: int
    retries: int
    concurrency: int = 1
    grade_concurrency: int = 4
    rate_limit_retries: int = 3


@dataclass
class Experiment:
    budget: Budget
    generation: GenerationSettings
    seed: int
    strata: dict[str, dict[str, int]]

    @property
    def pilot_strata(self) -> dict[str, int]:
        return self.strata["pilot"]

    @property
    def grid_strata(self) -> dict[str, int]:
        return self.strata["grid"]


def load_experiment(path: Path | str | None = None) -> Experiment:
    raw = yaml.safe_load(Path(path or DEFAULT_CONFIG).read_text())
    s = raw["sampling"]
    return Experiment(
        budget=Budget(**raw["budget"]),
        generation=GenerationSettings(**raw["generation"]),
        seed=s["seed"],
        strata={"pilot": s["pilot"]["strata"], "grid": s["grid"]["strata"]},
    )


# A stratum name is either a benchmark, or `benchmark_difficulty` where the
# benchmark actually ships difficulty labels (LiveCodeBench does; HumanEval+
# and MBPP+ do not).
def _stratum_query(stratum: str) -> tuple[str, list]:
    if stratum.startswith("livecodebench_"):
        difficulty = stratum.split("_", 1)[1]
        return ("SELECT problem_id FROM problems WHERE benchmark = ? "
                "AND difficulty = ? ORDER BY problem_id"), ["livecodebench", difficulty]
    return "SELECT problem_id FROM problems WHERE benchmark = ? ORDER BY problem_id", [stratum]


def sample_problems(conn: sqlite3.Connection, strata: dict[str, int],
                    seed: int) -> list[str]:
    """Pick problems per stratum, deterministically.

    `ORDER BY problem_id` before sampling, and a fresh Random per stratum, so
    the selection depends only on (seed, stratum, pool) -- not on dict order,
    row insertion order, or how many other strata were requested.
    """
    chosen: list[str] = []
    for stratum in sorted(strata):
        want = strata[stratum]
        if want <= 0:
            continue
        sql, params = _stratum_query(stratum)
        pool = [r[0] for r in conn.execute(sql, params)]
        if not pool:
            raise ValueError(f"stratum {stratum!r} is empty -- run init_db.py")
        rng = random.Random(f"{seed}:{stratum}")
        if want >= len(pool):
            picked = list(pool)      # asking for more than exists takes all
        else:
            picked = rng.sample(pool, want)
        chosen.extend(sorted(picked))
    return chosen


def describe_sample(conn: sqlite3.Connection, problem_ids: list[str]) -> list[dict]:
    """Per-stratum counts for the sample, so a run can print what it will do."""
    if not problem_ids:
        return []
    marks = ",".join("?" * len(problem_ids))
    rows = conn.execute(
        f"""SELECT benchmark, COALESCE(difficulty, '-') AS difficulty,
                   COUNT(*) AS n, ROUND(AVG(prompt_chars)) AS avg_chars,
                   ROUND(AVG(n_tests)) AS avg_tests
            FROM problems WHERE problem_id IN ({marks})
            GROUP BY benchmark, COALESCE(difficulty, '-')
            ORDER BY benchmark, difficulty""",
        problem_ids,
    ).fetchall()
    return [dict(r) for r in rows]
