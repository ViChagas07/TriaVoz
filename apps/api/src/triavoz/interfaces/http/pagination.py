from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID


def encode_cursor(timestamp: datetime, item_id: UUID) -> str:
    raw = json.dumps({"t": timestamp.isoformat(), "id": str(item_id)}).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str | None) -> tuple[datetime | None, UUID | None]:
    if not cursor:
        return None, None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(data["t"]), UUID(data["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("invalid_cursor") from exc
