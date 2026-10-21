from __future__ import annotations

import uuid

from triavoz.application.abuse.ports import ScoringInputs
from triavoz.application.abuse.scoring import score_call


def _inputs(**overrides: object) -> ScoringInputs:
    base = dict(
        call_id=uuid.uuid4(),
        status="completed",
        duration_seconds=120,
        patient_turns=4,
        successful_tool_calls=2,
        average_stt_confidence=0.92,
        appointment_created=True,
        request_created=False,
        previous_calls_24h=0,
        abusive_language=False,
    )
    base.update(overrides)
    return ScoringInputs(**base)  # type: ignore[arg-type]


def test_clean_call_is_not_flagged() -> None:
    result = score_call(_inputs())
    assert result.score == 0
    assert result.flags == ()
    assert result.needs_review is False


def test_very_short_empty_call_crosses_review_threshold() -> None:
    result = score_call(
        _inputs(
            duration_seconds=5,
            patient_turns=0,
            successful_tool_calls=0,
            appointment_created=False,
            average_stt_confidence=None,
        )
    )
    assert result.score == 65
    assert result.flags == ("very_short", "no_patient_speech", "no_valid_data")
    assert result.needs_review is True


def test_repeat_caller_and_low_confidence_are_scored() -> None:
    two = score_call(_inputs(previous_calls_24h=2))
    many = score_call(_inputs(previous_calls_24h=5, average_stt_confidence=0.30))
    assert two.score == 10 and two.flags == ("repeat_caller",)
    assert many.score == 35
    assert many.flags == ("repeat_caller", "low_stt_confidence")
    assert many.needs_review is False


def test_abusive_language_and_threshold_override() -> None:
    result = score_call(_inputs(abusive_language=True), review_threshold=30)
    assert result.score == 30
    assert result.flags == ("abusive_language",)
    assert result.needs_review is True


def test_score_is_clamped_to_100() -> None:
    result = score_call(
        _inputs(
            duration_seconds=1,
            patient_turns=0,
            successful_tool_calls=0,
            appointment_created=False,
            previous_calls_24h=9,
            average_stt_confidence=0.1,
            abusive_language=True,
        )
    )
    assert result.score == 100
    assert result.needs_review is True
