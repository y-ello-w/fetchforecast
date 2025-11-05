from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, Iterable, List

from . import config
from .models import ForecastDaily, Mountain
from .sources.base import BaseSource


def run_daily(
    target_date: dt.date,
    mountains: Iterable[Mountain],
    sources: Dict[str, BaseSource],
    *,
    output_dir: Path | None = None,
) -> List[ForecastDaily]:
    config.ensure_directories()
    folder = output_dir or config.data_folder_for(target_date.isoformat())
    results: List[ForecastDaily] = []
    for mountain in mountains:
        for key, source in sources.items():
            if key not in mountain.sources and mountain.sources:
                continue
            daily = source.collect(mountain, target_date)
            results.append(daily)
            write_daily_json(folder, daily)
    return results


def write_daily_json(folder: Path, daily: ForecastDaily) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{daily.mountain_id}_{daily.source_name}_{daily.target_date.isoformat()}.json"
    path = folder / filename
    payload = json.dumps(daily.model_dump(mode="json"), indent=2, ensure_ascii=False)
    path.write_text(payload, encoding="utf-8")


__all__ = ["run_daily", "write_daily_json"]

