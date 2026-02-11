# Development Notes

Quick reference for common developer workflows.

Run the API (dev, SQLite):

```powershell
$env:VS_DB_MODE='sqlite'
.\.venv\Scripts\python.exe -m uvicorn vanguard_signal.api.app:app --reload --port 8000
```

Run tests (all unit tests):

```powershell
$env:VS_DB_MODE='sqlite'
.\.venv\Scripts\python.exe -m pytest -q
```

Run the optional live Google Trends test (network call):

```powershell
$env:RUN_LIVE_TESTS='1'
$env:VS_DB_MODE='sqlite'
.\.venv\Scripts\python.exe -m pytest tests/test_trending_fallback.py -q
```

Run a single test file:

```powershell
$env:VS_DB_MODE='sqlite'
.\.venv\Scripts\python.exe -m pytest tests/test_watchlist_api.py -q
```

CI
- GitHub Actions workflow `.github/workflows/ci.yml` runs `pytest` on push/PR.
- Use `.github/workflows/live-test-dispatch.yml` (workflow_dispatch) to run live connector tests on-demand.

Creating a PR
- Commit your changes and push to a branch, then open a PR on GitHub. CI will run automatically.
