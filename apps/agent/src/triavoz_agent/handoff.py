"""Human handoff adapters.

Web demo: persist a callback request and close politely (implemented in CallContext).
SIP/phone: LiveKit SIP REFER transfer. The Python API is
`LiveKitAPI.sip.transfer_sip_participant(TransferSIPParticipantRequest(...))` (livekit-api
1.2.x, verified against the LiveKit SIP reference). A live SIP trunk is not configured in
this repository, so this path is implemented but not exercised in the demo.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit import api

log = logging.getLogger("triavoz.handoff")


class SipHandoff:
    def __init__(
        self,
        *,
        http_url: str,
        api_key: str,
        api_secret: str,
        room_name: str,
        participant_identity: str,
        transfer_to: str,
    ) -> None:
        self._http_url = http_url
        self._api_key = api_key
        self._api_secret = api_secret
        self._room_name = room_name
        self._participant_identity = participant_identity
        self._transfer_to = transfer_to

    async def __call__(self) -> None:
        client = api.LiveKitAPI(self._http_url, self._api_key, self._api_secret)
        try:
            request = api.TransferSIPParticipantRequest(
                room_name=self._room_name,
                participant_identity=self._participant_identity,
                transfer_to=self._transfer_to,
                play_dialtone=True,
            )
            await client.sip.transfer_sip_participant(request, timeout=30.0)
        finally:
            await client.aclose()


def find_caller_identity(room: Any) -> str | None:
    """Return the remote participant identity (SIP participant on phone calls)."""
    local = getattr(room, "local_participant", None)
    local_identity = getattr(local, "identity", None)
    for participant in getattr(room, "remote_participants", {}).values():
        identity = getattr(participant, "identity", None)
        if identity and identity != local_identity:
            return str(identity)
    return None
