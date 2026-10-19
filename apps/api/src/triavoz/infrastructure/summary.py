"""Summary generation port implementation.

P03 ships a stub: producing a clinical-adjacent summary requires a reviewed prompt, provider
credentials and cost guardrails (P07). The endpoint is wired now and returns 503 until configured.
"""

from __future__ import annotations

from typing import Any


class UnconfiguredCallSummaryGenerator:
    async def summarize(self, call: dict[str, Any], turns: list[dict[str, Any]]) -> str | None:
        return None
