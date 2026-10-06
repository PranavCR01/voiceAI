# Attribution

Manifests contain reference transcripts and metadata only, never audio.

## primock57.jsonl
Transcripts from **PriMock57** by Babylon Health (Papadopoulos Korfiatis et al., "PriMock57: A Dataset Of Primary Care Mock Consultations", ACL 2022), https://github.com/babylonhealth/primock57, commit `cd2ac707ad03cb4d2531f4ec6b90c659bf4357c5`, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

Changes: transcripts were split into one record per utterance with timings; seven misspelled drug names were corrected (originals kept in `ref_text_original`; list in `harness/datasets/primock57.py`); utterances with `<UNIN/>` or `<INAUDIBLE_SPEECH/>` are marked excluded.
