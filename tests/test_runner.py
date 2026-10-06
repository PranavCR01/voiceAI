import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import JsonValue

from harness.datasets.manifest import Utterance
from harness.providers.base import PermanentError, RetryableError, Transcript
from harness.providers.registry import ProviderConfig
from harness.providers.runner import RunConflictError, raw_filename, run_batch
from harness.results import read_run

CONFIG = ProviderConfig.model_validate(
    {
        "config_id": "fake_batch",
        "provider": "fake",
        "model_id": "fake-1",
        "mode": "batch",
        "settings": {"smart_format": True},
        "pricing": {
            "amount": 0.01,
            "unit": "minute",
            "billing_basis": "audio_duration",
            "source": "test",
            "as_of": "2026-10-06",
        },
        "env_key": "FAKE_API_KEY",
    }
)


def utts(n: int, *, excluded: int = 0) -> list[Utterance]:
    return [
        Utterance(
            utt_id=f"t:{i:03d}",
            dataset="t",
            subset="s",
            speaker_id=f"spk{i % 3}",
            audio_path=f"t/{i}.wav",
            ref_text=f"utterance number {i}",
            sample_rate=16000,
            license="CC0-1.0",
            exclude_reason="too_short" if i < excluded else None,
        )
        for i in range(n)
    ]


async def load(utt: Utterance) -> Utterance:
    return utt  # the fake adapter transcribes the utterance object itself


class Crash(BaseException):
    """Simulates the process dying (not caught by the runner's Exception handlers)."""


class FakeAdapter:
    def __init__(
        self,
        *,
        failures: Mapping[str, list[Exception]] | None = None,
        crash_after: int | None = None,
        delay: float = 0.0,
    ) -> None:
        self.failures = {k: list(v) for k, v in (failures or {}).items()}
        self.crash_after = crash_after
        self.delay = delay
        self.calls = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def transcribe(self, clip: Any, settings: Mapping[str, JsonValue]) -> Transcript:
        self.calls += 1
        if self.crash_after is not None and self.calls > self.crash_after:
            raise Crash()
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            queue = self.failures.get(clip.utt_id)
            if queue:
                raise queue.pop(0)
            return Transcript(
                text=clip.ref_text.upper(), raw={"id": clip.utt_id, "settings": dict(settings)}
            )
        finally:
            self.in_flight -= 1


async def no_sleep(_: float) -> None:
    return None


def run(tmp_path: Path, adapter: FakeAdapter, manifest: list[Utterance], **kw: Any) -> Any:
    return asyncio.run(
        run_batch(
            CONFIG,
            adapter,
            manifest,
            load_clip=load,
            results_dir=tmp_path,
            manifest_label="test",
            sleep=no_sleep,
            sha="abcdef0",
            **kw,
        )
    )


def comparable(run_dir: Path) -> list[tuple[str, str, str | None, str | None]]:
    return [(r.utt_id, r.hyp_text, r.raw_response_path, r.error) for r in read_run(run_dir).rows]


def test_full_run_writes_results_raw_and_meta(tmp_path: Path) -> None:
    summary = run(tmp_path, FakeAdapter(), utts(5, excluded=1))
    assert (summary.attempted, summary.succeeded, summary.failed) == (4, 4, 0)
    assert summary.skipped_excluded == 1
    r = read_run(summary.run_dir)
    assert r.meta.run_id == "fake-batch" and r.meta.git_sha == "abcdef0"
    assert r.meta.settings == {"smart_format": True}
    row = r.by_utt()["t:001"]
    assert row.hyp_text == "UTTERANCE NUMBER 1"
    assert row.raw_response_path == f"raw/{raw_filename('t:001', '.json')}"
    assert (summary.run_dir / row.raw_response_path).read_text().startswith('{"id": "t:001"')
    assert "t:000" not in r.by_utt()  # excluded


def test_interrupted_then_resumed_equals_uninterrupted(tmp_path: Path) -> None:
    manifest = utts(30)
    run(tmp_path / "clean", FakeAdapter(), manifest)

    with pytest.raises(Crash):
        run(
            tmp_path / "resumed",
            FakeAdapter(crash_after=12),
            manifest,
            flush_every=5,
            concurrency=1,
        )
    partial = read_run(tmp_path / "resumed" / "fake-batch")
    assert 0 < len(partial.rows) < 30  # some work survived the crash
    resumed = FakeAdapter()
    summary = run(tmp_path / "resumed", resumed, manifest, flush_every=5)
    assert resumed.calls == 30 - len(partial.rows)  # only the missing ones were redone
    assert summary.skipped_existing == len(partial.rows)
    assert comparable(tmp_path / "resumed" / "fake-batch") == comparable(
        tmp_path / "clean" / "fake-batch"
    )


