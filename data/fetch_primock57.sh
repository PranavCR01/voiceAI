#!/usr/bin/env bash
# Fetch PriMock57 (CC BY 4.0) at the pinned commit into data/raw/primock57.
# Needs git-lfs for the audio (~1.1 GB). Set SKIP_AUDIO=1 to fetch transcripts and notes only.
# Then build the manifest:
#   uv run python -m harness.datasets.primock57 --root data/raw/primock57 \
#       --out data/manifests/primock57.jsonl
set -euo pipefail

COMMIT=cd2ac707ad03cb4d2531f4ec6b90c659bf4357c5  # keep in sync with harness/datasets/primock57.py
DEST="$(cd "$(dirname "$0")" && pwd)/raw/primock57"

if [ -d "$DEST/.git" ]; then
  echo "$DEST already exists; delete it to re-fetch." >&2
  exit 1
fi
if [ "${SKIP_AUDIO:-0}" = 1 ]; then
  export GIT_LFS_SKIP_SMUDGE=1
elif ! git lfs version >/dev/null 2>&1; then
  echo "git-lfs is required for the audio (or set SKIP_AUDIO=1)." >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
git clone https://github.com/babylonhealth/primock57.git "$DEST"
git -C "$DEST" checkout --quiet "$COMMIT"
if [ "${SKIP_AUDIO:-0}" != 1 ]; then
  git -C "$DEST" lfs pull
fi
echo "PriMock57 at $COMMIT -> $DEST"
