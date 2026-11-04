"""Speech start/end per utterance with Silero VAD on ONNX Runtime (#15).

Why: TTFS and endpoint delay (#14) are measured from when the speaker actually stopped. A clip's
`end_s` includes trailing silence of varying length, so using it would charge that silence to
the provider. We store VAD speech bounds per utterance in a sidecar next to the manifest:

    uv run python -m harness.vad --manifest data/manifests/x.jsonl --data-root data/raw
    -> data/manifests/x.speech.jsonl (one SpeechSpan per line, sorted by utt_id)

Model: `silero_vad.onnx` from the pinned `silero-vad` wheel, fetched by
`data/fetch_silero_vad.py` into `data/cache/` (the package itself hard-requires torch, so it is
not a dependency). Run with onnxruntime, 512-sample windows (32 ms) at 16 kHz, 256 at 8 kHz,
each prefixed with the previous window's last 64 (32) samples as context, as Silero's own
wrapper does.

Bounds are offline: the whole clip's probabilities are known, so the end is the end of the last
speech window, with no min-silence wait. Resolution is one window (32 ms). The pure logic
(`segments`, `speech_bounds`) is tested exactly on hand-made probability sequences.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from harness.audio import AudioClip, load_clip
from harness.datasets.manifest import UTT_ID_PATTERN, Utterance, read_manifest

VAD_PACKAGE = "silero-vad==6.2.3"
MODEL_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "cache" / "silero_vad" / ("silero_vad.onnx")
)
# sample rate -> (window samples, context samples), as in Silero's OnnxWrapper
_WINDOWS = {16000: (512, 64), 8000: (256, 32)}
LOW_COVERAGE = 0.30  # flag (not drop) clips where detected speech covers less than this


class VadError(RuntimeError):
    pass


@dataclass(frozen=True)
class VadParams:
    threshold: float = 0.5  # a window at or above this enters speech
    neg_threshold: float = 0.35  # below this leaves speech (hysteresis)
    min_speech_ms: int = 64  # segments shorter than this are dropped (clicks, breaths)
    min_silence_ms: int = 96  # gaps shorter than this are merged into one segment

    def __post_init__(self) -> None:
        if not 0 < self.neg_threshold <= self.threshold < 1:
            raise ValueError("need 0 < neg_threshold <= threshold < 1")
        if self.min_speech_ms < 0 or self.min_silence_ms < 0:
            raise ValueError("durations must be >= 0")


DEFAULT_PARAMS = VadParams()


@dataclass(frozen=True)
class Bounds:
    start_ms: int
    end_ms: int
    coverage: float  # speech ms / clip ms


def window_ms(sample_rate: int) -> float:
    if sample_rate not in _WINDOWS:
        raise VadError(f"Silero VAD needs 16000 or 8000 Hz audio, got {sample_rate}")
    return 1000 * _WINDOWS[sample_rate][0] / sample_rate


def segments(
    probs: Sequence[float], win_ms: float, params: VadParams = DEFAULT_PARAMS
) -> list[tuple[int, int]]:
    """Speech segments as [start, end) window indices.

    Enter at p >= threshold, leave at p < neg_threshold; merge gaps shorter than
    min_silence_ms, then drop segments shorter than min_speech_ms.
    """
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for i, p in enumerate(probs):
        if start is None and p >= params.threshold:
            start = i
        elif start is not None and p < params.neg_threshold:
            raw.append((start, i))
            start = None
    if start is not None:
        raw.append((start, len(probs)))
    merged: list[tuple[int, int]] = []
    for s, e in raw:
        if merged and (s - merged[-1][1]) * win_ms < params.min_silence_ms:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [(s, e) for s, e in merged if (e - s) * win_ms >= params.min_speech_ms]


def speech_bounds(
    probs: Sequence[float], win_ms: float, params: VadParams = DEFAULT_PARAMS
) -> Bounds | None:
    """First speech start and last speech end in ms (window resolution), or None."""
    segs = segments(probs, win_ms, params)
    if not segs:
        return None
    total = len(probs) * win_ms
    speech = sum(e - s for s, e in segs) * win_ms
    return Bounds(round(segs[0][0] * win_ms), round(segs[-1][1] * win_ms), speech / total)


def vad_id(params: VadParams = DEFAULT_PARAMS) -> str:
    return (
        f"{VAD_PACKAGE}/onnx-{MODEL_SHA256[:12]}/thr{params.threshold}-{params.neg_threshold}"
        f"/minspeech{params.min_speech_ms}ms/minsilence{params.min_silence_ms}ms/offline"
    )


class SileroVad:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        if not model_path.exists():
            raise VadError(f"{model_path} missing: run `python data/fetch_silero_vad.py`")
        data = model_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
            raise VadError(f"{model_path}: sha256 does not match the pinned model")
        import onnxruntime as ort  # heavy import, only when a model is used

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(data, opts, providers=["CPUExecutionProvider"])

    def probabilities(self, clip: AudioClip) -> np.ndarray:
        """One speech probability per window; a final partial window is zero-padded."""
        window_ms(clip.sample_rate)  # validates the rate
        win, ctx = _WINDOWS[clip.sample_rate]
        audio = clip.samples.astype(np.float32) / 32768.0
        n = -(-len(audio) // win)
        audio = np.pad(audio, (0, n * win - len(audio)))
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, ctx), dtype=np.float32)
        sr = np.array(clip.sample_rate, dtype=np.int64)
        out = np.empty(n, dtype=np.float32)
        for i in range(n):
            x = np.concatenate([context, audio[None, i * win : (i + 1) * win]], axis=1)
            prob, state = self.session.run(None, {"input": x, "state": state, "sr": sr})
            out[i] = prob[0, 0]
            context = x[:, -ctx:]
        return out


# --- sidecar -------------------------------------------------------------------------------


class SpeechSpan(BaseModel):
    """VAD speech bounds for one utterance, in ms from the start of the clip."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    utt_id: str = Field(pattern=UTT_ID_PATTERN)
    speech_start_ms: int | None = Field(default=None, ge=0)  # None when no speech was found
    speech_end_ms: int | None = Field(default=None, ge=0)
    clip_ms: int = Field(gt=0)
    coverage: float = Field(ge=0, le=1)
    flags: tuple[str, ...] = ()  # "no_speech", "low_coverage"
    vad_id: str = Field(min_length=1)


