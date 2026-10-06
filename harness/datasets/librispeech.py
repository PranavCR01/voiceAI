"""LibriSpeech loader: `*.trans.txt` transcripts -> utterance manifest.

LibriSpeech (openslr.org/12, CC BY 4.0): read audiobook speech, 16 kHz FLAC. The clean control
set is `test-clean` (2,620 utterances, 40 speakers). Layout:

    <root>/<subset>/<speaker>/<chapter>/<speaker>-<chapter>.trans.txt
    <root>/<subset>/<speaker>/<chapter>/<speaker>-<chapter>-<utt>.flac

Each transcript line is `<utt_key> <UPPERCASE TEXT>`. See data/README.md for fetching.

    uv run python -m harness.datasets.librispeech --root data/raw/LibriSpeech \\
        --data-root data/raw --out data/manifests/librispeech_test_clean.jsonl
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from harness.datasets.manifest import Utterance, write_manifest

DATASET = "librispeech"
LICENSE = "CC-BY-4.0"
LANGUAGE = "en"  # mostly North American readers; no region-specific date formats in the text
SAMPLE_RATE = 16_000
_KEY = re.compile(r"^(\d+)-(\d+)-(\d+)$")


def load(root: Path, *, data_root: Path, subset: str = "test-clean") -> list[Utterance]:
    """All utterances of one subset. `audio_path` is relative to `data_root`."""
    subset_dir = root / subset
    transcripts = sorted(subset_dir.glob("*/*/*.trans.txt"))
    if not transcripts:
        raise FileNotFoundError(f"no *.trans.txt files under {subset_dir}")
    utts = []
    for trans in transcripts:
        for lineno, line in enumerate(trans.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            key, _, text = line.partition(" ")
            m = _KEY.match(key)
            if m is None or not text.strip():
                raise ValueError(f"{trans}:{lineno}: expected '<spk>-<chapter>-<utt> TEXT'")
            speaker, chapter, _ = m.groups()
            if trans.parent != subset_dir / speaker / chapter:
                raise ValueError(f"{trans}:{lineno}: {key} does not match its directory")
            audio = trans.parent / f"{key}.flac"
            utts.append(
                Utterance(
                    utt_id=f"{DATASET}:{subset}:{key}",
                    dataset=DATASET,
                    subset=subset,
                    speaker_id=speaker,
                    audio_path=audio.relative_to(data_root).as_posix(),
                    ref_text=text.strip(),
                    sample_rate=SAMPLE_RATE,
                    license=LICENSE,
                    language=LANGUAGE,
                )
            )
    return utts


def main() -> None:
    parser = argparse.ArgumentParser(description="LibriSpeech transcripts -> manifest")
    parser.add_argument("--root", type=Path, required=True, help="the LibriSpeech/ directory")
    parser.add_argument("--data-root", type=Path, required=True, help="audio paths relative to")
    parser.add_argument("--subset", default="test-clean")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    utts = load(args.root.resolve(), data_root=args.data_root.resolve(), subset=args.subset)
    write_manifest(args.out, utts)
    print(f"{len(utts)} utterances, {len({u.speaker_id for u in utts})} speakers -> {args.out}")


if __name__ == "__main__":
    main()
