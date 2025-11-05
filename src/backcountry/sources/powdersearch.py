from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..models import ForecastDaily, ForecastPeriod, Mountain
from .base import BaseSource, DEFAULT_TIMEOUT

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_MISSING_MARKERS = {"/", "-", "--"}


class PowderSearchSource(BaseSource):
    """Scrape hourly conditions from PowderSearch."""

    source_name = "powdersearch"

    def build_requests(self, mountain: Mountain, target_date: dt.date) -> List[str]:
        url = mountain.sources.get(self.source_name)
        if not url:
            raise ValueError(f"PowderSearch URL is not configured for {mountain.mountain_id}")
        return [url]

    def fetch_text(self, url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
        if self._is_local_url(url):
            path = self._resolve_local_path(url)
            return self._load_local_text(path)
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "shift_jis" in content_type or "sjis" in content_type:
            response.encoding = "shift_jis"
        else:
            if response.encoding and response.encoding.lower() == "iso-8859-1" and response.apparent_encoding:
                response.encoding = response.apparent_encoding
            elif not response.encoding:
                response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def collect(
        self,
        mountain: Mountain,
        target_date: dt.date,
    ) -> ForecastDaily:
        fetched_at = dt.datetime.now(dt.timezone.utc)
        all_hours: List[Dict[str, object]] = []
        urls: List[str] = []
        for url in self.build_requests(mountain, target_date):
            text = self._fetch_with_fallback(url, mountain, target_date)
            urls.append(url)
            hourly_entries = self._parse_hourly_table(text, target_date)
            all_hours.extend(hourly_entries)
        all_hours.sort(key=lambda item: int(item["hour"]))
        summary = {
            "hours": all_hours,
            "source_urls": urls,
            "fetched_at": fetched_at.isoformat(),
            "units": {
                "temperature_c": "degC",
                "precipitation_mm": "mm",
                "wind_speed_ms": "m/s",
                "sunshine_hours": "hours",
                "snow_depth_cm": "cm",
                "snowfall_cm": "cm",
            },
        }
        return ForecastDaily(
            mountain_id=mountain.mountain_id,
            source_name=self.source_name,
            target_date=target_date,
            periods=[],
            daily_summary_json=summary,
        )

    def parse(
        self,
        mountain: Mountain,
        target_date: dt.date,
        fetched_at: dt.datetime,
        text: str,
        *,
        url: str,
    ) -> List[ForecastPeriod]:
        # The aggregate data is exposed via collect(), so no period data is returned here.
        return []

    def _parse_hourly_table(self, html: str, target_date: dt.date) -> List[Dict[str, object]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table#detail_data")
        if table is None:
            return []
        body = table.find("tbody") or table
        target_day = target_date.day
        current_day: Optional[int] = None
        hours: List[Dict[str, object]] = []
        for row in body.find_all("tr", recursive=False):
            cells = row.find_all(["td", "th"], recursive=False)
            if not cells:
                continue
            if cells[0].name == "th":
                continue
            if len(cells) == 1 and cells[0].has_attr("colspan"):
                continue
            first_cell = cells[0]
            if isinstance(first_cell, Tag) and first_cell.has_attr("rowspan"):
                current_day = self._extract_int(first_cell)
                cells = cells[1:]
            if current_day is None or current_day != target_day:
                continue
            if not cells:
                continue
            hour_value = self._extract_int(cells[0])
            if hour_value is None:
                continue
            temperature = self._extract_float(cells, 1)
            precipitation = self._extract_float(cells, 2)
            wind_direction, wind_speed = self._parse_wind(cells, 3)
            sunshine = self._extract_float(cells, 4)
            snow_depth = self._extract_float(cells, 5)
            snowfall = self._extract_float(cells, 6)
            entry: Dict[str, object] = {
                "hour": hour_value,
                "temperature_c": temperature,
                "precipitation_mm": precipitation,
                "wind_direction": wind_direction,
                "wind_speed_ms": wind_speed,
                "sunshine_hours": sunshine,
                "snow_depth_cm": snow_depth,
                "snowfall_cm": snowfall,
            }
            hours.append(entry)
        return hours

    @staticmethod
    def _cell_text(cell: Tag | None) -> str:
        if cell is None:
            return ""
        text = cell.get_text(separator=" ", strip=True)
        return text.replace("\u3000", " ").strip()

    @classmethod
    def _extract_int(cls, cell: Tag | None) -> Optional[int]:
        if cell is None:
            return None
        text = cls._cell_text(cell)
        match = _NUM_RE.search(text)
        if not match:
            return None
        try:
            return int(float(match.group()))
        except ValueError:
            return None

    @classmethod
    def _extract_float(cls, cells: Sequence[Tag], index: int) -> Optional[float]:
        if index >= len(cells):
            return None
        text = cls._cell_text(cells[index])
        if not text or text in _MISSING_MARKERS:
            return None
        match = _NUM_RE.search(text)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None

    @classmethod
    def _parse_wind(cls, cells: Sequence[Tag], index: int) -> Tuple[Optional[str], Optional[float]]:
        if index >= len(cells):
            return None, None
        text = cls._cell_text(cells[index])
        if not text or text in _MISSING_MARKERS:
            return None, None
        direction: Optional[str]
        speed: Optional[float]
        if "/" in text:
            direction_part, speed_part = text.split("/", 1)
            direction = direction_part.strip() or None
            speed = cls._parse_float_value(speed_part)
        else:
            direction = text.strip() or None
            speed = None
        return direction, speed

    @staticmethod
    def _parse_float_value(text: str) -> Optional[float]:
        match = _NUM_RE.search(text)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None
