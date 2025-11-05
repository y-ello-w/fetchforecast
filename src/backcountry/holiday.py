from __future__ import annotations

import datetime as dt
from typing import Iterable, List

try:
    import jpholiday
except ImportError:  # pragma: no cover - optional dependency fallback
    jpholiday = None  # type: ignore

from .models import HolidayDay


def is_japanese_holiday(day: dt.date) -> tuple[bool, str | None]:
    if jpholiday is None:
        return False, None
    name = jpholiday.is_holiday_name(day)
    return (name is not None), name


def build_holiday_days(dates: Iterable[dt.date]) -> List[HolidayDay]:
    records: List[HolidayDay] = []
    for day in dates:
        is_weekend = day.weekday() >= 5
        is_holiday, name = is_japanese_holiday(day)
        records.append(
            HolidayDay(
                date=day,
                is_weekend=is_weekend,
                is_holiday=is_holiday,
                holiday_name=name,
            )
        )
    return records


__all__ = ["build_holiday_days", "is_japanese_holiday"]

