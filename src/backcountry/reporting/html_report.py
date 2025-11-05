from __future__ import annotations

from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import ForecastDaily


def render_daily_html(dailies: Iterable[ForecastDaily], *, template_dir: Path, output_path: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("daily_report.html")
    html = template.render(dailies=list(dailies))
    output_path.write_text(html, encoding="utf-8")


__all__ = ["render_daily_html"]

