import datetime as dt

import requests

from backcountry.models import Mountain
from backcountry.sources.powdersearch import PowderSearchSource
from backcountry.sources.snowforecast import SnowForecastSource


def test_snowforecast_offline_fallback(monkeypatch):
    source = SnowForecastSource()
    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"snowforecast": "https://example.com/hakuba"},
    )
    target_date = dt.date(2025, 10, 13)

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("network blocked")

    source.fetch_text = _raise  # type: ignore[assignment]
    monkeypatch.setenv("BACKCOUNTRY_OFFLINE", "1")
    monkeypatch.setenv("BACKCOUNTRY_OFFLINE_SAMPLE_DIR", "local_samples")

    daily = source.collect(mountain, target_date)

    assert daily.periods, "offline fallback should load local sample periods"
    assert {period.target_date for period in daily.periods} == {target_date}


def test_powdersearch_offline_fallback(monkeypatch):
    source = PowderSearchSource()
    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"powdersearch": "https://example.com/200081d3g.html"},
    )
    target_date = dt.date(2025, 10, 13)

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("network blocked")

    source.fetch_text = _raise  # type: ignore[assignment]
    monkeypatch.setenv("BACKCOUNTRY_OFFLINE", "1")
    monkeypatch.setenv("BACKCOUNTRY_OFFLINE_SAMPLE_DIR", "local_samples")

    daily = source.collect(mountain, target_date)

    summary = daily.daily_summary_json
    assert summary["hours"], "offline fallback should populate hourly summary"
    assert summary["source_urls"] == ["https://example.com/200081d3g.html"]
