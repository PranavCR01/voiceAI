#!/usr/bin/env bash
# Fetch augmentation sources (#16) into data/raw/augment/ (gitignored):
#   OpenSLR SLR28 "rirs_noises" (Apache 2.0, https://www.openslr.org/28/): simulated and real room
#   impulse responses, isotropic noises, and point-source noises extracted from MUSAN.
# configs/augment.yaml points at RIRS_NOISES/pointsource_noises and RIRS_NOISES/simulated_rirs.
# The archive's sha256 is pinned: a changed archive would change which file a seed picks.
set -euo pipefail
URL=https://www.openslr.org/resources/28/rirs_noises.zip
SHA256=3b50cfde915b3984738169b4beb341e9f6b8062ae4c2076146c5db71c2c05dc7  # recorded on first fetch, 2026-11-05
DEST="$(cd "$(dirname "$0")" && pwd)/raw/augment"
mkdir -p "$DEST"
ZIP="$DEST/rirs_noises.zip"
if [ -d "$DEST/RIRS_NOISES" ]; then
  echo "$DEST/RIRS_NOISES already exists; delete it to re-fetch." >&2
  exit 1
fi
if [ ! -f "$ZIP" ]; then
  curl -fL --retry 3 -o "$ZIP.part" "$URL"
  mv "$ZIP.part" "$ZIP"
fi
echo "$SHA256  $ZIP" | sha256sum -c -
unzip -q "$ZIP" -d "$DEST"
rm "$ZIP"
echo "SLR28 -> $DEST/RIRS_NOISES"
