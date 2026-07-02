from pathlib import Path
import re

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702"

block = r'''
<!-- NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702 -->
<section id="nova-desktop-execution-native" class="panel-section nova-desktop-execution-native" aria-label="Execution Panel">
    <div class="panel-section-title">Execution</div>

    <div data-execution-panel>
        <div class="nova-panel-muted">
            No steps yet. Start with <strong>auto-plan &lt;goal&gt;</strong>, then use Run Step.
        </div>
    </div>

    <div class="nova-desktop-execution-native-actions">
        <button type="button" data-exec-fill="run step">Run Step</button>
        <button type="button" data-exec-fill="run all">Run All</button>
        <button type="button" data-exec-fill="stop">Stop</button>
    </div>
</section>
'''

style_and_script = r'''
<style>
/* NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702 */
#nova-desktop-execution-native {
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
    margin: 10px 0 12px 0 !important;
    padding: 12px !important;
    border: 1px solid rgba(168,85,247,0.32) !important;
    border-radius: 16px !important;
    background: rgba(15,23,42,0.78) !important;
    color: #f8fafc !important;
}

#nova-desktop-execution-native .panel-section-title {
    margin-bottom: 10px !important;
    font-weight: 900 !important;
    letter-spacing: 0.02em !important;
    color: #facc15 !important;
}

#nova-desktop-execution-native [data-execution-panel] {
    display: block !important;
    min-height: 62px !important;
    padding: 10px !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.06) !important;
    color: #dbeafe !important;
    font-size: 13px !important;
    line-height: 1.35 !important;
}

#nova-desktop-execution-native .nova-desktop-execution-native-actions {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 8px !important;
    margin-top: 10px !important;
}

#nova-desktop-execution-native button {
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 12px !important;
    padding: 8px 6px !important;
    background: rgba(168,85,247,0.16) !important;
    color: #fff !important;
    font-weight: 800 !important;
    cursor: pointer !important;
}
</style>

<script>
(function () {
    const MARK = "NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702";
    if (window[MARK]) return;
    window[MARK] = true;

    function findInput() {
        return document.querySelector("textarea") ||
               document.querySelector("input[type='text']") ||
               document.querySelector("[contenteditable='true']");
    }

    function setInput(value) {
        const input = findInput();
        if (!input) return;

        if (input.isContentEditable) {
            input.textContent = value;
            input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
        } else {
            input.value = value;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }

        input.focus();
    }

    function start() {
        document.querySelectorAll("#nova-desktop-execution-native [data-exec-fill]").forEach(button => {
            button.addEventListener("click", () => {
                setInput(button.getAttribute("data-exec-fill") || "");
            });
        });

        console.log("[NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702] active");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
</script>
'''

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

if MARKER in text:
    print("already patched", TEMPLATE)
else:
    patterns = [
        r'(<aside\b[^>]*class=["\'][^"\']*\bpanel\b[^"\']*\btools\b[^"\']*["\'][^>]*>)',
        r'(<aside\b[^>]*class=["\'][^"\']*\btools\b[^"\']*\bpanel\b[^"\']*["\'][^>]*>)',
    ]

    match = None
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            break

    if not match:
        raise SystemExit("could not find right tools aside; not patching")

    text = text[:match.end()] + "\n" + block + "\n" + text[match.end():]

    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching styles/scripts")

    text = text[:idx] + style_and_script + "\n" + text[idx:]
    TEMPLATE.write_text(text, encoding="utf-8")
    print("patched", TEMPLATE)
