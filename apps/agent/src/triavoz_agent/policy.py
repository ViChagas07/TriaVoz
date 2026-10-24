"""Pure handoff/limit policy, independent of LiveKit and the LLM.

Order is non-negotiable: an emergency signal wins over abuse strikes and turn limits. Abuse gets one
calm warning; the second strike ends the call. Two consecutive clarification messages from the agent
trigger a misunderstanding handoff, and exceeding the turn budget does the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_URGENT = re.compile(
    r"dor no peito|aperto no peito|falta de ar|n[ãa]o consigo respirar|sem ar|"
    r"sangramento (intenso|forte)|desmaiei|desmaio|infarto|avc|derrame|convuls[ãa]o|"
    r"emerg[eê]ncia|urgente|suic[ií]d|me matar|quero morrer|overdose|atropelament|"
    r"acidente grave|chest pain|can'?t breathe|emergency|suicid",
    re.IGNORECASE,
)
_ABUSIVE = re.compile(
    r"\b(idiota|imbecil|est[úu]pid[ao]|burr[ao]|ot[áa]ri[ao]|desgra[çc]ad[ao]|"
    r"filh[ao] da puta|vai se foder|vai tomar no cu|cala a boca|in[úu]til)\b",
    re.IGNORECASE,
)
_CLARIFY = re.compile(
    r"n[ãa]o entendi|pode repetir|n[ãa]o consegui entender|desculpe,? n[ãa]o",
    re.IGNORECASE,
)


def contains_emergency(text: str | None) -> bool:
    return bool(text and _URGENT.search(text))


@dataclass
class SilencePolicy:
    """One warning, then close. The clock resets on every caller turn."""

    timeout_seconds: float
    warned: bool = False

    def evaluate(self, idle_seconds: float) -> str | None:
        if idle_seconds < self.timeout_seconds:
            return None
        if not self.warned:
            self.warned = True
            return "warn"
        return "close"

    def note_activity(self) -> None:
        self.warned = False


@dataclass
class HandoffPolicy:
    max_turns: int = 20
    clarify_threshold: int = 2
    clarify_streak: int = 0
    user_turns: int = 0
    abuse_strikes: int = 0
    emergency: bool = False

    def observe_user(self, text: str) -> str | None:
        if contains_emergency(text):
            self.emergency = True
            return "urgency"
        if self.emergency:
            # Emergency routing has priority; later turns must not trigger abuse/turn endings.
            return None
        self.user_turns += 1
        if _ABUSIVE.search(text):
            self.abuse_strikes += 1
            return "abuse" if self.abuse_strikes == 1 else "abuse_final"
        if self.max_turns > 0 and self.user_turns > self.max_turns:
            return "max_turns"
        return None

    def observe_assistant(self, text: str) -> str | None:
        if self.emergency:
            return None
        if not _CLARIFY.search(text):
            self.clarify_streak = 0
            return None
        self.clarify_streak += 1
        if self.clarify_streak >= self.clarify_threshold:
            self.clarify_streak = 0
            return "misunderstanding"
        return None
