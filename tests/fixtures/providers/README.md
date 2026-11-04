# Provider response fixtures

**Deepgram: captured 2026-11-04** from the live API (PriMock57 `day2_consultation10:patient:0054`, CC BY 4.0; `error_401` from a deliberately invalid key; `error_400_keyterm` from `keyterm` on `model=nova-2`). Scrubbed: `request_id` zeroed, `metadata.sha256` (audio hash) zeroed, `metadata.created` set to midnight. Everything else is verbatim.

**AssemblyAI, ElevenLabs: doc-derived, not captured.** These were written from recollection of each vendor's API shape because vendor docs are unreachable from the cloud environment. On the first live run (#13), replace each with a real captured response (remove API keys, request ids and account ids) and note the capture date here. Until then, the parser tests prove our parsing logic, not that the vendor's format is current.

| Provider | File | Endpoint |
|---|---|---|
| Deepgram | `deepgram/success.json`, `deepgram/error_401.json`, `deepgram/error_400_keyterm.json` | `POST /v1/listen` |
| AssemblyAI | `assemblyai/upload.json`, `transcript_{queued,processing,completed,error}.json` | `POST /v2/upload`, `POST /v2/transcript`, `GET /v2/transcript/{id}` |
| ElevenLabs | `elevenlabs/success.json` | `POST /v1/speech-to-text` |
