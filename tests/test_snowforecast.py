import datetime as dt
from pathlib import Path

from backcountry.models import Mountain, Period
from backcountry.sources.snowforecast import SnowForecastSource


def test_parse_snowforecast_fixture():
    html = Path("tests/fixtures/snowforecast_sample.html").read_text(encoding="utf-8")
    source = SnowForecastSource()
    mountain = Mountain(
        mountain_id="hakuba",
        name="Hakuba",
        sources={"snowforecast": "https://example.com/hakuba"},
    )
    periods = source.parse(
        mountain,
        target_date=dt.date(2025, 1, 10),
        fetched_at=dt.datetime(2025, 1, 9, 0, 0),
        text=html,
        url="https://example.com/hakuba",
    )

    assert [p.period for p in periods] == [Period.NIGHT, Period.MORNING, Period.AFTERNOON]

    night, morning, afternoon = periods
    assert night.snowfall_cm == 5.0
    assert night.wind_speed_ms == 2.78
    assert night.wind_dir == "NW"
    assert night.temp_low_c == -12.0
    assert night.notes == "rain_mm=0"

    assert morning.snowfall_cm == 2.0
    assert morning.temp_high_c == -3.0
    assert morning.wind_speed_ms == 4.17
    assert morning.notes == "rain_mm=1"

    assert afternoon.snowfall_cm == 10.0
    assert afternoon.wind_speed_ms == 5.56
    assert afternoon.weather_desc == "Heavy snow"
    assert afternoon.temp_low_c == -15.0

