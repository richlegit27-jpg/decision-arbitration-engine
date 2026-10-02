from collections import Counter
import ast
from html.parser import HTMLParser
from pathlib import Path

from flask import Flask, render_template


ROOT = Path(__file__).resolve().parents[1]


class MobileNavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}
        self.ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
            self.parents[element_id] = tuple(self.stack)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, element_id or "", values.get("class", "")))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def test_mobile_projects_button_is_a_sibling_of_sessions_outside_tools_menu():
    html = (ROOT / "templates" / "mobile.html").read_text(encoding="utf-8")
    parser = MobileNavigationParser()
    parser.feed(html)

    projects_parents = parser.parents["nova-mobile-projects-toggle"]
    sessions_parents = parser.parents["nova-mobile-sessions-toggle"]
    assert projects_parents == sessions_parents
    assert any(parent[2] == "mobile-header-actions" for parent in projects_parents)
    assert not any(parent[1] == "nova-mobile-tools-panel" for parent in projects_parents)
    assert Counter(parser.ids)["nova-mobile-projects-toggle"] == 1


def test_mobile_project_controls_match_real_project_api_and_are_safe_to_render():
    template = (ROOT / "templates" / "mobile.html").read_text(encoding="utf-8")
    script = (ROOT / "static" / "js" / "mobile" / "nova-mobile-projects.js").read_text(encoding="utf-8")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8-sig")

    assert 'api("/api/projects")' in script
    assert 'api("/api/projects/new"' in script
    assert '`/api/projects/${encodeURIComponent(state.projectId)}/execution/control`' in script
    assert '`/api/projects/${encodeURIComponent(state.projectId)}/files`' in script
    assert '`/api/projects/${encodeURIComponent(state.projectId)}/phases`' in script
    assert '"/api/projects/new"' in app_source
    assert '"/api/projects/<project_id>/execution/control"' in app_source
    assert '"/api/projects/<project_id>/files"' in app_source
    assert "innerHTML" not in script
    assert 'id="nova-mobile-project-run"' in template
    assert 'id="nova-mobile-project-continue"' in template
    assert 'id="nova-mobile-project-approve"' in template
    assert 'id="nova-mobile-project-phase-list"' in template


def test_public_homepage_renders_outcome_message_and_real_destinations():
    app = Flask("nova_home_test", template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
    with app.test_request_context("/"):
        html = render_template("nova_landing.html")

    assert "Bring the goal." in html
    assert "Start a project" in html
    for path in ("/register", "/login", "/features", "/about", "/billing", "/faq", "/roadmap", "/contact", "/privacy", "/terms"):
        assert f'href="{path}"' in html


def test_roadmap_footer_destination_has_a_real_route():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8-sig"))
    route_found = any(
        isinstance(node, ast.FunctionDef)
        and node.name == "nova_roadmap_page"
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "get"
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and decorator.args[0].value == "/roadmap"
            for decorator in node.decorator_list
        )
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "render_template"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "nova_roadmap.html"
            for call in ast.walk(node)
        )
        for node in tree.body
    )
    assert route_found

