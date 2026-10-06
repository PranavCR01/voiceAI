# Data

The repo holds manifests (`data/manifests/`), lexicons and fetch scripts only. Audio lives under `data/raw/` (gitignored), and manifest `audio_path`s are relative to that data root.

Fetch on your own machine. The cloud dev environment's network policy blocks these hosts (openslr.org, api.fda.gov), and Common Voice needs a logged-in acceptance of terms.

## PriMock57 (CC BY 4.0)
```
./data/fetch_primock57.sh              # needs git-lfs; SKIP_AUDIO=1 for transcripts only
uv run python -m harness.datasets.primock57 --root data/raw/primock57 --out data/manifests/primock57.jsonl
```
The manifest is already committed; rebuilding it must give identical bytes.

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
