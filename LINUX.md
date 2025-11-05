# Linux/WSL Setup Guide (VS Code)

This project is intended to run on Linux. For WSL (Windows Subsystem for Linux) with VS Code, use the following setup. The canonical project root is:

- /home/y_ello_w/work/project/backcountry

## Prerequisites
- Windows 10/11 with WSL2 enabled and a Linux distro (e.g., Ubuntu)
- VS Code + Remote Development (WSL) extension installed on Windows
- Python 3.10+ on WSL (3.11 recommended)

## First-time Setup (WSL shell)
```bash
# Create workspace folder and place repo
mkdir -p /home/y_ello_w/work/project
cd /home/y_ello_w/work/project
# Option A: clone
# git clone <repo_url> backcountry
# Option B: copy project here if already on Windows side
#  (Explorer) \\wsl$\\<Distro>\\home\\y_ello_w\\work\\project

cd backcountry

# Python virtualenv
python3 -m venv .venv
source .venv/bin/activate
python -V

# Install dependencies
pip install -U pip
pip install -r requirements.txt
```

## Open in VS Code (Remote - WSL)
1. From Windows VS Code, press F1 → "WSL: Connect to WSL".
2. File → Open Folder… → select `/home/y_ello_w/work/project/backcountry`.
3. When prompted, install recommended extensions in WSL.
4. Select interpreter: `.venv/bin/python` (bottom-left Python status item).
5. Testing: the repo includes `.env` with `PYTHONPATH=src`, so discovery works.

## Quick Commands
- Run daily pipeline
```bash
python scripts/run_daily.py --date 2025-10-11
```
- Render report
```bash
python scripts/render_report.py 2025-10-11 2025-10-12
```
- Run tests
```bash
pytest -q
# or via VS Code Test Explorer
```

## Scheduling (cron)
```bash
crontab -e
# Example: run every day at 06:00 (JST)
0 6 * * * cd /home/y_ello_w/work/project/backcountry && . .venv/bin/activate && python scripts/run_daily.py >> logs/cron.log 2>&1
```

## Access from Windows
- Explorer path: `\\wsl$\<Distro>\home\y_ello_w\work\project\backcountry`
- If you need to copy reports to Windows Documents:
```bash
cp reports/*.html /mnt/c/Users/<YourWindowsUser>/Documents/
```

## Notes
- Avoid working from `/mnt/c/...` within WSL due to I/O and file watching performance. Keep the project under `/home/...`.
- Encoding differences are handled by the scrapers; JSON and templates are UTF-8.
- No global PYTHONPATH changes are required; scripts add `src/` automatically. Tests rely on `PYTHONPATH=src` via `.env`.
