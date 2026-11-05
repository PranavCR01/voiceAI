# Streaming latency

Milliseconds, p50 / p95 with 95% bootstrap intervals resampling whole speakers; timeouts count as +inf (rate shown). Anchors and metric definitions: `harness/streaming/README.md`. RTT is the median TCP connect time to the endpoint. Latency is compared only between configs run from the same machine and network, and no winner is called with fewer than 10 speakers.

## Provider endpointing (natural)

| Config | Sessions | Speakers | RTT | Connect | First partial | TTFS | Finalize latency | Endpoint delay | Premature endpoints |
|---|---|---|---|---|---|---|---|---|---|
| prov_a_stream | 24 | 12 | 21 | 91 [85, 96] / 102 [97, 103] | 183 [165, 198] / 216 [201, 219] | 310 [250, 360] / 420 [370, timeout] (timeouts 4.2%) | n/a (not_applicable 24) | 410 [350, 460] / 520 [470, timeout] (timeouts 4.2%) | 0.0% |

- prov_a_stream: TTFS basis word_timestamps 23; speaker clustering effect 1.22.

## Forced finalization (forced)

| Config | Sessions | Speakers | RTT | Connect | First partial | TTFS | Finalize latency | Endpoint delay | Premature endpoints |
|---|---|---|---|---|---|---|---|---|---|
| prov_b_stream | 24 | 12 | 21 | 91 [85, 96] / 102 [97, 103] | 183 [165, 198] / 216 [201, 219] | 310 [250, 360] / 420 [370, 430] | 309 [249, 359] / 419 [369, 429] | n/a (not_applicable 24) | 0.0% |

- prov_b_stream: TTFS basis word_timestamps 24; speaker clustering effect 1.22.
