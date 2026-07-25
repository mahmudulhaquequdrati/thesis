"""Check config/models.yaml against OpenRouter's live /models. Free, no key.

Four files tell the reader to run this script, and until now it did not exist:
the roster was verified by hand on 2026-07-25 and only the result was
committed. That is fine once; it is not fine as the thing THESIS.md section 9
requires be re-run before the grid, because the open-weight landscape moves
every 6-8 weeks and a stale price silently corrupts every CPC number.

Checks each roster entry for:
  1. existence      -- is the slug still served?
  2. price          -- do pricing.prompt/.completion x 1e6 match the yaml?
  3. capability     -- is `reasoning` in supported_parameters?
  4. context length -- unchanged?

Exits non-zero on any drift, so it can gate a run.

Run:  uv run python scripts/verify_roster.py
      uv run python scripts/verify_roster.py --update-snapshot
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr.effort import DEFAULT_ROSTER, load_roster  # noqa: E402

MODELS_URL = "https://openrouter.ai/api/v1/models"
# Prices in the yaml are rounded for readability; anything under this is a
# rounding artefact, not a price change.
TOLERANCE = 0.001


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def check(entry: dict, live: dict | None, section: str) -> list[str]:
    slug = entry["slug"]
    if live is None:
        return [f"{slug}: NOT FOUND on OpenRouter (was in `{section}`)"]

    problems = []
    price_in = float(live["pricing"]["prompt"]) * 1e6
    price_out = float(live["pricing"]["completion"]) * 1e6

    for label, want, got in (("price_in_per_m", entry["price_in_per_m"], price_in),
                             ("price_out_per_m", entry["price_out_per_m"], price_out)):
        if abs(float(want) - got) > TOLERANCE:
            problems.append(f"{slug}: {label} says {want}, live is {got:.4f}")

    if int(entry.get("context_length", 0)) != int(live.get("context_length") or 0):
        problems.append(f"{slug}: context_length says {entry.get('context_length')}, "
                        f"live is {live.get('context_length')}")

    supported = live.get("supported_parameters") or []
    if entry.get("supports_reasoning") and "reasoning" not in supported:
        problems.append(f"{slug}: yaml claims supports_reasoning but `reasoning` "
                        f"is not in supported_parameters")

    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-snapshot", action="store_true",
                    help="rewrite snapshot_date in the yaml if everything matches")
    args = ap.parse_args()

    print(f"  GET {MODELS_URL}")
    live_index = {m["id"]: m for m in fetch(MODELS_URL)["data"]}
    print(f"  {len(live_index)} models served\n")

    roster = load_roster()
    print(f"  roster snapshot_date: {roster['snapshot_date']}\n")

    drift: list[str] = []
    for section in ("models", "held_out"):
        for entry in roster.get(section, []):
            slug = entry["slug"]
            live = live_index.get(slug)
            issues = check(entry, live, section)
            drift.extend(issues)
            if issues:
                print(f"  DRIFT  {slug}")
                for i in issues:
                    print(f"         {i}")
            else:
                p = live["pricing"]
                print(f"  ok     {slug:34} "
                      f"${float(p['prompt']) * 1e6:.4f} / "
                      f"${float(p['completion']) * 1e6:.4f} per M")

    # Rejected models are documentation, but a price collapse is the one thing
    # that would justify re-litigating a rejection, so report it rather than
    # failing on it.
    if roster.get("rejected"):
        print("\n  rejected (informational -- reasons in the yaml):")
        for entry in roster["rejected"]:
            live = live_index.get(entry["slug"])
            if live is None:
                print(f"    {entry['slug']:34} no longer served")
            else:
                p = live["pricing"]
                print(f"    {entry['slug']:34} "
                      f"${float(p['prompt']) * 1e6:.4f} / "
                      f"${float(p['completion']) * 1e6:.4f} per M")

    print()
    if drift:
        print(f"  {len(drift)} problem(s). config/models.yaml is STALE -- fix it "
              f"before spending money.")
        sys.exit(1)

    print("  roster verified: every slug exists, prices and capabilities match.")

    if args.update_snapshot:
        from datetime import date
        today = date.today().isoformat()
        text = DEFAULT_ROSTER.read_text()
        old = f'snapshot_date: "{roster["snapshot_date"]}"'
        DEFAULT_ROSTER.write_text(text.replace(old, f'snapshot_date: "{today}"', 1))
        print(f"  snapshot_date updated to {today}")


if __name__ == "__main__":
    main()
