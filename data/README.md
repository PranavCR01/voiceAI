# Data

The repo holds manifests (`data/manifests/`), lexicons and fetch scripts only. Audio lives under `data/raw/` (gitignored), and manifest `audio_path`s are relative to that data root.

Fetch on your own machine. The cloud dev environment's network policy blocks these hosts (openslr.org, api.fda.gov), and Common Voice needs a logged-in acceptance of terms.

## PriMock57 (CC BY 4.0)
```
./data/fetch_primock57.sh              # needs git-lfs; SKIP_AUDIO=1 for transcripts only
uv run python -m harness.datasets.primock57 --root data/raw/primock57 --out data/manifests/primock57.jsonl
```
The manifest is already committed; rebuilding it must give identical bytes. In a cloud session `git lfs pull` is refused by the git proxy; the script then fetches the audio from GitHub's media host and checks each file's sha256.

## Speech bounds sidecars (Silero VAD)
```
python data/fetch_silero_vad.py        # pinned silero-vad wheel -> data/cache/ (sha256-checked)
uv run python -m harness.vad --manifest data/manifests/primock57.jsonl --data-root data/raw
```
Writes `data/manifests/<name>.speech.jsonl` (`SpeechSpan` per utterance: speech start/end in ms from the clip start, coverage, flags `no_speech`/`low_coverage`, `vad_id`). Needs the audio; the PriMock57 sidecar is committed. Join with `harness.vad.join_speech`, which reports missing utterances rather than filling zeros. Why VAD bounds and their known bias: `docs/DECISIONS.md` (2026-11-04, VAD bounds).

## LibriSpeech test-clean (CC BY 4.0)
1. Download `test-clean.tar.gz` (~346 MB) from https://www.openslr.org/12 and check it against the md5 listed on that page.
2. `tar -xzf test-clean.tar.gz -C data/raw` (creates `data/raw/LibriSpeech/test-clean/...`).
3. Build the manifest:
```
uv run python -m harness.datasets.librispeech --root data/raw/LibriSpeech --data-root data/raw \
    --out data/manifests/librispeech_test_clean.jsonl
```
Expect 2,620 utterances from 40 speakers.

## Common Voice English (CC0)
Do not script the download: Mozilla requires accepting its terms per download.
1. Get the English release from Mozilla Common Voice (https://commonvoice.mozilla.org/datasets; newer releases may be distributed through the Mozilla Data Collective). Note the exact release name (e.g. `cv-corpus-21.0-2025-03-14`).
2. Extract so that `data/raw/<release>/en/test.tsv` and `data/raw/<release>/en/clips/` exist.
3. Build an accent-stratified sample from the held-out test split:
```
uv run python -m harness.datasets.common_voice --root data/raw/<release>/en --data-root data/raw \
    --release <release> -n 400 --seed 0 --out data/manifests/common_voice_en.jsonl
```
Defaults: 400 clips, at most 10 per speaker, accents with under 5 clips pooled into one "other" stratum. Record the release, seed and flags in `docs/RESEARCH.md` when you commit a manifest.

## Synthetic caller scripts (#17)
```
uv run python -m harness.synthetic.scripts --profile configs/profiles/healthcare_intake.yaml \
    --out data/manifests/synthetic_healthcare_intake.jsonl [--voice vendor:voice_id:en-US ...]
```
Seeded and deterministic. Writes a manifest of `synthetic: true` utterances (spoken-form references, `speaker_id` = TTS voice, `audio_path` where synthesis will write) and `<name>.entities.jsonl` (inserted entities and disfluency per utterance). The committed manifests use 10 placeholder voices (`tts_a.voice1` … `tts_b.voice5`); regenerate with real voice ids before synthesizing (owner's machine). Phone numbers are from fiction-reserved ranges.
