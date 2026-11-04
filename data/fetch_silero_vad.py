"""Fetch the Silero VAD ONNX model (MIT) from its pinned PyPI wheel into data/cache/.

    python data/fetch_silero_vad.py        # idempotent; CI runs it before the tests

The `silero-vad` package hard-requires torch, so it is not a dependency: we download its wheel,
check the wheel's sha256, extract only `silero_vad/data/silero_vad.onnx`, check that file's
sha256, and run it with onnxruntime (harness/vad.py). Stdlib only, so it runs before `uv sync`.
Keep the pins in sync with harness/vad.py (MODEL_SHA256, VAD_PACKAGE).
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

WHEEL_URL = (
    "https://files.pythonhosted.org/packages/84/ef/"
    "9099037ed6f180ea33220178df4107112c0ce2bf5fb4d6f6ab19db2844ed/"
    "silero_vad-6.2.3-py3-none-any.whl"
)
WHEEL_SHA256 = "7b7f5436cfcb02fae583a05b512ea96467fd449fe54cb49a5e4f06c51a1e43b8"
MEMBER = "silero_vad/data/silero_vad.onnx"
MODEL_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
DEST = Path(__file__).resolve().parent / "cache" / "silero_vad" / "silero_vad.onnx"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(dest: Path = DEST) -> Path:
    if dest.exists() and _sha256(dest.read_bytes()) == MODEL_SHA256:
        return dest
    with urllib.request.urlopen(WHEEL_URL, timeout=120) as resp:  # noqa: S310 - pinned https URL
        wheel = resp.read()
    if _sha256(wheel) != WHEEL_SHA256:
        raise SystemExit(f"wheel sha256 mismatch: {_sha256(wheel)}")
    with zipfile.ZipFile(io.BytesIO(wheel)) as zf:
        model = zf.read(MEMBER)
    if _sha256(model) != MODEL_SHA256:
        raise SystemExit(f"model sha256 mismatch: {_sha256(model)}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(model)
    tmp.replace(dest)
    return dest


if __name__ == "__main__":
    print(f"silero_vad.onnx -> {fetch()}", file=sys.stderr)
