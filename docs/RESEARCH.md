# Research notes

Condensed from a deep-research report dated **October 2026**. Prices, model names and licenses are perishable: re-verify against the vendor's own page before publishing any number. "(vendor)" = vendor-authored claim. "(verify)" = not confirmed against a primary source.

## Gap this project fills
Coval (open-source benchmarks, perturbation sets incl. phone codec), Pipecat stt-benchmark (TTFS + LLM-judged semantic WER), Artificial Analysis (AA-WER, speed) and the HF Open ASR Leaderboard rank providers on generic audio. None take the customer's own audio + constraints and return a deterministic recommendation with CIs, entity error rates, endpointing error rates and in-pipeline TTFA. Commercial agent-testing platforms (Hamming, Coval platform, Cekura, Roark, Bluejay) may cover parts of this for paying customers — frame this project as an open, inspectable FDE tool, not a competitor.

## Datasets (v1)
| Dataset | License | Notes |
|---|---|---|
| PriMock57 | **CC BY 4.0 (verified 2026-10-06, repo LICENSE.md)** | 57 mock GP consultations, 8h38m, 7 clinicians + 57 actors. WAV 16-bit/16 kHz, doctor and patient on **separate channels** (source was Opus video). Transcripts: Praat TextGrid, utterance-level intervals (`xmin`, `xmax`, `text`). Tags `<UNSURE>…`, `<UNIN/>` must be handled (exclude utterances or tagged spans from scoring). Fetched via Git LFS from `github.com/babylonhealth/primock57`. UK accents. ACL 2022 paper: Google Cloud STT 30.9% WER, Azure 31.3%. Pinned commit `cd2ac707ad03cb4d2531f4ec6b90c659bf4357c5`, fetched by `data/fetch_primock57.sh` (`SKIP_AUDIO=1` for transcripts only; they are plain git, only audio is LFS). Manifest committed at `data/manifests/primock57.jsonl`: 7,108 utterances, 5,255 scorable (5.5 h, ~57k words; 2,640 patient / 2,615 doctor), 1,147 excluded `<UNIN/>`, 706 excluded `<INAUDIBLE_SPEECH/>` (an undocumented tag). Clinician identities are not published (57 consultations, 7 clinicians), so doctor speaker IDs are per consultation. |
| LibriSpeech test-clean | CC BY 4.0 | Clean control; too easy for 2026 models. 2,620 utterances, 40 speakers, 16 kHz FLAC. Loader: `harness/datasets/librispeech.py`; fetch steps in `data/README.md` (openslr.org is blocked from the cloud environment). |
| Common Voice English | CC0 | Accent spread; check current download portal/terms. Loader samples the held-out `test.tsv`: accent round robin, ≤10 clips per speaker, accents with <5 clips pooled. MP3 clips assumed 48 kHz (verify on decode). The `accents` column is free text since v8 (`accent` before). |
| Pipecat smart-turn-data v3.x | Open per HF card (verify) | Complete/incomplete turn labels; endpointing eval. |
| Afrispeech-Dialog | CC BY-NC-SA 4.0 | v2 candidate: accented medical dialogue; non-commercial. |

