"""Batch runner: one provider configuration over a manifest -> a results run (#8 format).

    uv run python -m harness.providers.runner --config deepgram_nova3_batch \\
        --manifest data/manifests/primock57.jsonl --data-root data/raw --results results/

Behaviour:
- Bounded concurrency; transient failures (`RetryableError`) retried with exponential backoff;
  the final failure is recorded per utterance (`error`, empty hypothesis), never dropped.
- Resumable: the run id defaults to the config id, results are flushed to disk every
  `flush_every` utterances, and re-running skips utterances already recorded (failed ones too,
  unless `retry_failed`). A crash loses at most the unflushed in-flight work.
- A resume refuses to mix configurations: the stored run.json must match the registry entry.
- Raw responses go to `<run>/raw/`, one file per utterance.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness.audio import AudioClip, AudioError, load_clip
from harness.datasets.manifest import Utterance, read_manifest
from harness.providers.base import BatchAdapter, PermanentError, RetryableError, Transcript
from harness.providers.registry import Mode, ProviderConfig, load_registry
from harness.results import RUN_META, ResultRow, RunMeta, read_run, write_run

ClipLoader = Callable[[Utterance], Awaitable[Any]]
Sleep = Callable[[float], Awaitable[None]]

# Adapter factories by provider, filled in by #13. Kept here so the CLI can resolve a config.
BATCH_ADAPTERS: dict[str, Callable[[ProviderConfig], BatchAdapter]] = {}


class RunConflictError(ValueError):
    """An existing run directory was produced by a different configuration."""


@dataclass(frozen=True)
class RunSummary:
    run_dir: Path
    attempted: int
    succeeded: int
    failed: int
    skipped_existing: int
    skipped_excluded: int


def git_sha(cwd: Path | None = None) -> str:
    """HEAD commit, suffixed `-dirty` when the working tree has uncommitted changes."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{sha}-dirty" if dirty else sha


def raw_filename(utt_id: str, suffix: str) -> str:
    """Filesystem-safe name for an utterance's raw response (":" is invalid on Windows)."""
    return utt_id.replace(":", "__").replace("/", "_") + suffix


def _meta_for(config: ProviderConfig, run_id: str, manifest_label: str, sha: str) -> RunMeta:
    return RunMeta(
        run_id=run_id,
        config_id=config.config_id,
        provider=config.provider,
        model_id=config.model_id,
        mode=config.mode.value,
        settings=dict(config.settings),
        created_at=datetime.now(UTC),
        git_sha=sha,
        manifest=manifest_label,
    )


def _check_resumable(existing: RunMeta, config: ProviderConfig) -> None:
    mismatches = [
        name
        for name, old, new in [
            ("config_id", existing.config_id, config.config_id),
            ("provider", existing.provider, config.provider),
            ("model_id", existing.model_id, config.model_id),
            ("mode", existing.mode, config.mode.value),
            ("settings", existing.settings, dict(config.settings)),
        ]
        if old != new
    ]
    if mismatches:
        raise RunConflictError(
            f"run {existing.run_id} was made with different {', '.join(mismatches)}; "
            "use a new --run-id instead of mixing configurations in one run"
        )


async def _transcribe_with_retry(
    adapter: BatchAdapter,
    clip: Any,
    config: ProviderConfig,
    *,
    max_attempts: int,
    backoff_s: float,
    sleep: Sleep,
) -> Transcript:
    for attempt in range(1, max_attempts + 1):
        try:
            return await adapter.transcribe(clip, config.settings)
        except RetryableError:
            if attempt == max_attempts:
                raise
            await sleep(backoff_s * 2 ** (attempt - 1))
    raise AssertionError("unreachable")  # pragma: no cover


