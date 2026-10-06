# Project

## One line
A voice-stack recommender for forward deployed engineers: describe the use case and constraints (and ideally bring sample audio), and it tells you which STT model, which settings and which turn-detection approach to use, where that choice breaks, and how sure it is.

## Problem
Public leaderboards (Artificial Analysis, Open ASR, Coval, Pipecat stt-benchmark) rank STT providers on generic audio, and their filters amount to "sort by price/latency". A real deployment cares about different things: are the domain's critical entities (drug names, account numbers, SKUs, dates) transcribed correctly, does the agent cut callers off mid-sentence, how long until the agent answers, what does a call minute cost *on this vendor's billing basis*, does the vendor meet compliance needs. None of the public boards answers those for a specific use case, on the customer's audio, with confidence intervals.

## How it works
**Input: a use-case profile** (`configs/profiles/*.yaml`):
- Use case: domain, channel (telephony 8 kHz / web or app 16 kHz), language(s), expected accents, call length, agent talk ratio.
- Constraints: max p95 time-to-first-audio, minimum entity recall per category, max cost per minute, compliance (BAA required, data residency), deployment (managed API vs self-hosted), concurrency.
- Domain terms: entity categories and term lists (used for scoring and for keyterm boosting).
- Optional: path to a manifest of the customer's own audio + reference transcripts.

**Two modes:**
1. **Customer audio (high confidence).** Every candidate configuration is run on the supplied audio, plus channel-matched augmentation (e.g. 8 kHz mu-law, noise).
2. **No customer audio (lower confidence).** The profile is matched to the closest built-in reference suite; the output states it was measured on proxy audio and which suite.

**Output:** a recommendation memo — chosen STT model + settings (endpointing/turn-detection policy, keyterms, encoding/sample rate), runners-up that were statistically tied, configurations rejected and which constraint they failed, "breaks at" thresholds (SNR, concurrency), cost per minute with talk-ratio sensitivity, and every number with its interval.

**Determinism:** same profile + same results → same recommendation. No LLM in scoring or ranking.

## v1 recommendation scope
- **Recommended:** STT model, STT settings, turn-detection policy.
- **Measured but not recommended:** LLM time-to-first-token and TTS time-to-first-byte (as TTFA contributors), LLM/TTS cost per minute. Recommending LLM/TTS needs task evals and listening tests → v2.

## Reference use cases
Built-in suites the no-audio mode falls back to. v1 ships one; the profile format must not assume it.
1. **Healthcare patient intake (v1, first and demo).** Entities: medications, dosages, dates of birth, phone numbers. Data: PriMock57 + synthetic intake scripts.
2. *v2 candidates:* contact-center billing/collections (Earnings-22 for numbers and finance terms), appointment scheduling for field services, recruiting screens.

### Demo agent: healthcare intake
The in-pipeline measurements (TTFA, endpointing, barge-in) need a running agent. **Fictional clinic: patient intake and appointment line.** The agent:
1. Verifies identity (full name + date of birth) before discussing anything patient-specific.
2. Collects reason for visit, current medications (name + dose) and allergies.
3. Books or reschedules an appointment (tool calls: `lookup_patient`, `book_appointment`).
4. Escalates on red-flag symptoms (chest pain, trouble breathing, suicidal ideation): tells the caller to hang up and dial 911 / transfers to a human. It never gives medical advice.

All patients are fictional. No real PHI ever enters the system. The project does not claim HIPAA compliance; vendor BAA availability is a profile constraint, recorded per vendor, not asserted.

## Pipeline (what "the whole stack" means here)
1. Transport: local audio → Twilio Media Streams (8 kHz mu-law).
2. VAD: Silero.
3. Turn detection: Smart Turn v3 / provider endpointing / Deepgram Flux — chosen by the hand-built turn controller's policy.
4. Streaming STT: swappable provider.
5. LLM with tool calls, streamed.
6. Streaming TTS: ElevenLabs, sentence-chunked.
7. Barge-in: stop audio, cancel LLM, truncate history to what the caller actually heard.
8. Observability: per-turn latency waterfall across every stage.

## v1 scope
**Providers:** Deepgram Nova-3, Deepgram Flux, AssemblyAI Universal-Streaming, ElevenLabs Scribe v2 Realtime.

**Datasets (manifests only, no audio in repo):**
| Subset | Role |
|---|---|
| LibriSpeech test-clean | clean control |
| Common Voice English | accent spread |
| PriMock57 (patient + doctor channels) | medical conversation, medical entity scoring |
| Pipecat smart-turn test data | endpointing |
| Synthetic intake scripts (2 TTS vendors, clearly labeled) | controlled entities: drug names, doses, DOBs, phone numbers |
| Telephony (8 kHz mu-law) + noise (SNR 20/10/5/0 dB) variants of PriMock57 and Common Voice | realism |

**Metrics:**
- Pooled WER (headline) + per-utterance mean, Whisper-normalized.
- Entity recall by category, categories defined by the profile (v1 reference: medication names, dosages, dates, numbers/phone), with and without keyterm boosting; false insertions of boosted terms.
- Streaming: time to first partial, TTFS (speech end → final transcript), p50/p95/p99.
- Endpointing: premature-endpoint rate, late-endpoint rate, delay distribution; sweep per knob → trade-off curve.
- In-pipeline: TTFA decomposed (endpointing, STT final, LLM TTFT, TTS TTFB, transport); barge-in stop latency; false barge-in on backchannels.
- Stats: paired bootstrap (10k, cluster by speaker where needed), Wilson intervals for proportions, Holm correction.

**Deliverables:** the recommender + profile format, one worked memo for the healthcare reference profile ("Clinic intake line, 8 kHz, p95 TTFA < 1.2 s, medication recall > 95%, cost < $X/min") and a second profile run in no-audio mode to show the tool is not healthcare-specific, latency waterfall, endpointing trade-off curve, 3-minute demo video, runbook.

## Out of scope for v1 (v2 candidates)
Self-hosted Parakeet on GPU, 20-stream load tests (v1 does 1 and 5), Opus packet-loss simulation, TTS quality scoring, self-recorded speaker set, additional reference suites (finance, contact center), LLM/TTS recommendations, Soniox / AssemblyAI Universal-3.x Pro Realtime.

## Milestones
- **M0 Scaffold:** repo layout, tooling, CI, manifest schema, use-case profile schema.
- **M1 Offline scoring:** loaders, normalization, WER, entities, stats, batch-mode report on fixtures. *(cloud)*
- **M1-spike (owner, local, in parallel):** stock Pipecat agent talking end-to-end. De-risks keys and audio.
- **M2 Streaming + augmentation:** streaming adapters, TTFS, raw-WebSocket client (hand-written), augmentation pipeline. *(mostly local)*
- **M3 Agent:** intake agent, tools, hand-built turn/barge-in controller, tracing. *(local; controller policy logic testable in cloud on recorded traces)*
- **M4 End-to-end metrics + recommender.** *(recommender in cloud)*
- **M5 Packaging:** memo, README, demo, write-up.
