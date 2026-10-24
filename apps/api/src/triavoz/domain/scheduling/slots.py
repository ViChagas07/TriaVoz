"""Pure slot computation (no I/O, no framework). The LLM NEVER invents a time: it only offers
what this function returns, and booking re-validates against it AND against the DB constraint."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class WorkWindow:
    start: time
    end: time


@dataclass(frozen=True)
class Interval:
    start: datetime  # tz-aware
    end: datetime  # tz-aware

    def overlaps(self, other_start: datetime, other_end: datetime) -> bool:
        return self.start < other_end and other_start < self.end


def free_slots(
    *,
    day: date,
    tz: ZoneInfo,
    windows: Sequence[WorkWindow],
    busy: Sequence[Interval],
    duration: timedelta,
    now: datetime,
    step: timedelta = timedelta(minutes=15),
    min_notice: timedelta = timedelta(0),
) -> list[datetime]:
    """Start times (tz-aware, clinic timezone) where `duration` fits inside a work window,
    does not overlap `busy`, and is not earlier than now + min_notice."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if duration <= timedelta(0):
        raise ValueError("duration must be positive")
    if step <= timedelta(0):
        raise ValueError("step must be positive")
    if min_notice < timedelta(0):
        raise ValueError("min_notice must not be negative")
    earliest = now + min_notice
    result: list[datetime] = []
    for w in windows:
        cursor = datetime.combine(day, w.start, tzinfo=tz)
        window_end = datetime.combine(day, w.end, tzinfo=tz)
        while cursor + duration <= window_end:
            end = cursor + duration
            if cursor >= earliest and not any(b.overlaps(cursor, end) for b in busy):
                result.append(cursor)
            cursor += step
    return sorted(set(result))
