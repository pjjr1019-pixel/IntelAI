PR Title: Add live-trends toggle docs and prepare for CI

Summary:
- Add `docs/LIVE_TRENDS.md` documenting `VS_ENABLE_LIVE_TRENDS` and recommended CI settings.
- Ensure CI sets `VS_ENABLE_LIVE_TRENDS=false` to avoid flaky external network calls.

Changes:
- Added `docs/LIVE_TRENDS.md` (details of the config toggle, local test commands, and CI guidance)
- Minor test updates and headless Playwright script to mock `/api/trending/history/*` for UI E2E.

Why:
- Prevent flaky CI failures and accidental external calls during automated runs.
- Provide local guidance for running live connector tests when desired.

Testing performed:
- Local `pytest` runs (unit + connector mocks) passed.
- Headless `tools/headless_check.py` verified `GoogleTrendsPanel` UI rendering using a mocked `HistoricalTrendResponse`.

CI Notes & Recommendations:
- Set env `VS_ENABLE_LIVE_TRENDS=false` in CI (default) to prevent external calls.
- Optionally add a workflow dispatch (manual) to run live connector tests with `VS_ENABLE_LIVE_TRENDS=true` and a secret API key configured.

Steps to push locally (PowerShell):
```powershell
# After installing Git
cd "C:\Users\Pgiov\OneDrive\Documents\Custom programs\Intel-AI"
git checkout -b fix/trending-live-fallback-docs
git add -A
git commit -m "Add live-trends toggle docs and prepare for CI"
git push -u origin fix/trending-live-fallback-docs
```

Notes:
- If you prefer to upload `docs/LIVE_TRENDS.md` via GitHub web UI, use `changes.zip` (repo root) or paste the file contents from this PR description.
- Once pushed, open a PR with the title above and paste the summary and CI notes.
