# CLAUDE.md

Voice-stack recommender: takes a use-case profile (constraints, domain terms, optional customer audio) and recommends the full cascaded stack (STT, turn detection, LLM, TTS, and their settings), with confidence intervals. Healthcare intake is the first reference use case and the demo agent — nothing outside `configs/profiles/healthcare_*` and `data/lexicons/` may assume healthcare.
Read `docs/PROJECT.md` for scope and `docs/DECISIONS.md` before changing anything it covers.

## Stack
- Python 3.12 (`.python-version`), asyncio. Package manager: `uv`. Exact versions locked in `uv.lock` (committed); CI runs `uv sync --locked`, so update the lock with `uv lock` when changing deps.
- Scoring: jiwer, Whisper `EnglishTextNormalizer` (pinned), NumPy/SciPy.
- Agent (milestone 3+): Pipecat (pinned version, never float), Silero VAD, Smart Turn v3, ElevenLabs TTS.
- Results: Parquet. Reports: Jinja2 → Markdown/HTML.

## Commands
- Install: `uv sync`
- Test: `uv run pytest`
- Lint/format: `uv run ruff check . && uv run ruff format --check .`
- Types: `uv run mypy harness recommender`

## Hard rules
1. Never commit audio (`*.wav`, `*.mp3`, `*.flac`, `*.webm`, `*.opus`, `*.ogg`). Commit manifests, recipes and scripts that fetch data.
2. Never use an LLM as a judge anywhere in scoring or in the recommender. LLMs are systems under test only; scoring is rule-based and deterministic.
3. Tests run on recorded fixtures (small JSON/text files in `tests/fixtures/`). No test may call a live provider API or need an API key.
4. Augmentation is seeded; the manifest records seed, noise file, SNR and codec chain.
5. Pin provider model IDs in `configs/providers.yaml`. Store raw provider responses next to every result.
6. Hand-written modules — do not generate or rewrite these without explicit instruction in the issue:
   `agent/turn_controller/` and the raw-WebSocket STT client in `harness/providers/` (whichever one is marked `# hand-written`).
7. Prices, model names and dataset licenses are perishable. Anything user-facing cites `docs/RESEARCH.md` and its date.
8. Every PR updates the docs it invalidates. New decisions go in `docs/DECISIONS.md` (dated, with the reason and what it replaced).

## Layout
```
configs/      providers.yaml, profiles/*.yaml (use case + constraints), augment.yaml
data/         manifests + fetch scripts only
harness/      datasets/ augment/ providers/ metrics/ load/
agent/        pipeline.py, turn_controller/, tools/
recommender/  deterministic constraint filter + ranking
reports/      templates + generated example memos
tests/        unit tests, fixtures, recorded event traces
docs/         PROJECT.md, DECISIONS.md, RESEARCH.md
```

## Git
One branch + PR per issue, targeting `main`. Owner squash-merges.

## Where work runs
- Cloud sessions: pure code with fixture tests (scaffold, loaders, metrics, stats, recommender, reports).
- Owner's machine: anything needing live APIs, a mic/speakers, latency measurement, Twilio.
