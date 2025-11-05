from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from ..models import ForecastPeriod, Mountain, Period
from .base import BaseSource

_PERIOD_MAP: Dict[str, Period] = {
    "morning": Period.MORNING,
    "am": Period.MORNING,
    "afternoon": Period.AFTERNOON,
    "pm": Period.AFTERNOON,
    "night": Period.NIGHT,
    "evening": Period.NIGHT,
}

_JAPANESE_PERIOD_MAP: Dict[str, Period] = {
    "??": Period.MORNING,
    "??": Period.AFTERNOON,
    "?": Period.NIGHT,
}

_WIND_COMBINED_RE = re.compile(r"(?P<speed>\d+(?:\.\d+)?)(?P<dir>[A-Z]+)?")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


class SnowForecastSource(BaseSource):
    source_name = "snowforecast"

    def build_requests(self, mountain: Mountain, target_date: dt.date) -> List[str]:
        url = mountain.sources.get(self.source_name)
        if not url:
            raise ValueError(f"SnowForecast URL is not configured for {mountain.mountain_id}")
        return [url]

    def parse(
        self,
        mountain: Mountain,
        target_date: dt.date,
        fetched_at: dt.datetime,
        text: str,
        *,
        url: str,
    ) -> List[ForecastPeriod]:
        soup = BeautifulSoup(text, "html.parser")
        table = soup.select_one("table.forecast-table__table--content")
        if table:
            return self._parse_table(table, mountain, target_date)
        return []

    def _parse_table(
        self,
        table: BeautifulSoup,
        mountain: Mountain,
        target_date: dt.date,
    ) -> List[ForecastPeriod]:
        day_row = table.select_one("tr[data-row='days']")
        time_row = table.select_one("tr[data-row='time']")
        if not day_row or not time_row:
            return []

        date_sequence: List[Optional[str]] = []
        for cell in day_row.find_all(["th", "td"], recursive=False):
            date = cell.get("data-date")
            colspan = int(cell.get("colspan") or 1)
            date_sequence.extend([date] * colspan)
        if date_sequence and date_sequence[0] is None:
            date_sequence = date_sequence[1:]

        periods_raw = [c.get_text(strip=True) for c in time_row.find_all(["td", "th"], recursive=False)]
        if len(periods_raw) != len(date_sequence):
            length = min(len(periods_raw), len(date_sequence))
            periods_raw = periods_raw[:length]
            date_sequence = date_sequence[:length]

        phrases = self._row_values(table, "phrases")
        wind = self._row_values(table, "wind")
        snow = self._row_values(table, "snow")
        rain = self._row_values(table, "rain")
        temp_max = self._row_values(table, "temperature-max")
        temp_min = self._row_values(table, "temperature-min")

        periods: List[ForecastPeriod] = []
        for idx, (date_str, period_label) in enumerate(zip(date_sequence, periods_raw)):
            if not date_str:
                continue
            if date_str != target_date.isoformat():
                continue
            period_enum = self._normalize_period(period_label)
            if period_enum is None:
                continue
            wind_speed, wind_dir = self._parse_wind(wind, idx)
            period = ForecastPeriod(
                mountain_id=mountain.mountain_id,
                source_name=self.source_name,
                target_date=target_date,
                period=period_enum,
                snowfall_cm=self._extract_float(snow, idx),
                temp_high_c=self._extract_float(temp_max, idx),
                temp_low_c=self._extract_float(temp_min, idx),
                wind_speed_ms=wind_speed,
                wind_dir=wind_dir,
                weather_desc=self._value_at(phrases, idx),
                notes=self._build_notes(rain, idx),
            )
            periods.append(period)
        return periods

    @staticmethod
    def _row_values(table: BeautifulSoup, row_name: str) -> List[str]:
        row = table.select_one(f"tr[data-row='{row_name}']")
        if not row:
            return []
        cells = row.find_all(["td", "th"], recursive=False)
        values = [c.get_text(strip=True) for c in cells]
        if values:
            values = values[1:]
        return values

    @staticmethod
    def _value_at(values: List[str], index: int) -> Optional[str]:
        if index >= len(values):
            return None
        value = values[index].strip()
        return value or None

    @classmethod
    def _extract_float(cls, values: List[str], index: int) -> Optional[float]:
        text = cls._value_at(values, index)
        if not text:
            return None
        match = _NUM_RE.search(text)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None

    @classmethod
    def _parse_wind(cls, values: List[str], index: int) -> tuple[Optional[float], Optional[str]]:
        text = cls._value_at(values, index)
        if not text:
            return None, None
        match = _WIND_COMBINED_RE.search(text)
        if not match:
            return None, None
        speed = float(match.group("speed"))
        direction = match.group("dir")
        speed_ms = round(speed / 3.6, 2)
        return speed_ms, direction

    @staticmethod
    def _build_notes(values: List[str], index: int) -> Optional[str]:
        text = SnowForecastSource._value_at(values, index)
        if not text:
            return None
        match = _NUM_RE.search(text)
        if not match:
            return None
        return f"rain_mm={match.group()}"

    @staticmethod
    def _normalize_period(label: str | None) -> Optional[Period]:
        if not label:
            return None
        cleaned = label.strip().lower()
        cleaned = re.sub(r"[^a-z ]", " ", cleaned)
        for token in cleaned.split():
            if token in _PERIOD_MAP:
                return _PERIOD_MAP[token]
        for jp_label, period in _JAPANESE_PERIOD_MAP.items():
            if jp_label in label:
                return period
        return None


__all__ = ["SnowForecastSource"]

