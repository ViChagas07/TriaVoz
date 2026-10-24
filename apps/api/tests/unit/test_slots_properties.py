"""Property-style tests for the pure slot engine.

The example-based tests in `test_slots.py` pin the known edges. These properties cover the whole
input space cheaply: every returned slot must be inside a window, aligned to the step grid, clear
of every busy interval and after the notice cut-off; conversely, every candidate that satisfies
those rules must be returned. This is intentionally independent from the cursor loop in the
implementation (it enumerates integer minutes instead).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from triavoz.domain.scheduling.slots import Interval, WorkWindow, free_slots

TZ = ZoneInfo("America/Bahia")
DAY = date(2030, 1, 7)  # a Monday
LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)


@st.composite
def windows(draw: st.DrawFn) -> list[WorkWindow]:
    count = draw(st.integers(min_value=0, max_value=3))
    out: list[WorkWindow] = []
    for _ in range(count):
        start = draw(st.integers(min_value=0, max_value=1438))
        end = draw(st.integers(min_value=start + 1, max_value=1439))
        out.append(WorkWindow(time(start // 60, start % 60), time(end // 60, end % 60)))
    return out


@st.composite
def busy_intervals(draw: st.DrawFn) -> list[Interval]:
    count = draw(st.integers(min_value=0, max_value=3))
    out: list[Interval] = []
    for _ in range(count):
        start_minute = draw(st.integers(min_value=-120, max_value=1559))
        length = draw(st.integers(min_value=1, max_value=240))
        start = datetime.combine(DAY, time.min, tzinfo=TZ) + timedelta(minutes=start_minute)
        end = start + timedelta(minutes=length)
        # Exercise the mixed-timezone comparison path too.
        if draw(st.booleans()):
            start, end = start.astimezone(UTC), end.astimezone(UTC)
        out.append(Interval(start, end))
    return out


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    day=st.dates(min_value=date(2028, 1, 1), max_value=date(2032, 12, 31)),
    window_list=windows(),
    busy=busy_intervals(),
    duration_min=st.integers(min_value=1, max_value=240),
    step_min=st.integers(min_value=1, max_value=60),
    notice_min=st.integers(min_value=0, max_value=240),
    now_offset_min=st.integers(min_value=-2880, max_value=4320),
)
def test_every_slot_is_valid_and_every_valid_slot_is_returned(
    day: date,
    window_list: list[WorkWindow],
    busy: list[Interval],
    duration_min: int,
    step_min: int,
    notice_min: int,
    now_offset_min: int,
) -> None:
    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=step_min)
    notice = timedelta(minutes=notice_min)
    day_start = datetime.combine(day, time.min, tzinfo=TZ)
    now = (day_start + timedelta(minutes=now_offset_min)).astimezone(UTC)

    slots = free_slots(
        day=day,
        tz=TZ,
        windows=window_list,
        busy=busy,
        duration=duration,
        now=now,
        step=step,
        min_notice=notice,
    )

    assert slots == sorted(set(slots))
    earliest = now + notice
    expected: set[datetime] = set()
    for window in window_list:
        start_minute = window.start.hour * 60 + window.start.minute
        end_minute = window.end.hour * 60 + window.end.minute
        window_end = day_start + timedelta(minutes=end_minute)
        for minute in range(start_minute, end_minute + 1):
            if (minute - start_minute) % step_min != 0:
                continue
            cursor = day_start + timedelta(minutes=minute)
            if cursor + duration > window_end:
                break
            if cursor < earliest:
                continue
            if any(item.overlaps(cursor, cursor + duration) for item in busy):
                continue
            expected.add(cursor)

    assert slots == sorted(expected)

    for slot in slots:
        assert slot.tzinfo is not None
        assert slot >= earliest
        assert slot.utcoffset() == day_start.utcoffset()
        assert any(
            datetime.combine(day, window.start, tzinfo=TZ)
            <= slot
            <= datetime.combine(day, window.end, tzinfo=TZ) - duration
            for window in window_list
        )
        assert all(not item.overlaps(slot, slot + duration) for item in busy)


@given(
    start_min=st.integers(min_value=0, max_value=1438),
    duration_min=st.integers(min_value=1, max_value=240),
    step_min=st.integers(min_value=1, max_value=60),
)
@settings(max_examples=100, deadline=None)
def test_slots_are_aligned_to_the_window_start(
    start_min: int, duration_min: int, step_min: int
) -> None:
    start = time(start_min // 60, start_min % 60)
    end = time(23, 59)
    slots = free_slots(
        day=DAY,
        tz=TZ,
        windows=[WorkWindow(start, end)],
        busy=[],
        duration=timedelta(minutes=duration_min),
        now=LONG_AGO,
        step=timedelta(minutes=step_min),
    )
    window_start = datetime.combine(DAY, start, tzinfo=TZ)
    offsets = {(slot - window_start).total_seconds() % (step_min * 60) for slot in slots}
    assert offsets <= {0}
