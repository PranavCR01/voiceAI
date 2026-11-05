"""Deterministic static charts for the reports (#22). Same input -> byte-identical SVG.

    uv run python -m harness.charts tradeoff --csv reports/generated/endpointing_sweep.csv \\
        --out reports/generated/endpointing_tradeoff.svg

Endpointing trade-off: small multiples, one panel per config (shared axes, so panels compare
directly), x = p95 endpoint delay, y = premature-endpoint rate, one point per knob value with
its 95% intervals as error bars and the knob value as a direct label. One colour (palette slot 1)
because each panel holds one series: four configs in one plot would need a fourth categorical
hue, and the reference palette's fourth slot fails the all-pairs colour checks (dataviz
guidance). Static SVG for a Markdown report, so no hover layer; the CSV/table is the accessible
view. Light surface only.

Determinism: Agg backend, fixed `svg.hashsalt`, text kept as text (`svg.fonttype: none`), no
date metadata, fixed figure size and fonts.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SERIES = "#2a78d6"  # palette slot 1 (blue), validated light

STYLE: dict[Any, Any] = {
    "svg.hashsalt": "voiceai",
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
}


def _f(row: Mapping[str, object], key: str) -> float:
    v = row.get(key)
    return math.nan if v in (None, "") else float(str(v))


def tradeoff_svg(rows: Sequence[Mapping[str, object]], out: Path) -> None:
    configs = sorted({str(r["config_id"]) for r in rows})
    if not configs:
        raise ValueError("no sweep rows")
    cols = min(2, len(configs))
    nrows = math.ceil(len(configs) / cols)
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(
            nrows, cols, figsize=(3.6 * cols, 2.8 * nrows), sharex=True, sharey=True, squeeze=False
        )
        for ax in axes.flat[len(configs) :]:
            ax.set_visible(False)
        for ax, cid in zip(axes.flat, configs, strict=False):
            pts = sorted(
                (r for r in rows if r["config_id"] == cid), key=lambda r: _f(r, "delay_p95_ms")
            )
            x = [_f(r, "delay_p95_ms") for r in pts]
            y = [100 * _f(r, "premature_rate") for r in pts]
            xerr = [
                [max(0.0, xi - _f(r, "delay_p95_low")) for xi, r in zip(x, pts, strict=True)],
                [max(0.0, _f(r, "delay_p95_high") - xi) for xi, r in zip(x, pts, strict=True)],
            ]
            yerr = [
                [max(0.0, yi - 100 * _f(r, "premature_low")) for yi, r in zip(y, pts, strict=True)],
                [
                    max(0.0, 100 * _f(r, "premature_high") - yi)
                    for yi, r in zip(y, pts, strict=True)
                ],
            ]
            ax.errorbar(
                x, y, xerr=xerr, yerr=yerr, color=SERIES, ecolor=SERIES, elinewidth=1,
                alpha=1.0, linewidth=1.5, marker="o", markersize=6, markeredgecolor=SURFACE,
                markeredgewidth=1.5, capsize=0, zorder=3,
            )  # fmt: skip
            knob = str(pts[0]["knob"]) if pts else ""
            for xi, yi, r in zip(x, y, pts, strict=True):
                if math.isfinite(xi) and math.isfinite(yi):
                    ax.annotate(
                        str(r["value"]), (xi, yi), textcoords="offset points", xytext=(5, 4),
                        fontsize=7.5, color=INK_2,
                    )  # fmt: skip
            ax.set_title(f"{cid}\n({knob})", fontsize=9, loc="left")
            ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
            ax.tick_params(length=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        # x labels on the lowest *visible* panel of each column (a hidden empty slot at the
        # bottom would otherwise leave the panel above it without an x axis).
        for col in range(cols):
            shown = [axes[r, col] for r in range(nrows) if axes[r, col].get_visible()]
            if shown:
                shown[-1].xaxis.set_tick_params(labelbottom=True)
                shown[-1].set_xlabel("p95 endpoint delay (ms)")
        for ax in axes[:, 0]:
            ax.set_ylabel("premature endpoints (%)")
        axes[0, 0].set_ylim(bottom=0)  # a rate starts at zero (axes are shared)
        axes[0, 0].set_xlim(left=0)
        fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, format="svg", metadata={"Date": None, "Creator": None})
        plt.close(fig)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tradeoff")
    t.add_argument("--csv", type=Path, required=True)
    t.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    tradeoff_svg(read_csv(args.csv), args.out)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
