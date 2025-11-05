from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Dict, List, Optional

try:  # Prefer real pydantic if available.
    from pydantic import BaseModel, Field  # type: ignore
except (ModuleNotFoundError, ImportError):  # pragma: no cover - offline fallback
    from .compat.pydantic import BaseModel, Field  # type: ignore


class Period(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"


class Mountain(BaseModel):
    mountain_id: str
    name: str
    region: Optional[str] = None
    sources: Dict[str, str] = Field(default_factory=dict)
    elevation: Optional[int] = None
    notes: Optional[str] = None


class SourceRaw(BaseModel):
    id: str
    mountain_id: str
    source_name: str
    fetched_at: dt.datetime
    raw_payload: str
    status: str
    notes: Optional[str] = None


class ForecastPeriod(BaseModel):
    mountain_id: str
    source_name: str
    target_date: dt.date
    period: Period
    snowfall_cm: Optional[float] = None
    snowdepth_cm: Optional[float] = None
    temp_low_c: Optional[float] = None
    temp_high_c: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_gust_ms: Optional[float] = None
    wind_dir: Optional[str] = None
    weather_desc: Optional[str] = None
    notes: Optional[str] = None


class ForecastDaily(BaseModel):
    mountain_id: str
    source_name: str
    target_date: dt.date
    periods: List[ForecastPeriod]
    daily_summary_json: Dict[str, Any] = Field(default_factory=dict)
    condition_score: Optional[float] = None
    confidence: Optional[float] = None


class HolidayDay(BaseModel):
    date: dt.date
    is_weekend: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    notes: Optional[str] = None


class SummaryReport(BaseModel):
    report_date: dt.date
    mountain_id: str
    target_date: dt.date
    aggregate_score: Optional[float] = None
    headline: Optional[str] = None
    details_json: Dict[str, Any] = Field(default_factory=dict)
    published_at: Optional[dt.datetime] = None


class ObservationActual(BaseModel):
    mountain_id: str
    observation_date: dt.date
    snowfall_cm: Optional[float] = None
    snowdepth_cm: Optional[float] = None
    temp_c: Optional[float] = None
    notes: Optional[str] = None

