# ADR 0002 — Own voice pipeline (LiveKit Agents) instead of a hosted agent platform

**Status:** accepted · **Context:** the project brief teaches the pieces (STT, LLM tool calling, streaming TTS, real-time orchestration with barge-in, observability); a hosted platform hides most of them. The author also wants ElevenLabs on the stack.
**Decision:** build the pipeline with LiveKit Agents: Deepgram STT → Claude (tool calling) → ElevenLabs TTS. Keep a provider port so a hosted platform can be added as an alternative adapter later.
**Consequences:** more moving parts and API keys; we measure latency and cost per stage; telephony and human transfer need explicit work (SIP) and are verified against current docs before promising them.
