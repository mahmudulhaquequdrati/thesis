"""Grade every generation that has code but no result yet. FREE -- no API calls.

    uv run python scripts/grade.py

Separate from buying on purpose. Grading is CPU-bound and slow (a LiveCodeBench
problem runs its tests twice, in two subprocesses), while buying is I/O-bound
and costs money. Interleaving them made the paid calls wait on the grader.

Safe to run any time, including while a purchase run is going. Re-grading after
fixing an extraction bug costs nothing, which is the whole reason
`raw_response` is stored verbatim.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db, runner  # noqa: E402
from carr.experiment import load_experiment  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--workers", type=int, help="default from experiment.yaml")
    args = ap.parse_args()

    path = Path(args.db) if args.db else db.DEFAULT_DB
    if not path.exists():
        sys.exit(f"no database at {path}")

    exp = load_experiment()
    workers = args.workers or exp.generation.grade_concurrency
    conn = db.connect(path)

    pending = conn.execute(
        """SELECT COUNT(*) FROM generations g
           LEFT JOIN results r ON r.gen_id = g.gen_id
           WHERE r.gen_id IS NULL AND g.extracted_code IS NOT NULL"""
    ).fetchone()[0]
    print(f"  {pending} generations to grade, {workers} at a time (free)\n", flush=True)
    if not pending:
        return

    done = [0]
    started = time.time()

    def on_graded(row, res):
        done[0] += 1
        if done[0] % 25 == 0 or done[0] == pending:
            rate = done[0] / max(1e-9, time.time() - started)
            left = (pending - done[0]) / max(1e-9, rate)
            print(f"  {done[0]:>5}/{pending}   {rate * 60:.0f}/min   "
                  f"~{left / 60:.0f} min left", flush=True)

    graded, passed = runner.grade_pending(conn, concurrency=workers,
                                          on_graded=on_graded)
    print(f"\n  graded {graded}, passed {passed} "
          f"({100 * passed / max(1, graded):.0f}%) in "
          f"{(time.time() - started) / 60:.1f} min")
    print("\n  next:  uv run python scripts/results.py\n")
    conn.close()


if __name__ == "__main__":
    main()
