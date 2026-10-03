import json
import shutil
import subprocess
from pathlib import Path

import pytest

from nova_backend.services.chat.handle import normalize_created_project_title
from nova_backend.services.project_brain_context_builder import build_first_saved_task_answer


ROOT = Path(__file__).resolve().parents[2]


def test_created_project_title_removes_boilerplate_and_punctuation():
    assert normalize_created_project_title(
        "A project to build a simple calculator website with HTML, CSS, and JavaScript."
    ) == "Simple calculator website with HTML, CSS, and JavaScript"
    assert normalize_created_project_title("A tiny tool...") == "Tiny tool"


def test_first_saved_task_answer_uses_active_persisted_project():
    assert build_first_saved_task_answer(
        {"tasks": [{"title": "Analyze project goal and requirements"}]}
    ) == "The first saved task is Analyze project goal and requirements."


def test_app_loads_markdown_renderer_before_chat_message_renderer():
    template = (ROOT / "templates" / "app.html").read_text(encoding="utf-8-sig")
    markdown_index = template.index("/static/js/answer-payload.js")
    messages_index = template.index("/static/js/chat-messages.js")
    assert markdown_index < messages_index


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is unavailable")
def test_markdown_renderer_keeps_lists_nested_and_blocks_vertical():
    renderer = ROOT / "static" / "js" / "answer-payload.js"
    script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(renderer))}, 'utf8');
const context = {{window: {{}}, document: {{addEventListener() {{}}}}, navigator: {{clipboard: {{writeText() {{}}}}}}}};
vm.runInNewContext(source, context);
const html = context.window.NovaAnswerPayload.renderAnswerPayload(
  '# Steps\\n\\n- first\\n- second\\n  - nested\\n\\n1. one\\n2. two\\n\\n```js\\nconst x = 1;\\n```'
);
if (!html.includes('<h1>Steps</h1>')) throw new Error('heading was not rendered');
if (!html.includes('<ul><li>first</li><li>second<ul><li>nested</li></ul></li></ul>')) throw new Error('unordered/nested list structure is incorrect');
if (!html.includes('<ol><li>one</li><li>two</li></ol>')) throw new Error('ordered list structure is incorrect');
if (!html.includes('<pre><code>const x = 1;</code></pre>')) throw new Error('code fence was not rendered');
"""
    subprocess.run(["node", "-e", script], check=True, cwd=ROOT)
