"""Text normalization applied to both reference and hypothesis before WER.

Wraps the Whisper EnglishTextNormalizer (the `whisper-normalizer` package, a standalone port of
OpenAI Whisper's normalizer). Its version is part of every result's metadata because changing it
changes WER.
"""

from __future__ import annotations

import re
import warnings
from functools import cache
from importlib.metadata import version

with warnings.catch_warnings():
    # The package ships a docstring with an invalid escape sequence; harmless.
    warnings.simplefilter("ignore", SyntaxWarning)
    from whisper_normalizer.english import EnglishTextNormalizer

NORMALIZER_ID = f"whisper-normalizer=={version('whisper-normalizer')}/EnglishTextNormalizer"

# Transcriber markup such as <UNSURE>word</UNSURE> or <UNIN/>. Paired tags are unwrapped (the
# transcriber's best guess is kept); self-closing tags are dropped. Utterances that should not be
# scored at all (e.g. containing <UNIN/>) are excluded by the dataset loader, not here.
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9_-]*\s*/?>")


@cache
def _normalizer() -> EnglishTextNormalizer:
    return EnglishTextNormalizer()


def strip_markup(text: str) -> str:
    return _TAG.sub(" ", text)


def normalize(text: str) -> str:
    """Markup-stripped, Whisper-normalized text with single spaces."""
    out: str = _normalizer()(strip_markup(text))
    return " ".join(out.split())
