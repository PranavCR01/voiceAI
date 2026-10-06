# CLAUDE.md

Voice AI STT bake-off harness with a healthcare intake voice agent as its in-pipeline scenario.
Read `docs/PROJECT.md` for scope and `docs/DECISIONS.md` before changing anything it covers.

## Stack
- Python 3.12, asyncio. Package manager: `uv`. Dependencies pinned in `pyproject.toml` + `uv.lock`.
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
2. Never use an LLM anywhere in scoring or in the recommender. Both must be deterministic.
3. Tests run on recorded fixtures (small JSON/text files in `tests/fixtures/`). No test may call a live provider API or need an API key.
4. Augmentation is seeded; the manifest records seed, noise file, SNR and codec chain.
5. Pin provider model IDs in `configs/providers.yaml`. Store raw provider responses next to every result.
6. Hand-written modules — do not generate or rewrite these without explicit instruction in the issue:
   `agent/turn_controller/` and the raw-WebSocket STT client in `harness/providers/` (whichever one is marked `# hand-written`).
7. Prices, model names and dataset licenses are perishable. Anything user-facing cites `docs/RESEARCH.md` and its date.
8. Every PR updates the docs it invalidates. New decisions go in `docs/DECISIONS.md` (dated, with the reason and what it replaced).

## Layout
```
configs/      providers.yaml, scenarios/*.yaml, augment.yaml
data/         manifests + fetch scripts only
harness/      datasets/ augment/ providers/ metrics/ load/
agent/        pipeline.py, turn_controller/, tools/
recommender/  deterministic constraint filter + ranking
reports/      templates + generated example memos
tests/        unit tests, fixtures, recorded event traces
docs/         PROJECT.md, DECISIONS.md, RESEARCH.md
```

## Where work runs
- Cloud sessions: pure code with fixture tests (scaffold, loaders, metrics, stats, recommender, reports).
- Owner's machine: anything needing live APIs, a mic/speakers, latency measurement, Twilio.
