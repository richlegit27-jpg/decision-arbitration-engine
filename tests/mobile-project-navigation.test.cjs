const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

class FakeClassList {
  constructor(...initial) { this.values = new Set(initial); }
  contains(name) { return this.values.has(name); }
  add(name) { this.values.add(name); }
  toggle(name, force) {
    const shouldAdd = force === undefined ? !this.values.has(name) : Boolean(force);
    if (shouldAdd) this.values.add(name);
    else this.values.delete(name);
    return shouldAdd;
  }
}

function element(...classes) {
  return {
    classList: new FakeClassList(...classes),
    attributes: {},
    handlers: {},
    addEventListener(name, callback) { this.handlers[name] = callback; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name] ?? null; },
  };
}

test("Back to Chat closes mobile project views without issuing project mutations", () => {
  const ids = [
    "nova-mobile-projects-toggle", "nova-mobile-sessions-toggle",
    "nova-mobile-projects-close", "nova-mobile-project-back",
    "nova-mobile-project-retry", "nova-mobile-project-create-form",
    "nova-mobile-project-refresh", "nova-mobile-project-run",
    "nova-mobile-project-continue", "nova-mobile-project-pause",
    "nova-mobile-project-approve", "nova-mobile-project-reset", "nova-mobile-project-next-action",
    "nova-mobile-projects-panel", "nova-mobile-project-workspace",
  ];
  const elements = new Map(ids.map((id) => [id, element("hidden")]));
  elements.get("nova-mobile-projects-toggle").setAttribute("aria-expanded", "true");
  elements.get("nova-mobile-projects-panel").setAttribute("aria-hidden", "false");
  elements.get("nova-mobile-project-workspace").setAttribute("aria-hidden", "false");
  const requests = [];
  const context = {
    window: {},
    document: { getElementById: (id) => elements.get(id) || null },
    fetch: (...args) => { requests.push(args); throw new Error("Unexpected API request"); },
    URLSearchParams,
    Set,
    Map,
    encodeURIComponent,
    console,
  };

  const source = fs.readFileSync(path.join(__dirname, "../static/js/mobile/nova-mobile-projects.js"), "utf8");
  vm.runInNewContext(source, context, { filename: "nova-mobile-projects.js" });
  elements.get("nova-mobile-projects-panel").classList.toggle("hidden", false);
  elements.get("nova-mobile-project-workspace").classList.toggle("hidden", false);
  elements.get("nova-mobile-project-back").handlers.click();

  assert.equal(elements.get("nova-mobile-projects-panel").classList.contains("hidden"), true);
  assert.equal(elements.get("nova-mobile-project-workspace").classList.contains("hidden"), true);
  assert.equal(elements.get("nova-mobile-projects-panel").getAttribute("aria-hidden"), "true");
  assert.equal(elements.get("nova-mobile-project-workspace").getAttribute("aria-hidden"), "true");
  assert.equal(elements.get("nova-mobile-projects-toggle").getAttribute("aria-expanded"), "false");
  assert.deepEqual(requests, []);
});
