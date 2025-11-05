from __future__ import annotations

import datetime as dt
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List
from urllib.parse import unquote, urlparse

import requests

from ..models import ForecastDaily, ForecastPeriod, Mountain

DEFAULT_TIMEOUT = 20


class BaseSource(ABC):
    """Common interface for forecast scraping sources."""

    source_name: str

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (compatible; BackcountryBot/0.1; +https://example.com/bot)",
        )

    def fetch_text(self, url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
        if self._is_local_url(url):
            path = self._resolve_local_path(url)
            return self._load_local_text(path)
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _is_local_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in ("", "file")

    @staticmethod
    def _resolve_local_path(url: str) -> Path:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            path_str = unquote(parsed.path)
            if parsed.netloc and parsed.netloc not in ("", "localhost"):
                path_str = f"//{parsed.netloc}{path_str}"
        else:
            path_str = url
        path = Path(path_str)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path

    @staticmethod
    def _load_local_text(path: Path) -> str:
        data = path.read_bytes()
        for encoding in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    @abstractmethod
    def build_requests(self, mountain: Mountain, target_date: dt.date) -> Iterable[str]:
        """Return the URLs to fetch for the given mountain and date."""

    @abstractmethod
    def parse(
        self,
        mountain: Mountain,
        target_date: dt.date,
        fetched_at: dt.datetime,
        text: str,
        *,
        url: str,
    ) -> List[ForecastPeriod]:
        """Turn response text into normalized period forecasts."""

    def collect(self, mountain: Mountain, target_date: dt.date) -> ForecastDaily:
        fetched_at = dt.datetime.utcnow()
        period_entries: List[ForecastPeriod] = []
        for url in self.build_requests(mountain, target_date):
            text = self._fetch_with_fallback(url, mountain, target_date)
            period_entries.extend(
                self.parse(
                    mountain,
                    target_date,
                    fetched_at,
                    text,
                    url=url,
                )
            )
        daily = ForecastDaily(
            mountain_id=mountain.mountain_id,
            source_name=self.source_name,
            target_date=target_date,
            periods=period_entries,
        )
        return daily

    def _fetch_with_fallback(
        self,
        url: str,
        mountain: Mountain,
        target_date: dt.date,
        *,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        if self._is_local_url(url):
            path = self._resolve_local_path(url)
            return self._load_local_text(path)
        try:
            return self.fetch_text(url, timeout=timeout)
        except requests.RequestException as exc:
            fallback_path = self._offline_sample_path(target_date)
            if fallback_path and fallback_path.exists():
                return self._load_local_text(fallback_path)
            if fallback_path:
                raise RuntimeError(
                    f"Failed to fetch {url!r} and offline sample not found at {fallback_path}"
                ) from exc
            raise

    def _offline_sample_path(self, target_date: dt.date) -> Path | None:
        flag = os.environ.get("BACKCOUNTRY_OFFLINE")
        if not flag:
            return None
        offline_dir = os.environ.get("BACKCOUNTRY_OFFLINE_SAMPLE_DIR", "local_samples")
        path = Path(offline_dir)
        if not path.is_absolute():
            from .. import config

            path = config.PROJECT_ROOT / path
        filename = f"{self.source_name}_{target_date.isoformat()}.html"
        return path / filename


__all__ = ["BaseSource"]

