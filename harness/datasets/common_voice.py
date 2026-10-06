"""Common Voice (English) loader: release TSV -> accent-stratified utterance manifest.

Mozilla Common Voice (CC0): crowd-recorded read sentences, MP3 clips, many accents. Downloading
requires accepting Mozilla's terms, so it is never scripted here (see data/README.md).

Which rows: the release's `test.tsv` by default (held-out speakers). Which accent: the `accents`
column (releases since v8) or `accent` (older); blank means "unspecified".

Sampling (deterministic for a seed): rows are grouped by accent; within each accent they are
shuffled; then accents take turns contributing one clip each (round robin, accents in sorted
order) until `n` clips are chosen. The accent field is free text since v8, so the real data has
hundreds of one-off strings; accents with fewer than `min_stratum` clips are pooled into one
"other" group that takes a single turn, so they don't crowd out the common accents. A speaker
contributes at most `per_speaker_cap` clips, so no voice dominates. Round robin spreads clips
across accents instead of mirroring Common Voice's heavy skew toward a few accents; small
strata are exhausted early and stop contributing.

    uv run python -m harness.datasets.common_voice --root data/raw/cv-corpus-XX/en \\
        --data-root data/raw --release cv-corpus-XX --out data/manifests/common_voice_en.jsonl
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from harness.datasets.manifest import Utterance, write_manifest

DATASET = "common_voice"
LICENSE = "CC0-1.0"
LANGUAGE = "en"  # accents vary; no single regional date convention
# Common Voice MP3 clips are distributed at 48 kHz; confirm when decoding (resampling happens
# in augmentation anyway).
SAMPLE_RATE = 48_000
UNSPECIFIED = "unspecified"
OTHER = "other (rare accents)"


@dataclass(frozen=True)
class Clip:
    client_id: str
    path: str
    sentence: str
    accent: str


def _accent(row: dict[str, str]) -> str:
    raw = (row.get("accents") or row.get("accent") or "").strip()
    return " ".join(raw.lower().split()) or UNSPECIFIED


def read_tsv(tsv: Path) -> list[Clip]:
    with tsv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        missing = {"client_id", "path", "sentence"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{tsv}: missing columns {sorted(missing)}")
        return [
            Clip(row["client_id"], row["path"], row["sentence"].strip(), _accent(row))
            for row in reader
            if row["sentence"] and row["sentence"].strip()
        ]


def sample(
    clips: list[Clip],
    *,
    n: int,
    seed: int,
    per_speaker_cap: int = 10,
    min_stratum: int = 5,
) -> list[Clip]:
    """Accent round-robin sample of up to `n` clips, at most `per_speaker_cap` per speaker.

    Accents with fewer than `min_stratum` clips share one stratum (`OTHER`).
    """
    if n < 1 or per_speaker_cap < 1 or min_stratum < 1:
        raise ValueError("n, per_speaker_cap and min_stratum must be >= 1")
    rng = random.Random(seed)
    sizes = Counter(c.accent for c in clips)
    queues: dict[str, list[Clip]] = defaultdict(list)
    for clip in sorted(clips, key=lambda c: c.path):  # input order must not matter
        stratum = clip.accent if sizes[clip.accent] >= min_stratum else OTHER
        queues[stratum].append(clip)
    for accent in sorted(queues):
        rng.shuffle(queues[accent])
    per_speaker: Counter[str] = Counter()
    chosen: list[Clip] = []
    active = sorted(queues)
    while len(chosen) < n and active:
        still_active = []
        for accent in active:
            queue = queues[accent]
            while queue and per_speaker[queue[-1].client_id] >= per_speaker_cap:
                queue.pop()  # this speaker is full; skip their remaining clips
            if not queue:
                continue
            clip = queue.pop()
            chosen.append(clip)
            per_speaker[clip.client_id] += 1
            still_active.append(accent)
            if len(chosen) == n:
                break
        active = still_active
    return chosen


def load(
    root: Path,
    *,
    data_root: Path,
    release: str,
    split: str = "test",
    n: int = 400,
    seed: int = 0,
    per_speaker_cap: int = 10,
    min_stratum: int = 5,
) -> list[Utterance]:
    """Sampled utterances from `<root>/<split>.tsv`; audio under `<root>/clips/`."""
    chosen = sample(
        read_tsv(root / f"{split}.tsv"),
        n=n,
        seed=seed,
        per_speaker_cap=per_speaker_cap,
        min_stratum=min_stratum,
    )
    return [
        Utterance(
            utt_id=f"{DATASET}:{release}:{Path(c.path).stem}",
            dataset=DATASET,
            subset=f"{release}/{split}",
            # client_id is a long hash; it is the only speaker identity Common Voice provides.
            speaker_id=c.client_id,
            audio_path=(root / "clips" / c.path).relative_to(data_root).as_posix(),
            ref_text=c.sentence,
            sample_rate=SAMPLE_RATE,
            license=LICENSE,
            language=LANGUAGE,
        )
        for c in chosen
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Common Voice TSV -> sampled manifest")
    parser.add_argument("--root", type=Path, required=True, help="the release's en/ directory")
    parser.add_argument("--data-root", type=Path, required=True, help="audio paths relative to")
    parser.add_argument("--release", required=True, help="e.g. cv-corpus-21.0-2025-03-14")
    parser.add_argument("--split", default="test")
    parser.add_argument("-n", type=int, default=400)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--per-speaker-cap", type=int, default=10)
    parser.add_argument("--min-stratum", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    utts = load(
        args.root.resolve(),
        data_root=args.data_root.resolve(),
        release=args.release,
        split=args.split,
        n=args.n,
        seed=args.seed,
        per_speaker_cap=args.per_speaker_cap,
        min_stratum=args.min_stratum,
    )
    write_manifest(args.out, utts)
    print(f"{len(utts)} utterances, {len({u.speaker_id for u in utts})} speakers -> {args.out}")


if __name__ == "__main__":
    main()
