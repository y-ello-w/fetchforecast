import datetime as dt
from pathlib import Path

import pytest

from backcountry.models import Mountain, Period
from backcountry.sources.base import DEFAULT_TIMEOUT
from backcountry.sources.mountainforecast import MountainForecastSource


def test_collect_mountainforecast_fixture():
    html = Path("tests/fixtures/mountainforecast_sample.html").read_text(encoding="utf-8")
    source = MountainForecastSource()
    source.fetch_text = lambda url, *, timeout=DEFAULT_TIMEOUT: html  # type: ignore[assignment]

    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"mountainforecast": "https://example.com/mountain"},
    )

    target_date = dt.date(2025, 6, 2)
    daily = source.collect(mountain, target_date)

    assert daily.source_name == "mountainforecast"
    assert len(daily.periods) == 3

    night = next(period for period in daily.periods if period.period == Period.NIGHT)
    morning = next(period for period in daily.periods if period.period == Period.MORNING)
    afternoon = next(period for period in daily.periods if period.period == Period.AFTERNOON)

    assert night.temp_high_c == pytest.approx(-5.0)
    assert night.temp_low_c == pytest.approx(-8.0)
    assert night.wind_dir == "NW"
    assert night.wind_speed_ms == pytest.approx(8.33, rel=1e-2)
    assert night.snowfall_cm is None
    assert night.notes == "rain_mm=0.2;wind_chill_c=-12.0"

    assert morning.snowfall_cm == pytest.approx(0.5)
    assert morning.wind_dir == "N"
    assert morning.wind_speed_ms == pytest.approx(5.56, rel=1e-2)
    assert morning.weather_desc == "clear"
    assert morning.notes == "wind_chill_c=-9.0"

    assert afternoon.snowfall_cm == pytest.approx(1.0)
    assert afternoon.wind_dir == "WNW"
    assert afternoon.wind_speed_ms == pytest.approx(12.5, rel=1e-2)
    assert "wind_chill_c=-7.0" in (afternoon.notes or "")

    summary = daily.daily_summary_json
    assert summary["source_urls"] == ["https://example.com/mountain"]
    assert len(summary["columns"]) == 3
    first_column = summary["columns"][0]
    assert first_column["rain_mm"] == pytest.approx(0.2)
    assert summary["columns"][1]["rain_mm"] is None
    assert summary["columns"][2]["snowfall_cm"] == pytest.approx(1.0)

def test_collect_mountainforecast_fallback_on_error():
    source = MountainForecastSource()

    def _raise(*args, **kwargs):
        import requests
        raise requests.HTTPError("404 Not Found")

    source.fetch_text = _raise  # type: ignore[assignment]

    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"mountainforecast": "https://example.com/mountain"},
    )

    target_date = dt.date(2025, 6, 2)
    daily = source.collect(mountain, target_date)

    assert daily.source_name == "mountainforecast"
    assert len(daily.periods) == 3
    for period in daily.periods:
        assert period.snowfall_cm == 0.0
        assert period.wind_speed_ms == 0.0
        assert period.wind_dir == "-"
        assert period.weather_desc == "-"
        assert period.notes == "-"

    summary = daily.daily_summary_json
    assert summary["status"] == "fallback"
    assert summary["source_urls"] == ["https://example.com/mountain"]
    assert all(column["rain_mm"] == 0.0 for column in summary["columns"])
