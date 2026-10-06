# Project

## One line
The tool a forward deployed engineer would run in week one of a healthcare voice-agent proof of concept: given the customer's audio and constraints, which STT configuration should they use, where does it break, and how sure are we?

## Problem
Public leaderboards (Artificial Analysis, Open ASR, Coval, Pipecat stt-benchmark) rank STT providers on generic audio. A healthcare customer cares about different things: are drug names, dosages and dates of birth transcribed correctly, does the agent cut patients off mid-sentence, how long until the agent answers, what does a call minute cost. None of the public boards answers those on the customer's own audio with confidence intervals.

## Scenario
**Fictional clinic: patient intake and appointment line.** A caller phones the clinic. The agent:
1. Verifies identity (full name + date of birth) before discussing anything patient-specific.
2. Collects reason for visit, current medications (name + dose) and allergies.
3. Books or reschedules an appointment (tool calls: `lookup_patient`, `book_appointment`).
4. Escalates on red-flag symptoms (chest pain, trouble breathing, suicidal ideation): tells the caller to hang up and dial 911 / transfers to a human. It never gives medical advice.

All patients are fictional. No real PHI ever enters the system. The project does not claim HIPAA compliance; vendor BAA availability is recorded as a constraint in the recommender, not asserted.

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
- Entity recall by category: medication names, dosages, dates, numbers/phone, with and without keyterm boosting; false insertions of boosted terms.
- Streaming: time to first partial, TTFS (speech end → final transcript), p50/p95/p99.
- Endpointing: premature-endpoint rate, late-endpoint rate, delay distribution; sweep per knob → trade-off curve.
- In-pipeline: TTFA decomposed (endpointing, STT final, LLM TTFT, TTS TTFB, transport); barge-in stop latency; false barge-in on backchannels.
- Stats: paired bootstrap (10k, cluster by speaker where needed), Wilson intervals for proportions, Holm correction.

**Deliverables:** recommender output + one customer memo ("Clinic intake line, 8 kHz, p95 TTFA < 1.2 s, medication recall > 95%, cost < $X/min"), latency waterfall, endpointing trade-off curve, 3-minute demo video, runbook.

## Out of scope for v1 (v2 candidates)
Self-hosted Parakeet on GPU, 20-stream load tests (v1 does 1 and 5), Opus packet-loss simulation, TTS quality scoring, self-recorded speaker set, memos for other industries, Soniox / AssemblyAI Universal-3.x Pro Realtime.

## Milestones
- **M0 Scaffold:** repo layout, tooling, CI, manifest schema.
- **M1 Offline scoring:** loaders, normalization, WER, entities, stats, batch-mode report on fixtures. *(cloud)*
- **M1-spike (owner, local, in parallel):** stock Pipecat agent talking end-to-end. De-risks keys and audio.
- **M2 Streaming + augmentation:** streaming adapters, TTFS, raw-WebSocket client (hand-written), augmentation pipeline. *(mostly local)*
- **M3 Agent:** intake agent, tools, hand-built turn/barge-in controller, tracing. *(local; controller policy logic testable in cloud on recorded traces)*
- **M4 End-to-end metrics + recommender.** *(recommender in cloud)*
- **M5 Packaging:** memo, README, demo, write-up.
