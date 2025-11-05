from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from ..models import ForecastDaily, ForecastPeriod, Mountain, Period
from .base import BaseSource, DEFAULT_TIMEOUT

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_WIND_RE = re.compile(r"(?P<speed>\d+)(?:-(?P<gust>\d+))?(?P<dir>[A-Z]+)?")
_MISSING_MARKERS = {"?", "-", "--", ""}
_PERIOD_MAP = {"night": Period.NIGHT, "am": Period.MORNING, "pm": Period.AFTERNOON}


class MountainForecastSource(BaseSource):
    """Scrape period forecasts from Mountain-Forecast."""

    source_name = "mountainforecast"

    def build_requests(self, mountain: Mountain, target_date: dt.date) -> List[str]:
        url = mountain.sources.get(self.source_name)
        if not url:
            raise ValueError(f"Mountain-Forecast URL is not configured for {mountain.mountain_id}")
        return [url]

    def fetch_text(self, url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
        if self._is_local_url(url):
            path = self._resolve_local_path(url)
            return self._load_local_text(path)
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        if not response.encoding:
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def collect(
        self,
        mountain: Mountain,
        target_date: dt.date,
    ) -> ForecastDaily:
        fetched_at = dt.datetime.now(dt.timezone.utc)
        periods: List[ForecastPeriod] = []
        summary_columns: List[Dict[str, object]] = []
        source_urls: List[str] = []
        for url in self.build_requests(mountain, target_date):
            try:
                text = self._fetch_with_fallback(url, mountain, target_date)
            except requests.RequestException as exc:
                return self._fallback_daily(mountain, target_date, fetched_at, [url], str(exc))
            source_urls.append(url)
            parsed_periods, parsed_summary = self._parse_forecast_table(text, mountain, target_date)
            periods.extend(parsed_periods)
            summary_columns.extend(parsed_summary)
        daily = ForecastDaily(
            mountain_id=mountain.mountain_id,
            source_name=self.source_name,
            target_date=target_date,
            periods=periods,
            daily_summary_json={
                "columns": summary_columns,
                "source_urls": source_urls,
                "fetched_at": fetched_at.isoformat(),
                "units": {
                    "temperature_c": "degC",
                    "wind_speed_kmh": "km/h",
                    "wind_speed_ms": "m/s",
                    "rain_mm": "mm",
                    "snowfall_cm": "cm",
                    "wind_chill_c": "degC",
                },
            },
        )
        return daily

    def parse(
        self,
        mountain: Mountain,
        target_date: dt.date,
        fetched_at: dt.datetime,
        text: str,
        *,
        url: str,
    ) -> List[ForecastPeriod]:
        periods, _ = self._parse_forecast_table(text, mountain, target_date)
        return periods

    def _fallback_daily(
        self,
        mountain: Mountain,
        target_date: dt.date,
        fetched_at: dt.datetime,
        source_urls: List[str],
        reason: str,
    ) -> ForecastDaily:
        placeholder_periods: List[ForecastPeriod] = []
        summary_columns: List[Dict[str, object]] = []
        target_iso = target_date.isoformat()
        for period_enum, label in [
            (Period.NIGHT, "night"),
            (Period.MORNING, "am"),
            (Period.AFTERNOON, "pm"),
        ]:
            placeholder_periods.append(
                ForecastPeriod(
                    mountain_id=mountain.mountain_id,
                    source_name=self.source_name,
                    target_date=target_date,
                    period=period_enum,
                    snowfall_cm=0.0,
                    snowdepth_cm=0.0,
                    temp_low_c=0.0,
                    temp_high_c=0.0,
                    wind_speed_ms=0.0,
                    wind_gust_ms=0.0,
                    wind_dir="-",
                    weather_desc="-",
                    notes="-",
                )
            )
            summary_columns.append(
                {
                    "date": target_iso,
                    "period_label": label,
                    "weather": "-",
                    "wind_direction": "-",
                    "wind_speed_kmh": 0.0,
                    "wind_speed_ms": 0.0,
                    "wind_gust_kmh": 0.0,
                    "wind_gust_ms": 0.0,
                    "temperature_max_c": 0.0,
                    "temperature_min_c": 0.0,
                    "temperature_chill_c": 0.0,
                    "snowfall_cm": 0.0,
                    "rain_mm": 0.0,
                }
            )
        return ForecastDaily(
            mountain_id=mountain.mountain_id,
            source_name=self.source_name,
            target_date=target_date,
            periods=placeholder_periods,
            daily_summary_json={
                "status": "fallback",
                "reason": reason,
                "source_urls": source_urls,
                "fetched_at": fetched_at.isoformat(),
                "columns": summary_columns,
                "units": {
                    "temperature_c": "degC",
                    "wind_speed_kmh": "km/h",
                    "wind_speed_ms": "m/s",
                    "rain_mm": "mm",
                    "snowfall_cm": "cm",
                    "wind_chill_c": "degC",
                },
            },
        )

    def _parse_forecast_table(
        self,
        html: str,
        mountain: Mountain,
        target_date: dt.date,
    ) -> Tuple[List[ForecastPeriod], List[Dict[str, object]]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.forecast-table__table--content")
        if table is None:
            return [], []
        date_labels = self._expand_dates(table)
        time_labels = self._row_values(table, "time")
        if not date_labels or not time_labels:
            return [], []
        column_count = min(len(date_labels), len(time_labels))
        date_labels = date_labels[:column_count]
        time_labels = time_labels[:column_count]

        phrases = self._row_values(table, "phrases")
        weather = self._row_values(table, "weather")
        wind_values = self._row_values(table, "wind")
        snow_values = self._row_values(table, "snow")
        rain_values = self._row_values(table, "rain")
        temp_max_values = self._row_values(table, "temperature-max")
        temp_min_values = self._row_values(table, "temperature-min")
        temp_chill_values = self._row_values(table, "temperature-chill")

        periods: List[ForecastPeriod] = []
        summary: List[Dict[str, object]] = []
        target_iso = target_date.isoformat()

        for index in range(column_count):
            date_str = date_labels[index]
            time_label = time_labels[index]
            if not date_str or not time_label:
                continue
            part = self._normalize_period(time_label)
            if part is None:
                continue
            phrase = self._value_at(phrases, index) or self._value_at(weather, index)
            weather_desc = phrase or None
            wind_dir, wind_speed_ms, wind_speed_kmh, wind_gust_ms, wind_gust_kmh = self._parse_wind(
                self._value_at(wind_values, index)
            )
            snow = self._parse_float(self._value_at(snow_values, index))
            rain = self._parse_float(self._value_at(rain_values, index))
            temp_max = self._parse_float(self._value_at(temp_max_values, index))
            temp_min = self._parse_float(self._value_at(temp_min_values, index))
            temp_chill = self._parse_float(self._value_at(temp_chill_values, index))

            summary_entry: Dict[str, object] = {
                "date": date_str,
                "period_label": time_label.lower(),
                "weather": weather_desc,
                "wind_direction": wind_dir,
                "wind_speed_kmh": wind_speed_kmh,
                "wind_speed_ms": wind_speed_ms,
                "wind_gust_kmh": wind_gust_kmh,
                "wind_gust_ms": wind_gust_ms,
                "temperature_max_c": temp_max,
                "temperature_min_c": temp_min,
                "temperature_chill_c": temp_chill,
                "snowfall_cm": snow,
                "rain_mm": rain,
            }
            summary.append(summary_entry)

            if date_str != target_iso:
                continue

            notes_parts: List[str] = []
            if rain is not None:
                notes_parts.append(f"rain_mm={rain}")
            if temp_chill is not None:
                notes_parts.append(f"wind_chill_c={temp_chill}")
            notes = ";".join(notes_parts) if notes_parts else None

            period = ForecastPeriod(
                mountain_id=mountain.mountain_id,
                source_name=self.source_name,
                target_date=target_date,
                period=part,
                snowfall_cm=snow,
                temp_high_c=temp_max,
                temp_low_c=temp_min,
                wind_speed_ms=wind_speed_ms,
                wind_gust_ms=wind_gust_ms,
                wind_dir=wind_dir,
                weather_desc=weather_desc,
                notes=notes,
            )
            periods.append(period)

        return periods, summary

    @staticmethod
    def _expand_dates(table: Tag) -> List[Optional[str]]:
        row = table.select_one("tr[data-row='days']")
        if row is None:
            return []
        labels: List[Optional[str]] = []
        for cell in row.find_all("td", recursive=False):
            date_str = cell.get("data-date")
            colspan = int(cell.get("colspan") or 1)
            labels.extend([date_str] * colspan)
        return labels

    def _row_values(self, table: Tag, row_name: str) -> List[Optional[str]]:
        row = table.select_one(f"tr[data-row='{row_name}']")
        if row is None:
            return []
        values: List[Optional[str]] = []
        for cell in row.find_all("td", recursive=False):
            values.append(self._cell_text(cell))
        return values

    @staticmethod
    def _cell_text(cell: Tag | None) -> Optional[str]:
        if cell is None:
            return None
        text = cell.get_text(" ", strip=True)
        text = text.replace("\xa0", " ").strip()
        if not text or text in _MISSING_MARKERS:
            return None
        return text

    @staticmethod
    def _value_at(values: Sequence[Optional[str]], index: int) -> Optional[str]:
        if index >= len(values):
            return None
        return values[index]

    @staticmethod
    def _parse_float(text: Optional[str]) -> Optional[float]:
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
    def _parse_wind(
        cls,
        text: Optional[str],
    ) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float], Optional[float]]:
        if not text:
            return None, None, None, None, None
        cleaned = text.replace("\u2013", "-")
        cleaned = cleaned.replace("km/h", "")
        cleaned = cleaned.replace("KM/H", "")
        cleaned = cleaned.replace("Calm", "0")
        cleaned = cleaned.replace("calm", "0")
        cleaned = cleaned.replace("\xa0", "")
        cleaned_no_space = cleaned.replace(" ", "")
        cleaned_no_space = cleaned_no_space.upper()
        if cleaned_no_space in {"", "0"}:
            return None, 0.0, 0.0, None, None
        match = _WIND_RE.search(cleaned_no_space)
        if not match:
            return None, None, None, None, None
        speed_kmh = float(match.group("speed"))
        gust = match.group("gust")
        gust_kmh = float(gust) if gust else None
        direction = match.group("dir") or None
        speed_ms = round(speed_kmh / 3.6, 2)
        gust_ms = round(gust_kmh / 3.6, 2) if gust_kmh is not None else None
        return direction, speed_ms, speed_kmh, gust_ms, gust_kmh

    @staticmethod
    def _normalize_period(label: str) -> Optional[Period]:
        cleaned = label.strip().lower()
        return _PERIOD_MAP.get(cleaned)


__all__ = ["MountainForecastSource"]
