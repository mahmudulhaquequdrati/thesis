"""Expand config/models.yaml into the list of (model, effort) configurations.

This is the only place that turns the roster into configs. Four models x two
effort levels = 8, plus the held-out model at one effort = 9. Pairing each model
with *itself* at two effort levels is what keeps the effort axis clean: within a
pair the only thing that changes is the thinking mode, so a difference in
pass@1 or cost is attributable to reasoning rather than to model capability.

Nothing outside this module may hardcode a model slug (CLAUDE.md section 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROSTER = ROOT / "config" / "models.yaml"


@dataclass
class Config:
    """One cell of the effort axis: a model at a specific thinking mode."""

    model_slug: str
    family: str
    effort_label: str        # "off" | "high"
    effort_mechanism: str    # "native_toggle" | "budget_forcing" -- NOT equivalent
    params: dict[str, Any]   # the exact `reasoning` block sent to the API
    price_in_per_m: float
    price_out_per_m: float
    context_length: int
    snapshot_date: str
    held_out: bool = False
    subset_only: bool = False
    role: str = ""
    # Position in the cheapest-first ordering. Assigned by load_configs so it
    # is stable across runs; used as config_id when seeding the DB.
    tier_index: int = 0

    @property
    def label(self) -> str:
        """Short human-readable id, e.g. 'deepseek/deepseek-v4-flash | high'."""
        return f"{self.model_slug} | {self.effort_label}"

    @property
    def thinking(self) -> bool:
        return self.effort_label != "off"


def _expand(entry: dict, snapshot_date: str, held_out: bool) -> list[Config]:
    return [
        Config(
            model_slug=entry["slug"],
            family=entry["family"],
            effort_label=effort["label"],
            effort_mechanism=effort["mechanism"],
            params=effort.get("params", {}),
            price_in_per_m=float(entry["price_in_per_m"]),
            price_out_per_m=float(entry["price_out_per_m"]),
            context_length=int(entry["context_length"]),
            snapshot_date=snapshot_date,
            held_out=held_out,
            # Read the flag rather than inferring it from which YAML key the
            # model sat under -- the two happen to agree today, and silently
            # disagreeing later is exactly the kind of bug that costs money.
            subset_only=bool(entry.get("subset_only", False)),
            role=entry.get("role", ""),
        )
        for effort in entry["efforts"]
    ]


def load_configs(path: Path | str | None = None) -> list[Config]:
    """Return the 9 configs, cheapest output price first.

    Cheapest-first is the order runner.py must also use, so that a budget
    breach costs the expensive tail rather than the cheap foundation.
    """
    roster = yaml.safe_load(Path(path or DEFAULT_ROSTER).read_text())
    snapshot = roster["snapshot_date"]

    configs: list[Config] = []
    for entry in roster.get("models", []):
        configs.extend(_expand(entry, snapshot, held_out=False))
    for entry in roster.get("held_out", []):
        configs.extend(_expand(entry, snapshot, held_out=True))

    # Deterministic: price, then slug, then effort. Fixed ordering matters
    # because config_id is assigned by position when the DB is seeded.
    configs.sort(key=lambda c: (c.price_out_per_m, c.model_slug, c.effort_label))
    for i, c in enumerate(configs):
        c.tier_index = i
    return configs


def load_roster(path: Path | str | None = None) -> dict:
    """The raw YAML, for callers that need `rejected:` or the header fields."""
    return yaml.safe_load(Path(path or DEFAULT_ROSTER).read_text())


if __name__ == "__main__":
    for i, c in enumerate(load_configs(), 1):
        tag = " [held-out, subset]" if c.held_out else ""
        print(f"{i}. {c.label:45} ${c.price_in_per_m}/${c.price_out_per_m} per M{tag}")
