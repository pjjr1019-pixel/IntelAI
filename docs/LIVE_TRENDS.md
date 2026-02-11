# Live trends toggle

This document explains the `VS_ENABLE_LIVE_TRENDS` runtime toggle.

- Env var: `VS_ENABLE_LIVE_TRENDS`
  - When set to `0`/`false`, the API will not call external Google Trends and will return HTTP 503 for live-preview endpoints. Use this to prevent network calls during CI runs.
  - When set to `1`/`true`, the API may perform live Google Trends preview requests when needed by endpoints/tests.

Recommendations
- CI: set `VS_ENABLE_LIVE_TRENDS=false` to avoid external network dependencies. Use the on-demand `live-test-dispatch` GitHub Actions workflow when you need to run live connector tests.
- Local dev: to run live connector tests, set `RUN_LIVE_TESTS=1` and `VS_ENABLE_LIVE_TRENDS=1` before running `pytest`.

Example (PowerShell):

```powershell
$env:VS_ENABLE_LIVE_TRENDS='1'
$env:RUN_LIVE_TESTS='1'
$env:VS_DB_MODE='sqlite'
.\.venv\Scripts\python.exe -m pytest tests/test_trending_fallback.py -q
```
