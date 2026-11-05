# Decisions

Newest first. Each entry: date, decision, reason, what it replaced (if anything).

## 2026-11-05 — Report charts: deterministic SVG small multiples (#22)
- `harness/charts.py` draws the endpointing trade-off from the sweep CSV with matplotlib (new dependency): x = p95 endpoint delay, y = premature-endpoint rate, a point per knob value with both 95% intervals as error bars and the value as a direct label.
- **Small multiples, one config per panel, shared axes, one colour.** Four configs in one plot would need a fourth categorical hue, and the reference palette's fourth slot (yellow beside orange) fails the all-pairs colour checks. Separate panels also avoid a legend lookup. Rates start at 0 and delay at 0, so slopes aren't exaggerated.
- **Static, light-surface SVG without a hover layer:** the issue asks for charts next to a Markdown report that must read without them, so the CSV/table is the accessible view. Deviates from the dataviz default of interactive charts; revisit if the report moves to HTML.
- **Determinism:** Agg backend, fixed `svg.hashsalt`, text kept as text, no date metadata. A test asserts byte-identical output for identical input, and different output when the data changes. Determinism holds per matplotlib version (pinned in `uv.lock`), like ffmpeg for augmentation.

## 2026-11-05 — Endpointing outcomes and knob sweeps (#20, code half)
- **One outcome per natural-mode session** (`harness/metrics/endpointing.py`), judged against the send time of the chunk containing the true speech end (the TTFS anchor):
  - *premature*: any provider endpoint before it. That includes one fired during a mid-sentence pause.
  - *correct*: the first endpoint after it, within `late_after_ms` (default 3 s).
  - *late*: none within that window.
  - For a turn labelled *incomplete* (smart-turn's incomplete samples), any endpoint is premature, because the caller never finished.
  - Forced-mode or ground-truth-less sessions are *unscorable* and counted, not rated.
  - Premature takes precedence: an agent that interrupted once has failed that turn even if it endpointed again at the right time.
- **Rates use Wilson intervals, not clustered**, like the empty-on-speech rate. Delay percentiles use the speaker-clustered bootstrap. Weakness: if premature endpoints cluster by speaker (fast talkers, long pausers), the Wilson interval is too narrow. A clustered rate interval is a follow-up once real sweep data shows how much speakers matter.
- **Sweeps** (`harness/providers/sweep.py`, `configs/sweeps/*.yaml`): every knob value is an ordinary streaming run (`<config>-<knob>-<value>`, the value in `RunMeta.settings`, forced to `finalization: natural`), so each curve point resumes and re-scores like any run. Sweeps read run directories directly, because `read_runs` (reports) allows one run per config. `summarize` writes one CSV row per point for the report (#22).
- Committed sweeps: Nova-3 `endpointing` 100–1200 ms, Flux `eot_threshold` 0.5–0.9, AssemblyAI `max_turn_silence` 400–2000 ms (streaming host currently unreachable), Scribe `vad_silence_threshold_secs` 0.3–1.5 s. A test checks every value is a setting the adapter accepts.
- **Not done here (owner):** the smart-turn data loader (Hugging Face) and the mid-utterance pause set (needs synthesized audio, #17), plus the live sweeps. Turn labels are read from `<manifest>.turns.jsonl` when present; unlabelled utterances count as complete turns.

## 2026-11-05 — Streaming adapters (#18): one session loop, thin protocols, live-probed
- **Design:** `harness/streaming/session.py` runs any session (connect, pace, forced finalize right after the chunk containing the true speech end, close after trailing silence, record everything). Each provider is a `StreamProtocol` whose `handle(message)` maps one message to trace events, so the mapping is replay-tested on recorded messages. `harness/providers/stream_runner.py` runs sessions one at a time, because overlapping sessions would distort latency (concurrency is #21). It writes `traces/` plus a `results.parquet` of concatenated finals, which the offline report scores unchanged.
- **New trace kind `info`** for every message that isn't a transcript/endpoint/VAD/error event (session start, metadata, warnings). Without it those raw messages were dropped, against hard rule 5. Metrics ignore it.
- **Protocols checked against current vendor docs, then probed live** on one PriMock57 utterance in both modes (Deepgram Nova-3, Flux, Scribe Realtime). The probes found three things the docs alone wouldn't have:
  - **Scribe:** with its default 1.5 s VAD silence and our 1.5 s of trailing silence, our closing commit always answered first, so natural-mode "endpoint delay" was measuring our commit (1,701 ms). Replies to our own commits are now `info`, not `endpoint`, and the Scribe config streams 3 s of trailing silence. The VAD commit then arrives at +1,688 ms.
  - **Flux:** CloseStream sends no EndOfTurn, so the last turn would vanish. Close is now ForceEndTurn + CloseStream, and an EndOfTurn with `trigger: manual` is a `final` but not an `endpoint`. Flux word start times are contiguous on an ~80 ms grid; only end times are precise.
  - **Word timings are in audio time** for Nova-3 and Scribe: words fall inside the VAD speech span. Scribe's docs don't state the reference point.
- **AssemblyAI streaming** (host `streaming.assemblyai.com`, allowed later the same day) probed live too; fixtures are live captures. The model id was invalid (`universal-streaming`) and is now `universal-streaming-english`, the $0.15/h model the entry was priced for. Without settings it returns unformatted text, so the config sets `format_turns: true` (comparable with Deepgram `smart_format` and Scribe), and the adapter's final waits for the formatted end-of-turn message.
- **Finalize latency overstates speed when a forced finalize splits the last word off.** On AssemblyAI the first final came 39 ms after `ForceEndpoint` without the last word ("…couple of."); "Days?" arrived as a new turn 471 ms after speech end. TTFS already handles this (final containing the last word), so forced-mode comparisons should read TTFS. Finalize latency stays in the table but isn't a ranking metric. Replaces nothing; the #14 definition stands, with this caveat.
- **Probe numbers are not latency results.** One utterance from a cloud container through an egress proxy (the RTT probe there measures the proxy hop): Nova-3 TTFS 477 ms natural (`endpointing: 300`) / 111 ms forced; Flux 134 / 143 ms; Scribe 1,702 ms natural (VAD) / 211 ms forced. AssemblyAI (formatted): 509 ms natural / 471 ms forced (TTFS). They show the mechanics work. Latency runs belong on the owner's fixed machine (#18 acceptance).

## 2026-11-05 — Telephone band-pass step; noisy phone recipes now include it; parallel augmentation
- **New step `bandpass`** (300–3,400 Hz, two cascaded 2-pole Butterworth sections per edge = 24 dB/octave, via ffmpeg `highpass`/`lowpass`, args recorded). Reason: `telephony_mulaw` keeps 0–4 kHz, while a real phone channel cuts below ~300 Hz and above ~3.4 kHz (ITU-T G.712 mask). Measured on tones at 8 kHz: 0 dB at 1 kHz, −6 dB at the cutoffs, < −30 dB at 100 Hz, ~−5 dB at 3.9 kHz. It's a stand-in for the mask, not a model of any network (no AGC, echo cancellation or packet loss).
- **New recipe `telephony_g712`** = resample 8 kHz → bandpass → mu-law. `telephony_mulaw` is unchanged, because its manifest and three runs are committed and must keep their meaning.
- **`phone_noisy_snr10` / `phone_noisy_snr5` now include the band-pass** (noise → resample → bandpass → mu-law). They had never been run, so nothing recorded changes. They compare against `telephony_g712`, which isolates the noise effect from the channel effect.
- **`--workers`** (thread pool, default CPU count) for `harness.augment.run`. The single-threaded `telephony_mulaw` build took 22 min for 5,255 utterances. Output is identical for any worker count (tested), since every step's seed depends only on the utterance.

## 2026-11-05 — PriMock57 on a simulated phone line (8 kHz mu-law): the ranking holds, the gaps narrow
Three configs on `data/manifests/primock57.telephony_mulaw.jsonl` (recipe `telephony_mulaw`, seed 0; 5,255 utterances each, 0 failed), results in `results_augmented/telephony_mulaw/`, report `reports/generated/primock57_telephony_batch.md`. Degradation is paired per utterance against each config's clean run, speaker-clustered bootstrap (10,000 resamples):

| Config | Clean WER | Phone WER | Degradation [95% CI] | Medication (clean → phone) | Empty on speech |
|---|---|---|---|---|---|
| Scribe v2 | 5.65% | 6.80% | +1.15 pp [+0.90, +1.42] | 135 → 131 | 17 → 23 |
| AssemblyAI U-3.5 Pro | 6.56% | 7.27% | **+0.71 pp** [+0.55, +0.88] | 138 → 131 | 19 → 16 |
| Deepgram Nova-3 | 7.42% | 8.56% | +1.14 pp [+0.91, +1.38] | 121 → 117 | 57 → 49 |

- **Ranking unchanged, all pairs distinguishable:** Scribe 6.8% < AssemblyAI 7.3% (+0.5 pp [+0.1, +0.9], p = 0.019) < Deepgram 8.6%. Patient side: 8.3 / 9.1 / 10.3%.
- **AssemblyAI degrades least** (+11% relative vs +20% Scribe, +15% Deepgram), so Scribe's lead over it halves (0.9 → 0.5 pp). Medication recall ties between Scribe and AssemblyAI on the phone line (131/163 each).
- Scribe's degradation is well above its run-to-run noise (~0.1 pp WER between identical runs), so the +1.15 pp is a real effect, not repeat variance.
- **Weakness, and why this is a floor, not a field estimate:** the simulation is studio-quality 16 kHz audio resampled to 8 kHz and mu-law coded. A real phone call also has a handset/network band-pass (~300–3,400 Hz, while ours keeps 0–4 kHz), AGC, echo cancellation, background noise and occasional packet loss. Real calls will degrade more; the noisy-phone recipes (`phone_noisy_snr10/5`) are the next step toward that.
- Spend: ≈ $1.20 (AssemblyAI) + ~6–9k ElevenLabs credits + ≈ $1.40 (Deepgram). The augmentation itself took 22 min for 5,255 utterances (three ffmpeg processes per utterance, single-threaded); parallelising `harness.augment.run` is worth doing before running the SNR sweep.

## 2026-11-05 — Scribe v2 run-to-run noise floor: the keyterm gain is about half noise
Retest of `elevenlabs_scribe_v2_batch` (same config, `results_retest/elevenlabs-scribe-v2-batch-retest`, 5,255 utterances, 0 failed, 14 empty on speech vs 17 in the first run).
- **Scribe is ~7× less repeatable than Deepgram at `temperature: 0`.** Identical runs differ on **605 raw / 250 normalized** transcripts (11.5% / 4.8%). Deepgram's retest: 1.6% / 0.9%. WER 5.7% → 5.6%. Medication recall 135 → **138**/163, so ±3 entities flip between identical runs.
- **The keyterm gain shrinks against the retest:** plain-vs-boosted differ on 1,075 raw / 410 normalized transcripts, against 605 / 250 between identical runs, so roughly half of what looked like the keyterm effect is noise. Boosted vs retest: WER −0.1 pp [−0.2, −0.0] (p = 0.013; it was −0.2 pp against the first run), medication 138 → 143. Read it as **a small real gain (+5 ± 3 medication entities, ~0.1 pp WER)**, not the +8 / 0.2 pp of the six-config entry below.
- Consequence for the recommender: with Scribe, differences under ~0.1 pp WER or ~3 entities between configs on PriMock57 are within run-to-run noise. A single run per config is not enough to rank Scribe settings; repeat runs (or the `seed` setting, which the API documents as best-effort) are needed before trusting small gaps.

## 2026-11-05 — Augmentation pipeline (#16)
`configs/augment.yaml` + `harness/augment/` (`codec.py`, `noise.py`, `reverb.py`, `recipes.py`, `run.py`); usage and the recorded step parameters are in `harness/augment/README.md`.
- **Seeds per utterance and step, by hash.** Each step's seed is SHA-256 of (run seed, parent `utt_id`, step index), so an utterance's augmentation is the same whatever the order, `--limit` or other manifest rows. A single RNG walked across the manifest would change every later utterance when one is added. Different run seed → different noise file/offset (tested).
- **SNR on the VAD speech region** (#15 sidecar) when the parent has a span, else the whole clip, recorded per step. Measured over a whole PriMock57 clip, leading/trailing silence would count as speech: the generated test clip (half silence) reads ~3 dB worse whole-clip than on its speech region, so "10 dB" would really be ~13 dB at the voice. On clipping, the whole mix is scaled down, which keeps the SNR.
- **Reverb aligned on the RIR's direct path** (largest sample) and re-levelled to the input's speech-region power. A plain convolution delays speech by the RIR's propagation time, and the latency anchor (#14) would charge that to the provider.
- **Codecs via ffmpeg with `+bitexact` flags; args recorded verbatim with the ffmpeg version**, and a test replays the recorded commands and gets identical samples. Opus decode output is trimmed/padded to the input length (encoder delay and final-frame padding would otherwise shift timing).
- **mu-law children stay 8 kHz** (`sample_rate: 8000`); `load_clip` upsamples to 16 kHz for providers, which is what a phone line delivers. Band-limit check: energy above 4.5 kHz after upsampling is ~3×10⁻⁶ of the total. Between 4.0 and 4.5 kHz ~0.1% leaks, and that comes from ffmpeg's upsampler, identically with or without mu-law, not from the recipe.
- **Sources: OpenSLR SLR28 (Apache 2.0) for both noise and reverb, not MUSAN.** SLR28 contains point-source noises extracted from MUSAN and the simulated RIRs, 1.3 GB instead of 11 GB. Weakness: the point-source set is smaller and less varied than MUSAN's `noise/`; switching is a config change, recorded in each step's `noise_file`. Fetched by `data/fetch_augment_sources.sh` with the archive's sha256 pinned, since a changed archive would change which file a seed picks.
- Phone + noise recipes add noise **before** the codec (noise is at the caller's end).
- **Child manifests are not committed yet.** At ~1.9 KB per utterance (the ffmpeg commands are recorded verbatim) a full PriMock57 child manifest is ~10 MB, and it is exactly reproducible from the parent manifest, recipe, seed, pinned SLR28 archive and ffmpeg version. Commit one together with the first provider run that uses it, because the report needs the manifest to re-score.

## 2026-11-05 — Six-config PriMock57 batch comparison: AssemblyAI, Scribe keyterms, Scribe Medical, Deepgram re-run (#13)
Four new runs, 5,255 scorable utterances each, 0 failed: `assemblyai_batch` (Universal-3.5 Pro; every transcript reports `speech_model_used: universal-3-5-pro`), `elevenlabs_scribe_v2_batch_keyterms_common`, `elevenlabs_scribe_v2_medical_batch`, and `deepgram_nova3_batch_keyterms_common` re-run with the openFDA boost list. The old `_common` run (hand-written UK list) moved to `results_superseded/`, tracked like `results_retest/`, because a report takes one run per config. Report: `reports/generated/primock57_batch.md`.

| Config | WER [95% CI] | Medication recall | Empty on speech | False keyterms |
|---|---|---|---|---|
| Scribe v2 + openFDA list | **5.5%** [5.0, 6.0] | **87.7%** (143/163) | 15 | 12 |
| Scribe v2 | 5.7% [5.1, 6.2] | 82.8% (135) | 17 | 3 |
| Scribe v2 Medical | 5.8% [5.3, 6.4] | 82.8% (135) | 43 | 5 |
| AssemblyAI Universal-3.5 Pro | 6.6% [6.0, 7.1] | 84.7% (138) | 19 | 1 |
| Deepgram Nova-3 (all three configs) | 7.4% [6.8, 8.1] | 74.2% / 87.7% oracle / 73.6% openFDA | 57–63 | 1–9 |

- **Ranking on WER, all distinguishable except Scribe vs Scribe Medical:** Scribe family < AssemblyAI (−0.9 pp vs Deepgram, +0.9 pp vs Scribe) < Deepgram. Same order on the patient side (6.7 / 7.0 / 7.1 / 8.1 / 8.7%); pairwise verdicts per side are in the report.
- **The same boost list helps Scribe and does nothing for Deepgram.** With the openFDA list, Scribe medication recall goes 135 → 143 (equal to Deepgram's *oracle* lexicon) and WER drops 0.2 pp [0.1, 0.3]. Deepgram goes 121 → 120 and WER is unchanged. Deepgram with the old hand-written UK list had gained 7 (78.5%), so for Deepgram the list's overlap with what speakers say matters, and the openFDA list (15 of 49 scoring-lexicon terms) has too little. The cost on Scribe: false keyterm insertions 3 → 12.
- **Caveat on the Scribe keyterm gain: no noise floor yet.** Raw transcripts differ between the plain and boosted Scribe runs on 1,075 of 5,255 utterances (20%). Deepgram's identical-config retest differed on 1.6%. Either keyterms change Scribe's output broadly or Scribe at `temperature: 0` is much less repeatable than Deepgram. A retest of `elevenlabs_scribe_v2_batch` (~$1.20) would tell. Until then the +8 medication entities (overlapping intervals: 82.8% [76.3, 87.8] vs 87.7% [81.8, 91.9]) are suggestive, not established.
- **Scribe v2 Medical shows no benefit here.** Medication recall is identical (135/163), WER is a tie with Scribe v2, and it drops 2.5× more short backchannels (43 vs 17 empty on speech, all 1–2-word "OK"/"Yeah"). The vendor's "35% fewer errors on clinical audio" isn't visible on patient-doctor conversation. PriMock57 has few drug names, so this is weak evidence either way.
- **AssemblyAI:** 6.6% WER, medication 84.7% unboosted, and the only provider that writes dosages as digits (formatted 87.5% vs 0–25% for the others). It reported a 4.32 s clip as `audio_duration: 5`, consistent with billing rounded up to whole seconds (+~13% on short clips). Its run records `git_sha a0f7da9…-dirty`. The uncommitted changes were the new ElevenLabs registry entries and the `.gitignore` line, committed next (6ad3640), and they don't touch AssemblyAI requests.
- **Spend for the four runs:** ≈ $1.20 (AssemblyAI) + ~6–9k ElevenLabs credits each (~$1.20–1.50) + Deepgram ≈ $1.85 (5.5 h × $0.0056/min).

## 2026-11-05 — First ElevenLabs Scribe v2 batch run on PriMock57 (#13)
Run `results/elevenlabs-scribe-v2-batch` (settings `language_code: en`, `temperature: 0`; git `beb7ab9`): 5,255 scorable utterances, 0 failed, 17 empty on speech. Report: `reports/generated/primock57_batch.md`.
- **Scribe v2 beats every Deepgram config on WER:** 5.7% [5.1, 6.2] vs 7.4% [6.8, 8.1], difference +1.8 pp [+1.4, +2.1] (Holm p = 0.001, 114 speakers). The gap holds on both sides: doctor 4.7% vs 6.5%, patient 7.0% vs 8.7%. Whisper-only WER moves the same way (8.4% vs 10.2%), so the gap is not an artifact of the equivalence layer. It is one dataset (UK English, consultation-room audio, 16 kHz), and Deepgram ran without `language=en-GB` hints; nothing here says how they compare on 8 kHz telephony.
- **Far fewer empty transcripts on speech:** 0.3% [0.2, 0.5] (17/5,105) vs 1.1% [0.9, 1.4] for Deepgram plain. For an agent that is about 4× fewer turns where it hears silence.
- **Medication recall without any boosting is 82.8% [76.3, 87.8] (135/163)**, above Deepgram plain (74.2%) and Deepgram with the independent boost list (78.5%), below Deepgram with the oracle lexicon (87.7%). Intervals overlap with every Deepgram config, so this is suggestive, not established. Scribe with keyterms is not run yet.
- **DOB recall 18/21 vs 19/21 (tie).** One miss is shared with Deepgram (both hear "June" where the reference says "November", possibly a reference error). One is "the 20th of the 4th, 1980": the right date in a form the scorer doesn't equate with "twentieth of April". Scribe writes dates as spoken ("the 2nd of November, 1992"), never as digits, so the registry has no `output_date_order` for it. "Formatted" (digits) is 52.4% vs Deepgram's 90.5%, a formatting difference, not an accuracy one.
- **Cost was 18× lower than the pricing page implied.** Response headers give 18 credits ($0.0036) per audio minute, rounded up per request. The pricing page says 330 credits/min. Run cost ≈ 6–9k credits (~$1.20).
- **Fixture:** `tests/fixtures/providers/elevenlabs/success.json` is a captured response (transcription id zeroed).
- `verify: true` stays: the price basis (credits vs USD, per-request rounding) is measured on one Starter-plan key only.

## 2026-11-05 — ElevenLabs and AssemblyAI batch adapters checked against docs (#13); openFDA boost list
- **Live status:** `api.assemblyai.com` is refused by the network proxy (403 on CONNECT), so AssemblyAI is checked against docs only and its fixtures stay hand-written. `api.elevenlabs.io` was refused at first and allowed later the same day (entry above has the run). Sources and details: `docs/RESEARCH.md` (2026-11-05).
- *(Corrected the same day.)* This entry first said the PriMock57 run wouldn't fit the key's 20k credits, using the pricing page's "330 credits per minute" (~109k credits). Measured cost is 18 credits per minute (~6–9k credits for the run); see the entry above.
- **AssemblyAI fix:** `speech_model: universal` was wrong twice over: the field is deprecated and the id doesn't exist. The adapter sends `speech_models: [<model_id>]` (`universal-3-5-pro`). It sends a one-model list on purpose: the default list silently falls back to Universal-2, which would put a different model's output under this config's name. A completed transcript whose `speech_model_used` differs is a permanent error. Price filled: $0.21/h.
- **ElevenLabs keyterms are capped at 100 by the adapter.** Above 100 the API bills each request for at least 20 s. PriMock57 utterances average ~3.8 s, so a 101-term list would cost roughly 5× the base rate. The other documented limits (≤50 chars, ≤5 words, no `<>{}[]\`) are checked before any request, and a test checks every profile's boost list passes.
- **Pinned defaults in the ElevenLabs registry entry:** `language_code: en` (Scribe auto-detects by default, where Deepgram defaults to English; one-word backchannels are where detection is weakest) and `temperature: 0` (documented default is "based on the model, usually 0"). Same for AssemblyAI: `language_code: en`. New adapter settings, none sent unless configured: ElevenLabs `no_verbatim`, `temperature`, `seed`.
- **Boost list replaced with a ranked public list, which fits PriMock57 worse.** openFDA was reachable, so `healthcare_intake` now boosts with `data/lexicons/openfda_rx_generics.txt`: the top US prescription generics by NDC product listings, salts and case merged, combinations and non-drugs dropped, the UK name added after the US one where they differ (fixed map), 100 terms (the ElevenLabs limit). It is built by `data/lexicons/fetch_openfda_generics.py` from a committed snapshot, and a test pins the output. Weaknesses:
  - The rank measures US manufacturing breadth, not prescribing.
  - It excludes OTC drugs, so paracetamol/acetaminophen, the most-said drug in PriMock57, is missing, as are salbutamol, codeine, trimethoprim and nitrofurantoin.
  - It shares **15** of the scoring lexicon's 49 terms, against **25** for the hand-written list, so a re-run of `deepgram_nova3_batch_keyterms_common` should show a smaller gain than the 74.2% → 78.5% measured with the old list.
  - It does fit the profile itself, which describes a US clinic (en-US, US residency), while PriMock57 is UK audio. That tension (boost for the deployment vs. score on UK audio) is the real reason no list fits both.
  - Replace it with UK prescribing volumes (NHSBSA/OpenPrescribing, still 403) when reachable.
  - The hand-written `common_uk_generics.txt` is kept, marked superseded, because the recorded `_common` run used it (its `run.json` lists the terms).
- **Report regenerated** (`reports/generated/primock57_batch.md`). Only the false-keyterm baseline for the unboosted run changed (overall 4 → 1, patient 3 → 0), because unboosted runs are counted against the profile's current list. The `_common` run's 9 is still counted against the old list it used, so **those two numbers no longer compare** until `_common` is re-run with the new list. The "plain 4 vs independent list 9" figure in the 2026-11-04 entry is read against the old list.

## 2026-11-05 — Synthetic caller scripts (#17, text half); equivalence v4 ("ninth")
- **Generator** `harness/synthetic/scripts.py`: seeded, profile-driven. Carrier sentences live in a per-profile file (`synthetic_templates`, new profile field; `configs/profiles/healthcare_intake.templates.yaml`, `utility_billing_support.templates.yaml`), because healthcare wording may not appear outside `configs/profiles/healthcare_*`. The generator renders entities by *kind*: lexicon term; spoken date / dosage / phone / amount / duration; a regex category only if it's a fixed-length digit pattern (otherwise an error, not a guess).
- **Spoken references:** the reference is exactly what the TTS will read ("oh seven seven double oh…", "the twenty ninth of April nineteen eighty two", "five hundred milligrams"), so the normalizer decides equivalence with provider output. Templates are chosen to fill the least-covered category first.
- **Committed:** `data/manifests/synthetic_healthcare_intake.jsonl` (806 utterances: medication 338, dosage/date_of_birth/phone 300 each) and `synthetic_utility_billing_support.jsonl` (900), with `.entities.jsonl` sidecars (inserted entities and disfluency per utterance). The tagger finds **100%** of inserted entities in both. Disfluent: 28.9% / 30.6% (leading filler, mid filler, or restart; never inside an entity).
- **Weaknesses:**
  - The lexicon includes creams and OTC brands, so some lines are implausible ("one tablet of bactroban"). That gives the ASR language model a less natural context than real speech; it's acceptable for an entity stress test but is one more reason synthetic results stay in their own section.
  - Dates of birth span 1935–2008 uniformly, years are always spoken in full, and the sentence variety is small (18 healthcare templates). Read synthetic entity recall as "can it get these entities in clean speech", not as a field estimate.
- **Voices:** one voice per script line (round robin, no duplicated text). **The default is 2 vendors × 5 voices, not the issue's minimum of 2 × 2:** the report resamples whole speakers (= voices) and calls no winner under 10 clusters, so 4 voices would make every synthetic table unrankable. The committed manifests use placeholder voices `tts_{a,b}.voice{1..5}`; the owner regenerates with real ids (`--voice vendor:id:locale`) before synthesis, which changes the utt_ids and audio paths but not the text (same seed).
- **Fictional numbers only:** UK Ofcom drama ranges (07700 900xxx, 020 7946 0xxx) and US 555-01xx.
- **Equivalence v4, found by the generator:** Whisper's normalizer turns every ordinal word into digits except "ninth" (its table spells it "nineth"), so "the twenty ninth of April" stayed "20 ninth of april" and couldn't match a provider's "April 29th". This affects real speech: on PriMock57 the rule fixes 2 utterances (7 errors) and raises DOB recall from 17/21 to **19/21** (90.5% [71.1, 97.3]) for all three configs. Those were the two misses earlier misread as "reference has no day". New rule `ninth`: "ninth" → "nineth" before Whisper (fixtures added). Normalizer id `equiv-v3` → `equiv-v4`; the PriMock57 report and equivalence breakdown were regenerated with it.
- **Not done here (owner):** `synthesize.py` and the audio. It needs two TTS vendors' keys, and per CLAUDE.md live-API work runs on the owner's machine.

## 2026-11-04 — Keyterm leakage measured; run-to-run noise floor
Two new Deepgram runs on PriMock57 (5,255 utterances each, 0 failed): `deepgram_nova3_batch_keyterms_common` (independent 86-term list) and a repeat of `deepgram_nova3_batch` (`results_retest/`, kept apart because a report takes one run per config).
- **A realistic boost list buys about a third of the oracle gain.** Medication recall: plain 74.2% (121/163) → independent list **78.5%** [71.6, 84.1] (128/163; 9 gained, 2 lost) → oracle lexicon 87.7% (143/163). So most of the +13.5 pp reported in #13 came from boosting the test set's own drug names. Brands (Ventolin, Piriton), which callers actually say, are the gap.
- **The cost is false insertions.** Counted against the same 86-term list, plain writes a boosted term the speaker didn't say 4 times, the independent list 9 times. WER is unchanged across all three (7.4%, every pair a tie).
- **Noise floor, identical config run twice:** raw transcripts differ on 1.6% of utterances (0.9% after normalization), WER differs by 0.026 pp, and medication recall is identical (0 of 163 entities flip). Empty-on-speech recurs in 54 of 57 cases, so it's mostly deterministic. Between configs, 3.7–4.3% of normalized transcripts differ, so most of the 412 differences noted in the #13 entry were real effects of keyterms rather than noise. Small entity differences between configs are therefore attributable here, but the sample (163 medication mentions) is still small.
- Reproducibility note: both runs record `git_sha` `1d54f4d…-dirty`. The uncommitted changes were the keyterm plumbing committed next (a427ec4), which doesn't change the requests sent beyond the boost list, and that list is recorded in `run.json`.
- Spend: 5.5 h of scorable audio per run at the unverified $0.0043/min ≈ $1.42 per run (four runs so far ≈ $5.70), plus any keyterm surcharge.

## 2026-11-04 — VAD speech bounds (#15): Silero on ONNX Runtime, offline, validated on PriMock57
- **Why VAD end, not `end_s`:** latency (#14) is measured from when the speaker stopped. PriMock57 annotation boundaries carry trailing silence: median **131 ms** (p95 335 ms) after the VAD speech end, and 288 ms (p95 480 ms) of lead before the start. Using `end_s` would charge that to every provider. This is smaller than the issue assumed but not negligible against a 300 ms endpointing budget.
- **Model:** `silero_vad.onnx` from the pinned `silero-vad==6.2.3` wheel (MIT; wheel and model sha256 pinned). The pip package hard-requires torch, so it is not a dependency: `data/fetch_silero_vad.py` downloads the wheel from PyPI, extracts the model into `data/cache/` (gitignored) and checks both hashes. CI runs it before the tests with `REQUIRE_SILERO=1`, so the model test can't silently skip there. Strictly this is a fetch at setup time, not "weights from a pip install" as the issue asked; it's the closest that avoids torch.
- **Algorithm (`vad_id` records it):** 512-sample windows (32 ms) at 16 kHz with 64 samples of context; hysteresis enter ≥ 0.5 / leave < 0.35; merge gaps < 96 ms; drop segments < 64 ms; bounds = first segment start, last segment end. **Offline**, so there's no min-silence wait at the end: the issue's predicted "lag of roughly the min-silence setting" doesn't apply. Resolution ±32 ms.
- **Measured bias (5,079 scorable utterances with Deepgram word timestamps):** VAD end minus Deepgram's last-word end has median **+64 ms** (p25 +16, p75 +144, p95 +368). 91% agree within 250 ms; VAD ends > 250 ms early in 0.3%. Since speech end is the latency anchor, TTFS/endpoint delay measured from it will read about 64 ms *shorter* than if anchored on the acoustic end of the last word (trailing phoneme decay plus window rounding).
- **Deepgram batch word timestamps can run past the end of the audio:** in 299 of 5,079 utterances (5.9%) the last word "ends" after the clip does, e.g. "yes" ending at 4,960 ms on a 955 ms clip. These were 250 of the 262 apparent "VAD ended early" cases, and they're excluded from the figures above. This matters for #14/#18, where TTFS identifies the last word from word timings. The existing rule (ignore words ending > 300 ms past the true speech end) already guards against it; keep it.
- **Acceptance deviation:** the issue's synthetic-burst test is replaced by exact tests of the start/end logic on hand-made probability sequences, plus the real-speech validation above. Silero barely fires on synthetic voice-like signals (peak 0.74, then ~0.3), so a synthetic test would test the signal generator, not our code.
- **Flags (PriMock57, all 7,108):** `no_speech` 159 (49 scorable, all backchannels under 1.5 s such as "Yeah.", "OK.", "Mm-hmm.", many `<UNSURE>`), `low_coverage` 364. Flagged, not dropped. Latency metrics must skip `no_speech` utterances (there is no anchor); the join reports missing utterances rather than filling zeros.
- Sidecar committed: `data/manifests/primock57.speech.jsonl` (1.7 MB, text, no audio).

## 2026-11-04 — Keyterm boost list separated from the scoring lexicon
- `healthcare_intake` now boosts with `data/lexicons/common_uk_generics.txt` (new profile field `keyterms_path`): 86 common UK primary-care generics written without reference to PriMock57, since openFDA, NHSBSA and OpenPrescribing were unreachable. It shares 25 of the scoring lexicon's 49 terms; the other 24 are mostly brands (Ventolin, Piriton, Cerazette), US names (acetaminophen) and spelling variants, which a deployment can't predict. Weakness: hand-written, not ranked by a public dataset. Replace it with a ranked list when one is reachable. Scoring still uses `medications.txt`.
- Registry `keyterms:` takes `profile` (the boost list) or `lexicon` (the scoring lexicon, i.e. the oracle). `deepgram_nova3_batch_keyterms` is now `keyterms: lexicon`; the new `deepgram_nova3_batch_keyterms_common` is `keyterms: profile`.
- **Runs now record the exact boosted list** (`run.json` `keyterms`), and resume refuses a different list. Reason: `"profile"` alone stops describing a run as soon as the profile changes.
- **Relabeled one recorded run:** `results/deepgram-nova3-batch-keyterms/run.json` had `keyterms: profile`, which at its git SHA (8f09f37; profile and lexicon unchanged since) resolved to the 49 lexicon terms. Its settings now read `lexicon` and its `keyterms` field lists those 49 terms. The hypotheses are untouched.
- The report counts false keyterm insertions against each run's own list. A run without boosting is counted against the profile's boost list as a baseline.

## 2026-11-04 — Equivalence layer checked rule by rule: the WER gap is one spelling convention
New diagnostic `python -m harness.metrics.equivalence_breakdown` (output: `reports/generated/equivalence_breakdown.md`). For each rule it reports WER with that rule off, how many utterances it helps or hurts, and the changed utterances, so the matches can be read. A WER drop alone can't show a rule is right, since an over-matching rule also lowers WER. Rules are switchable via `normalize(disable=...)`, for diagnostics only.

On the two Deepgram PriMock57 runs (Whisper-only 10.25% → full layer 7.44%):
- **`okay` accounts for −2.73 of the −2.81 pp.** PriMock57 references write "OK."/"OK" 1,626 times and "Okay" 24 times; Deepgram writes "Okay", and Whisper's normalizer doesn't equate them. 1,426 utterances helped, 0 hurt. It's a real equivalence, but it means **Whisper-only WER on PriMock57 is inflated by about 2.7 pp by a transcription convention** and shouldn't be compared with leaderboard numbers without saying so.
- `numeric_dates` (−0.08 pp, 18 utts), `spoken_dates` (−0.08, 17), `ordinals` (−0.07, 17): all date/ordinal formatting, examples checked, no over-matches.
- `paren_digits`, `units`, `decimals`, `digit_one`, `digit_join`: no effect on this data (PriMock57 has almost no numbers). They stay covered by the normalization fixtures and get re-checked on the synthetic intake set (#17).
- `leading_zero` **adds** 1 error (0 helped): the reference "oh three hundred" goes through Whisper as "300", while Deepgram's "0300" keeps its zero under the rule. That's an under-match (spoken "oh" as zero), recorded as known and not fixed: one utterance, and fixing it means guessing when "oh" is a digit.
- No rule over-matches on this data.

## 2026-11-04 — "Empty on speech" metric; runner flags `suspect_empty`
- **Definition:** a successful request whose raw hypothesis is blank while the *normalized* reference has words (`harness.metrics.wer.empty_on_speech`). Rate = those / successful requests on references with words, Wilson 95% interval (not speaker-clustered). Failed requests are excluded here because they already count in "Failed".
- **The proposed definition ("an empty hyp on a non-empty reference") overcounts by 2.5×.** Whisper drops fillers, so 88 of the 145 empty hypotheses in the plain run are on references like "Mm.", "Um", "<UNSURE>Um</UNSURE>", where empty is correct. Real rate on PriMock57: plain 1.1% [0.9, 1.4] (57/5,105), keyterms 1.2% [1.0, 1.6] (63/5,105); patient side 1.6–1.8%, doctor 0.6–0.7%. Most are 1-word backchannels ("Yeah", "Okay"); about 7–9 per config are 3+ words, e.g. the 11-word sentence in the #13 entry below.
- **Runner:** sets `ResultRow.suspect_empty` with the same predicate, counts it in the run summary, and never retries those rows (retrying only the bad rows would be cherry-picking; `--retry-failed` leaves them alone). Runs recorded before today have no column and read as False. The report recomputes from text, so old runs score the same.
- An agent hears silence on these turns, so for turn-taking this is a missed turn, not just WER. Reported per config so provider differences show up once more vendors run.

## 2026-11-04 — Dates: provider output order + spoken day-month order (equivalence v3)
DOB recall on PriMock57 was 2/21 for both Deepgram configs; it is now 17/21 (81.0% [60.0, 92.3]), and 19/21 after equivalence v4 (2026-11-05 entry). *(Correction 2026-11-05: two of the four misses were attributed below to "references with no day"; they actually contained "ninth", which Whisper doesn't normalize. The two remaining misses are real: wrong month, November → June; wrong day, 22 → 27.)*
- **The fix proposed in the #13 entry below (read hypothesis dates month-first) was necessary but not sufficient: on its own it moves DOB recall from 2/21 to 2/21.** Most misses were word order: people say "the twentieth of April", formatters write "April 20, 1980", so a correct date cost two errors. Both changes were needed.
- **Hypothesis date order per provider config.** New registry field `output_date_order` (`mdy`/`dmy`/unset = same as the reference). References are still read by manifest `language`. Both Deepgram batch configs are `mdy`: `smart_format` writes `04/20/1980` for en-GB audio, and `language=en-GB` doesn't change it (observed 2026-11-04, not from docs). Ambiguous digits (05/06/1990) follow the stated order, never a guess. The report reads the registry (`--registry`, default `configs/providers.yaml`), shows a "Hyp. dates" column, and the normalizer id records both orders when they differ (`.../equiv-v3/dmy,hyp-mdy`).
- **Equivalence v3: "D [of] MONTH" → "MONTH D"**, on both sides, plus "MONTH one" → "MONTH 1" (Whisper spells a lone 1). "may"/"march" count as months only after "of" or before a 4-digit year, so "one may be late" and "we march 2 miles" are untouched (fixtures). Replaces, for dates only, "word-order differences are not equated" (equivalence v2 entry): this is the same convention gap the numeric-date rule already closes. Any other word order still counts. Side effect: the "of" is gone, so reference word counts fall slightly (PriMock57: 56,812 → 56,798) and pooled WER drops 0.1 pp (7.5% → 7.4%; patient 9.0% → 8.8%).
- Normalizer id changes from `equiv-v2` to `equiv-v3`; earlier reports are not comparable digit-for-digit.

## 2026-11-04 — Commit run results, not raw responses
`results/<run_id>/run.json` and `results.parquet` are tracked; everything else under `results/` (the `raw/` provider responses) stays local and ignored. Reason: cloud containers are reclaimed, and the scoring follow-ups to #13 (per-provider date order, empty-transcript rate, equivalence-rule breakdown) need the hypotheses to re-score without paying for new runs. The two Deepgram runs are ~600 KB together. Raw responses are kept out because they carry provider request ids and are ~46 MB uncompressed; the cost is that anything needing word timings or confidences (e.g. telling a provider's empty response apart from a correctly empty transcript) can't be recomputed from the repo. Replaced: all of `results/` gitignored.

## 2026-11-04 — First live Deepgram batch run (#13): how to read the numbers
Ran in a cloud session, not on the owner's machine: batch accuracy needs only the API key and audio, no latency or mic. Report: `reports/generated/primock57_batch.md` (both configs, 5,255 scorable utterances, 114 speakers, 0 failed). Read it with these caveats:
- **Keyterm gain is an oracle upper bound.** Medication recall goes 74.2% → 87.7% (121 → 143 of 163) with WER unchanged (tie, ±0.1 pp), and false keyterm insertions go 3 → 9. But the keyterm list is `data/lexicons/medications.txt`, built from drugs *observed in PriMock57*, so the model was told the test set's exact vocabulary. A real intake line won't know which drugs callers will say. Before the recommender uses this gain, rerun with a lexicon not derived from the test set (openFDA list, or held-out consultations).
- *(Fixed, see "Dates: provider output order" above.)* **Date-of-birth recall (9.5%) is a scoring artifact, not an STT result.** Deepgram transcribes the dates correctly, but `smart_format` writes them US-style (`04/20/1980`, `05/16/1982`, even with `language=en-GB`), and the `dmy` date normalizer reads those as different or invalid dates. Fix in the scorer: accept an all-digit date whose order is unambiguous (day > 12), and decide what to do with ambiguous ones. Until then, ignore the DOB row for any provider whose formatter writes dates as month-first digits.
- **Deepgram batch is not deterministic, and an empty 200 looks like a success.** The keyterms run returned an empty transcript (0 words, confidence 0.0, 6.4 s of speech) for `day1_consultation02:doctor:0047`; re-requested 3× with the same keyterms it came back correct. 8 utterances were empty only with keyterms and 5 only without, mostly backchannels. 412 of 5,255 transcripts differ between the two configs, and part of that is run-to-run noise of unknown size. So WER differences of ~0.1 pp between configs can't be attributed to the setting. Results were left as captured (no selective re-runs). Follow-ups: a test-retest run of one config to measure the noise floor, and making the runner flag empty transcripts on clips with speech as suspect.
- PriMock57 audio via `git lfs pull` is refused by the cloud git proxy; `data/fetch_primock57.sh` now falls back to GitHub's media host with sha256 checks.

## 2026-11-03 — TTFS from word timestamps; speaker-clustered latency intervals
Fixes two weaknesses of the first #14 implementation (entry below):
- **TTFS used the last final as "the final covering the last word"**, so a short trailing final transcribed from silence, or a re-sent final, made a provider look slower (a fixture showed 1,750 ms instead of 250 ms). Finals now carry word timings in audio time; the last word is the latest-ending word that ends within 300 ms of the true speech end, and TTFS is the arrival of the first final containing it. Without word timings it falls back to the last final, labelled `basis: last_final`, and summaries count sessions per basis, so a report can't silently mix the two. #18 adapters must keep word timings.
- **Latency intervals resampled sessions independently**, which was an untested assumption. `summarize(..., clusters=utt→speaker)` now resamples whole speakers (conservative; same rule as WER), and reports `cluster_effect`, the clustered/iid p50 interval-width ratio, so real data shows whether speaker clustering mattered. Simulated data with speaker effects gives a ratio > 2; independent data gives ≈ 1. Reports (#22) should cluster by default.

## 2026-11-03 — Streaming trace format and latency metrics
- One trace per session, all metrics computed afterwards from traces, so they are tested on hand-specified traces without a live provider. Schema: `harness/streaming/README.md`.
- Anchor: an audio moment (speech start/end from #15) maps to the time the chunk containing it was *sent*. A late chunk moves the anchor with it, so pacing jitter isn't charged to the provider.
- TTFS: see the entry above (word timestamps). Endpoint delay is natural-mode only; finalize latency is forced-mode only; endpoints before the anchor are counted as premature for #20.
- Timeouts are +inf in percentile aggregates, with the timeout rate beside them: if >5% of sessions never finalize, p95 reads as the timeout rather than a number computed over survivors. Percentiles use the `inverted_cdf` method (an observed value, no interpolation) so inf doesn't turn into NaN.
- Percentile intervals: see the entry above (speaker clustering).

## 2026-11-03 — Forced finalization as a separate latency; configurable host
- Prompted by an external comment on #20 (from someone who disclosed working for an STT vendor; the comment was later deleted). Judged on its merits:
- **Adopted:** measure finalize latency separately. In `forced` mode the adapter sends the provider's explicit finalize when the paced audio reaches the true speech end, and we time finalize → final. TTFS mixes model + network speed with the provider's endpointing policy; an agent with its own turn detector (our M5 controller) only needs the former, and the recommender scores STT and turn detection as separate layers. Providers without an explicit finalize show "not supported". Added to #14 and #18.
- **Adopted:** registry `base_url` (https only). The Deepgram adapter uses it, so any Deepgram-protocol endpoint (self-hosted, proxy, compatible vendor) is a registry entry; other adapters reject it. "Compatible" is checked per setting, never assumed.
- **Not adopted:** adding the commenter's own service as a fifth provider. No public footprint could be found, and providers are chosen by relevance to customers and hiring teams, not by request.

## 2026-10-06 — Batch adapters
- Plain `httpx`, no vendor SDKs: every request is visible and testable with a mock transport; no SDK version drift.
- Every provider receives the same 16 kHz mono WAV produced by `harness/audio.py`.
- Adapters reject settings they don't map (a typo can't become a silent default). Keyterm boosting is its own configuration (`*_keyterms`, `keyterms: profile` + `--profile`), so boosting is measured, never a hidden default.
- ElevenLabs audio-event tags are forced off (`tag_audio_events=false`).
- AssemblyAI is asynchronous (upload → create → poll); a poll timeout is retryable, a transcript `error` status is permanent.
- Written from recollection: vendor docs are blocked from the cloud environment. Request shapes and response fixtures are unverified; `harness/providers/README.md` holds the checklist, and the first live run must replace the fixtures with captured responses before results are trusted.

## 2026-10-06 — Audio I/O
- One decoding path (`harness/audio.py`) for adapters, augmentation and VAD, so every provider hears identical audio. Whole files are decoded once (ffmpeg → mono int16 at the target rate, cached) and segments are cut in NumPy: sample-exact for every format, where ffmpeg's own seeking isn't (MP3).
- The decoded file's real sample rate is recorded on every clip; a mismatch with the manifest warns (Common Voice's 48 kHz is an assumption until decoded).
- µ-law encoding is byte-identical to ffmpeg's `pcm_mulaw` over all 65,536 inputs (tested exhaustively). ffmpeg builds its encoder as a nearest-level lookup table rather than the Sun/ITU arithmetic; the two differ by one code at segment boundaries on 512 inputs. We match ffmpeg because the augmentation pipeline's telephony codec is ffmpeg, and two µ-law paths that disagree would make "telephony" mean two things.
- `pace()` schedules chunk k at t0 + k·chunk_ms on the monotonic clock (absolute deadlines), so a late chunk never shifts later ones; each chunk records scheduled and actual time, which the latency metrics use (#14). Wall-clock tests carry a `timing` marker (`pytest -m "not timing"` on a loaded machine).
- CI installs ffmpeg explicitly.

## 2026-10-06 — Provider registry and batch runner
- `configs/providers.yaml` holds one entry per *configuration* (provider + pinned model id + mode + settings). Prices carry `billing_basis` (audio vs session duration vs per channel), `source` and `as_of`, because the basis changes cost per conversation minute more than the headline rate. BAA status defaults to `unknown` and needs a source to be `yes`/`no`.
- Everything is `verify: true` until checked against vendor docs on the owner's machine; a verified entry must have a price. The CLI warns when running an unverified config.
- Batch and streaming configs are separate entries (`*_batch`, `*_stream`); batch exists to get a first real offline report quickly, and the report labels the mode.
- Runner: run id defaults to the config id so re-running resumes; results flushed every 20 utterances; failed requests recorded with the error and an empty transcript (scored as all-deletions by the report), skipped on resume unless `--retry-failed`. Retries only for `RetryableError` (429/5xx/timeouts), exponential backoff, 3 attempts. A resume refuses a run directory made with a different provider/model/settings.
- `git_sha` gets a `-dirty` suffix when the working tree has uncommitted changes, so a result can't silently claim a clean commit.

## 2026-10-06 — LibriSpeech and Common Voice loaders
- `audio_path` is computed relative to an explicit `--data-root`, so manifests stay portable regardless of where a dataset is unpacked.
- Common Voice is sampled, not loaded whole: 400 clips from the held-out `test.tsv` by default. Accents take turns (round robin) so the set measures *spread across accents*, not Common Voice's skewed population; WER on it is not an estimate of WER on "typical" Common Voice audio, and the report must not present it as one.
- The accent field has been free text since v8, so accents with fewer than 5 clips are pooled into one "other" stratum; otherwise hundreds of one-off strings would crowd out the main accents. Labels on clips are unchanged.
- At most 10 clips per speaker (`client_id`), so speaker clustering in the bootstrap has many clusters.
- Neither dataset can be fetched from the cloud environment (openslr.org blocked; Common Voice needs a terms acceptance), so both loaders are verified on fixtures that mirror the real layouts, including the pre-v8 `accent` column. The first real run on the owner's machine is the end-to-end check; expected counts are in `data/README.md`.
- Language tags: both `en` (no region), so numeric dates read month-first. LibriSpeech references contain no numeric dates; Common Voice sentences are rarely numeric.

## 2026-10-06 — Results format and offline report rules
- One run = one configuration. `<results>/<run_id>/run.json` (RunMeta: config, pinned model id, settings, date, git SHA) + `results.parquet` (one row per utterance: raw hypothesis, raw-response path, timestamps, error). Rows store the *raw* hypothesis; the normalizer id lives in the report header because normalization happens at scoring time (the issue asked for it per row; that would record a choice not yet made).
- Paired comparison: within each table, only utterances every run covers are scored; the number dropped is reported. A failed request is scored as an empty transcript (all deletions), never skipped, so unreliable providers aren't flattered.
- Real and synthetic audio are separate sections, never pooled. Each section has an "All" table plus one per subset when there are several.
- Intervals are speaker-clustered by default (`--cluster-by none` to resample utterances). Pairwise p-values are Holm-adjusted within each table.
- **No winner is called with fewer than 10 clusters** in a table ("too few speakers (n) to call"): with 2 speakers the bootstrap reported p = 0.001 on the fixture, which is meaningless. Ties and intervals are still shown.
- Headline WER (Whisper + equivalence layer) sits beside Whisper-only WER for leaderboard comparability; the per-utterance date order comes from the manifest `language`.
- Golden-file test pins the rendered report; regenerate deliberately with `UPDATE_GOLDEN=1 uv run pytest tests/test_report.py`. Scale check: PriMock57 (5,255 utterances, 2 configs, profile) renders in ~35 s.

## 2026-10-06 — PriMock57 loader choices
- Utterances containing `<UNIN/>` or the undocumented `<INAUDIBLE_SPEECH/>` are kept in the manifest but excluded from scoring: the reference is missing words there, so a provider that transcribes them would be charged insertions. This excludes 26% of utterances (1,853 of 7,108). They are likely the harder audio, so PriMock57 accuracy is optimistic relative to its full difficulty; the memo should say so. `<UNSURE>` spans are kept (inner text is the transcriber's best guess). No utterance is under the 0.3 s minimum.
- Seven known drug-name misspellings are corrected in `ref_text`, with the original in the new `ref_text_original` manifest field (5 utterances affected).
- New manifest field `language` (BCP-47). PriMock57 is `en-GB`, and `date_order_for(language)` turns that into day-first date reading, so the runner reads it from the data instead of having to remember it. Month-first: US-style regions and bare/missing tags; everything else day-first.
- Speaker IDs are `{consultation}_{role}`. Clinician identities aren't published, so the same doctor appears as several speakers and doctor-side speaker clustering understates correlation. Patients are 57 distinct actors. For the intake scenario the patient side is the caller, and it is unaffected.
- The generated manifest (3.7 MB of CC BY 4.0 text, no audio) is committed with attribution, so scoring and reports work without fetching the dataset; a test checks it stays valid and consistent with the correction map.

## 2026-10-06 — Entity scoring rules
- Tagging runs on the normalized reference so spans line up with the WER alignment. Recovery is strict (every token correct); a per-entity character error rate sits beside it so one wrong digit in a phone number isn't scored like a missing phone number.
- "Formatted" = recovered and the raw hypothesis carries the entity's numbers as digits. It measures downstream usability, separate from accuracy.
- The `number` builtin yields to every other category (drops overlapping spans), so a billing "amount" doesn't also count account numbers or the day in a date.
- Medication lexicon built from names observed in PriMock57 (49, hand-checked); openFDA merge deferred to the owner's machine because the cloud environment can't reach api.fda.gov. Reference misspellings (paracetemol, lisonopril…) are not lexicon terms; the PriMock57 loader (#5) should correct them, otherwise a provider that spells correctly is scored as wrong.
- PriMock57 alone has too few dosages (18), dates (21) and phones (0 real) for intervals. Synthetic intake scripts are required for those categories, not optional.
Rules in `harness/metrics/ENTITIES.md`.

## 2026-10-06 — Equivalence layer v2: work around Whisper's digit handling
Found while designing entity tagging: Whisper's normalizer rewrites the digit 1 as "one" (`1.5` → `one.5`, `5 1 5` → `5 one 5`, `2.1` → `2 one`), drops leading zeros (`07700` → `7700`, while spoken "oh seven seven…" keeps them), turns "zero point five" into `.5`, and deletes parenthesized text (the `(555)` area code). Each would corrupt dosage and phone-number scoring. v2 adds, each with a fixture:
- Before Whisper: digits in parentheses are unwrapped; numbers with a leading zero are spelled digit by digit so Whisper rebuilds them with the zero.
- After Whisper: `one.N` → `1.N`, `.N` → `0.N`, `one` next to a digit group → `1`; runs of digit groups totalling ≥7 digits, or ≥3 single digits, are joined into one token (grouping of phone/account numbers is formatting). Two-token runs under 7 digits are not joined (`10 1` could be "10, 1").
Known remaining: `2.1` loses its decimal point inside Whisper (`2 1`) identically on both sides, so it is still equal; "half a" is not 0.5.
Replaces: equivalence layer v1 (entry below); normalizer id changes from `equiv-v1` to `equiv-v2`.

## 2026-10-06 — Statistics conventions
- Pooled-WER intervals: paired percentile bootstrap (default 10,000 resamples, 95%). All systems share the same resample weights, so differences are paired. With `cluster_ids` (speakers), whole clusters are resampled; use it whenever a speaker contributes many utterances, since iid resampling understates uncertainty when difficulty clusters by speaker (a test shows the clustered interval is >1.5x wider on such data).
- Bootstrap p-value: two-sided, 2 x min(share of resampled differences <= 0, share >= 0), with the +1 correction ((count + 1)/(B + 1)) so it is never reported as 0; capped at 1. Identical systems give p = 1.
- Resamples that draw only empty references (possible only when some references are empty) are dropped and counted in `dropped_resamples`.
- "Distinguishable" means the difference interval strictly excludes 0; touching 0 is a tie.
- Proportions use the Wilson score interval; the normal quantile comes from the stdlib (`statistics.NormalDist`), so no SciPy dependency.
- Holm step-down adjusts p-values when many pairwise claims are made at once.

## 2026-10-06 — Equivalence layer on top of Whisper normalization
Headline WER uses Whisper normalization **plus** a small, versioned equivalence layer (`EQUIVALENCE_VERSION`, id from `normalizer_id()`); plain-Whisper WER is kept as a second column for comparability with public leaderboards. Reason: a provider that formats "10 mg" should not lose to one that writes "ten milligrams" against a spoken reference. Rules (all domain-neutral, each with a fixture):
- Unit abbreviations ↔ spelled units (mg, mcg/µg, ml, kg, km; US and UK spellings).
- Numeric dates (`03/04/1980`, `03-04-1980`; same separator twice, `/` or `-` only) → month name. Day/month order is a parameter (`mdy` default, `dmy` for UK-style references); it is part of the normalizer id. The runner should derive it from the profile/dataset locale.
- Ordinal suffixes dropped (`3rd` → `3`), so "march 3rd" equals "03/03".
- `O.K.` / `ok` → `okay` (Whisper alone turns `O.K.` into `0 k`).
Rejected: joining hyphenated words to equate `co-pay`/`copay`. It broke the more common hyphen-vs-space case (`follow-up`/`follow up`), which Whisper already equates. A test enforces that the layer never separates a pair Whisper equates.
Still not equated (recorded as KNOWN MISMATCH): hyphenated vs closed compounds, day-first dates under `mdy`, word-order differences (correctly), synonyms (correctly). Digit-by-digit speech collapsing to one token (`one two three four` → `1234`) is handled in entity scoring (#7) with a character-level rate, not here.

## 2026-10-06 — WER normalization and empty references
- Normalizer: `whisper-normalizer` (standalone port of OpenAI Whisper's `EnglishTextNormalizer`; avoids pulling in torch). Version pinned in `uv.lock`; exposed as `WHISPER_ID`, and the full id including the equivalence layer comes from `normalizer_id()`. Being a third-party port, it could diverge from OpenAI's; the fixture table pins its behavior.
- Transcriber markup (`<TAG>…</TAG>`, `<TAG/>`) is stripped generically before normalization: paired tags keep their inner text, self-closing tags are dropped. Utterances that shouldn't be scored at all are excluded by the loader (`exclude_reason`), not by the normalizer.
- Empty reference: excluded from mean per-utterance WER (undefined), but its insertions count in pooled WER (hallucinated speech on silence is a real error). Pooled/mean raise if nothing is scorable.

## 2026-10-06 — Profile schema and reference-suite matching
- Relative paths in a profile resolve against the profile file's directory (portable: a customer profile folder can carry its own lexicons and manifests).
- Entity categories are compared by **signature**: builtin type for builtins, name for lexicon/regex. So `date_of_birth` and `due_date` both count as `date`.
- Matching rule: rank suites by (channel supported, languages shared, entity signatures covered), highest first; ties go to the alphabetically first `suite_id`. A match is a proxy unless the suite supports the channel, *every* profile language and *every* entity signature — partial language coverage (e.g. en-US + es-US against an English-only suite) is a proxy.
- `min_entity_recall` keys must name defined entities (catches typos that would silently drop a constraint). `min_check_pass_rate` keys are not checked yet; they're validated against conversation scripts in M3.
- Seed lexicons (`data/lexicons/*.txt`) were placeholders so the example profiles load; #7 replaced the medication one with a list built from PriMock57 (the billing one remains a seed).

## 2026-10-06 — Manifest schema is strict
`Utterance` rejects unknown fields and is immutable; `start_s`/`end_s` are both set or both None; `parent_utt_id` is required exactly when `augmentation` is non-empty; `audio_path` must be relative to the data root. Reason: every loader, augmenter and provider adapter shares this format, so silent shape drift would corrupt comparisons; failing at load time is cheaper than a wrong WER table. Schema doc: `harness/datasets/README.md`.

## 2026-10-06 — Recommend the whole cascaded stack, in a single version
The tool recommends STT, turn detection, LLM and TTS (plus settings), and the assembled stack is re-checked end to end. There is no v1/v2 split; previously deferred items become "stretch, after M7". LLM is scored by deterministic rule checks on scripted conversations (the LLM is tested, never the judge); TTS by TTFB, round-trip WER through a fixed different-vendor STT, entity pronunciation and UTMOS, with a small human listening test used only to validate UTMOS. Speech-to-speech models are excluded (a third architecture). Reason: owner wants a full-stack recommendation. Cost: estimate grows from ~5 to ~8–10 weeks; mitigated by milestones that each end in a demo.
Replaces: "v1 recommends STT/turn detection only" (in the entry below) and the "v1 scope cut" deferral list.

## 2026-10-06 — Commit directly to main
Solo project, one session at a time: a PR adds a click without adding review. CI runs on push to `main`; checks are run locally before every push. Branch + PR only when sessions run in parallel. Cloud sessions are assigned their own branch, so start each with "push to main when done".
Replaces: "Branch per issue, squash-merge to main" (below).

## 2026-10-06 — Branch per issue, squash-merge to main *(superseded above)*
Owner is the only contributor, but parallel Claude Code sessions, CI-before-merge and a reviewable diff per issue justify one branch + PR per issue. Owner merges (squash) and deletes the branch. `main` is the default branch.

## 2026-10-06 — The tool is a general recommender; healthcare is the first reference use case
Input is a use-case profile (use case, constraints, domain terms, optional customer audio); output is a recommended STT model + settings + turn-detection policy with intervals and "breaks at" thresholds. Two modes: customer audio (high confidence) and no audio (falls back to the closest built-in reference suite, labeled as proxy). Healthcare intake is the first reference suite and the demo agent. Reason: the owner's intent is a tool any FDE can point at any use case. A constraints-only recommender without measurement is just a filtered leaderboard, which already exists, so measurement on the customer's audio stays central.
v1 recommends STT model/settings/turn detection only; LLM and TTS are measured as latency/cost contributors but not recommended (v2: needs task evals and listening tests).
Replaces: "Scenario is healthcare patient intake" (below), which framed the whole tool as healthcare-specific.

## 2026-10-06 — Scenario is healthcare patient intake *(superseded above: healthcare is now the first reference use case, not the scope)*
Fictional clinic intake/appointment line. Reason: PriMock57 gives openly licensed (CC BY 4.0, verified on the repo LICENSE.md) medical conversation audio with timed utterance transcripts; medication/dosage entity scoring is the most persuasive metric in the research. Replaced: loan-servicing / collections agent.
Known weakness: PriMock57 is mock GP consultations with UK accents, not intake phone calls. It's a proxy; the memo says so.

## 2026-10-06 — Harness is the backbone, agent is the scenario
The STT bake-off/recommendation harness is the product. The intake agent exists to measure in-pipeline metrics (TTFA, endpointing, barge-in) and to be the demo. Replaced: two competing framings (agent-with-evals vs vendor harness).

## 2026-10-06 — v1 scope cut
Keep: 4 provider configs, 5 dataset groups + telephony/noise variants, WER + entity + streaming + endpointing + in-pipeline metrics, one memo. Defer to v2: Parakeet/GPU, 20-stream load, Opus packet loss, TTS scoring, self-recorded set. Reason: full research plan exceeds 4–5 weeks for a first voice agent build.

## 2026-10-06 — Pipecat, with two hand-built pieces
Pipecat (pinned) for transport and provider plumbing. Hand-built: (1) turn-taking/barge-in controller with event tracing, (2) one raw-WebSocket streaming STT client. Reason: framework keeps every layer visible without weeks of audio plumbing; the hand-built pieces are where depth shows. Controller policy logic is pure Python, unit-tested on recorded event traces, so framework upgrades don't silently break it.

## 2026-10-06 — Pooled WER is the headline WER
Pooled = total errors / total reference words. Per-utterance mean is reported alongside. Reason: per-utterance mean overweights short turns, which dominate voice-agent audio.

## 2026-10-06 — No LLM in scoring or recommendation
Semantic/LLM-judged WER is non-deterministic and conflicts with a reproducible recommendation. May appear later only as a clearly labeled secondary column.

## 2026-10-06 — Recommender treats overlapping CIs as ties
Hard-filter on constraints using CI bounds (e.g. upper 95% bound of p95 TTFA must be under budget), then rank survivors; ties broken by cost, then p95 latency. It may answer "not distinguishable".

## 2026-10-06 — Open corpora only; no social-video audio
YouTube/TikTok/Instagram terms bar downloading/scraping; no ground-truth transcripts; redistribution risk. Publish manifests and augmentation recipes, never audio.

## 2026-10-06 — Repo is the only source of truth
Decisions made in chat don't exist until written here or in an issue.
