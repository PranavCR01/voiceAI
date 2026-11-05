"""Read API keys from `.env` into the environment (no python-dotenv dependency).

The runners call `load_env()` before reading keys, so `set -a; source .env` (bash) is no longer
needed and the same command works in PowerShell. Rules: `KEY=value` lines, optional `export `,
`#` comments, optional matching single/double quotes. Line endings are stripped, including the
`\\r` of a file saved with CRLF on Windows (a key with a trailing `\\r` is rejected by every
provider as an invalid credential). Variables already set in the environment win.
"""

from __future__ import annotations

import os
import re
from collections.abc import MutableMapping
from pathlib import Path

_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():  # splits on \r\n, \n and lone \r
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if m is None:
            continue
        key, value = m.group(1), m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        out[key] = value
    return out


def load_env(
    path: Path = Path(".env"), environ: MutableMapping[str, str] | None = None
) -> list[str]:
    """Set unset, non-empty keys from `path` (if it exists); returns the names that were set."""
    env = os.environ if environ is None else environ
    if not path.exists():
        return []
    # utf-8-sig: Notepad may save a byte-order mark, which would otherwise prefix the first key
    values = parse_env(path.read_text(encoding="utf-8-sig"))
    loaded = [k for k, v in values.items() if v and not env.get(k)]
    for k in loaded:
        env[k] = values[k]
    return loaded
