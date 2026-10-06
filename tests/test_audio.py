import asyncio
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

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
    start = time.monotonic()
    chunks = asyncio.run(_collect(clip, chunk_ms=20))
    elapsed = time.monotonic() - start
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
    assert last.lateness_ms < 20
    assert max(c.lateness_ms for c in chunks) < 20


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
