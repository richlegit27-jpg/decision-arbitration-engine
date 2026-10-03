import re
from html.parser import HTMLParser
from pathlib import Path

from flask import Flask, render_template


ROOT = Path(__file__).resolve().parents[1]


class ElementIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, _tag, attrs):
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)


def test_super_ai_template_renders_and_contains_every_script_control():
    app = Flask(
        "nova_super_ai_template_test",
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    with app.test_request_context("/super-ai"):
        html = render_template("super_ai.html")

    parser = ElementIds()
    parser.feed(html)
    script = (ROOT / "static" / "js" / "nova-super-ai.js").read_text(
        encoding="utf-8"
    )
    referenced_ids = set(
        re.findall(r'\$\("([A-Za-z][\w-]*)"\)', script)
    )

    assert "nova-super-ai.css" in html
    assert "nova-super-ai.js" in html
    assert referenced_ids <= parser.ids, sorted(referenced_ids - parser.ids)
