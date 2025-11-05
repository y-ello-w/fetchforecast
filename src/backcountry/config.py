from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
# Note: project stores mountain configuration in JSON (see README and scripts)
# Keep this constant aligned with that filename for clarity.
DEFAULT_MOUNTAIN_LIST = PROJECT_ROOT / "mountains.json"
DEFAULT_SOURCES: List[str] = ["snowforecast", "mountainforecast", "powdersearch"]


def ensure_directories(extra_paths: Iterable[Path] | None = None) -> None:
    """Create standard directories if they do not yet exist."""
    paths = [DATA_DIR, LOG_DIR]
    if extra_paths:
        paths.extend(extra_paths)
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def data_folder_for(date_str: str) -> Path:
    """Return the folder where normalized data for the given date is stored."""
    folder = DATA_DIR / date_str
    folder.mkdir(parents=True, exist_ok=True)
    return folder

