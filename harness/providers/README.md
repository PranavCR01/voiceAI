# STT providers

- `registry.py` + `configs/providers.yaml`: pinned configurations (see the file header).
- `runner.py`: batch runner (resumable, retries, raw responses kept).
- `*_batch.py`: batch adapters. Plain `httpx`, no vendor SDKs, so every request is visible.
- `http.py`: shared error classification. HTTP 408/409/425/429/5xx and transport errors (timeouts, dropped connections) are retryable; everything else is permanent.

## VERIFY before the first live run

The adapters were written from recollection of each API because vendor docs are blocked from the cloud environment. Check each item against current docs, fix code and fixtures, then set `verify: false` in the registry and record the doc URL and date in `docs/RESEARCH.md`.

**Deepgram** (`deepgram_batch.py`)
- [ ] `POST https://api.deepgram.com/v1/listen`, header `Authorization: Token <key>`, raw audio body with `Content-Type: audio/wav`.
- [ ] Query params `model=nova-3`, `smart_format`, `punctuate`, `language`; Nova-3 keyterm prompting as a repeated `keyterm` param (and whether it costs extra).
- [ ] Transcript at `results.channels[0].alternatives[0].transcript`.

**AssemblyAI** (`assemblyai_batch.py`)
- [ ] `POST /v2/upload` (raw bytes, header `authorization: <key>`) → `upload_url`.
- [ ] `POST /v2/transcript` with `audio_url`, `speech_model` (is `universal` the right current id?), `format_text`, `punctuate`, `language_code`, keyterms as `keyterms_prompt` (name and whether it's allowed for the chosen model).
- [ ] Poll `GET /v2/transcript/{id}`; statuses `queued` / `processing` / `completed` / `error`; text in `text`.
- [ ] Batch price for the chosen model (registry has none).

**ElevenLabs** (`elevenlabs_batch.py`)
- [ ] `POST https://api.elevenlabs.io/v1/speech-to-text`, header `xi-api-key`, multipart with `file` and `model_id` (`scribe_v2`?).
- [ ] `tag_audio_events=false` still the way to suppress "(laughter)"-style tags.
- [ ] Keyterm field name and format for Scribe v2 (sent here as repeated `keyterms` fields), and its add-on price.
- [ ] Text at top-level `text`.

## First live run (owner's machine)

```bash
cp .env.example .env   # fill DEEPGRAM_API_KEY etc.; never commit .env
set -a; source .env; set +a
./data/fetch_primock57.sh            # audio needs git-lfs (~1.1 GB)

# 1. Trial: 5 utterances, check the raw responses look like the fixtures
uv run python -m harness.providers.runner --config deepgram_nova3_batch \
    --manifest data/manifests/primock57.jsonl --data-root data/raw --results results/ --limit 5

# 2. Full patient-side runs for at least two configs (resumable: re-run the same command after a crash)
uv run python -m harness.providers.runner --config deepgram_nova3_batch \
    --manifest data/manifests/primock57.jsonl --data-root data/raw --results results/
uv run python -m harness.providers.runner --config elevenlabs_scribe_v2_batch \
    --manifest data/manifests/primock57.jsonl --data-root data/raw --results results/
uv run python -m harness.providers.runner --config deepgram_nova3_batch_keyterms \
    --profile configs/profiles/healthcare_intake.yaml \
    --manifest data/manifests/primock57.jsonl --data-root data/raw --results results/

# 3. Report
uv run python -m harness.report --results results/ --manifest data/manifests/primock57.jsonl \
    --profile configs/profiles/healthcare_intake.yaml --out reports/generated/primock57_batch.md
```

Then: replace `tests/fixtures/providers/*` with scrubbed captured responses, commit the report (text only; `results/` stays local), and add a DECISIONS entry for anything surprising. Cost check before step 2: PriMock57 scorable audio is about 5.5 h (both roles) per config.
