"""Pure handoff policy, independent of LiveKit and the LLM.

Urgency is fail-open (it never blocks the booking flow); two consecutive assistant clarification
messages are treated as repeated misunderstanding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_URGENT = re.compile(
    r"dor no peito|falta de ar|sangramento|desmaio|infarto|avc|derrame|"
    r"emerg[eê]ncia|urgente|suic[ií]d|me matar|não consigo respirar",
    re.IGNORECASE,
)
_CLARIFY = re.compile(
    r"n[ãa]o entendi|pode repetir|n[ãa]o consegui entender|desculpe,? n[ãa]o",
    re.IGNORECASE,
)


@dataclass
class HandoffPolicy:
    clarify_streak: int = 0

    def observe_user(self, text: str) -> str | None:
        return "urgency" if _URGENT.search(text) else None

    def observe_assistant(self, text: str) -> str | None:
        if not _CLARIFY.search(text):
            self.clarify_streak = 0
            return None
        self.clarify_streak += 1
        if self.clarify_streak >= 2:
            self.clarify_streak = 0
            return "misunderstanding"
        return None
