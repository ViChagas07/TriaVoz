# TriaVoz voice worker

LiveKit Agents worker: **Deepgram STT → Claude (tool calling) → ElevenLabs TTS**, with VAD-based
turn handling and barge-in. It never touches the database: every tool calls the TriaVoz API
(`/internal/agent/*`, HMAC-signed), which applies tenant RLS.

```bash
poetry install
poetry run python -m triavoz_agent.main dev      # local, against LiveKit (see ../../.env.example)
```

Read `../../docs/specs/03-voice-agent.md` before changing anything here.
