# Augmentation (#16)

Recipes live in `configs/augment.yaml`; `run.py` applies one to a manifest and writes augmented WAVs under `<data-root>/augmented/<recipe>/` (never committed) plus a child manifest (may be committed).

```bash
./data/fetch_augment_sources.sh                      # SLR28 noises + RIRs into data/raw/augment/
uv run python -m harness.augment.run --manifest data/manifests/primock57.jsonl \
    --data-root data/raw --recipe telephony_mulaw \
    --out data/manifests/primock57.telephony_mulaw.jsonl
# Score it in its own results directory (run ids default to the config id):
uv run python -m harness.providers.runner --config deepgram_nova3_batch \
    --manifest data/manifests/primock57.telephony_mulaw.jsonl --data-root data/raw \
    --results results_augmented/telephony_mulaw/
```

## Child utterances
`utt_id` = `<parent>:<recipe>`, `parent_utt_id` = parent, same `ref_text`, `speaker_id`, `subset`, `language`, `exclude_reason`. `audio_path` points at the augmented WAV, `start_s`/`end_s`/`channel` are cleared, and `sample_rate` is the output rate (8000 after a mu-law recipe). Providers still receive 16 kHz: `load_clip` upsamples, as a phone-to-cloud path would. Excluded parents are skipped unless `--include-excluded`.

## Steps
Every step records `kind`, a `seed` and the parameters needed to reproduce it:

| kind | config | recorded |
|---|---|---|
| `resample` | `rate` | `rate_in`, `rate_out`, `ffmpeg_args`, `ffmpeg_version` |
| `bandpass` | `low_hz` (300), `high_hz` (3400), `sections` (2) | `rate`, the three settings, `ffmpeg_args`, `ffmpeg_version` |
| `mulaw` | — | `rate`, `ffmpeg_args` (encode, decode), `ffmpeg_version` |
| `opus` | `bitrate` (e.g. `12k`) | `rate`, `bitrate`, `ffmpeg_args`, `ffmpeg_version` |
| `noise` | `snr_db` | `noise_file`, `noise_offset_samples`, `noise_rate`, `noise_tiled`, `snr_region` (`vad`/`whole_clip`), `snr_region_s`, `noise_gain`, `peak_scale` |
| `reverb` | — | `rir_file`, `rir_rate`, `direct_index`, `level_scale` |

- **Seeds:** each step's seed is derived from (run `--seed`, parent `utt_id`, step index) by SHA-256, so the result doesn't depend on order, `--limit` or the rest of the manifest. Same recipe + seed → byte-identical WAV and manifest.
- **SNR** is computed over the speech region: the VAD bounds from `<manifest>.speech.jsonl` (#15) when present, else the whole clip (recorded). On PriMock57-style clips the whole-clip SNR would read worse than labelled, because leading and trailing silence counts as "speech". If the mix would clip, the whole mix is scaled down (`peak_scale`), which keeps the SNR.
- **Reverb** is aligned on the RIR's largest sample (the direct path), so speech isn't delayed, and the output is scaled back to the input's power over the speech region.
- **Band-pass** is `sections` cascaded 2-pole Butterworth high-pass and low-pass filters (ffmpeg `highpass`/`lowpass`, 12 dB/octave each): with 2 sections, −6 dB at 300 and 3,400 Hz, >30 dB down at 100 Hz, ~−5 dB at 3.9 kHz. A rough stand-in for the ITU-T G.712 telephone channel, not any particular network.
- **Parallel:** `--workers N` (default: CPU count) runs utterances on a thread pool; the output is identical for any N (tested), because seeds depend only on the utterance.
- **Codecs** run through ffmpeg with bit-exact flags; the recorded args can be replayed (a test does). A different ffmpeg build may produce different bytes, which is why the version is recorded. Opus output is trimmed/padded to the input length so timing doesn't move.
- Noise/RIR files are chosen from the sorted list under the configured source directory, so adding files to it changes which file a seed picks; record the source set when publishing results.
