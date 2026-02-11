import sys, time, json
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print('PLAYWRIGHT_MISSING', e)
    sys.exit(2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = 'http://127.0.0.1:3000/dashboard'

    # mock payload to return for trending-history requests
    sample_payload = {
        "keyword": "test-keyword",
        "geo": "US",
        "data_points": [
            {"timestamp": "2026-02-11T00:00:00", "value": 10.0, "velocity": 0.0},
            {"timestamp": "2026-02-11T01:00:00", "value": 40.0, "velocity": 30.0},
            {"timestamp": "2026-02-11T02:00:00", "value": 20.0, "velocity": -20.0}
        ],
        "total_points": 3,
        "first_seen": "2026-02-11T00:00:00",
        "last_seen": "2026-02-11T02:00:00",
        "generated_at": datetime.utcnow().isoformat() + 'Z'
    }

    def mock_trending(route, request):
        route.fulfill(status=200, body=json.dumps(sample_payload), headers={"Content-Type": "application/json"})

    # intercept any client requests to the trending-history API and return sample data
    page.route("**/api/trending/history/*", mock_trending)
    print('VISITING', url)
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
    except Exception as e:
        print('GOTO_FAILED', e)
    # allow extra time for client-side hydration and network calls
    page.wait_for_timeout(3000)

    # capture requests seen during navigation/hydration
    seen = []
    def _on_request(req):
        seen.append(req.url)
    page.on('request', _on_request)

    # wait a bit more for any client-side requests
    page.wait_for_timeout(3000)

    content = page.content()
    found = ('GoogleTrendsPanel' in content) or ('google-trends' in content) or ('data-testid="google-trends-panel"' in content)
    print('LENGTH', len(content))
    print('FOUND_PANEL_IN_HTML', found)

    # evaluate the live DOM for text markers
    try:
        eval_res = page.evaluate("""
            () => {
                const sel = document.querySelector('[data-testid="google-trends-panel"]') || document.querySelector('#google-trends-panel');
                if (sel) return {found: true, text: (sel.textContent||'').slice(0,300)};
                const byText = Array.from(document.querySelectorAll('div')).filter(d => /google trends|trends/i.test(d.textContent || ''));
                if (byText.length) return {found: true, text: (byText[0].textContent||'').slice(0,300)};
                return {found: false, text: ''};
            }
        """)
        print('EVAL_FOUND', eval_res.get('found'))
        print('EVAL_TEXT_SNIPPET', eval_res.get('text'))
    except Exception as e:
        print('EVAL_FAILED', e)

    # list any trending-history related requests
    trending_reqs = [u for u in seen if '/api/trending/history' in u]
    print('REQUESTS_FOUND', trending_reqs)
    print('SNIPPET')
    print(content[:2000])
    # try a direct fetch from the page context to check CORS/server reachability
    try:
        fetch_res = page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/api/trending/history/test-keyword');
                    const t = await r.text();
                    return {status: r.status, text: t.slice(0,1000)};
                } catch (e) {
                    return {error: String(e)};
                }
            }
        """)
        print('FETCH_IN_BROWSER', fetch_res)
    except Exception as e:
        print('FETCH_FAILED', e)
    browser.close()
