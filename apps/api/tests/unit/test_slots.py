from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from triavoz.domain.scheduling.slots import Interval, WorkWindow, free_slots

TZ = ZoneInfo("America/Bahia")
DAY = date(2030, 1, 7)  # a Monday
LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)


def at(h: int, m: int = 0) -> datetime:
    return datetime.combine(DAY, time(h, m), tzinfo=TZ)


def test_offers_every_step_inside_the_window() -> None:
    slots = free_slots(
        day=DAY,
        tz=TZ,
        windows=[WorkWindow(time(9), time(11))],
        busy=[],
        duration=timedelta(minutes=30),
        now=LONG_AGO,
        step=timedelta(minutes=30),
    )
    assert slots == [at(9), at(9, 30), at(10), at(10, 30)]


def test_busy_interval_blocks_overlapping_slots_only() -> None:
    busy = [Interval(at(10), at(10, 30))]
    slots = free_slots(
        day=DAY,
        tz=TZ,
        windows=[WorkWindow(time(9), time(11))],
        busy=busy,
        duration=timedelta(minutes=30),
        now=LONG_AGO,
        step=timedelta(minutes=30),
    )
    assert at(10) not in slots
    assert at(9, 30) in slots and at(10, 30) in slots


def test_longer_service_only_fits_where_it_ends_before_the_busy_block() -> None:
    busy = [Interval(at(10), at(10, 30))]
    slots = free_slots(
        day=DAY,
        tz=TZ,
        windows=[WorkWindow(time(9), time(11))],
        busy=busy,
        duration=timedelta(minutes=60),
        now=LONG_AGO,
        step=timedelta(minutes=30),
    )
    # 09:00-10:00 ends exactly when the busy block starts (free); 09:30 and 10:00 overlap it.
    assert slots == [at(9)]


def test_past_and_min_notice_are_excluded() -> None:
    now = at(9, 40).astimezone(UTC)
    slots = free_slots(
        day=DAY,
        tz=TZ,
        windows=[WorkWindow(time(9), time(11))],
        busy=[],
        duration=timedelta(minutes=30),
        now=now,
        step=timedelta(minutes=30),
        min_notice=timedelta(minutes=30),
    )
    assert slots == [at(10, 30)]


def test_duration_longer_than_window_yields_nothing() -> None:
    assert (
        free_slots(
            day=DAY,
            tz=TZ,
            windows=[WorkWindow(time(9), time(9, 20))],
            busy=[],
            duration=timedelta(minutes=30),
            now=LONG_AGO,
        )
        == []
    )


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError):
        free_slots(
            day=DAY,
            tz=TZ,
            windows=[],
            busy=[],
            duration=timedelta(minutes=30),
            now=datetime(2020, 1, 1),
        )


@pytest.mark.parametrize(
    ("duration", "step", "min_notice"),
    [
        (timedelta(0), timedelta(minutes=15), timedelta(0)),
        (timedelta(minutes=-5), timedelta(minutes=15), timedelta(0)),
        (timedelta(minutes=30), timedelta(0), timedelta(0)),
        (timedelta(minutes=30), timedelta(minutes=-15), timedelta(0)),
        (timedelta(minutes=30), timedelta(minutes=15), timedelta(minutes=-1)),
    ],
)
def test_non_positive_duration_step_or_negative_notice_is_rejected(
    duration: timedelta, step: timedelta, min_notice: timedelta
) -> None:
    with pytest.raises(ValueError):
        free_slots(
            day=DAY,
            tz=TZ,
            windows=[WorkWindow(time(9), time(11))],
            busy=[],
            duration=duration,
            now=LONG_AGO,
            step=step,
            min_notice=min_notice,
        )
