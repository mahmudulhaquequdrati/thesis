"""Figures for the write-up. Free -- reads the database, writes PNGs.

Eight figures, one per claim the thesis actually makes:

  fig_effort_by_tier     when thinking helps, and where it does not
  fig_effect_by_model    the effect is per model, and it changes sign
  fig_reasoning_outcome  long reasoning means failure, not effort
  fig_frontier           the cost-accuracy hull, the oracle, and the gap
  fig_abort_curve        the honest tradeoff, with its uncertainty band
  fig_cpc                cost per correct answer with intervals
  fig_coverage           the unbalanced grid, shown before any result
  fig_reasoning_by_tier  reasoning length tracks difficulty

Design rules, because these end up in a document and get printed:

  * Error bars wherever an interval exists. A bare bar chart of these numbers
    would imply a precision the data does not have -- five config pairs have
    overlapping CPC intervals, and the whole point of computing them was to
    stop that being invisible.
  * Greyscale-safe. Colour carries no information that hatching, position or a
    label does not also carry.
  * Sample sizes printed on the figure. Several panels rest on 60-107 problems
    and a reader deserves to see that without hunting for it.
  * No chart junk: no gridlines behind bars, no 3D, no truncated y-axes on
    proportions -- a bar chart of percentages starts at zero.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")          # headless: no display on a build machine
import matplotlib.pyplot as plt  # noqa: E402

from carr import analysis  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGURE_DIR = ROOT / "data" / "figures"     # gitignored; regenerated, never edited

# Muted, print-safe, and distinguishable in greyscale by lightness.
INK = "#1a1a1a"
OFF_C = "#b0b0b0"
HIGH_C = "#3d3d3d"
ACCENT = "#8c2f39"


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK, labelsize=9)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#999")


def _save(fig, name: str) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ------------------------------------------------------------------ figure 1


def fig_effort_by_tier(conn) -> Path:
    """Pass rate off vs on, per difficulty tier. The headline result.

    Ordered easy to hard so the widening gap reads left to right: reasoning
    buys almost nothing on saturated benchmarks and more than doubles the pass
    rate on hard problems.
    """
    order = ["mbpp_plus", "humaneval_plus", "easy", "medium", "hard"]
    label = {"mbpp_plus": "MBPP+", "humaneval_plus": "HumanEval+",
             "easy": "LCB easy", "medium": "LCB medium", "hard": "LCB hard"}

    rows = {(r["tier"], r["effort"]): r for r in analysis.saturation(conn)}
    tiers = [t for t in order if (t, "off") in rows or (t, "high") in rows]

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    width = 0.38
    for i, effort in enumerate(("off", "high")):
        xs = [j + (i - 0.5) * width for j in range(len(tiers))]
        ys = [rows.get((t, effort), {}).get("pct", 0) for t in tiers]
        ns = [rows.get((t, effort), {}).get("n", 0) for t in tiers]
        bars = ax.bar(xs, ys, width,
                      label=f"reasoning {effort}",
                      color=OFF_C if effort == "off" else HIGH_C,
                      edgecolor=INK, linewidth=0.6,
                      hatch="" if effort == "off" else "///")
        for b, y, n in zip(bars, ys, ns):
            ax.text(b.get_x() + b.get_width() / 2, y + 1.5, f"{y:.0f}%",
                    ha="center", fontsize=8, color=INK)
            ax.text(b.get_x() + b.get_width() / 2, 1.5, f"n={n}",
                    ha="center", fontsize=6.5, color="#666")

    ax.set_xticks(range(len(tiers)))
    ax.set_xticklabels([label[t] for t in tiers], fontsize=9)
    ax.set_ylabel("problems solved (%)", fontsize=9)
    ax.set_ylim(0, 108)
    ax.set_title("Reasoning helps only where the benchmark is hard enough to notice",
                 fontsize=10.5, color=INK, pad=26)
    # Outside the axes: inside, it sat on top of the HumanEval+ bar label.
    ax.legend(frameon=False, fontsize=9, ncol=2,
              loc="lower center", bbox_to_anchor=(0.5, 1.005))
    ax.axhline(90, color="#bbb", lw=0.8, ls=":")
    ax.text(len(tiers) - 0.4, 91, "saturation", fontsize=7, color="#888")
    _style(ax)
    return _save(fig, "01-effort-by-tier")


# ------------------------------------------------------------------ figure 2


def fig_reasoning_outcome(conn) -> Path:
    """Mean reasoning tokens by outcome. Long thinking predicts failure."""
    rows = {r["outcome"]: r for r in analysis.waste(conn)}
    order = [("passed", "solved"), ("failed", "wrong answer"),
             ("wasted (no answer)", "billed, no answer")]
    present = [(k, lbl) for k, lbl in order if k in rows]

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ys = [rows[k]["avg_reasoning"] or 0 for k, _ in present]
    colors = [OFF_C, "#8a8a8a", ACCENT][:len(present)]
    bars = ax.barh([lbl for _, lbl in present], ys, color=colors,
                   edgecolor=INK, linewidth=0.6, height=0.55)
    for b, (k, _), y in zip(bars, present, ys):
        ax.text(y + max(ys) * 0.015, b.get_y() + b.get_height() / 2,
                f"{y:,.0f} tokens   (n={rows[k]['n']}, "
                f"${rows[k]['total_usd'] or 0:.2f})",
                va="center", fontsize=8, color=INK)

    ax.set_xlabel("mean reasoning tokens per call", fontsize=9)
    ax.set_xlim(0, max(ys) * 1.55)
    ax.set_title("A model that reasons for a long time is failing, not working harder",
                 fontsize=10.5, color=INK, pad=12)
    _style(ax)
    return _save(fig, "02-reasoning-vs-outcome")


# ------------------------------------------------------------------ figure 3


def fig_frontier(conn, seed: int = 0) -> Path:
    """Cost-accuracy frontier, its convex hull, and the oracle above it.

    The gap between the oracle and the hull at equal budget is the whole of
    RQ4 in one picture: what problem-level information is worth.
    """
    cfg_ids, probs = analysis.frontier_subset(conn, min_problems=50)
    pts = analysis.frontier(conn, cfg_ids, probs, seed=seed, n_resamples=800)
    if len(pts) < 3:
        raise RuntimeError("not enough shared coverage to draw a frontier")
    hull = analysis.upper_hull(analysis.pareto_front(pts))
    orc = analysis.oracle(conn, cfg_ids, probs)
    blind = analysis.hull_accuracy_at(hull, orc["cost"])

    fig, ax = plt.subplots(figsize=(7.4, 4.8))

    ax.plot([p["cost"] for p in hull], [p["accuracy"] for p in hull],
            "-", color=INK, lw=1.4, zorder=2,
            label="convex hull (best problem-blind strategy)")

    hull_ids = {p["config_id"] for p in hull}
    for p in pts:
        on_hull = p["config_id"] in hull_ids
        ax.errorbar(p["cost"], p["accuracy"],
                    yerr=[[p["accuracy"] - p["acc_lo"]], [p["acc_hi"] - p["accuracy"]]],
                    fmt="o" if on_hull else "s",
                    ms=8 if on_hull else 5.5,
                    color=INK if on_hull else "#9a9a9a",
                    ecolor="#bbb", capsize=3, lw=1, zorder=3)
        ax.annotate(f"{p['model_slug'].split('/')[-1]}|{p['effort_label']}",
                    (p["cost"], p["accuracy"]),
                    textcoords="offset points", xytext=(9, 6 if on_hull else -12),
                    fontsize=7.5, color=INK if on_hull else "#777")

    ax.plot(orc["cost"], orc["accuracy"], "*", ms=17, color=ACCENT, zorder=4,
            label="oracle (knows the cheapest config that works)")
    if blind is not None:
        ax.annotate("", xy=(orc["cost"], orc["accuracy"]),
                    xytext=(orc["cost"], blind),
                    arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1.3))
        # Left of the arrow: to its right sits the flash|high point label.
        ax.text(orc["cost"] * 0.86, (orc["accuracy"] + blind) / 2,
                f"{orc['accuracy'] - blind:.1f} points\nvalue of knowing\nthe problem",
                fontsize=8, color=ACCENT, va="center", ha="right")

    ax.set_xscale("log")
    ax.set_xlabel("mean cost per problem (USD, log scale)", fontsize=9)
    ax.set_ylabel("problems solved (%)", fontsize=9)
    ax.set_ylim(0, 108)
    ax.set_title(f"Cost-accuracy frontier  ({len(cfg_ids)} configs, "
                 f"{len(probs)} shared problems; bars are 95% CI)",
                 fontsize=10.5, color=INK, pad=12)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _style(ax)
    return _save(fig, "03-frontier-and-hull")


# ------------------------------------------------------------------ figure 4


def fig_abort_curve(conn, seed: int = 0) -> Path:
    """The tradeoff an abort threshold buys, with its uncertainty band.

    Deliberately drawn with the band, because the point of this figure is that
    there is NO free threshold -- the pilot's apparent one was an artefact of a
    truncation ceiling.
    """
    curve = analysis.abort_curve_ci(conn, seed=seed, n_resamples=800)
    if not curve:
        raise RuntimeError("no thinking calls to draw an abort curve from")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    saved = [c["saved_pct"] for c in curve]
    kept = [c["kept_pct"] for c in curve]

    ax.fill_between(saved, [c["kept_lo"] for c in curve],
                    [c["kept_hi"] for c in curve],
                    color="#d8d8d8", alpha=0.65, lw=0, label="95% CI")
    ax.plot(saved, kept, "-o", color=INK, lw=1.5, ms=5, zorder=3)
    for c in curve:
        ax.annotate(f"{c['threshold'] // 1000}k", (c["saved_pct"], c["kept_pct"]),
                    textcoords="offset points", xytext=(6, 5),
                    fontsize=7.5, color="#555")

    ax.set_xlabel("cost saved (%)", fontsize=9)
    ax.set_ylabel("solutions retained (%)", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_title("Aborting on reasoning length: a tradeoff, not a free saving\n"
                 f"labels are the reasoning-token threshold "
                 f"(n={curve[0]['n_problems']} problems)",
                 fontsize=10.5, color=INK, pad=12)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    _style(ax)
    return _save(fig, "04-abort-tradeoff")


# ------------------------------------------------------------------ figure 5


def fig_effect_by_model(conn) -> Path:
    """The effect of reasoning per (tier, model). Now the headline figure.

    Figure 1 is an aggregate, and the aggregate averages over models whose
    responses point in opposite directions: +52.9 points on deepseek-v4-flash
    and -18.2 on qwen3.5-9b, on the same hard problems. A reader who sees only
    figure 1 draws a conclusion neither model supports.

    Bars are the delta, so the sign is the message. Censoring is annotated on
    every negative bar because it is what separates the two failure modes -- a
    -18.2 at 81% censored is a model that will not stop, while a -24.4 at 0%
    censored is a model that terminated and got it wrong.
    """
    rows = analysis.within_model_effect(conn)
    if not rows:
        raise RuntimeError("no (tier, model) pair has both arms covered")

    label = {"mbpp_plus": "MBPP+", "humaneval_plus": "HumanEval+",
             "easy": "LCB easy", "medium": "LCB medium", "hard": "LCB hard"}
    order = {"mbpp_plus": 0, "humaneval_plus": 1, "easy": 2, "medium": 3, "hard": 4}
    rows = sorted(rows, key=lambda r: (order.get(r["tier"], 9), -r["delta"]))

    names = [f"{label.get(r['tier'], r['tier'])}\n{r['model'].split('/')[1]}"
             for r in rows]
    deltas = [r["delta"] for r in rows]

    x_lo = min(deltas) - 34
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    bars = ax.barh(range(len(rows)), deltas,
                   color=[HIGH_C if d >= 0 else ACCENT for d in deltas],
                   edgecolor=INK, linewidth=0.6)

    for i, (b, r) in enumerate(zip(bars, rows)):
        d = r["delta"]
        # The delta and its two denominators, so no bar can be read without them.
        ax.text(d + (1.4 if d >= 0 else -1.4), i, f"{d:+.1f}",
                va="center", ha="left" if d >= 0 else "right",
                fontsize=8.5, color=INK)
        # Pinned to the left margin, never over a bar: on the dark fill the
        # grey was unreadable, and these denominators are the point.
        ax.text(x_lo + 0.8, i,
                f"{r['off_pct']:.0f}% (n={r['off_n']}) -> "
                f"{r['high_pct']:.0f}% (n={r['high_n']})",
                va="center", ha="left", fontsize=6.6, color="#555")
        if r["censored_pct"] >= 20:
            ax.text(d + (1.4 if d >= 0 else -1.4), i - 0.32,
                    f"{r['censored_pct']:.0f}% truncated",
                    va="center", ha="left" if d >= 0 else "right",
                    fontsize=6.4, color=ACCENT)

    ax.axvline(0, color=INK, lw=1.0)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(names, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("percentage points gained by enabling reasoning", fontsize=9)
    ax.set_xlim(x_lo, max(deltas) + 14)
    ax.set_title("The effect of reasoning is a property of the MODEL,\n"
                 "not of the difficulty tier",
                 fontsize=10.5, color=INK, pad=10)
    _style(ax)
    return _save(fig, "05-effect-by-model")


# ------------------------------------------------------------------ figure 6


def fig_cpc(conn, seed: int = 0) -> Path:
    """Cost per correct answer per config, with its bootstrap interval.

    Over the paired problem set, because a CPC computed over each config's own
    problems compares models on different exams. Log x-axis: the spread is
    orders of magnitude, and a linear axis would flatten every cheap config
    into one bar at the left edge. `n` is printed per bar because coverage
    inside the paired set still varies (16-107 problems).
    """
    rows = [r for r in analysis.cost_per_correct(conn, seed=seed, n_resamples=2000)
            if r["cpc_usd"] is not None]
    if not rows:
        raise RuntimeError("no CPC rows to draw")
    rows = rows[::-1]                      # cheapest at the top of the chart

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    labels = [f"{r['model_slug'].split('/')[-1]}|{r['effort_label']}" for r in rows]
    x = [r["cpc_usd"] for r in rows]
    lo = [r["cpc_usd"] - r["cpc_lo"] if r["cpc_lo"] == r["cpc_lo"] else 0 for r in rows]
    hi = [r["cpc_hi"] - r["cpc_usd"] if r["cpc_hi"] == r["cpc_hi"] else 0 for r in rows]
    colors = [HIGH_C if r["effort_label"] != "off" else OFF_C for r in rows]
    ax.barh(labels, x, xerr=[lo, hi], color=colors, edgecolor=INK, linewidth=0.6,
            height=0.6, ecolor="#666", capsize=3)
    for i, r in enumerate(rows):
        ax.text(r["cpc_hi"] * 1.15 if r["cpc_hi"] == r["cpc_hi"] else r["cpc_usd"] * 1.15,
                i, f"${r['cpc_usd']:.5f}   n={r['n_problems']}, solved {r['solved']}",
                va="center", fontsize=7.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(min(x) * 0.5, max(x) * 12)
    ax.set_xlabel("cost per correct answer (USD, log scale; bars are 95% CI)", fontsize=9)
    ax.set_title("Cost per correct answer spans orders of magnitude "
                 "(dark = reasoning on, light = off)", fontsize=10.5, color=INK, pad=12)
    _style(ax)
    return _save(fig, "06-cost-per-correct")


# ------------------------------------------------------------------ figure 7


def fig_coverage(conn) -> Path:
    """How many problems each config actually ran. The grid's imbalance.

    Drawn so the reader can see, before any result, that the cheap `off` arm
    is complete and the expensive arms are not -- the run was cheapest-first
    and stopped at the cost cap. Every comparison in the thesis is restricted
    to shared problems because of this picture.
    """
    rows = conn.execute("""
        SELECT c.model_slug, c.effort_label, c.price_out_per_m,
               COUNT(DISTINCT g.problem_id) AS n
        FROM generations g JOIN configs c ON c.config_id = g.config_id
        WHERE COALESCE(g.is_mock, 0) = 0
        GROUP BY c.config_id ORDER BY c.price_out_per_m, c.effort_label
    """).fetchall()
    if not rows:
        raise RuntimeError("no generations to draw coverage from")
    total = conn.execute(
        "SELECT COUNT(DISTINCT problem_id) FROM generations").fetchone()[0]

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    labels = [f"{r['model_slug'].split('/')[-1]}|{r['effort_label']}" for r in rows]
    ns = [r["n"] for r in rows]
    colors = [HIGH_C if r["effort_label"] != "off" else OFF_C for r in rows]
    ax.barh(labels, ns, color=colors, edgecolor=INK, linewidth=0.6, height=0.6)
    ax.axvline(total, color=ACCENT, lw=1, ls="--")
    ax.text(total, -0.9, f"{total} problems in the run set", fontsize=7.5,
            color=ACCENT, ha="right", va="top")
    for i, n in enumerate(ns):
        ax.text(n + total * 0.01, i, str(n), va="center", fontsize=8, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, total * 1.12)
    ax.set_xlabel("problems with at least one generation", fontsize=9)
    ax.set_title("Coverage per configuration: cheapest-first, stopped at the cap",
                 fontsize=10.5, color=INK, pad=12)
    _style(ax)
    return _save(fig, "07-coverage")


# ------------------------------------------------------------------ figure 8


def fig_reasoning_by_tier(conn) -> Path:
    """Mean reasoning tokens per tier, easy to hard, with min-max whiskers.

    The monotone rise is a validity check: the models' internal effort tracks a
    difficulty label they never saw.
    """
    order = ["mbpp_plus", "humaneval_plus", "easy", "medium", "hard"]
    label = {"mbpp_plus": "MBPP+", "humaneval_plus": "HumanEval+",
             "easy": "LCB easy", "medium": "LCB medium", "hard": "LCB hard"}
    rows = {r["tier"]: r for r in analysis.reasoning_by_tier(conn)}
    tiers = [t for t in order if t in rows]
    if not tiers:
        raise RuntimeError("no reasoning rows to draw")

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    means = [rows[t]["avg_reasoning"] or 0 for t in tiers]
    mins = [rows[t]["min_reasoning"] or 0 for t in tiers]
    maxs = [rows[t]["max_reasoning"] or 0 for t in tiers]
    ax.bar([label[t] for t in tiers], means, color=HIGH_C, edgecolor=INK,
           linewidth=0.6, width=0.55)
    ax.errorbar(range(len(tiers)), means,
                yerr=[[m - lo for m, lo in zip(means, mins)],
                      [hi - m for m, hi in zip(means, maxs)]],
                fmt="none", ecolor="#999", capsize=3, lw=0.8)
    for i, t in enumerate(tiers):
        ax.text(i, means[i] + max(maxs) * 0.02, f"{means[i]:,.0f}\n(n={rows[t]['n']})",
                ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylabel("mean reasoning tokens per call", fontsize=9)
    ax.set_ylim(0, max(maxs) * 1.12)
    ax.set_title("Reasoning length rises with difficulty (whiskers: min to max)",
                 fontsize=10.5, color=INK, pad=12)
    _style(ax)
    return _save(fig, "08-reasoning-by-tier")


def make_all(conn, seed: int = 0) -> list[Path]:
    out = []
    for fn in (lambda c: fig_effort_by_tier(c),
               lambda c: fig_effect_by_model(c),
               lambda c: fig_reasoning_outcome(c),
               lambda c: fig_frontier(c, seed=seed),
               lambda c: fig_abort_curve(c, seed=seed),
               lambda c: fig_cpc(c, seed=seed),
               lambda c: fig_coverage(c),
               lambda c: fig_reasoning_by_tier(c)):
        try:
            out.append(fn(conn))
        except Exception as exc:                       # noqa: BLE001
            # One figure failing must not cost the others. A missing panel is
            # obvious; a crashed script that produced nothing is annoying.
            print(f"  skipped a figure: {type(exc).__name__}: {exc}")
    return out
