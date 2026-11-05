# Degradation under `telephony_g712`

Paired per utterance against the same config on the parent (clean) audio; 95% bootstrap intervals resampling whole speakers. Difference = augmented − clean WER.

| Config | Clean WER | Augmented WER | Difference [95% CI] | Relative | p | Utts | Speakers |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.56% | 7.61% | +1.05 pp [+0.86, +1.26] | +16% | 0.0002 | 5255 | 114 |
| deepgram_nova3_batch | 7.42% | 9.79% | +2.36 pp [+2.04, +2.71] | +32% | 0.0002 | 5255 | 114 |
