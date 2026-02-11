# Running tests

Quick commands to run the project's test suite locally and how to enable the optional live Google Trends test.

Prerequisites
- Activate the project's virtualenv: `.\.venv\Scripts\Activate` (Windows PowerShell)
- Install dev dependencies (if you haven't): `python -m pip install -r requirements.txt` or `python -m pip install pytest`

Run all tests (uses SQLite dev mode):

```powershell
$env:VS_DB_MODE='sqlite'; .\.venv\Scripts\python.exe -m pytest -q
```

Run a single test file:

```powershell
$env:VS_DB_MODE='sqlite'; .\.venv\Scripts\python.exe -m pytest tests/test_user_preferences.py -q
```

Run only the optional live Google Trends test (this makes network calls and is skipped by default):

```powershell
$env:RUN_LIVE_TESTS='1'; $env:VS_DB_MODE='sqlite'; .\.venv\Scripts\python.exe -m pytest tests/test_trending_fallback.py -q
```

Notes
- The watchlist API tests use a temporary file; to run the server locally you can set `VS_WATCHLIST_PATH` to point to a test file to avoid modifying the repo `data/watchlist.json`.
- CI: a GitHub Actions workflow is present at `.github/workflows/ci.yml` and runs `pytest` on push/PR against `main`/`master`.
