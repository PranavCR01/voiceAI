# Degradation under `phone_noisy_snr5`

Paired per utterance against the same config on the parent (clean) audio; 95% bootstrap intervals resampling whole speakers. Difference = augmented − clean WER.

| Config | Clean WER | Augmented WER | Difference [95% CI] | Relative | p | Utts | Speakers |
|---|---|---|---|---|---|---|---|
| assemblyai_batch | 6.56% | 12.63% | +6.07 pp [+5.35, +6.85] | +93% | 0.0002 | 5255 | 114 |
| elevenlabs_scribe_v2_batch | 5.65% | 13.34% | +7.69 pp [+6.88, +8.56] | +136% | 0.0002 | 5255 | 114 |
| deepgram_nova3_batch | 7.42% | 22.22% | +14.80 pp [+13.47, +16.18] | +199% | 0.0002 | 5255 | 114 |
