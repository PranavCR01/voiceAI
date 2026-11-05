"""Apply an augmentation recipe to a manifest: augmented WAVs plus a child manifest.

    uv run python -m harness.augment.run --manifest data/manifests/primock57.jsonl \\
        --data-root data/raw --recipe telephony_mulaw \\
        --out data/manifests/primock57.telephony_mulaw.jsonl

Audio goes to `<data-root>/augmented/<recipe>/` (never committed). Each child utterance has
`utt_id` `<parent>:<recipe>`, `parent_utt_id`, the same reference/speaker/language, and the full
step list (files, offsets, SNR, ffmpeg args, seeds), so the manifest alone reproduces the audio.
Feed the child manifest to the runner with its own `--results` directory: run ids default to the
config id, and a report takes one run per config.

The SNR region comes from the parent manifest's VAD sidecar (`<manifest>.speech.jsonl`, #15)
when it has the utterance, else the whole clip; each noise step records which.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.audio import AudioClip, load_clip, to_wav_bytes
from harness.augment.recipes import AugmentConfig, SpeechRegion, apply, load_config
from harness.datasets.manifest import Utterance, read_manifest, write_manifest
from harness.vad import SpeechSpan, read_speech, sidecar_path

DEFAULT_CONFIG = Path("configs/augment.yaml")
AUGMENTED_DIR = "augmented"


def speech_region(clip: AudioClip, span: SpeechSpan | None) -> SpeechRegion:
    if span is None or span.speech_start_ms is None or span.speech_end_ms is None:
        return SpeechRegion(0.0, clip.duration_s, "whole_clip")
    return SpeechRegion(span.speech_start_ms / 1000, span.speech_end_ms / 1000, "vad")


def audio_relpath(recipe: str, utt_id: str) -> str:
    return f"{AUGMENTED_DIR}/{recipe}/{utt_id.replace(':', '__')}.wav"


def augment_one(
    utt: Utterance,
    *,
    recipe: str,
    config: AugmentConfig,
    data_root: Path,
    seed: int,
    span: SpeechSpan | None,
) -> Utterance:
    clip = load_clip(utt, data_root)
    out = apply(
        config.recipe(recipe),
        clip.samples,
        clip.sample_rate,
        speech_region(clip, span),
        utt_id=utt.utt_id,
        run_seed=seed,
        data_root=data_root,
        sources=config.sources,
    )
    rel = audio_relpath(recipe, utt.utt_id)
    path = data_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        to_wav_bytes(AudioClip(out.samples, out.sample_rate, utt.utt_id, out.sample_rate))
    )
    return utt.model_copy(
        update={
            "utt_id": f"{utt.utt_id}:{recipe}",
            "parent_utt_id": utt.utt_id,
            "audio_path": rel,
            "channel": None,
            "start_s": None,
            "end_s": None,
            "sample_rate": out.sample_rate,
            "augmentation": out.steps,
        }
    )


def augment_manifest(
    utts: Sequence[Utterance],
    *,
    recipe: str,
    config: AugmentConfig,
    data_root: Path,
    seed: int,
    spans: dict[str, SpeechSpan],
    limit: int | None = None,
    include_excluded: bool = False,
    workers: int = 1,
) -> list[Utterance]:
    """`workers` > 1 runs utterances on a thread pool (the work is mostly ffmpeg subprocesses).
    Output is identical for any worker count: every step's seed depends only on the utterance."""
    config.recipe(recipe)  # fail on an unknown recipe before any work
    todo = [u for u in utts if include_excluded or u.exclude_reason is None]
    if any(u.augmentation for u in todo):
        raise ValueError("manifest already contains augmented utterances; augment the parents")
    todo = todo[:limit] if limit is not None else todo
    if workers < 1:
        raise ValueError("workers must be >= 1")

    def one(u: Utterance) -> Utterance:
        return augment_one(
            u,
            recipe=recipe,
            config=config,
            data_root=data_root,
            seed=seed,
            span=spans.get(u.utt_id),
        )

    if workers == 1:
        return [one(u) for u in todo]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, todo))


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", type=Path, required=True, help="child manifest to write")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, help="only the first N (scorable) utterances")
    ap.add_argument("--include-excluded", action="store_true")
    ap.add_argument(
        "--workers", type=int, default=os.cpu_count() or 1, help="parallel utterances (threads)"
    )
    args = ap.parse_args(argv)

    side = sidecar_path(args.manifest)
    spans = read_speech(side) if side.exists() else {}
    children = augment_manifest(
        read_manifest(args.manifest),
        recipe=args.recipe,
        config=load_config(args.config),
        data_root=args.data_root,
        seed=args.seed,
        spans=spans,
        limit=args.limit,
        include_excluded=args.include_excluded,
        workers=args.workers,
    )
    write_manifest(args.out, children)
    vad = sum(1 for c in children for s in c.augmentation if s.params.get("snr_region") == "vad")
    audio_dir = args.data_root / AUGMENTED_DIR / args.recipe
    print(
        f"{args.recipe}: {len(children)} utterances -> {args.out} (audio under {audio_dir};"
        f" noise steps on the VAD region: {vad})"
    )


if __name__ == "__main__":
    main()
