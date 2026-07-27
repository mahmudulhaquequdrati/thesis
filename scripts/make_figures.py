"""Render the thesis figures to data/figures/. Free -- no API calls.

    uv run python scripts/make_figures.py

Regenerated from the database every time, never hand-edited, and gitignored:
a figure that disagrees with the data it came from is worse than no figure.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db, figures  # noqa: E402
from carr.experiment import load_experiment  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    path = Path(args.db) if args.db else db.DEFAULT_DB
    if not path.exists():
        sys.exit(f"no database at {path}\nrun: uv run python scripts/init_db.py")

    conn = db.connect(path)
    s = db.summary(conn)
    print(f"  {s['generations']} generations, {s['results']} graded\n")
    for p in figures.make_all(conn, seed=load_experiment().seed):
        print(f"  {p.relative_to(Path.cwd()) if p.is_relative_to(Path.cwd()) else p}"
              f"   ({p.stat().st_size // 1024} KB)")
    print(f"\n  open {figures.FIGURE_DIR}\n")
    conn.close()


if __name__ == "__main__":
    main()
