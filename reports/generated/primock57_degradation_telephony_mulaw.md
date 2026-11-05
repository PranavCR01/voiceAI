# Degradation under `telephony_mulaw`

Paired per utterance against the same config on the parent (clean) audio; 95% bootstrap intervals resampling whole speakers. Difference = augmented − clean WER.

| Config | Clean WER | Augmented WER | Difference [95% CI] | Relative | p | Utts | Speakers |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.56% | 7.27% | +0.71 pp [+0.55, +0.88] | +11% | 0.0002 | 5255 | 114 |
| deepgram_nova3_batch | 7.42% | 8.56% | +1.14 pp [+0.91, +1.38] | +15% | 0.0002 | 5255 | 114 |
| elevenlabs_scribe_v2_batch | 5.65% | 6.80% | +1.15 pp [+0.90, +1.42] | +20% | 0.0002 | 5255 | 114 |
