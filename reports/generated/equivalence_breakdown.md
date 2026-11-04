# Equivalence layer: per-rule breakdown

- **Data:** `data/manifests/primock57.jsonl`, 5255 utterances scored by every run.
- **Diagnostic only.** Scoring always applies every rule. "Without" = that one rule off, all others on. Helped/hurt = utterances with fewer/more errors *because of* the rule. A WER drop doesn't prove a rule right (an over-match also lowers WER): read the examples.

| Config | Whisper only | Full layer |
|---|---|---|
| deepgram_nova3_batch | 10.25% | 7.44% |
| deepgram_nova3_batch_keyterms | 10.24% | 7.43% |

| Rule | Config | WER without | Change from rule | Utts helped / hurt | Errors removed / added |
|---|---|---|---|---|---|
| `okay` | deepgram_nova3_batch | 10.16% | -2.73 pp | 1426 / 0 | 1549 / 0 |
| `numeric_dates` | deepgram_nova3_batch | 7.51% | -0.08 pp | 18 / 0 | 43 / 0 |
| `paren_digits` | deepgram_nova3_batch | 7.44% | +0.00 pp | 0 / 0 | 0 / 0 |
| `leading_zero` | deepgram_nova3_batch | 7.43% | +0.00 pp | 0 / 1 | 0 / 1 |
| `units` | deepgram_nova3_batch | 7.44% | +0.00 pp | 0 / 0 | 0 / 0 |
| `ordinals` | deepgram_nova3_batch | 7.51% | -0.07 pp | 17 / 0 | 41 / 0 |
| `decimals` | deepgram_nova3_batch | 7.44% | +0.00 pp | 0 / 0 | 0 / 0 |
| `digit_one` | deepgram_nova3_batch | 7.44% | +0.00 pp | 0 / 0 | 0 / 0 |
| `digit_join` | deepgram_nova3_batch | 7.44% | +0.00 pp | 0 / 0 | 0 / 0 |
| `spoken_dates` | deepgram_nova3_batch | 7.51% | -0.08 pp | 17 / 0 | 44 / 0 |
| `okay` | deepgram_nova3_batch_keyterms | 10.16% | -2.72 pp | 1422 / 0 | 1546 / 0 |
| `numeric_dates` | deepgram_nova3_batch_keyterms | 7.51% | -0.08 pp | 18 / 0 | 43 / 0 |
| `paren_digits` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 0 | 0 / 0 |
| `leading_zero` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 1 | 0 / 1 |
| `units` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 0 | 0 / 0 |
| `ordinals` | deepgram_nova3_batch_keyterms | 7.50% | -0.07 pp | 17 / 0 | 41 / 0 |
| `decimals` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 0 | 0 / 0 |
| `digit_one` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 0 | 0 / 0 |
| `digit_join` | deepgram_nova3_batch_keyterms | 7.43% | +0.00 pp | 0 / 0 | 0 / 0 |
| `spoken_dates` | deepgram_nova3_batch_keyterms | 7.51% | -0.08 pp | 17 / 0 | 44 / 0 |

## Examples (deepgram_nova3_batch; most errors removed first)

### `okay`

| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | Ref (without) | Hyp (without) |
|---|---|---|---|---|---|
| `primock57:day1_consultation06:doctor:0044` | 2 / 5 | okay okay fine okay so just to really recap so you are really in the last couple of weeks you have been feeling breathless but worse in the last couple of days you mentioned you had a bit of a dry cough | okay okay fine okay so just to really recap so really in the last couple of weeks you have been feeling breathless but worse in the last couple of days you mentioned you had a bit of a dry cough | ok ok fine ok so just to really recap so you are really in the last couple of weeks you have been feeling breathless but worse in the last couple of days you mentioned you had a bit of a dry cough | okay okay fine okay so just to really recap so really in the last couple of weeks you have been feeling breathless but worse in the last couple of days you mentioned you had a bit of a dry cough |
| `primock57:day1_consultation08:doctor:0045` | 0 / 3 | okay okay are you eating and drinking okay | okay okay are you eating and drinking okay | ok ok are you eating and drinking ok | okay okay are you eating and drinking okay |
| `primock57:day1_consultation08:doctor:0051` | 2 / 5 | okay and your waterworks are all okay you are passing urine okay | okay and your waterworks are all okay you passed urine okay | ok and your waterworks are all ok you are passing urine ok | okay and your waterworks are all okay you passed urine okay |
| `primock57:day1_consultation09:doctor:0032` | 0 / 3 | no fever okay fine sorry okay in terms of your bowel are your bowels working okay | no fever okay fine sorry okay in terms of your bowel are your bowels working okay | no fever ok fine sorry ok in terms of your bowel are your bowels working ok | no fever okay fine sorry okay in terms of your bowel are your bowels working okay |
| `primock57:day1_consultation09:patient:0106` | 1 / 4 | okay okay that that makes sense ohh okay thank you so much | okay okay that that makes sense okay thank you so much | ok ok that that makes sense ohh ok thank you so much | okay okay that that makes sense okay thank you so much |
| `primock57:day1_consultation11:doctor:0048` | 5 / 8 | okay so you are feeling hoarse okay and in terms of your waterworks are you passing urine okay | okay so you are getting hot okay in terms of your water works are you passing urine okay | ok so you are feeling hoarse ok and in terms of your waterworks are you passing urine ok | okay so you are getting hot okay in terms of your water works are you passing urine okay |
| `primock57:day1_consultation14:doctor:0042` | 2 / 5 | okay okay okay alright fine and in terms of any other symptoms so have you had any nausea have you had any vomiting | okay okay okay alright fine in terms of any other symptoms have you had any nausea have you had any vomiting | ok ok ok alright fine and in terms of any other symptoms so have you had any nausea have you had any vomiting | okay okay okay alright fine in terms of any other symptoms have you had any nausea have you had any vomiting |
| `primock57:day2_consultation02:doctor:0010` | 0 / 3 | okay okay great okay so tell me a bit about what has been happening you said you mentioned in the notes that you have got a problem with your elbow | okay okay great okay so tell me a bit about what has been happening you said you mentioned in the notes that you have got a problem with your elbow | ok ok great ok so tell me a bit about what has been happening you said you mentioned in the notes that you have got a problem with your elbow | okay okay great okay so tell me a bit about what has been happening you said you mentioned in the notes that you have got a problem with your elbow |

### `numeric_dates`

| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | Ref (without) | Hyp (without) |
|---|---|---|---|---|---|
| `primock57:day2_consultation09:patient:0010` | 0 / 3 | august 12 1958 | august 12 1958 | august 12 1958 | 08121958 |
| `primock57:day2_consultation10:patient:0006` | 1 / 4 | sure so it is ayrton warren and my date of birth is the may 16 1982 | sure so it is aaron warren and my date of birth is the may 16 1982 | sure so it is ayrton warren and my date of birth is the may 16 1982 | sure so it is aaron warren and my date of birth is the 05161982 |
| `primock57:day3_consultation07:patient:0010` | 0 / 3 | january 17 1987 | january 17 1987 | january 17 1987 | 01171987 |
| `primock57:day4_consultation01:patient:0010` | 1 / 4 | it is joe bloggs it is the june 7 1974 | it is joy bloggs it is the june 7 1974 | it is joe bloggs it is the june 7 1974 | it is joy bloggs it is the 06071974 |
| `primock57:day4_consultation03:patient:0008` | 0 / 3 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the 04201980 |
| `primock57:day4_consultation05:patient:0009` | 2 / 5 | yes my my name is roberto mendoza and i am i was born on the january 1 of 1992 | yes my my name is roberto mendoza i am i was born on the january 1 1992 | yes my my name is roberto mendoza and i am i was born on the january 1 of 1992 | yes my my name is roberto mendoza i am i was born on the 01011992 |
| `primock57:day4_consultation08:patient:0010` | 0 / 3 | yeah my date of birth is the august 8 1982 | yeah my date of birth is the august 8 1982 | yeah my date of birth is the august 8 1982 | yeah my date of birth is the 08081982 |
| `primock57:day4_consultation10:patient:0008` | 0 / 3 | july 23 1995 | july 23 1995 | july 23 1995 | 07231995 |

### `paren_digits`

No utterance changes.

### `leading_zero`

| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | Ref (without) | Hyp (without) |
|---|---|---|---|---|---|
| `primock57:day3_consultation03:doctor:0120` | 2 / 1 | ohh there is a number on your app yeah if you open up your app there is the number on there it is an 300 number yeah so just call that number | 0 there is a number on your app yeah if you open up your app there is the number on there it is an 0300 number yeah so just call that number | ohh there is a number on your app yeah if you open up your app there is the number on there it is an 300 number yeah so just call that number | 0 there is a number on your app yeah if you open up your app there is the number on there it is an 300 number yeah so just call that number |

### `units`

No utterance changes.

### `ordinals`

| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | Ref (without) | Hyp (without) |
|---|---|---|---|---|---|
| `primock57:day2_consultation02:patient:0006` | 0 / 3 | yes my name is john smith and i was born on the april 5 1973 | yes my name is john smith and i was born on the april 5 1973 | yes my name is john smith and i was born on the 5th of april 1973 | yes my name is john smith and i was born on the april 5 1973 |
| `primock57:day2_consultation07:patient:0006` | 1 / 4 | yeah sure my name is jim gowers and i was born in 1958 on the august 8 | yeah sure my name is tim gowers and i was born in 1958 on the august 8 | yeah sure my name is jim gowers and i was born in 1958 on the 8th of august | yeah sure my name is tim gowers and i was born in 1958 on the august 8 |
| `primock57:day2_consultation08:patient:0006` | 0 / 3 | yes it is sarah smith and it is the november 2 1992 | yes it is sarah smith and it is the november 2 1992 | yes it is sarah smith and it is the 2nd of november 1992 | yes it is sarah smith and it is the november 2 1992 |
| `primock57:day2_consultation10:patient:0006` | 1 / 4 | sure so it is ayrton warren and my date of birth is the may 16 1982 | sure so it is aaron warren and my date of birth is the may 16 1982 | sure so it is ayrton warren and my date of birth is the 16th of may 1982 | sure so it is aaron warren and my date of birth is the may 16 1982 |
| `primock57:day3_consultation01:patient:0010` | 1 / 4 | that is the october 1 99 | that is the october 1 1999 | that is the 1st of october 99 | that is the october 1 1999 |
| `primock57:day4_consultation01:patient:0010` | 1 / 4 | it is joe bloggs it is the june 7 1974 | it is joy bloggs it is the june 7 1974 | it is joe bloggs it is the 7th of june 1974 | it is joy bloggs it is the june 7 1974 |
| `primock57:day4_consultation03:patient:0008` | 0 / 3 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the 20th of april 1980 | my name is sarah smith and my date of birth is the april 20 1980 |
| `primock57:day4_consultation08:patient:0010` | 0 / 3 | yeah my date of birth is the august 8 1982 | yeah my date of birth is the august 8 1982 | yeah my date of birth is the 8th of august 1982 | yeah my date of birth is the august 8 1982 |

### `decimals`

No utterance changes.

### `digit_one`

No utterance changes.

### `digit_join`

No utterance changes.

### `spoken_dates`

| Utterance | Errors with / without | Ref (with rule) | Hyp (with rule) | Ref (without) | Hyp (without) |
|---|---|---|---|---|---|
| `primock57:day2_consultation02:patient:0006` | 0 / 3 | yes my name is john smith and i was born on the april 5 1973 | yes my name is john smith and i was born on the april 5 1973 | yes my name is john smith and i was born on the 5 of april 1973 | yes my name is john smith and i was born on the april 5 1973 |
| `primock57:day2_consultation07:patient:0006` | 1 / 4 | yeah sure my name is jim gowers and i was born in 1958 on the august 8 | yeah sure my name is tim gowers and i was born in 1958 on the august 8 | yeah sure my name is jim gowers and i was born in 1958 on the 8 of august | yeah sure my name is tim gowers and i was born in 1958 on the august 8 |
| `primock57:day2_consultation08:patient:0006` | 0 / 3 | yes it is sarah smith and it is the november 2 1992 | yes it is sarah smith and it is the november 2 1992 | yes it is sarah smith and it is the 2 of november 1992 | yes it is sarah smith and it is the november 2 1992 |
| `primock57:day2_consultation10:patient:0006` | 1 / 4 | sure so it is ayrton warren and my date of birth is the may 16 1982 | sure so it is aaron warren and my date of birth is the may 16 1982 | sure so it is ayrton warren and my date of birth is the 16 of may 1982 | sure so it is aaron warren and my date of birth is the may 16 1982 |
| `primock57:day3_consultation01:patient:0010` | 1 / 4 | that is the october 1 99 | that is the october 1 1999 | that is the 1 of october 99 | that is the october 1 1999 |
| `primock57:day3_consultation07:patient:0010` | 0 / 3 | january 17 1987 | january 17 1987 | 17 of january 1987 | january 17 1987 |
| `primock57:day4_consultation01:patient:0010` | 1 / 4 | it is joe bloggs it is the june 7 1974 | it is joy bloggs it is the june 7 1974 | it is joe bloggs it is the 7 of june 1974 | it is joy bloggs it is the june 7 1974 |
| `primock57:day4_consultation03:patient:0008` | 0 / 3 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the april 20 1980 | my name is sarah smith and my date of birth is the 20 of april 1980 | my name is sarah smith and my date of birth is the april 20 1980 |

