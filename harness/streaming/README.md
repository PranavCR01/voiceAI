# Streaming traces

Every streaming adapter (#18) and the hand-written client (#19) records one `SessionTrace` per (config, utterance), and all latency metrics are computed from traces afterwards (`harness/metrics/latency.py`). Code: `trace.py`.

`session.py` runs one session for any provider (#18): connect, pace the audio (`harness.audio.pace`), send the provider's finalize right after the chunk containing the true speech end in `forced` mode, send the close message after the trailing silence, and record every received message. A provider supplies a `StreamProtocol` (URL, headers, audio/finalize/close frames, and a pure `handle(message)` that maps one message to trace events), so the mapping is replay-tested on recorded messages without a network. `tests/test_stream_session.py` runs the whole session against a local echo server (the dry-run mode).

## File format
`<run>/traces/<trace_filename(utt_id)>.jsonl`: line 1 is `SessionMeta`, each later line one `Event`, in time order.

### SessionMeta
| Field | Meaning |
|---|---|
| `config_id`, `utt_id` | Which configuration and utterance. |
| `chunk_ms` | Audio chunk size used by the pacer. |
| `finalization_mode` | `natural` (provider endpointing decides) or `forced` (we send the provider's explicit finalize when the paced audio reaches the true speech end). |
| `finalize_supported` | False when the provider has no explicit finalize; forced-mode metrics then read "not supported". |
| `speech_start_ms`, `speech_end_ms` | Ground truth in audio time (#15). |
| `rtt_ms` | Network round-trip probe to the endpoint, so geography isn't mistaken for model speed. |

### Event
`t_ns` is monotonic-clock time since session start. Kinds:

| Kind | Recorded when | Extra fields |
|---|---|---|
| `connect_start` / `connect_ready` | Connection opened / ready to accept audio | |
| `audio_sent` | A chunk was sent (use the pacer's `sent_ns`, or better, the time right after the socket write) | `chunk_index`, `audio_offset_ms` |
| `audio_end` | Last audio chunk (incl. trailing silence) sent | |
| `finalize_sent` | Forced mode: explicit finalize sent | `audio_offset_ms` it was sent at, `raw` (the message) |
| `partial` / `final` | Provider transcript messages | `text`, `raw`; finals also `words` (word, `start_ms`, `end_ms` in *audio* time) whenever the provider returns word timings |
| `endpoint` | Provider end-of-turn signal (speech_final, utterance end, end of turn) | `raw` |
| `vad_event` | Provider speech start/end events, if any | `raw` |
| `error`, `closed` | Errors and session close | `raw` |
| `info` | Any other provider message (session start, metadata, warnings, replies to our own commits); kept so every received message is in the trace | `raw` |

Use `Recorder` during a live session: `start()`, then `record(kind, at_ns=..., **fields)`.

## Metrics (per session)
- **connection setup** = `connect_ready − connect_start`; never folded into speech latency.
- **first partial** = first `partial` − send time of the chunk containing speech onset.
- **TTFS** = arrival of the final containing the speaker's last word − send time of the chunk containing speech end. With word timings, the last word is the latest-ending word among those ending within 300 ms of the true speech end, and the first final containing it counts; so a trailing final transcribed from silence ("um" two seconds later) or a re-sent final doesn't make a provider look slower. Without word timings it falls back to the last final after the anchor. Each TTFS records its `basis` (`word_timestamps` or `last_final`), and summaries count sessions per basis.
- **finalize latency** (forced) = first `final` after `finalize_sent` − `finalize_sent`.
- **endpoint delay** (natural) = first `endpoint` at/after the speech-end anchor − anchor; endpoints before it are counted as premature (rates in #20).

Statuses: `ok`, `timeout`, `not_applicable`, `not_supported`, `missing_ground_truth`. Aggregates (`summarize`) report p50/p95/p99 with bootstrap CIs, treating timeouts as +inf, plus the timeout rate. Pass `clusters` (utt_id → speaker) to resample whole speakers, as the WER intervals do; the summary then reports `cluster_effect`, the clustered p50 interval width divided by the iid one (≈1: speakers don't matter; well above 1: they do, and iid intervals would have been too narrow).

## Provider message mapping
Adapters: `harness/providers/{deepgram,assemblyai,elevenlabs}_stream.py` (protocols checked against vendor docs 2026-11-05, sources in `docs/RESEARCH.md`). Session settings in the registry: `chunk_ms` (20), `finalization` (`natural`/`forced`), `trailing_silence_ms` (1500), `encoding` (`pcm16` 16 kHz / `mulaw` 8 kHz). Runner: `uv run python -m harness.providers.stream_runner` (one session at a time). `--subset patient --per-speaker 5 --seed 0` runs a seeded per-speaker sample (285 PriMock57 utterances from 57 patients, ~25 min per run; `harness/datasets/sample.py`), recorded in `run.json` as `sample`; the sweep takes the same flags. `--finalization forced` runs the forced mode of a config as its own run (`<config>-forced`). `uv run python -m harness.streaming.slim --results <dir>` writes slim, gzipped copies of the traces (no provider payloads); only those are committed, and `read_trace` falls back to them. Pacing on Windows: 1 ms timer resolution, and the waits run in a pacing thread (`time.sleep`, then a spin) because asyncio's timers wake up to ~15 ms late there; `python -m harness.pacing_check` measures it (`harness/audio.py`, DECISIONS 2026-11-05).

| Provider | `partial` | `final` (+ words) | `endpoint` | Forced finalize | Close |
|---|---|---|---|---|---|
| Deepgram Nova-3 (`/v1/listen`) | `Results`, `is_final: false`, non-empty | `Results`, `is_final: true`; words in s from stream start | `speech_final: true`; `UtteranceEnd` (not `last_word_end: -1`) | `{"type":"Finalize"}` | `CloseStream`, ends at `Metadata` |
| Deepgram Flux (`/v2/listen`) | `TurnInfo` `Update`/`StartOfTurn`/`EagerEndOfTurn`/`TurnResumed` | `TurnInfo` `EndOfTurn` | `EndOfTurn` unless `trigger: manual` (that's our ForceEndTurn) | `{"type":"ForceEndTurn"}` | ForceEndTurn then `CloseStream` (CloseStream alone sends no final turn) |
| AssemblyAI v3 | `Turn`, `end_of_turn: false` | the formatted end-of-turn `Turn` (first one for Universal Streaming without `format_turns`); words in ms from stream start | first `end_of_turn: true` per `turn_order` | `{"type":"ForceEndpoint"}` | `Terminate`, ends at `Termination` |
| ElevenLabs Scribe Realtime | `partial_transcript`, non-empty | `committed_transcript_with_timestamps` (`type: word`); s → ms | `committed_transcript` from the provider's own VAD commit; replies to our commits are `info` | empty chunk with `commit: true` | a commit; ends at its timestamped transcript |

**Word timings** are present for all four. Measured on live sessions (2026-11-05): Nova-3, Scribe and AssemblyAI last words end at 4,000 ms on the same clip, inside the VAD speech span, which confirms stream-start reference points (Scribe's isn't stated in its docs). Flux word *start* times are contiguous on an ~80 ms grid (the first word starts at 0 although speech started at 256 ms), so only Flux end times are precise; TTFS uses end times.

**Read forced mode through TTFS, not finalize latency alone.** A forced finalize can return a final that lacks the speaker's last word: on AssemblyAI the first final came 39 ms after `ForceEndpoint` ending "…the last couple of.", and "Days?" followed as a new turn 471 ms after speech end. Finalize latency (first final after the finalize) reads 39 ms; TTFS (the final containing the last word) reads 471 ms, which is what an agent waiting for the full utterance gets.

**Endpointing knobs** (registry settings, names from the docs): Nova-3 `endpointing` (ms, default 10), `utterance_end_ms` (1000–5000, needs `interim_results`), `vad_events`; Flux `eot_threshold` (0.5–1.0, 0.7), `eager_eot_threshold`, `eot_timeout_ms` (500–60000, 5000); AssemblyAI `mode`, `min_turn_silence`, `max_turn_silence`, `vad_threshold`, `end_of_turn_confidence_threshold` (Universal Streaming); Scribe `commit_strategy` (`vad` here), `vad_silence_threshold_secs` (default 1.5 s per the SDK), `vad_threshold`, `min_speech_duration_ms`, `min_silence_duration_ms`. Scribe's VAD needs `trailing_silence_ms` above its silence threshold, or the closing commit comes first and natural mode has no provider endpoint (the registry entry uses 3000).
