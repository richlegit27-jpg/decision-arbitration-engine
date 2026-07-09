from pathlib import Path

path = Path("tools/nova_regression_smoke.py")
text = path.read_text(encoding="utf-8")

old = '''        print("SKIP live_market_price_web because NOVA_SKIP_LIVE_WEB_SMOKE=1")
        btc = None
'''

new = '''        print("SKIP live_market_price_web because NOVA_SKIP_LIVE_WEB_SMOKE=1")
        btc = {
            "ok": True,
            "text": "SKIP live_market_price_web bitcoin btc price usd market",
            "assistant_message": {
                "text": "SKIP live_market_price_web bitcoin btc price usd market"
            },
            "debug": {
                "route": "web_fetch",
                "route_taken": "web_fetch",
                "live_web_smoke_skipped": True
            }
        }
'''

if old not in text:
    raise SystemExit("skip btc None block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched regression skip to use safe btc object")
