from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

import sys
from pathlib import Path as _PathForSys

# Ensure the project's src/ is on sys.path so this script runs without PYTHONPATH
_PROJECT_ROOT = _PathForSys(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from backcountry import config
from backcountry.models import ForecastDaily
from backcountry.reporting.html_report import render_daily_html


def load_daily_json(paths: Iterable[Path]) -> List[ForecastDaily]:
    dailies: List[ForecastDaily] = []
    for path in paths:
        try:
            dailies.append(ForecastDaily.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"warning: failed to parse {path}: {exc}", file=sys.stderr)
    return dailies


def iter_daily_files(dates: Iterable[str]) -> Iterable[Path]:
    for date_str in dates:
        folder = config.DATA_DIR / date_str
        if not folder.exists():
            print(f"warning: {folder} does not exist", file=sys.stderr)
            continue
        yield from sorted(folder.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render HTML report from stored daily forecasts")
    parser.add_argument("dates", nargs="+", help="Target dates (YYYY-MM-DD)")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML path",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=config.PROJECT_ROOT / "templates",
        help="Template directory containing daily_report.html",
    )
    args = parser.parse_args()

    files = list(iter_daily_files(args.dates))
    if not files:
        print("no forecast files found for given dates", file=sys.stderr)
        return 1

    dailies = load_daily_json(files)
    if not dailies:
        print("no valid forecast entries parsed", file=sys.stderr)
        return 1

    if args.output:
        output_path = args.output
    else:
        start = args.dates[0]
        end = args.dates[-1]
        output_path = config.PROJECT_ROOT / "reports" / f"forecast_{start}_to_{end}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    render_daily_html(dailies, template_dir=args.template_dir, output_path=output_path)
    print(f"report written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

