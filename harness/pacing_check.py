"""Pacing diagnostic: chunk send lateness for each pacer variant on this machine.

    uv run python -m harness.pacing_check [--seconds 3] [--repeats 3]

Each variant runs in a fresh Python process (the Windows throttling opt-out is process-wide):

- `shipped`: what `pace()` does by default on this OS (on Windows: waits in a pacing thread)
- `loop-capped`: precise, waits on the asyncio loop in sleeps <= 4 ms (the 2026-11-06 attempt)
- `loop-uncapped`: precise, one asyncio sleep to the spin margin (the 2026-11-05 attempt)
- `no-optout`: shipped without the power-throttling opt-out
- `plain`: a single asyncio sleep per chunk, no timer resolution change (the Linux default)
- `probe-asyncio`, `probe-time`: raw overshoot of `asyncio.sleep(0.004)` and `time.sleep(0.004)`
  (1 ms timer resolution on), to show which sleep mechanism is late

Prints p10/p50/p90/max/mean lateness or overshoot (ms) and the share above 5 ms, plus the loop
clock and whether the 1 ms timer and the throttling opt-out took effect (docs/DECISIONS.md).
Diagnostic only: nothing is written and no network is used.
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

VARIANTS = (
    "shipped", "loop-capped", "loop-uncapped", "no-optout", "plain", "probe-asyncio", "probe-time",
)  # fmt: skip


def probe(kind: str, seconds: float, step_s: float = 0.004) -> list[float]:
    """Overshoot (ms) of repeated `step_s` sleeps for `seconds`, with the 1 ms timer on."""
    out: list[float] = []

    async def asleep() -> None:
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            t = time.perf_counter_ns()
            await asyncio.sleep(step_s)
            out.append((time.perf_counter_ns() - t) / 1e6 - step_s * 1000)

    with audio.timer_resolution_1ms(audio._load_winmm()):
        if kind == "probe-asyncio":
            asyncio.run(asleep())
        else:
            end = time.perf_counter() + seconds
            while time.perf_counter() < end:
                t = time.perf_counter_ns()
                time.sleep(step_s)
                out.append((time.perf_counter_ns() - t) / 1e6 - step_s * 1000)
    return out


def measure(variant: str, seconds: float) -> list[float]:
    precise: bool | None = None
    if variant.startswith("probe-"):
        return probe(variant, seconds)
    if variant == "loop-capped":
        audio.PRECISE_WAIT, precise = "loop", True
    elif variant == "loop-uncapped":
        audio.PRECISE_WAIT, audio.MAX_SLEEP_NS, precise = "loop", 0, True
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
    sleep_clock = time.get_clock_info("perf_counter")
    with audio.timer_resolution_1ms(audio._load_winmm()) as timer_1ms:
        pass
    opted_out = audio.opt_out_timer_throttling(audio._load_kernel32())
    print(
        f"python {platform.python_version()} on {platform.platform()}; "
        f"loop clock {mono.implementation} resolution {mono.resolution * 1000:.3f} ms; "
        f"perf_counter {sleep_clock.implementation}; precise by default: {audio._IS_WINDOWS}; "
        f"timeBeginPeriod(1) ok: {timer_1ms}; throttling opt-out ok: {opted_out}; "
        f"precise wait: {audio.PRECISE_WAIT}"
    )
    print(f"{'variant':<14} {'n':>5} {'p10':>7} {'p50':>7} {'p90':>7} {'max':>7} {'mean':>7} >5ms")
    for v in VARIANTS:
        out = subprocess.run(
            [sys.executable, "-m", "harness.pacing_check", "--variant", v,
             "--seconds", str(args.seconds), "--repeats", str(args.repeats)],
            capture_output=True, text=True, check=True,
        ).stdout  # fmt: skip
        r = json.loads(out.strip().splitlines()[-1])
        print(
            f"{v:<14} {r['n']:>5} {r['p10']:>7.2f} {r['p50']:>7.2f} {r['p90']:>7.2f} "
            f"{r['max']:>7.2f} {r['mean']:>7.2f} {100 * r['over_5ms']:>4.0f}%"
        )


if __name__ == "__main__":
    main()
