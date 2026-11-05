# STT providers

- `registry.py` + `configs/providers.yaml`: pinned configurations (see the file header).
- `runner.py`: batch runner (resumable, retries, raw responses kept).
- `*_batch.py`: batch adapters. Plain `httpx`, no vendor SDKs, so every request is visible.
- `http.py`: shared error classification. HTTP 408/409/425/429/5xx and transport errors (timeouts, dropped connections) are retryable; everything else is permanent.

## VERIFY before the first live run

The adapters were first written from recollection of each API, because vendor docs were blocked from the cloud environment. Check each item against current docs, fix code and fixtures, then set `verify: false` in the registry and record the doc URL and date in `docs/RESEARCH.md`. As of 2026-11-05 the ElevenLabs and AssemblyAI docs are reachable from cloud sessions. `api.elevenlabs.io` is reachable too (ElevenLabs was run live); `api.assemblyai.com` is still refused (proxy 403), so AssemblyAI is checked against docs only.

**Deepgram** (`deepgram_batch.py`) — checked against the live API on 2026-11-04 (docs host still blocked from the cloud environment, so by probing, not reading docs; details in `docs/RESEARCH.md`)
- [x] `POST https://api.deepgram.com/v1/listen`, header `Authorization: Token <key>`, raw audio body with `Content-Type: audio/wav`. (200 with a real key; a bad key gives 401 `INVALID_AUTH`.)
- [x] Query params `model=nova-3`, `smart_format`, `punctuate`, `language`; Nova-3 keyterm prompting as a repeated `keyterm` param. (`keyterm` is recognized: on `nova-2` it is rejected with 400 "only supported for Nova-3 and Flux"; an unknown `language` is a 400.) Unknown params are **silently ignored**, so a misspelled setting would not fail on Deepgram's side; `check_settings` is the only guard.
- [x] Keyterm prompting costs extra: +$0.0013/min on Nova-3 pre-recorded ($0.0043/min), i.e. +30% (deepgram.com/pricing, 2026-11-05). Keyterms are capped at 500 tokens per request (developers.deepgram.com/docs/keyterm).
- [x] Transcript at `results.channels[0].alternatives[0].transcript`.

**AssemblyAI** (`assemblyai_batch.py`) — checked against the API reference 2026-11-05 (docs only; details in `docs/RESEARCH.md`)
- [x] `POST /v2/upload` (raw bytes, header `authorization: <key>`) → `upload_url`.
- [x] `POST /v2/transcript` with `audio_url`, `format_text`, `punctuate`, `language_code`, `keyterms_prompt`. **Fixed:** `speech_model` is deprecated and `universal` is not a valid id. The adapter now sends `speech_models: [<model_id>]` (registry: `universal-3-5-pro`). A one-model list is used because the default list falls back to `universal-2` for unsupported audio; the adapter also refuses a completed transcript whose `speech_model_used` differs from the config.
- [x] Poll `GET /v2/transcript/{id}`; statuses `queued` / `processing` / `completed` / `error`; text in `text`.
- [x] Batch price: Universal-3.5 Pro $0.21/h, keyterms +$0.05/h (pricing page). Billed per second of audio.
- [ ] Live run: `api.assemblyai.com` blocked from cloud sessions. Replace the fixtures with captured responses on the first run.

**ElevenLabs** (`elevenlabs_batch.py`) — checked against the API reference and the live API 2026-11-05 (details in `docs/RESEARCH.md`)
- [x] `POST https://api.elevenlabs.io/v1/speech-to-text`, header `xi-api-key`, multipart with `file` and `model_id` (`scribe_v2`; `scribe_v2_medical` also exists).
- [x] `tag_audio_events` (boolean) is still the field; sent as `false`.
- [x] `keyterms` is a list of strings: ≤1000 terms, ≤50 chars, ≤5 words each, none of `<>{}[]\`; +20% (reference) / +$0.05/h (pricing page). **More than 100 keyterms bill every request for at least 20 s**, so the adapter refuses >100 and checks the other limits before any request.
- [x] Multipart encoding of the `keyterms` list: repeated fields work (live). A nonsense keyterm changed the output ("One side" → "Wonside"), and a bad character in the second of two terms was rejected with **400** `invalid_keyword` (not the documented 422).
- [x] Text at top-level `text`; `words[]` entries have `type` `word`/`spacing`/`audio_event` and `logprob`; `language_code` comes back as `eng`; `audio_duration_secs` equals the clip length. Fixture replaced with a captured response.
- [x] Cost, measured from the `character-cost` and `fiat-cost-before-overages` response headers: **18 credits per audio minute**, $0.0036/min ($0.216/h), linear (30 s → 9, 60 s → 18), and a 1.95 s clip cost 1 credit, i.e. rounded up per request. The pricing page's "330 credits per minute" does not match. PriMock57 (5.5 h) costs ≤ ~8.8k credits.

## First live run

Deepgram batch was first run on 2026-11-04 from a cloud session (batch accuracy needs no mic or latency measurement); results and caveats are in `docs/DECISIONS.md`. Streaming and latency runs still need the owner's machine.


```bash
cp .env.example .env   # fill DEEPGRAM_API_KEY etc.; never commit .env
set -a; source .env; set +a
./data/fetch_primock57.sh            # audio needs git-lfs (~1.1 GB)

# 1. Trial: 5 scorable utterances (excluded rows do not count), check the raw responses look like the fixtures
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
