from pathlib import Path

path = Path("tools/nova_regression_smoke.py")
text = path.read_text(encoding="utf-8")

if "NOVA_SKIP_LIVE_WEB_SMOKE" in text:
    print("live web skip already installed")
    raise SystemExit(0)

if "import os" not in text.splitlines()[:10]:
    text = text.replace("import json\n", "import json\nimport os\n", 1)

old = '''    btc = post_chat(
        "bitcoin price right now",
        f"regression_btc_web_{stamp}",
    )
'''

new = '''    if os.environ.get("NOVA_SKIP_LIVE_WEB_SMOKE") == "1":
        print("SKIP live_market_price_web because NOVA_SKIP_LIVE_WEB_SMOKE=1")
        btc = None
    else:
        btc = post_chat(
            "bitcoin price right now",
            f"regression_btc_web_{stamp}",
        )
'''

if old not in text:
    raise SystemExit("btc live web block not found")

text = text.replace(old, new, 1)

old_assert = '''    assert_true(
        "live_market_price_web",
        _contains_any(
            _answer_text(btc),
            ["bitcoin", "btc", "$", "price", "usd", "market"],
        ),
        _answer_text(btc),
    )
'''

new_assert = '''    if btc is not None:
        assert_true(
            "live_market_price_web",
            _contains_any(
                _answer_text(btc),
                ["bitcoin", "btc", "$", "price", "usd", "market"],
            ),
            _answer_text(btc),
        )
'''

if old_assert not in text:
    raise SystemExit("live web assert block not found")

text = text.replace(old_assert, new_assert, 1)

path.write_text(text, encoding="utf-8")
print("patched optional live web regression smoke skip")
