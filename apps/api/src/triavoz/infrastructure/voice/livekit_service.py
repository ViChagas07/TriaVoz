"""LiveKit adapter for server-created demo rooms.

TODO(verify-docs): the LiveKit server SDK is `livekit-api` (the worker uses `livekit-agents`).
The calls below match the installed 1.2.x API (`LiveKitAPI.room.create_room`,
`AccessToken.with_grants`, `VideoGrants`). Re-check after a major SDK upgrade.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from livekit import api

from triavoz.application.voice.ports import VoiceRoom


class LiveKitVoiceService:
    def __init__(
        self,
        *,
        http_url: str,
        public_url: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        self._http_url = http_url
        self._public_url = public_url
        self._api_key = api_key
        self._api_secret = api_secret

    async def create_room(
        self,
        *,
        room_name: str,
        identity: str,
        metadata: dict[str, Any],
        ttl_seconds: int,
    ) -> VoiceRoom:
        client = api.LiveKitAPI(self._http_url, self._api_key, self._api_secret)
        try:
            await client.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    metadata=json.dumps(metadata, ensure_ascii=False),
                    empty_timeout=ttl_seconds,
                    max_participants=2,
                )
            )
        finally:
            await client.aclose()

        token = (
            api.AccessToken(self._api_key, self._api_secret)
            .with_identity(identity)
            .with_name("Paciente (demo)")
            .with_ttl(timedelta(seconds=ttl_seconds))
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
        return VoiceRoom(room_name=room_name, token=token, url=self._public_url)
