from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import sys
from pathlib import Path as _PathForSys

# Ensure the project's src/ is on sys.path so this script runs without PYTHONPATH
_PROJECT_ROOT = _PathForSys(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from backcountry import config
from backcountry.models import Mountain
from backcountry.pipeline import run_daily
from backcountry.sources.mountainforecast import MountainForecastSource
from backcountry.sources.powdersearch import PowderSearchSource
from backcountry.sources.snowforecast import SnowForecastSource


def load_mountains(path: Path) -> list[Mountain]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Mountain(**entry) for entry in data]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily backcountry forecast pipeline")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD", default=dt.date.today().isoformat())
    parser.add_argument("--mountains", type=Path, default=config.PROJECT_ROOT / "mountains.json")
    args = parser.parse_args()

    target_date = dt.date.fromisoformat(args.date)
    mountains = load_mountains(args.mountains)
    sources = {
        "snowforecast": SnowForecastSource(),
        "powdersearch": PowderSearchSource(),
        "mountainforecast": MountainForecastSource(),
    }

    run_daily(target_date, mountains, sources)


if __name__ == "__main__":
    main()
