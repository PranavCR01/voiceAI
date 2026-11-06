import asyncio
import subprocess
import threading
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import harness.audio as audio_mod
from harness.audio import (
    AudioClip,
    AudioError,
    SampleRateMismatchWarning,
    clear_cache,
    load_clip,
    mulaw_decode,
    mulaw_encode,
    pace,
    resample,
    to_mulaw_8k,
    to_pcm16_bytes,
    to_wav_bytes,
)
from harness.datasets.manifest import Utterance


def tone(freq: float, seconds: float, rate: int, amp: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * rate)) / rate
    return (amp * 32767 * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def write_wav(path: Path, channels: list[np.ndarray], rate: int) -> Path:
    data = np.stack(channels, axis=1) if len(channels) > 1 else channels[0][:, None]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(len(channels))
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.astype("<i2").tobytes())
    return path


def transcode(src: Path, dst: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), str(dst)], check=True
    )
    return dst


def utt(path: Path, root: Path, **kw: Any) -> Utterance:
    fields: dict[str, Any] = {
        "utt_id": "a:1",
        "dataset": "a",
        "subset": "s",
        "speaker_id": "x",
        "audio_path": path.relative_to(root).as_posix(),
        "ref_text": "",
        "sample_rate": 22050,
        "license": "CC0-1.0",
    }
    fields.update(kw)
    return Utterance(**fields)


def dominant_hz(samples: np.ndarray, rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(samples.astype(np.float64)))
    return float(np.fft.rfftfreq(len(samples), 1 / rate)[np.argmax(spectrum)])


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    clear_cache()


@pytest.mark.parametrize(("suffix", "tolerance_s"), [(".wav", 0.0), (".flac", 0.0), (".mp3", 0.06)])
def test_decode_resample_formats(tmp_path: Path, suffix: str, tolerance_s: float) -> None:
    src = write_wav(tmp_path / "src.wav", [tone(440, 2.0, 22050)], 22050)
    path = src if suffix == ".wav" else transcode(src, tmp_path / f"tone{suffix}")
    clip = load_clip(utt(path, tmp_path), tmp_path, sample_rate=16000)
    assert clip.sample_rate == 16000 and clip.source_sample_rate == 22050
    assert clip.duration_s == pytest.approx(2.0, abs=tolerance_s + 1 / 16000)
    assert dominant_hz(clip.samples, 16000) == pytest.approx(440, abs=2)


def test_segment_cut_is_sample_exact_at_native_rate(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    noise = rng.integers(-8000, 8000, 16000 * 3).astype(np.int16)
    path = write_wav(tmp_path / "n.wav", [noise], 16000)
    u = utt(path, tmp_path, sample_rate=16000, start_s=0.5, end_s=1.25)
    clip = load_clip(u, tmp_path, sample_rate=16000)
    np.testing.assert_array_equal(clip.samples, noise[8000:20000])


def test_segment_cut_length_after_resampling(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "t.wav", [tone(300, 3.0, 44100)], 44100)
    u = utt(path, tmp_path, sample_rate=44100, start_s=0.25, end_s=1.75)
    clip = load_clip(u, tmp_path, sample_rate=16000)
    assert abs(len(clip.samples) - 24000) <= 1


def test_channel_selection_and_downmix(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "st.wav", [tone(440, 1.0, 16000), tone(880, 1.0, 16000)], 16000)
    left = load_clip(utt(path, tmp_path, sample_rate=16000, channel=0), tmp_path)
    right = load_clip(utt(path, tmp_path, sample_rate=16000, channel=1), tmp_path)
    assert dominant_hz(left.samples, 16000) == pytest.approx(440, abs=2)
    assert dominant_hz(right.samples, 16000) == pytest.approx(880, abs=2)
    with pytest.raises(AudioError, match="channel 2 requested"):
        load_clip(utt(path, tmp_path, sample_rate=16000, channel=2), tmp_path)


def test_sample_rate_mismatch_warns_and_records(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "t.wav", [tone(440, 0.5, 16000)], 16000)
    with pytest.warns(SampleRateMismatchWarning, match="manifest says 48000"):
        clip = load_clip(utt(path, tmp_path, sample_rate=48000), tmp_path)
    assert clip.source_sample_rate == 16000


def test_missing_and_corrupt_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_clip(utt(tmp_path / "missing.wav", tmp_path), tmp_path)
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio at all")
    with pytest.raises(AudioError):
        load_clip(utt(bad, tmp_path), tmp_path)


def test_paths_with_spaces(tmp_path: Path) -> None:
    d = tmp_path / "dir with spaces"
    d.mkdir()
    path = write_wav(d / "my file.wav", [tone(440, 0.5, 16000)], 16000)
    assert load_clip(utt(path, tmp_path, sample_rate=16000), tmp_path).duration_s == pytest.approx(
        0.5
    )


def test_mulaw_matches_ffmpeg_reference(tmp_path: Path) -> None:
    pcm = np.arange(-32768, 32768, dtype=np.int32).astype(np.int16)  # every possible sample
    ref = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            "8000",
            "-ac",
            "1",
            "-i",
            "-",
            "-f",
            "mulaw",
            "-",
        ],
        input=pcm.astype("<i2").tobytes(),
        capture_output=True,
        check=True,
    ).stdout
    ours = mulaw_encode(pcm)
    assert ours == ref
    decoded_ref = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-f",
            "mulaw",
            "-ar",
            "8000",
            "-ac",
            "1",
            "-i",
            "-",
            "-f",
            "s16le",
            "-",
        ],
        input=ref,
        capture_output=True,
        check=True,
    ).stdout
    np.testing.assert_array_equal(mulaw_decode(ours), np.frombuffer(decoded_ref, "<i2"))


