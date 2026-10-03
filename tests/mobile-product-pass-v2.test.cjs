const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const activeMobileTemplate = () => read("templates/mobile.html").replace(/<!--[\s\S]*?-->/g, "");

test("mobile Billing navigates directly to the existing Billing page", () => {
  const html = activeMobileTemplate();
  assert.match(html, /<a\b[^>]*id="nova-mobile-menu-billing"[^>]*href="\/billing"/);
  assert.doesNotMatch(html, /billing\.onclick\s*=|nova-mobile-billing-panel/);
});

test("mobile menu removes the redundant Open Work destination", () => {
  const html = activeMobileTemplate();
  assert.doesNotMatch(html, /Open Current Work|Open Work|data-mobile-tool="execution"/i);
});

test("mobile Settings presents account-backed values and no dead feature promises", () => {
  const html = activeMobileTemplate();
  assert.doesNotMatch(html, /Theme:\s*Coming soon|Voice settings:\s*Coming soon/i);
  assert.match(html, /Available credits/);
  assert.match(html, /Monthly credits/);
  assert.match(html, /\/billing/);
});

test("mobile project overview consumes saved brain fields and progressively discloses details", () => {
  const html = activeMobileTemplate();
  const js = read("static/js/mobile/nova-mobile-projects.js");
  for (const id of ["nova-mobile-project-goal-summary", "nova-mobile-project-progress-meter", "nova-mobile-project-next-title", "nova-mobile-project-current-list", "nova-mobile-project-done-list", "nova-mobile-project-coming-list"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /<details class="nova-mobile-project-details">/);
  for (const field of ["brain?.goal", "brain?.next_move", "brain?.current_work", "brain?.blocked_work", "brain?.completed_work", "brain?.remaining_work", "completion_percentage", "move?.owner"]) {
    assert.ok(js.includes(field), `expected project overview to use ${field}`);
  }
});

test("mobile attachment flow previews multiple files, reports state, and removes by selected item", () => {
  const js = read("static/js/mobile/nova-mobile-upload-change-authority-v1.js");
  assert.match(js, /input\.multiple\s*=\s*true/);
  assert.match(js, /pending_upload:\s*true/);
  assert.match(js, /current\.upload_error\s*=\s*true/);
  assert.match(js, /function removeAttachment\(clientId\)/);
  assert.match(js, /findIndex\(function \(item\) \{ return \(item\.client_id \|\| item\.id\) === clientId; \}\)/);
  assert.match(js, /window\.addEventListener\(eventName, clearPendingAttachments\)/);
  assert.match(js, /nova-mobile-send-complete/);
  assert.match(js, /nova-mobile-upload-preview-name/);
  assert.match(js, /nova-mobile-upload-preview-info/);
  assert.match(js, /nova-mobile-upload-preview-state/);
  assert.match(js, /Upload stopped before the page was closed/);
  assert.match(js, /Your session expired/);
  assert.match(js, /This file is too large to upload/);
  assert.match(js, /This file type is not supported/);
});

test("mobile execution copy distinguishes statuses and uses real task, target, reason, result, and next fields", () => {
  const js = read("static/js/mobile/nova-mobile-projects.js");
  for (const status of ["Running", "Completed", "Waiting for you", "Waiting for approval", "Blocked", "Failed", "Paused", "Not started"]) {
    assert.ok(js.includes(status), `expected execution state ${status}`);
  }
  for (const field of ["current_step", "target_file", "waiting_reason", "last_result", "last_completed_task", "brain?.next_move"]) {
    assert.ok(js.includes(field), `expected execution narrative to use ${field}`);
  }
});

test("active mobile HTML has unique IDs and script URLs", () => {
  const html = activeMobileTemplate();
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(ids.length, new Set(ids).size, "duplicate active element IDs found");
  const urls = [...html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(urls.length, new Set(urls).size, "duplicate active script URLs found");
});

test("shared mobile Markdown renderer outputs safe links, scrollable tables, code, and approval cards", () => {
  const context = { URL, setTimeout, document: { addEventListener() {} } };
  context.window = { location: { origin: "https://nova.test" }, setTimeout };
  vm.runInNewContext(read("static/js/answer-payload.js"), context);
  const html = context.window.NovaAnswerPayload.renderAnswerPayload(
    "> Note\n[site](https://example.com) [bad](javascript:alert(1))\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n```python\nprint(42)\n```"
  );
  assert.match(html, /<blockquote>/);
  assert.match(html, /href="https:\/\/example\.com"/);
  assert.doesNotMatch(html, /javascript:/);
  assert.match(html, /answer-table-wrap/);
  assert.match(html, /answer-token-keyword/);
  assert.match(html, /data-copy-code/);
  assert.match(context.window.NovaAnswerPayload.renderToolApprovalCard({ id: "m1", status: "tool_approval_required", toolApproval: { tool: "file.write", risk: "low" } }), /data-action="tool-approve"/);
});

test("shared mobile message stylesheet contains narrow-screen scroll and touch-target rules", () => {
  const css = read("static/css/nova-message-presentation.css") + read("static/css/nova-mobile-quality.css");
  assert.match(css, /@media\s*\(max-width:\s*360px\)/);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /\.answer-code pre[\s\S]*?overflow:\s*auto/);
  assert.match(css, /\.answer-table-wrap[\s\S]*?overflow-x:\s*auto/);
  assert.match(css, /overflow-x:\s*hidden/);
});
