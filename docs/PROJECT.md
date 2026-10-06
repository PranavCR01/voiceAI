# Project

## One line
A voice-stack recommender for forward deployed engineers: describe the use case and constraints (and ideally bring sample audio), and it recommends the whole cascaded stack — STT, turn detection, LLM, TTS, and their settings — says where that choice breaks, and how sure it is.

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

**Output:** a recommendation memo — chosen STT model + settings (keyterms, encoding/sample rate), turn-detection policy + thresholds, LLM + settings, TTS model/voice + settings, the assembled stack's TTFA and cost per minute, runners-up that were statistically tied, configurations rejected and which constraint they failed, "breaks at" thresholds (SNR, concurrency), cost per minute with talk-ratio sensitivity, and every number with its interval.

**Determinism:** same profile + same results → same recommendation. No LLM in scoring or ranking. (The LLM is a system under test; it is never the judge.)

## Recommendation scope (single version)
| Layer | What is recommended | How it is scored (deterministic) |
|---|---|---|
| STT | model + keyterms, encoding, sample rate | pooled WER, entity recall, TTFS, cost |
| Turn detection | policy (provider endpointing / VAD+timeout / Smart Turn / Flux / hybrid) + thresholds | premature/late endpoint rates, endpoint delay |
| LLM | model + settings (temperature, max tokens, prompt variant) | scripted multi-turn conversations with rule checks: correct tool + args, required step order (e.g. identity before disclosure), escalation on red flags, refusal of out-of-scope requests; TTFT p50/p95; cost per turn |
| TTS | model + voice + settings (streaming chunking, format) | TTFB p50/p95; intelligibility round-trip WER via a fixed STT from a different vendor; entity pronunciation fidelity (numbers, dates, drug names); UTMOS naturalness proxy; cost per character |
| Assembled stack | the combination | in-pipeline TTFA decomposition, barge-in latency, end-to-end task success on scripted calls |

Combination rule: layers are scored independently, survivors per layer are combined, and the stack is re-checked end-to-end against latency and cost constraints (layers interact: a slow LLM can eat the budget a fast STT saved). The recommender reports the cheapest passing stack and the fastest passing stack.

Human input that does *not* feed the ranking: a small blind pairwise TTS listening test, used only to validate that UTMOS agrees with people on this project's voices; disagreement is reported in the memo.

**Excluded:** speech-to-speech models (e.g. realtime S2S APIs). They replace the cascade, so comparing them is a third architecture. Revisit only after everything above ships.

## Reference use cases
Built-in suites the no-audio mode falls back to. The first one ships with the tool; the profile format must not assume it.
1. **Healthcare patient intake (first, and the demo).** Entities: medications, dosages, dates of birth, phone numbers. Data: PriMock57 + synthetic intake scripts.
2. *Later suites (stretch):* contact-center billing/collections (Earnings-22 for numbers and finance terms), appointment scheduling for field services, recruiting screens.

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

## Scope
**STT:** Deepgram Nova-3, Deepgram Flux, AssemblyAI Universal-Streaming, ElevenLabs Scribe v2 Realtime.

**LLM and TTS candidates:** not yet researched. A research pass (pinned model IDs, prices, streaming support, tool-calling support, BAA availability) must land in `docs/RESEARCH.md` before the LLM/TTS issues are written. Working assumption: 3–4 LLMs across price/latency tiers and 3–4 streaming TTS vendors (ElevenLabs plus others to be chosen).

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
- LLM: per-check pass rate with Wilson CI over scripted conversations (N runs per script at fixed temperature to capture variance); TTFT p50/p95; tokens and cost per turn.
- TTS: TTFB p50/p95; round-trip WER; entity pronunciation fidelity; UTMOS; cost per minute of agent speech.
- Stats: paired bootstrap (10k, cluster by speaker where needed), Wilson intervals for proportions, Holm correction.

**Deliverables:** the recommender + profile format, one worked full-stack memo for the healthcare reference profile ("Clinic intake line, 8 kHz, p95 TTFA < 1.2 s, medication recall > 95%, identity-check pass rate > 99%, cost < $X/min") and a second profile run in no-audio mode to show the tool is not healthcare-specific, latency waterfall, endpointing trade-off curve, 3-minute demo video, runbook.

## Stretch (only after M7 ships)
Self-hosted Parakeet on GPU, 20-stream load tests (base does 1 and 5), Opus packet-loss simulation, self-recorded speaker set, additional reference suites (finance, contact center), Soniox / AssemblyAI Universal-3.x Pro Realtime, speech-to-speech models.

## Milestones
Single version; each milestone ends in something that runs and can be shown. Estimate: 8–10 weeks.
- **M0 Scaffold:** repo layout, tooling, CI, manifest schema, use-case profile schema.
- **M1 Offline STT scoring:** loaders, normalization, WER, entities, stats, offline report on fixtures. *(cloud)* → demo: STT accuracy report.
- **M1-spike (owner, local, in parallel):** stock Pipecat agent talking end to end. De-risks keys and audio.
- **M2 Streaming STT + augmentation:** streaming adapters, TTFS, raw-WebSocket client (hand-written), augmentation, endpointing sweep. *(mostly local)* → demo: STT latency + endpointing trade-off curve.
- **M3 LLM eval:** research pass, scripted conversation format, rule checks, runner, LLM report. *(checks + runner logic in cloud on recorded responses; live runs local)* → demo: LLM behavior scorecard.
- **M4 TTS eval:** research pass, TTFB harness, round-trip WER, entity pronunciation, UTMOS, listening-test kit. *(scoring in cloud; synthesis local)* → demo: TTS scorecard.
- **M5 Agent:** intake agent, tools, hand-built turn/barge-in controller, tracing. *(local; controller policy testable in cloud on recorded traces)* → demo: phone call with live barge-in.
- **M6 End-to-end + recommender:** scripted callers through the pipeline, TTFA decomposition, full-stack combination and constraint filter. *(recommender in cloud)* → demo: profile in, memo out.
- **M7 Packaging:** memos, README, demo video, runbook, write-up.