def span_for(clip: AudioClip, probs: Sequence[float], params: VadParams) -> SpeechSpan:
    b = speech_bounds(probs, window_ms(clip.sample_rate), params)
    clip_ms = max(1, round(clip.duration_s * 1000))
    common: dict[str, Any] = {"utt_id": clip.utt_id, "clip_ms": clip_ms, "vad_id": vad_id(params)}
    if b is None:
        return SpeechSpan(coverage=0.0, flags=("no_speech",), **common)
    return SpeechSpan(
        speech_start_ms=b.start_ms,
        speech_end_ms=min(b.end_ms, clip_ms),  # the last window may be zero-padded
        coverage=min(1.0, round(b.coverage, 4)),
        flags=("low_coverage",) if b.coverage < LOW_COVERAGE else (),
        **common,
    )


def sidecar_path(manifest: Path) -> Path:
    return manifest.with_name(manifest.name.removesuffix(".jsonl") + ".speech.jsonl")


def write_speech(path: Path, spans: Iterable[SpeechSpan]) -> None:
    lines = [s.model_dump_json() for s in sorted(spans, key=lambda s: s.utt_id)]
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def read_speech(path: Path) -> dict[str, SpeechSpan]:
    spans: dict[str, SpeechSpan] = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            span = SpeechSpan.model_validate_json(line)
        except ValueError as e:
            raise VadError(f"{path}:{n}: {e}") from e
        if span.utt_id in spans:
            raise VadError(f"{path}:{n}: duplicate utt_id {span.utt_id}")
        spans[span.utt_id] = span
    return spans


@dataclass(frozen=True)
class Joined:
    spans: dict[str, SpeechSpan]  # utt_id -> span, for manifest utterances that have one
    missing: tuple[str, ...]  # manifest utterances with no span (never filled with zeros)
    unknown: tuple[str, ...]  # spans for utterances not in the manifest


def join_speech(manifest: Sequence[Utterance], spans: dict[str, SpeechSpan]) -> Joined:
    ids = [u.utt_id for u in manifest]
    known = set(ids)
    return Joined(
        spans={i: spans[i] for i in ids if i in spans},
        missing=tuple(i for i in ids if i not in spans),
        unknown=tuple(sorted(set(spans) - known)),
    )


# --- CLI -----------------------------------------------------------------------------------


def compute(
    manifest: Sequence[Utterance],
    data_root: Path,
    *,
    params: VadParams = DEFAULT_PARAMS,
    workers: int = 4,
    model_path: Path = MODEL_PATH,
) -> list[SpeechSpan]:
    vad = SileroVad(model_path)

    def one(utt: Utterance) -> SpeechSpan:
        clip = load_clip(utt, data_root)
        return span_for(clip, vad.probabilities(clip).tolist(), params)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, manifest))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Silero VAD speech bounds per utterance")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="default: <manifest>.speech.jsonl")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    manifest = read_manifest(args.manifest)
    spans = compute(manifest, args.data_root, workers=args.workers)
    out = args.out or sidecar_path(args.manifest)
    write_speech(out, spans)
    flags: dict[str, int] = {}
    for s in spans:
        for f in s.flags:
            flags[f] = flags.get(f, 0) + 1
    print(json.dumps({"out": out.as_posix(), "utterances": len(spans), "flags": flags}))


if __name__ == "__main__":
    main()
