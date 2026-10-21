"""Emergency detection shared by the gatekeeper and the in-call worker policy.

Emergency routing is FAIL-OPEN: an urgency signal always wins over every anti-abuse limit. The
detector is deliberately small and auditable; it is not a medical triage tool.
"""

from __future__ import annotations

import re

__all__ = ["EMERGENCY_MESSAGE", "contains_emergency"]

# Portuguese first (the demo's language), plus a few English expressions heard on phone calls.
EMERGENCY_PATTERN = re.compile(
    r"dor no peito|aperto no peito|falta de ar|n[ãa]o consigo respirar|sem ar|"
    r"sangramento (intenso|forte)|desmaiei|desmaio|infarto|avc|derrame|convuls[ãa]o|"
    r"emerg[eê]ncia|urgente|suic[ií]d|me matar|quero morrer|overdose|"
    r"atropelament|acidente grave|"
    r"chest pain|can'?t breathe|emergency|suicid",
    re.IGNORECASE,
)

EMERGENCY_MESSAGE = (
    "Se isto é uma emergência, ligue agora para o SAMU no 192 ou procure o pronto-socorro "
    "mais próximo. Não espere por esta ligação."
)


def contains_emergency(text: str | None) -> bool:
    return bool(text and EMERGENCY_PATTERN.search(text))