def test_mulaw_round_trip_quality() -> None:
    clip = AudioClip(tone(300, 1.0, 16000), 16000, "a:1", 16000)
    data = to_mulaw_8k(clip)
    assert len(data) == 8000  # one byte per sample at 8 kHz
    reference = resample(clip, 8000).samples.astype(np.float64)
    error = mulaw_decode(data).astype(np.float64) - reference
    snr_db = 10 * np.log10(np.sum(reference**2) / np.sum(error**2))
    assert snr_db > 30


def test_wav_bytes_round_trip(tmp_path: Path) -> None:
    clip = AudioClip(tone(440, 0.25, 16000), 16000, "a:1", 16000)
    (tmp_path / "x.wav").write_bytes(to_wav_bytes(clip))
    with wave.open(str(tmp_path / "x.wav")) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        assert w.readframes(w.getnframes()) == to_pcm16_bytes(clip)


# --- pacing (wall-clock tests; skip with -m "not timing" on a loaded machine) -------------


async def _collect(clip: AudioClip, **kw: Any) -> list[Any]:
    return [c async for c in pace(clip, **kw)]


@pytest.mark.timing
def test_pace_one_second_in_twenty_ms_chunks() -> None:
    clip = AudioClip(tone(440, 1.0, 16000), 16000, "a:1", 16000)
    start = time.perf_counter()
    chunks = asyncio.run(_collect(clip, chunk_ms=20))
    elapsed = time.perf_counter() - start
    assert len(chunks) == 50
    assert all(len(c.data) == 640 for c in chunks)  # 20 ms of 16 kHz PCM16
    assert b"".join(c.data for c in chunks) == to_pcm16_bytes(clip)
    # The last chunk is due at 0.98 s; the whole yield loop takes about that long.
    assert elapsed == pytest.approx(0.98, rel=0.05)
    assert [c.audio_offset_ms for c in chunks[:3]] == [0, 20, 40]


