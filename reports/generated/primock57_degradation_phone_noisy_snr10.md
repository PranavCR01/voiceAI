# Degradation under `phone_noisy_snr10`

Paired per utterance against the same config on the parent (clean) audio; 95% bootstrap intervals resampling whole speakers. Difference = augmented − clean WER.

| Config | Clean WER | Augmented WER | Difference [95% CI] | Relative | p | Utts | Speakers |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.56% | 10.30% | +3.74 pp [+3.26, +4.27] | +57% | 0.0002 | 5255 | 114 |
| elevenlabs_scribe_v2_batch | 5.65% | 10.71% | +5.06 pp [+4.46, +5.71] | +90% | 0.0002 | 5255 | 114 |
| deepgram_nova3_batch | 7.42% | 17.10% | +9.68 pp [+8.76, +10.64] | +130% | 0.0002 | 5255 | 114 |
