# Utterance manifests

Every dataset loader, augmentation step and provider run reads and writes one format: a JSONL file with one `Utterance` per line (`harness/datasets/manifest.py`). Manifests hold text and metadata only; audio stays outside the repo under a data root.

## Fields
| Field | Type | Rules |
|---|---|---|
| `utt_id` | str | Unique within a manifest, deterministic across runs. Pattern `^[A-Za-z0-9][A-Za-z0-9._:-]*$`. Convention: `dataset:recording:speaker_or_channel:index`, colon-separated. |
| `dataset` | str | e.g. `primock57`, `librispeech`, `common_voice`. |
| `subset` | str | e.g. `test-clean`, `patient`, a Common Voice release version. |
| `speaker_id` | str | Used for cluster bootstrap; unique per real speaker within the dataset. |
| `audio_path` | str | Relative POSIX path under the data root; no absolute paths, `..` or backslashes. Resolve with `Utterance.resolve_audio(data_root)`. |
| `channel` | int \| None | Channel index in a multichannel file; None = mono or whole file. |
| `start_s`, `end_s` | float \| None | Segment within a longer file. Both set or both None; `end_s > start_s`; `start_s >= 0`. |
| `ref_text` | str | Verbatim reference transcript (may contain dataset tags; normalization happens in metrics). |
| `sample_rate` | int | Of the audio at `audio_path`, > 0. |
| `license` | str | SPDX-style id, e.g. `CC-BY-4.0`, `CC0-1.0`. |
| `synthetic` | bool | True for TTS-generated audio; reported in separate tables. |
| `augmentation` | list[AugmentStep] | Empty for originals. Each step: `kind`, `params` (JSON values), `seed` (int \| None). |
| `parent_utt_id` | str \| None | Required iff `augmentation` is non-empty; must differ from `utt_id`. |
| `exclude_reason` | str \| None | Set to keep an utterance in the manifest but skip it in scoring (e.g. `unintelligible`, `too_short`). |
| `language` | str \| None | BCP-47 tag of the reference text (`en-GB`). Decides how numeric dates are read when normalizing (`date_order_for`). |
| `ref_text_original` | str \| None | The transcript before the loader corrected it (e.g. a misspelled drug name). Only set when `ref_text` differs. |

Unknown fields are rejected, and utterances are immutable once loaded.

## Reading and writing
- `read_manifest(path)` skips blank lines and raises `ManifestError` naming the file and line on any invalid line, or on duplicate `utt_id`s.
- `write_manifest(path, utts)` sorts by `utt_id`, so regenerating a manifest from the same input yields identical bytes and clean diffs.
