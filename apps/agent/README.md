# TriaVoz voice worker

LiveKit Agents worker: **Deepgram STT → Claude (tool calling) → ElevenLabs TTS**, with VAD-based
turn handling and barge-in. It never touches the database: every tool calls the TriaVoz API
(`/internal/agent/*`, HMAC-signed), which applies tenant RLS.

```bash
poetry install
poetry run python -m triavoz_agent.main dev      # local, against LiveKit (see ../../.env.example)
```

Read `../../docs/specs/03-voice-agent.md` and ADR 0008 before changing anything here.

In-call protection (P05): one calm warning for abusive language then the call ends; max turns;
silence timeout after the greeting; hard duration cap from room metadata; two clarifications →
handoff. Urgency always wins (SAMU 192) and ignores those limits, with one grace window at the hard
cap. Provider startup/turn calls are bounded; failures request a callback and end cleanly.
