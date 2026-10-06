"""PriMock57 loader: TextGrid transcripts -> utterance manifest.

PriMock57 (github.com/babylonhealth/primock57, CC BY 4.0): 57 mock GP consultations, doctor and
patient recorded to separate 16 kHz mono WAV files, transcribed per utterance in Praat
TextGrids. Fetch with data/fetch_primock57.sh, then:

    uv run python -m harness.datasets.primock57 \\
        --root data/raw/primock57 --out data/manifests/primock57.jsonl

Audio paths in the manifest are relative to the data root (`data/raw`), e.g.
`primock57/audio/day1_consultation01_patient.wav`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from harness.datasets.manifest import Utterance, write_manifest
from harness.datasets.textgrid import read_textgrid

DATASET = "primock57"
LICENSE = "CC-BY-4.0"
LANGUAGE = "en-GB"  # UK clinicians and actors: numeric dates are day-first
SAMPLE_RATE = 16_000
PINNED_COMMIT = "cd2ac707ad03cb4d2531f4ec6b90c659bf4357c5"
MIN_DURATION_S = 0.3

# Transcriber misspellings of drug names, found while building the medication lexicon.
# Corrected so a provider that spells the drug right isn't scored as wrong; the original text is
# kept in `ref_text_original`.
CORRECTIONS: dict[str, str] = {
    "paracetemol": "paracetamol",
    "paracetmol": "paracetamol",
    "lisonopril": "lisinopril",
    "clinil": "clenil",
    "stemitil": "stemetil",
    "thyrocsin": "thyroxine",
    "fexofenatidine": "fexofenadine",
}
_CORRECTION = re.compile(r"\b(" + "|".join(map(re.escape, CORRECTIONS)) + r")\b", re.IGNORECASE)

# Self-closing tags marking speech the transcriber could not write down. The reference is
# missing words there, so a provider that transcribes them would be charged insertions.
_EXCLUDE_TAGS = {"<UNIN/>": "unintelligible", "<INAUDIBLE_SPEECH/>": "inaudible"}

_FILENAME = re.compile(r"^(day\d+_consultation\d+)_(doctor|patient)\.TextGrid$")


def correct(text: str) -> str:
    return _CORRECTION.sub(lambda m: CORRECTIONS[m.group(1).lower()], text)


def exclude_reason(text: str, duration_s: float) -> str | None:
    for tag, reason in _EXCLUDE_TAGS.items():
        if tag in text:
            return reason
    if duration_s < MIN_DURATION_S:
        return "too_short"
    return None


def load_transcript(path: Path) -> list[Utterance]:
    m = _FILENAME.match(path.name)
    if m is None:
        raise ValueError(f"unexpected PriMock57 transcript name: {path.name}")
    consultation, role = m.groups()
    tiers = read_textgrid(path)
    if len(tiers) != 1:
        raise ValueError(f"{path}: expected one interval tier, found {len(tiers)}")
    utts = []
    for iv in tiers[0].intervals:
        raw = iv.text.strip()
        if not raw:
            continue
        fixed = correct(raw)
        utts.append(
            Utterance(
                utt_id=f"{DATASET}:{consultation}:{role}:{iv.index:04d}",
                dataset=DATASET,
                subset=role,
                # Clinician identities are not published, so a doctor is only known per
                # consultation; the 57 patients are distinct actors.
                speaker_id=f"{consultation}_{role}",
                audio_path=f"{DATASET}/audio/{consultation}_{role}.wav",
                start_s=iv.xmin,
                end_s=iv.xmax,
                ref_text=fixed,
                sample_rate=SAMPLE_RATE,
                license=LICENSE,
                exclude_reason=exclude_reason(raw, iv.xmax - iv.xmin),
                language=LANGUAGE,
                ref_text_original=raw if fixed != raw else None,
            )
        )
    return utts


def load(root: Path) -> list[Utterance]:
    """All utterances from `root/transcripts/*.TextGrid`, both roles."""
    paths = sorted((root / "transcripts").glob("*.TextGrid"))
    if not paths:
        raise FileNotFoundError(f"no TextGrid files under {root / 'transcripts'}")
    return [u for p in paths for u in load_transcript(p)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", type=Path, required=True, help="PriMock57 checkout")
    parser.add_argument("--out", type=Path, required=True, help="manifest JSONL to write")
    args = parser.parse_args()
    utts = load(args.root)
    write_manifest(args.out, utts)
    excluded = sum(u.exclude_reason is not None for u in utts)
    corrected = sum(u.ref_text_original is not None for u in utts)
    print(f"{len(utts)} utterances ({excluded} excluded, {corrected} corrected) -> {args.out}")


if __name__ == "__main__":
    main()
