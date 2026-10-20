"""Latency percentiles per pipeline stage + cost estimate. Pure logic, unit-tested."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from triavoz_agent.config import WorkerConfig


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[k]


@dataclass
class LatencyTracker:
    samples: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def record(self, stage: str, seconds: float) -> None:
        if seconds >= 0:
            self.samples[stage].append(seconds)

    def summary_ms(self) -> dict[str, dict[str, float]]:
        return {
            stage: {
                "p50": round(percentile(v, 50) * 1000, 1),
                "p95": round(percentile(v, 95) * 1000, 1),
                "n": float(len(v)),
            }
            for stage, v in self.samples.items()
        }


@dataclass
class TurnLatencyTracker:
    """Correlates EOU + LLM TTFT + TTS TTFB into time-to-first-audio.

    Metrics are emitted in that order for a turn. A new EOU starts a fresh sample; TTS closes it.
    The individual stages are still recorded so the dashboard can show a breakdown.
    """

    latency: LatencyTracker
    current: dict[str, float] = field(default_factory=dict)

    def record(self, stage: str, seconds: float) -> None:
        if seconds < 0:
            return
        self.latency.record(stage, seconds)
        if stage == "end_of_utterance":
            self.current = {"end_of_utterance": seconds}
            return
        self.current[stage] = seconds
        if {"end_of_utterance", "llm_ttft", "tts_ttfb"} <= self.current.keys():
            self.latency.record(
                "time_to_first_audio",
                self.current["end_of_utterance"]
                + self.current["llm_ttft"]
                + self.current["tts_ttfb"],
            )
            self.current = {}


def estimate_cost_cents(
    cfg: WorkerConfig,
    *,
    stt_seconds: float,
    llm_input_tokens: int,
    llm_output_tokens: int,
    tts_characters: int,
) -> float:
    cost = (
        stt_seconds / 60 * cfg.price_stt_per_minute_cents
        + llm_input_tokens / 1_000_000 * cfg.price_llm_per_million_input_tokens_cents
        + llm_output_tokens / 1_000_000 * cfg.price_llm_per_million_output_tokens_cents
        + tts_characters / 1000 * cfg.price_tts_per_thousand_chars_cents
    )
    return round(cost, 4)
