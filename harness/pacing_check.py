"""Pacing diagnostic: chunk send lateness for each pacer variant on this machine.

    uv run python -m harness.pacing_check [--seconds 3] [--repeats 3]

Each variant runs in a fresh Python process (the Windows throttling opt-out is process-wide):

- `shipped`: what `pace()` does by default on this OS
- `no-cap`: precise, but one sleep to the spin margin (the 2026-11-05 Windows fix)
- `no-optout`: precise and capped, without the power-throttling opt-out
- `plain`: a single sleep per chunk, no timer resolution change (the Linux default)

Prints p10/p50/p90/max/mean lateness (ms) and the share of chunks later than 5 ms, plus the
loop-clock resolution that explains most Windows behaviour (docs/DECISIONS.md). Diagnostic only:
nothing is written and no network is used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Sequence

import numpy as np

from harness import audio

VARIANTS = ("shipped", "no-cap", "no-optout", "plain")


def measure(variant: str, seconds: float) -> list[float]:
    precise: bool | None = None
    if variant == "no-cap":
        audio.MAX_SLEEP_NS, precise = 0, True
    elif variant == "no-optout":
        audio.OPT_OUT_TIMER_THROTTLING, precise = False, True
    elif variant == "plain":
        precise = False
    elif variant != "shipped":
        raise ValueError(variant)
    clip = audio.AudioClip(np.zeros(int(16000 * seconds), dtype=np.int16), 16000, "a:1", 16000)

    async def run() -> list[float]:
        return [c.lateness_ms async for c in audio.pace(clip, chunk_ms=20, precise=precise)]

    return asyncio.run(run())


def stats(xs: Sequence[float]) -> dict[str, float]:
    s = sorted(xs)

    def q(p: float) -> float:
        return s[min(len(s) - 1, int(p * len(s)))]

    return {
        "n": len(s),
        "p10": q(0.1),
        "p50": q(0.5),
        "p90": q(0.9),
        "max": s[-1],
        "mean": statistics.fmean(s),
        "over_5ms": sum(x > 5 for x in s) / len(s),
    }


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--variant", choices=VARIANTS, help=argparse.SUPPRESS)  # child process
    args = ap.parse_args(argv)
    if args.variant:
        xs: list[float] = []
        for _ in range(args.repeats):
            xs += measure(args.variant, args.seconds)
        print(json.dumps(stats(xs)))
        return

    mono = time.get_clock_info("monotonic")
    print(
        f"python {platform.python_version()} on {platform.platform()}; "
        f"loop clock {mono.implementation} resolution {mono.resolution * 1000:.3f} ms; "
        f"precise by default: {audio._IS_WINDOWS}"
    )
    print(f"{'variant':<10} {'n':>5} {'p10':>7} {'p50':>7} {'p90':>7} {'max':>7} {'mean':>7} >5ms")
    for v in VARIANTS:
        out = subprocess.run(
            [sys.executable, "-m", "harness.pacing_check", "--variant", v,
             "--seconds", str(args.seconds), "--repeats", str(args.repeats)],
            capture_output=True, text=True, check=True,
        ).stdout  # fmt: skip
        r = json.loads(out.strip().splitlines()[-1])
        print(
            f"{v:<10} {r['n']:>5} {r['p10']:>7.2f} {r['p50']:>7.2f} {r['p90']:>7.2f} "
            f"{r['max']:>7.2f} {r['mean']:>7.2f} {100 * r['over_5ms']:>4.0f}%"
        )


if __name__ == "__main__":
    main()