Augmentation sources: MUSAN (SLR17, **CC BY 4.0, verified on https://www.openslr.org/17/ 2026-11-05**, 11 GB), DEMAND (CC BY-SA 3.0, verify; not used), OpenSLR SLR28 RIRs and noises (**Apache 2.0, verified on https://www.openslr.org/28/ 2026-11-05**, 1.3 GB; its point-source noises are extracted from MUSAN). SLR28 is the default source for both noise and reverb (`configs/augment.yaml`). Augmenting a CC BY-SA source makes share-alike derivatives; ND/NC-ND sources can't be published augmented. Publish recipe + manifest only.

**Medication lexicon (built 2026-10-06):** `data/lexicons/medications.txt`, 49 names observed in PriMock57 transcripts/notes at commit `cd2ac707ad03cb4d2531f4ec6b90c659bf4357c5`, hand-checked. openFDA (public domain) could not be fetched from the cloud environment then; it was reachable on 2026-11-05 and now supplies the boost list (below), not the scoring lexicon. Reference misspellings found in PriMock57 transcripts (fix in the loader, #5): paracetemol, paracetmol → paracetamol; lisonopril → lisinopril; clinil → clenil; stemitil → stemetil; thyrocsin → thyroxine; fexofenatidine → fexofenadine.

**Entity counts in PriMock57** (healthcare profile, 5,961 scorable utterances): medication 166, date 21, dosage 18, phone 2 (false positives). Too few dosages/dates/phones for useful intervals; synthetic intake scripts must supply them.

**Medical entities:** MedWER (arXiv 2609.05728, single author, verify) reports medical-term WER 7.8–10.3 pts above overall WER on jargon-heavy audio, 4.2–5.0 pts on PriMock57. Use as motivation, not as a claim to reproduce. Build the medication lexicon from a public-domain source (openFDA / FDA drug label names, verify licensing) plus terms observed in PriMock57 transcripts; publish the lexicon and tagging rules.

**Synthetic audio:** valid for targeted entity stress tests only, reported in a separate table. Use ≥2 TTS vendors; don't synthesize with ElevenLabs and score only ElevenLabs Scribe (family-advantage risk).

**Sample size rule of thumb:** ~300–500 utterances from 15+ speakers per condition resolves ~1–2 abs WER points; entity recall needs ~200+ instances per category. The bootstrap, not this rule, decides what we claim.

## Providers (v1)
| Config | List price (perishable) | Free credits | Knobs |
|---|---|---|---|
| Deepgram Nova-3 streaming | $0.0048/min promo vs $0.0077/min regular — model both | $200 | endpointing ms, utterance_end, keyterm, smart_format; multichannel billed per channel |
| Deepgram Flux | $0.0065/min English | same | built-in end-of-turn thresholds, eager EOT. Vendor: ~30% fewer false interruptions |
| AssemblyAI Universal-Streaming | $0.15/hr, **billed on session duration** | $50 | end-of-turn confidence, keyterms (+$0.04/hr) |
| ElevenLabs Scribe v2 Realtime | $0.39/hr (vendor pricing page, 2026-11-05) | plan-based | manual/VAD commit, silence threshold, keyterms, accepts 8 kHz mu-law; 10-min session cap (third-party, verify) |

**Registry status (2026-10-06):** every entry in `configs/providers.yaml` is `verify: true`. Model ids, settings names and prices above were copied from this research (mostly third-party trackers) because vendor docs are unreachable from the cloud environment. *(2026-11-05: `assemblyai_batch` now has a vendor-page price, and the ElevenLabs Scribe prices are confirmed on elevenlabs.io; see below.)* Verify each against the vendor's own docs/pricing page before its first live run (#13, #18), then set `verify: false`.

**Deepgram batch API, live-checked 2026-11-04** (cloud session; `developers.deepgram.com` still unreachable, so these are observed API behaviour, not doc citations). `POST https://api.deepgram.com/v1/listen`, `Authorization: Token <key>`, raw `audio/wav` body: 200. Bad key: 401 `{"err_code":"INVALID_AUTH"}`. `model=nova-3` resolves to `general-nova-3`, version `2025-07-31.0` (from `metadata.model_info`). Repeated `keyterm` is accepted on Nova-3 and rejected on Nova-2 (400: "`keyterm` is only supported for Nova-3 and Flux. Please use `keywords` instead."). Unknown `language` is a 400; unknown query params are silently ignored. Transcript at `results.channels[0].alternatives[0].transcript`; with `smart_format` the response also carries `paragraphs`. *(2026-11-05: price now confirmed on https://deepgram.com/pricing: Nova-3 monolingual pre-recorded $0.0043/min pay-as-you-go ($0.0036 Growth), keyterm prompting +$0.0013/min, billed per second with no block rounding. https://developers.deepgram.com/docs/keyterm: keyterms limited to 500 tokens per request. The Deepgram batch configs are now `verify: false`.)*

**ElevenLabs Scribe batch, checked against docs and the live API 2026-11-05** (`api.elevenlabs.io` was first refused by the proxy, then allowed later that day; the full PriMock57 run followed). Sources: API reference https://elevenlabs.io/docs/api-reference/speech-to-text/convert, capabilities https://elevenlabs.io/docs/capabilities/speech-to-text, keyterm guide https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting, models https://elevenlabs.io/docs/overview/models, pricing https://elevenlabs.io/pricing/api and https://elevenlabs.io/pricing.
- `POST https://api.elevenlabs.io/v1/speech-to-text`, header `xi-api-key`, multipart; `model_id` required (`scribe_v2`), `file` (≥100 ms). `tag_audio_events` boolean. `language_code` ISO-639-1/3, auto-detected if omitted. Also `temperature` (0–2; default "based on the model, usually 0"), `seed` (best-effort determinism), `no_verbatim` (drops fillers and false starts), `timestamps_granularity`, `file_format=pcm_s16le_16`.
- `keyterms`: list of strings, ≤1000 terms (batch), ≤50 chars, ≤5 words, none of `<>{}[]\`. Surcharge 20% (reference) or $0.05/h (pricing page). **>100 keyterms → minimum billable 20 s per request.**
- Response: `text` (required), `language_code` (e.g. `eng`), `language_probability`, `words[]` (`text`, `type` ∈ word/spacing/audio_event, `logprob`, `start`, `end`, `speaker_id`), optional `transcription_id`, `audio_duration_secs`. A 202/webhook shape and a multichannel `transcripts[]` shape exist; the adapter requests neither.
- Price: **$0.22/h** Scribe v2, $0.39/h Scribe v2 Realtime (pricing page FAQ). **Measured on a Starter-plan key:** the response headers `character-cost` and `fiat-cost-before-overages` gave 30 s → 9 credits / $0.0018, 60 s → 18 / $0.0036, 1.95 s → 1 / $0.0002. That is 18 credits per minute ($0.216/h), linear, rounded up to a whole credit per request. The pricing page's "Speech to Text 330 credits per minute" is ~18× too high for this API. The full PriMock57 run (5,255 requests, 5.5 h) should cost ≤ ~8.8k credits.
- Live behaviour: `language_code` comes back as `eng`; `audio_duration_secs` equals the clip length; repeated multipart `keyterms` fields are all parsed, and an invalid character gives **400** `invalid_keyword` (the reference documents 422). The key lacks `user_read`, so the account balance can't be read via the API. Concurrency limit reported in headers: 12.
- **Scribe v2 Medical** (`scribe_v2_medical`): batch fine-tune of Scribe v2 for drug names, anatomy and clinical dictation; same request shape and price; HIPAA-eligible with BAA for Enterprise (vendor). Not in the registry yet; the obvious second ElevenLabs config for the healthcare profile.
- Not verified: whether the keyterm surcharge follows the same per-request rounding.

**AssemblyAI batch, checked against docs 2026-11-05** (cloud session; `api.assemblyai.com` refused by the proxy). Sources: https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/files/upload, …/transcripts/submit, …/transcripts/get, https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model, https://www.assemblyai.com/docs/billing-and-pricing, https://www.assemblyai.com/pricing.
- Upload `POST /v2/upload` (octet-stream, header `authorization`) → `upload_url`. Create `POST /v2/transcript`. Poll `GET /v2/transcript/{id}`: `status` queued/processing/completed/error, `text`, `error`, `speech_model_used`.
- `speech_model` is **deprecated**; use `speech_models` (list, priority order). Valid ids: `universal-3-5-pro`, `universal-2` (plus `universal-3-6-pro-preview`). Default `["universal-3-5-pro", "universal-2"]` falls back to Universal-2 for languages U3.5 Pro lacks. `universal` (our old id) is not valid.
- `keyterms_prompt`: ≤1000 phrases on U3.5 Pro (≤200 on U2), ≤6 words each. `language_code` (`en`, `en_uk`, `en_us`, …), auto-detected if omitted. `domain: "medical-v1"` = Medical Mode (+$0.15/h).
- Price: Universal-3.5 Pro **$0.21/h**, Universal-2 $0.15/h; keyterms +$0.05/h on U3.5 Pro (included on U2). Billed per second of audio, failed transcripts not charged. New accounts get $50 of credit.

**Keyterm boost list from openFDA, 2026-11-05.** `data/lexicons/openfda_rx_generics.txt` (100 terms), built by `data/lexicons/fetch_openfda_generics.py` from the committed snapshot `openfda_ndc_rx_counts.json` (openFDA NDC directory, `product_type:"HUMAN PRESCRIPTION DRUG"`, count by `generic_name.exact`, top 1,000; data updated 2026-11-04; openFDA is CC0). The rank is the number of US product listings, a proxy for how widely a generic is manufactured and repackaged, **not prescribing volume**, and US-only. OTC drugs are outside it (no paracetamol/acetaminophen). NHSBSA open data and OpenPrescribing (UK prescribing volumes) were still unreachable (403). Overlap with the PriMock57-derived scoring lexicon: 15 of 49 terms (the hand-written list it replaces: 25).

Billing basis matters more than headline rate: session-duration billing charges while the agent talks. Model cost per conversation minute with talk-ratio sensitivity. Healthcare constraint: record whether each vendor offers a BAA (verify per vendor; do not assert).

Independent cross-check (Pipecat stt-benchmark, 1,000 smart-turn samples): AssemblyAI u3.5-pro 282 ms TTFS / 1.22% pooled WER; Cartesia ink-2 299 ms / 1.25%; Soniox rt-v5 260 ms / 1.09%; Azure ~1,016 ms; AWS ~1,136 ms.

## Methodology
- **WER:** jiwer alignment; Whisper EnglishTextNormalizer on ref and hyp (pin version). Pitfalls: numerals vs words, currency/percent, contractions, hyphens, UK/US spelling, fillers, casing. Report normalized WER and formatted-entity accuracy separately.
- **Entities:** regex for digits/doses/dates/phones + curated lexicon for medications. Exact-match recall per entity after alignment; CER on alphanumerics. Run with and without keyterm boosting; count false insertions of boosted terms.
- **Streaming latency:** real-time-paced, same machine/region, identical chunk size (20 ms frames), monotonic clock. Separate connection setup. TTFS = final transcript time − true speech end (Pipecat: VAD stop − stop delay; better: forced-alignment last word / PriMock57 `xmax`). Record RTT per endpoint.
- **Endpointing:** premature rate, late/missed rate, delay distribution; sweep each knob → interruption-vs-latency curve per config.
- **TTFA:** user speech end → first agent audio sample written to transport; decompose into endpointing, STT final, LLM TTFT, TTS TTFB, transport.
- **Barge-in:** user onset during agent speech → TTS stop; false barge-in rate on backchannels. Truncate LLM context using TTS word/char alignment.
- **Stats:** paired bootstrap over utterance IDs (10k, 95% percentile), cluster by speaker when needed; Wilson for proportions; Holm for many pairwise claims.

## Pipeline components
- Pipecat (pin version; frequent API changes). LiveKit Agents is the alternative. Avoid Vocode (stale).
- Silero VAD. Smart Turn v3: BSD-2, 8M params, needs VAD `stop_secs=0.2` and 16 kHz input; ~12.6 ms CPU inference (vendor).
- Twilio Media Streams: always `audio/x-mulaw`, 8000 Hz, base64 over WebSocket.
- ElevenLabs TTS over WebSocket; barge-in requires cancelling in-flight generation and flushing output buffer.

## Hiring signal (why this shape)
Vapi, Retell, Cartesia, Deepgram, ElevenLabs FDE/SE postings emphasize POC-to-production delivery, latency debugging, telephony (SIP/Twilio/WebRTC), reference architectures, demos for technical and exec audiences. Python most named.

## Budget
~$50–150 over 5 weeks; STT mostly covered by free credits. Twilio number + a few hundred minutes ~$10–30 (verify).
