"""Write slim trace copies (no provider payloads, gzipped) for every streaming run under a dir.

    uv run python -m harness.streaming.slim --results results_stream/

For each run (`run.json`), every row's `traces/<utt>.jsonl` gets a `traces/<utt>.jsonl.gz` beside
it (`harness.streaming.trace.write_slim_trace`). `.gitignore` tracks only the `.gz` copies, so a
clone can rebuild the latency report and the endpointing sweep without the raw traces, which
carry provider request ids and are ~10x larger. Idempotent: same trace in, same bytes out.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from harness.results import RUN_META, read_run
from harness.streaming.trace import read_trace, slim_path, write_slim_trace


def slim_runs(results_dir: Path) -> tuple[int, int, list[str]]:
    """(traces written, total slim bytes, rows whose full trace is missing)."""
    written, size, missing = 0, 0, []
    for run_dir in sorted(d for d in results_dir.iterdir() if (d / RUN_META).exists()):
        run = read_run(run_dir)
        for row in run.rows:
            if row.error is not None or not row.raw_response_path:
                continue
            full = run_dir / row.raw_response_path
            if not full.exists():
                missing.append(f"{run.meta.run_id}/{row.raw_response_path}")
                continue
            out = slim_path(full)
            write_slim_trace(out, read_trace(full))
            written += 1
            size += out.stat().st_size
    return written, size, missing


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, required=True)
    args = ap.parse_args(argv)
    written, size, missing = slim_runs(args.results)
    print(f"{written} slim traces, {size / 1e6:.1f} MB")
    if missing:
        raise SystemExit(f"{len(missing)} rows have no full trace, e.g. {missing[0]}")


if __name__ == "__main__":
    main()
