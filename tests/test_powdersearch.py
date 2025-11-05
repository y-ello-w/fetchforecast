import datetime as dt
from pathlib import Path

from backcountry.models import Mountain
from backcountry.sources.base import DEFAULT_TIMEOUT
from backcountry.sources.powdersearch import PowderSearchSource


def test_collect_powdersearch_fixture():
    html = Path("tests/fixtures/powdersearch_sample.html").read_text(encoding="utf-8")
    source = PowderSearchSource()
    source.fetch_text = lambda url, *, timeout=DEFAULT_TIMEOUT: html  # type: ignore[assignment]

    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"powdersearch": "https://example.com/200081d3g.html"},
    )

    target_date = dt.date(2025, 6, 2)
    daily = source.collect(mountain, target_date)

    assert daily.source_name == "powdersearch"
    assert daily.periods == []

    summary = daily.daily_summary_json
    assert summary["source_urls"] == ["https://example.com/200081d3g.html"]
    assert "fetched_at" in summary

    hours = summary["hours"]
    assert [entry["hour"] for entry in hours] == [21, 22, 23]

    hour_22 = next(entry for entry in hours if entry["hour"] == 22)
    assert hour_22["temperature_c"] == 11.5
    assert hour_22["precipitation_mm"] == 1.0
    assert hour_22["wind_direction"] == "NW"
    assert hour_22["wind_speed_ms"] == 4.5
    assert hour_22["sunshine_hours"] == 0.0
    assert hour_22["snow_depth_cm"] is None
    assert hour_22["snowfall_cm"] is None

    hour_21 = next(entry for entry in hours if entry["hour"] == 21)
    assert hour_21["temperature_c"] is None
    assert hour_21["precipitation_mm"] is None
    assert hour_21["wind_direction"] is None
    assert hour_21["wind_speed_ms"] is None

    hour_23 = next(entry for entry in hours if entry["hour"] == 23)
    assert hour_23["snow_depth_cm"] == 45.0
    assert hour_23["snowfall_cm"] == 0.0