@pytest.mark.timing
def test_pace_does_not_drift() -> None:
    clip = AudioClip(tone(440, 3.0, 16000), 16000, "a:1", 16000)
    chunks = asyncio.run(_collect(clip, chunk_ms=20))
    t0 = chunks[0].scheduled_ns
    last = chunks[-1]
    assert last.scheduled_ns - t0 == 149 * 20_000_000  # absolute schedule
    # No drift: lateness doesn't accumulate. A single scheduler/GC stall on a busy machine
    # can make one chunk late, so assert on the typical chunk and the last one, not the max.
    lateness = sorted(c.lateness_ms for c in chunks)
    assert lateness[len(lateness) // 2] < 5
    assert last.lateness_ms < 20


@pytest.mark.timing
def test_pace_mulaw_and_padding() -> None:
    clip = AudioClip(tone(440, 0.2, 16000), 16000, "a:1", 16000)
    chunks = asyncio.run(_collect(clip, chunk_ms=20, encoding="mulaw", pad_ms=100))
    assert len(chunks) == 15  # 200 ms of audio + 100 ms of silence
    assert all(len(c.data) == 160 for c in chunks)  # 20 ms of 8 kHz µ-law
    assert all(c.data == b"\xff" * 160 for c in chunks[-5:])  # µ-law silence


def test_pace_rejects_bad_arguments() -> None:
    clip = AudioClip(tone(440, 0.1, 16000), 16000, "a:1", 16000)
    with pytest.raises(ValueError):
        asyncio.run(_collect(clip, chunk_ms=0))


@pytest.mark.timing
def test_precise_pacing_on_any_os() -> None:
    """The precise path (capped sleeps, then spin), forced on. On Windows it is also the default,
    so this duplicates test_pace_does_not_drift there; on Linux it is the only real-clock run of
    the spin path."""
    clip = AudioClip(tone(440, 1.0, 16000), 16000, "a:1", 16000)
    chunks = asyncio.run(_collect(clip, chunk_ms=20, precise=True))
    lateness = sorted(c.lateness_ms for c in chunks)
    assert len(chunks) == 50
    assert all(c.sent_ns >= c.scheduled_ns for c in chunks)  # spin never yields early
    assert lateness[len(lateness) // 2] < 5


# --- precise waits and the Windows timer (logic only: mocked clock, sleep and winmm) --------


class FakeClock:
    """A clock that only moves when the fake sleep says so; records every sleep request."""

    def __init__(self, oversleep_ns: int = 0, undersleep_ns: int = 0) -> None:
        self.now = 1_000_000_000
        self.sleeps: list[float] = []
        self.oversleep_ns = oversleep_ns
        self.undersleep_ns = undersleep_ns

    def __call__(self) -> int:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if seconds == 0:
            self.now += 50_000  # one loop iteration while spinning
        else:
            # An early wake-up (the timer firing before its time) happens once, then sleeps
            # are honest: a real clock always moves forward while sleeping.
            self.now += int(seconds * 1e9) + self.oversleep_ns - self.undersleep_ns
            self.undersleep_ns = 0


def _wait(clock: FakeClock, due: int, margin: int, max_sleep: int = 0) -> None:
    asyncio.run(
        audio_mod.wait_until(
            due, spin_margin_ns=margin, max_sleep_ns=max_sleep, clock=clock, sleep=clock.sleep
        )
    )


def test_wait_until_caps_each_sleep_below_one_loop_clock_tick() -> None:
    """18 ms to the margin in steps of <= 4 ms: no single sleep spans a 15.6 ms Windows tick."""
    clock = FakeClock(oversleep_ns=300_000)
    due = clock.now + 20_000_000
    _wait(clock, due, 2_000_000, max_sleep=4_000_000)
    sleeps = [x for x in clock.sleeps if x > 0]
    assert max(sleeps) <= 0.004 + 1e-12
    assert len(sleeps) >= 4
    assert sum(sleeps) < 0.018 + 1e-9  # never sleeps past the margin
    assert due <= clock.now < due + 50_000


def test_wait_until_capped_and_early_wakeup_still_reaches_the_deadline() -> None:
    clock = FakeClock(undersleep_ns=3_000_000)
    due = clock.now + 20_000_000
    _wait(clock, due, 2_000_000, max_sleep=4_000_000)
    assert due <= clock.now < due + 50_000


def test_wait_until_without_margin_is_one_sleep() -> None:
    clock = FakeClock()
    _wait(clock, clock.now + 20_000_000, 0)
    assert clock.sleeps == [pytest.approx(0.020)]


def test_wait_until_sleeps_to_margin_then_spins_to_the_deadline() -> None:
    clock = FakeClock(oversleep_ns=500_000)  # 0.5 ms wake-up jitter, inside the 2 ms margin
    due = clock.now + 20_000_000
    _wait(clock, due, 2_000_000)
    assert clock.sleeps[0] == pytest.approx(0.018)
    assert all(s == 0 for s in clock.sleeps[1:])  # the rest is spinning
    assert len(clock.sleeps) > 1
    assert due <= clock.now < due + 50_000  # returns within one spin step of the deadline


def test_wait_until_early_wakeup_sleeps_again_never_returns_early() -> None:
    clock = FakeClock(undersleep_ns=8_000_000)  # the timer fires 8 ms early
    due = clock.now + 20_000_000
    _wait(clock, due, 2_000_000)
    assert clock.now >= due
    # After the early wake-up it sleeps again to the margin instead of spinning ~10 ms.
    assert clock.sleeps[:2] == [pytest.approx(0.018), pytest.approx(0.008)]
    assert all(x == 0 for x in clock.sleeps[2:]) and len(clock.sleeps) <= 2 + 41


def test_wait_until_inside_margin_or_past_due_does_not_sleep() -> None:
    clock = FakeClock()
    _wait(clock, clock.now + 1_000_000, 2_000_000)  # 1 ms left: spin only
    assert clock.sleeps and all(s == 0 for s in clock.sleeps)
    clock = FakeClock()
    _wait(clock, clock.now - 5_000_000, 2_000_000)  # already late: return at once
    assert clock.sleeps == []


class FakeWinMM:
    def __init__(self, begin_result: int = 0) -> None:
        self.calls: list[tuple[str, int]] = []
        self.begin_result = begin_result

    def timeBeginPeriod(self, period: int, /) -> int:  # noqa: N802
        self.calls.append(("begin", period))
        return self.begin_result

    def timeEndPeriod(self, period: int, /) -> int:  # noqa: N802
        self.calls.append(("end", period))
        return 0


def test_timer_resolution_begins_and_ends_even_on_error() -> None:
    winmm = FakeWinMM()
    with audio_mod.timer_resolution_1ms(winmm) as active:
        assert active
        assert winmm.calls == [("begin", 1)]
    assert winmm.calls == [("begin", 1), ("end", 1)]
    winmm = FakeWinMM()
    with pytest.raises(RuntimeError), audio_mod.timer_resolution_1ms(winmm):
        raise RuntimeError
    assert winmm.calls == [("begin", 1), ("end", 1)]


def test_timer_resolution_failure_or_absence_is_a_noop() -> None:
    winmm = FakeWinMM(begin_result=97)  # TIMERR_NOCANDO
    with audio_mod.timer_resolution_1ms(winmm) as active:
        assert not active
    assert winmm.calls == [("begin", 1)]  # no unmatched timeEndPeriod
    with audio_mod.timer_resolution_1ms(None) as active:
        assert not active


def test_load_winmm_is_none_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_mod, "_IS_WINDOWS", False)
    assert audio_mod._load_winmm() is None


class FakeKernel32:
    def __init__(self, result: int = 1) -> None:
        self.calls: list[tuple[Any, int, tuple[int, int, int], int]] = []
        self.result = result

    def GetCurrentProcess(self) -> Any:  # noqa: N802
        return "pseudo-handle"

    def SetProcessInformation(self, h: Any, cls: int, info: Any, size: int, /) -> int:  # noqa: N802
        st = info._obj  # ctypes.byref -> the structure
        self.calls.append((h, cls, (st.Version, st.ControlMask, st.StateMask), size))
        return self.result


def test_opt_out_timer_throttling_sends_the_documented_struct() -> None:
    k32 = FakeKernel32()
    assert audio_mod.opt_out_timer_throttling(k32)
    # ProcessPowerThrottling = 4; {version 1, control IGNORE_TIMER_RESOLUTION (0x4), state 0}
    assert k32.calls == [("pseudo-handle", 4, (1, 0x4, 0), 12)]
    assert not audio_mod.opt_out_timer_throttling(FakeKernel32(result=0))  # unsupported OS
    assert not audio_mod.opt_out_timer_throttling(None)


KERNEL32 = FakeKernel32()


def _patch_windows(monkeypatch: pytest.MonkeyPatch, winmm: FakeWinMM) -> list[tuple[str, int, int]]:
    """Pretend to be Windows: fake winmm/kernel32, and record every wait as (where it ran:
    "loop" or the pacing thread's name, spin margin, max sleep)."""
    waits: list[tuple[str, int, int]] = []
    real_wait, real_block = audio_mod.wait_until, audio_mod.block_until

    async def recording_wait(
        due_ns: int, *, spin_margin_ns: int = 0, max_sleep_ns: int = 0
    ) -> None:
        waits.append(("loop", spin_margin_ns, max_sleep_ns))
        await real_wait(due_ns, spin_margin_ns=spin_margin_ns, max_sleep_ns=max_sleep_ns)

    def recording_block(due_ns: int, *, spin_margin_ns: int) -> None:
        waits.append((threading.current_thread().name.split("_")[0], spin_margin_ns, 0))
        real_block(due_ns, spin_margin_ns=spin_margin_ns)

    monkeypatch.setattr(audio_mod, "_IS_WINDOWS", True)
    monkeypatch.setattr(audio_mod, "_load_winmm", lambda: winmm)
    monkeypatch.setattr(audio_mod, "_load_kernel32", lambda: KERNEL32)
    monkeypatch.setattr(audio_mod, "wait_until", recording_wait)
    monkeypatch.setattr(audio_mod, "block_until", recording_block)
    return waits


def test_pace_on_windows_holds_1ms_timer_while_pacing(monkeypatch: pytest.MonkeyPatch) -> None:
    winmm = FakeWinMM()
    margins = _patch_windows(monkeypatch, winmm)
    clip = AudioClip(tone(440, 0.1, 16000), 16000, "a:1", 16000)

    async def run() -> list[list[tuple[str, int]]]:
        seen = []
        async for _ in pace(clip, chunk_ms=20):
            seen.append(list(winmm.calls))
        return seen

    seen = asyncio.run(run())
    assert len(seen) == 5
    assert all(calls == [("begin", 1)] for calls in seen)  # active for every chunk
    assert winmm.calls == [("begin", 1), ("end", 1)]  # released when pacing ends
    # Every wait ran in the pacing thread, sleeping then spinning the last SPIN_MARGIN_NS.
    assert margins == [("pace", audio_mod.SPIN_MARGIN_NS, 0)] * 5
    assert KERNEL32.calls and KERNEL32.calls[-1][2] == (1, 0x4, 0)  # throttling opt-out sent


def test_pace_on_windows_releases_timer_when_consumer_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winmm = FakeWinMM()
    _patch_windows(monkeypatch, winmm)
    clip = AudioClip(tone(440, 0.2, 16000), 16000, "a:1", 16000)

    async def run() -> None:
        gen = pace(clip, chunk_ms=20)
        async for c in gen:
            if c.index == 1:
                break  # the session breaks out when the provider closes early
        await gen.aclose()

    asyncio.run(run())
    assert winmm.calls == [("begin", 1), ("end", 1)]


def test_pace_off_windows_keeps_plain_sleeps(monkeypatch: pytest.MonkeyPatch) -> None:
    winmm = FakeWinMM()
    margins = _patch_windows(monkeypatch, winmm)
    monkeypatch.setattr(audio_mod, "_IS_WINDOWS", False)
    clip = AudioClip(tone(440, 0.06, 16000), 16000, "a:1", 16000)
    asyncio.run(_collect(clip, chunk_ms=20))
    assert winmm.calls == []
    assert margins == [("loop", 0, 0)] * 3


def test_pacing_check_stats_and_variants() -> None:
    from harness.pacing_check import VARIANTS, stats

    s = stats([float(x) for x in range(10)])
    assert (s["n"], s["p10"], s["p50"], s["p90"], s["max"]) == (10, 1.0, 5.0, 9.0, 9.0)
    assert s["over_5ms"] == 0.4
    assert VARIANTS[0] == "shipped"


def test_pace_on_windows_loop_mode_uses_capped_loop_sleeps(monkeypatch: pytest.MonkeyPatch) -> None:
    waits = _patch_windows(monkeypatch, FakeWinMM())
    monkeypatch.setattr(audio_mod, "PRECISE_WAIT", "loop")
    clip = AudioClip(tone(440, 0.06, 16000), 16000, "a:1", 16000)
    asyncio.run(_collect(clip, chunk_ms=20))
    assert waits == [("loop", audio_mod.SPIN_MARGIN_NS, audio_mod.MAX_SLEEP_NS)] * 3


class SyncFakeClock(FakeClock):
    def sleep_sync(self, seconds: float) -> None:
        asyncio.run(self.sleep(seconds))


def test_block_until_sleeps_to_margin_then_spins_and_resleeps_after_early_wakeup() -> None:
    clock = SyncFakeClock(undersleep_ns=3_000_000)
    due = clock.now + 20_000_000
    audio_mod.block_until(due, spin_margin_ns=2_000_000, clock=clock, sleep=clock.sleep_sync)
    assert clock.sleeps[:2] == [pytest.approx(0.018), pytest.approx(0.003)]
    assert all(x == 0 for x in clock.sleeps[2:])
    assert due <= clock.now < due + 50_000
    late = SyncFakeClock()
    audio_mod.block_until(late.now - 1, spin_margin_ns=2_000_000, clock=late, sleep=late.sleep_sync)
    assert late.sleeps == []


def test_pacing_thread_is_released_when_consumer_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_windows(monkeypatch, FakeWinMM())
    clip = AudioClip(tone(440, 0.2, 16000), 16000, "a:1", 16000)

    async def run() -> None:
        gen = pace(clip, chunk_ms=20)
        async for c in gen:
            if c.index == 1:
                break
        await gen.aclose()

    asyncio.run(run())
    for _ in range(50):
        if not any(t.name.startswith("pace") for t in threading.enumerate()):
            break
        time.sleep(0.01)
    assert not any(t.name.startswith("pace") for t in threading.enumerate())