async def run_batch(
    config: ProviderConfig,
    adapter: BatchAdapter,
    manifest: Sequence[Utterance],
    *,
    load_clip: ClipLoader,
    results_dir: Path,
    manifest_label: str,
    run_id: str | None = None,
    concurrency: int = 4,
    include_excluded: bool = False,
    retry_failed: bool = False,
    max_attempts: int = 3,
    backoff_s: float = 1.0,
    flush_every: int = 20,
    sleep: Sleep = asyncio.sleep,
    sha: str | None = None,
) -> RunSummary:
    if config.mode is not Mode.BATCH:
        raise ValueError(f"{config.config_id} is a {config.mode} config; this runner is batch-only")
    if concurrency < 1 or max_attempts < 1 or flush_every < 1:
        raise ValueError("concurrency, max_attempts and flush_every must be >= 1")
    run_id = run_id or config.config_id.replace("_", "-")
    run_dir = results_dir / run_id

    rows: dict[str, ResultRow] = {}
    if (run_dir / RUN_META).exists():
        existing = read_run(run_dir)
        _check_resumable(existing.meta, config)
        meta = existing.meta
        rows = {r.utt_id: r for r in existing.rows if not (retry_failed and r.error is not None)}
    else:
        meta = _meta_for(config, run_id, manifest_label, sha or git_sha())

    skipped_excluded = (
        sum(u.exclude_reason is not None for u in manifest) if not include_excluded else 0
    )
    candidates = [u for u in manifest if include_excluded or u.exclude_reason is None]
    todo = [u for u in candidates if u.utt_id not in rows]
    skipped_existing = len(candidates) - len(todo)

    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    write_run(results_dir, meta, rows.values())  # make the run visible even if we crash early

    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    pending_since_flush = 0

    async def one(utt: Utterance) -> ResultRow:
        async with semaphore:
            started = datetime.now(UTC)
            try:
                clip = await load_clip(utt)
                tr = await _transcribe_with_retry(
                    adapter,
                    clip,
                    config,
                    max_attempts=max_attempts,
                    backoff_s=backoff_s,
                    sleep=sleep,
                )
            except (RetryableError, PermanentError) as e:
                return ResultRow(
                    utt_id=utt.utt_id,
                    hyp_text="",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    error=f"{type(e).__name__}: {e}",
                )
            except Exception as e:  # noqa: BLE001 - unknown failures are recorded, not fatal
                return ResultRow(
                    utt_id=utt.utt_id,
                    hyp_text="",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    error=f"unexpected {type(e).__name__}: {e}",
                )
            raw_name = raw_filename(utt.utt_id, tr.raw_suffix)
            raw_bytes = tr.raw if isinstance(tr.raw, bytes) else json.dumps(tr.raw).encode()
            (run_dir / "raw" / raw_name).write_bytes(raw_bytes)
            return ResultRow(
                utt_id=utt.utt_id,
                hyp_text=tr.text,
                raw_response_path=f"raw/{raw_name}",
                started_at=started,
                finished_at=datetime.now(UTC),
            )

    async def record(utt: Utterance) -> None:
        nonlocal pending_since_flush
        row = await one(utt)
        async with lock:
            rows[row.utt_id] = row
            pending_since_flush += 1
            if pending_since_flush >= flush_every:
                write_run(results_dir, meta, rows.values())
                pending_since_flush = 0

    await asyncio.gather(*(record(u) for u in todo))
    write_run(results_dir, meta, rows.values())

    done = [rows[u.utt_id] for u in todo]
    return RunSummary(
        run_dir=run_dir,
        attempted=len(todo),
        succeeded=sum(r.error is None for r in done),
        failed=sum(r.error is not None for r in done),
        skipped_existing=skipped_existing,
        skipped_excluded=skipped_excluded,
    )


def audio_loader(data_root: Path) -> ClipLoader:
    """Clip loader for real runs: decodes off the event loop (ffmpeg is blocking)."""

    async def load(utt: Utterance) -> AudioClip:
        try:
            return await asyncio.to_thread(load_clip, utt, data_root)
        except (FileNotFoundError, AudioError) as e:
            raise PermanentError(f"audio: {e}") from e

    return load


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run one batch STT configuration over a manifest")
    parser.add_argument("--config", required=True, help="config_id from the registry")
    parser.add_argument("--registry", type=Path, default=Path("configs/providers.yaml"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, help="only the first N utterances (trial runs)")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args(argv)

    config = load_registry(args.registry).get(args.config)
    if config.verify:
        print(f"warning: {config.config_id} has unverified model id/pricing (verify: true)")
    factory = BATCH_ADAPTERS.get(config.provider)
    if factory is None:
        raise SystemExit(f"no batch adapter for provider {config.provider!r} yet (#13)")
    if not os.environ.get(config.env_key):
        raise SystemExit(f"set {config.env_key} (see .env.example)")
    manifest = read_manifest(args.manifest)
    if args.limit:
        manifest = manifest[: args.limit]
    summary = asyncio.run(
        run_batch(
            config,
            factory(config),
            manifest,
            load_clip=audio_loader(args.data_root),
            results_dir=args.results,
            manifest_label=args.manifest.as_posix(),
            run_id=args.run_id,
            concurrency=args.concurrency,
            include_excluded=args.include_excluded,
            retry_failed=args.retry_failed,
        )
    )
    print(
        f"{summary.run_dir}: {summary.succeeded} ok, {summary.failed} failed, "
        f"{summary.skipped_existing} already done, {summary.skipped_excluded} excluded"
    )


if __name__ == "__main__":
    main()
