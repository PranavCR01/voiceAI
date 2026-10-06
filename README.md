# voiceAI

Describe a voice-agent use case and its constraints, ideally with sample audio, and get back the voice stack to use — speech-to-text, turn detection, LLM and text-to-speech, with settings, where that choice breaks, and how sure the recommendation is.

Under the hood: an STT bake-off harness scoring entity accuracy, endpointing errors, time-to-first-audio and cost per minute with confidence intervals, plus a reference voice agent (Pipecat, hand-built turn-taking/barge-in controller) for in-pipeline measurement. The first reference use case is healthcare patient intake.

Status: scaffolding. See `docs/PROJECT.md` for scope and `docs/DECISIONS.md` for the decision log.
