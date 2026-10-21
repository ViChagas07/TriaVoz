"""Post-call abuse scoring — pure and unit-tested.

The score is a triage signal for the dashboard, never an automatic punishment. A "review" badge
appears when the score reaches the configured threshold; a human decides what to do next.
"""

from __future__ import annotations

from dataclasses import dataclass

from triavoz.application.abuse.ports import ScoringInputs

__all__ = ["ScoreResult", "score_call"]

FLAG_VERY_SHORT = "very_short"
FLAG_NO_PATIENT_SPEECH = "no_patient_speech"
FLAG_NO_VALID_DATA = "no_valid_data"
FLAG_REPEAT_CALLER = "repeat_caller"
FLAG_LOW_STT_CONFIDENCE = "low_stt_confidence"
FLAG_ABUSIVE_LANGUAGE = "abusive_language"

_FLAG_ORDER = (
    FLAG_VERY_SHORT,
    FLAG_NO_PATIENT_SPEECH,
    FLAG_NO_VALID_DATA,
    FLAG_REPEAT_CALLER,
    FLAG_LOW_STT_CONFIDENCE,
    FLAG_ABUSIVE_LANGUAGE,
)

VERY_SHORT_SECONDS = 15
LOW_CONFIDENCE = 0.55
REPEAT_SUSPICIOUS = 2
REPEAT_ABUSIVE = 5


@dataclass(frozen=True)
class ScoreResult:
    score: int
    flags: tuple[str, ...]
    needs_review: bool


def score_call(inputs: ScoringInputs, *, review_threshold: int = 50) -> ScoreResult:
    points: dict[str, int] = {}

    if inputs.duration_seconds <= VERY_SHORT_SECONDS:
        points[FLAG_VERY_SHORT] = 25
    if inputs.patient_turns <= 0:
        points[FLAG_NO_PATIENT_SPEECH] = 20
    if (
        inputs.patient_turns <= 1
        and not inputs.appointment_created
        and not inputs.request_created
        and inputs.successful_tool_calls == 0
    ):
        points[FLAG_NO_VALID_DATA] = 20
    if inputs.previous_calls_24h >= REPEAT_ABUSIVE:
        points[FLAG_REPEAT_CALLER] = 20
    elif inputs.previous_calls_24h >= REPEAT_SUSPICIOUS:
        points[FLAG_REPEAT_CALLER] = 10
    if inputs.average_stt_confidence is not None and inputs.average_stt_confidence < LOW_CONFIDENCE:
        points[FLAG_LOW_STT_CONFIDENCE] = 15
    if inputs.abusive_language:
        points[FLAG_ABUSIVE_LANGUAGE] = 30

    score = max(0, min(100, sum(points.values())))
    flags = tuple(flag for flag in _FLAG_ORDER if flag in points)
    return ScoreResult(score=score, flags=flags, needs_review=score >= review_threshold)