def test_retryable_then_success(tmp_path: Path) -> None:
    adapter = FakeAdapter(failures={"t:000": [RetryableError("429"), RetryableError("429")]})
    summary = run(tmp_path, adapter, utts(1))
    row = read_run(summary.run_dir).rows[0]
    assert (row.error, row.hyp_text) == (None, "UTTERANCE NUMBER 0")
    assert adapter.calls == 3


def test_backoff_is_exponential(tmp_path: Path) -> None:
    waits: list[float] = []

    async def record_sleep(s: float) -> None:
        waits.append(s)

    adapter = FakeAdapter(failures={"t:000": [RetryableError("503")] * 2})
    asyncio.run(
        run_batch(
            CONFIG,
            adapter,
            utts(1),
            load_clip=load,
            results_dir=tmp_path,
            manifest_label="t",
            sleep=record_sleep,
            backoff_s=0.5,
            sha="abcdef0",
        )
    )
    assert waits == [0.5, 1.0]


@pytest.mark.parametrize(
    ("failures", "expected_calls", "error_prefix"),
    [
        ([RetryableError("429")] * 3, 3, "RetryableError: 429"),
        ([PermanentError("401 unauthorized")], 1, "PermanentError: 401"),
        ([ValueError("bad json")], 1, "unexpected ValueError: bad json"),
    ],
)
def test_failures_are_recorded_not_dropped(
    tmp_path: Path, failures: list[Exception], expected_calls: int, error_prefix: str
) -> None:
    adapter = FakeAdapter(failures={"t:000": failures})
    summary = run(tmp_path, adapter, utts(2))
    row = read_run(summary.run_dir).by_utt()["t:000"]
    assert row.hyp_text == "" and row.error is not None and row.error.startswith(error_prefix)
    assert row.raw_response_path is None
    assert adapter.calls == expected_calls + 1  # + the other utterance
    assert (summary.succeeded, summary.failed) == (1, 1)


def test_failed_rows_skipped_on_resume_unless_retry_failed(tmp_path: Path) -> None:
    run(tmp_path, FakeAdapter(failures={"t:000": [PermanentError("boom")]}), utts(2))
    again = FakeAdapter()
    assert run(tmp_path, again, utts(2)).attempted == 0
    summary = run(tmp_path, again, utts(2), retry_failed=True)
    assert summary.attempted == 1 and summary.succeeded == 1
    assert read_run(summary.run_dir).by_utt()["t:000"].error is None


def test_concurrency_limit(tmp_path: Path) -> None:
    adapter = FakeAdapter(delay=0.01)
    run(tmp_path, adapter, utts(20), concurrency=3)
    assert adapter.max_in_flight == 3


def test_resume_refuses_a_different_configuration(tmp_path: Path) -> None:
    run(tmp_path, FakeAdapter(), utts(2))
    changed = CONFIG.model_copy(update={"settings": {"smart_format": False}})
    with pytest.raises(RunConflictError, match="settings"):
        asyncio.run(
            run_batch(
                changed,
                FakeAdapter(),
                utts(2),
                load_clip=load,
                results_dir=tmp_path,
                manifest_label="t",
                sleep=no_sleep,
                sha="abcdef0",
            )
        )


def test_streaming_configs_rejected(tmp_path: Path) -> None:
    streaming = CONFIG.model_copy(update={"mode": "streaming"})
    with pytest.raises(ValueError, match="batch-only"):
        asyncio.run(
            run_batch(
                streaming,
                FakeAdapter(),
                utts(1),
                load_clip=load,
                results_dir=tmp_path,
                manifest_label="t",
            )
        )


def test_raw_filename_is_filesystem_safe() -> None:
    assert raw_filename("primock57:day1_consultation01:patient:0003", ".json") == (
        "primock57__day1_consultation01__patient__0003.json"
    )


def test_git_sha_reads_this_repo() -> None:
    import re

    from harness.providers.runner import git_sha

    assert re.fullmatch(r"[0-9a-f]{40}(-dirty)?", git_sha(Path(__file__).parent))
    assert git_sha(Path("/")) == "unknown"


def test_audio_loader_maps_missing_files_to_permanent_errors(tmp_path: Path) -> None:
    from harness.providers.runner import audio_loader

    summary = asyncio.run(
        run_batch(
            CONFIG,
            FakeAdapter(),
            utts(1),
            load_clip=audio_loader(tmp_path),
            results_dir=tmp_path / "r",
            manifest_label="t",
            sleep=no_sleep,
            sha="abcdef0",
        )
    )
    row = read_run(summary.run_dir).rows[0]
    assert row.error is not None and row.error.startswith("PermanentError: audio:")
