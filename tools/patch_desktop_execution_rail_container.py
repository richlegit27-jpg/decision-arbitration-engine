from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_RAIL_CONTAINER_RESTORE_SAFE_20260702"

block = r'''

<!-- NOVA_DESKTOP_EXECUTION_RAIL_CONTAINER_RESTORE_SAFE_20260702
     Restore desktop /app execution rail container expected by nova-composer-bundle.js.
     Safe placement before </body>. No mobile changes.
-->
<style>
    #nova-desktop-execution-rail {
        position: fixed;
        right: 18px;
        bottom: 92px;
        width: min(420px, calc(100vw - 36px));
        z-index: 9998;
        border: 1px solid rgba(168,85,247,0.24);
        border-radius: 18px;
        background: rgba(15,23,42,0.96);
        color: #f8fafc;
        box-shadow: 0 20px 52px rgba(0,0,0,0.42);
        overflow: hidden;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    #nova-desktop-execution-rail.is-collapsed .nova-desktop-exec-body {
        display: none !important;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 11px 13px;
        background: linear-gradient(135deg, rgba(124,58,237,0.42), rgba(37,99,235,0.26));
        border-bottom: 1px solid rgba(255,255,255,0.12);
    }

    #nova-desktop-execution-rail .nova-desktop-exec-title {
        font-size: 14px;
        font-weight: 900;
        letter-spacing: 0.02em;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-toggle {
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px;
        padding: 6px 10px;
        background: rgba(255,255,255,0.10);
        color: #fff;
        font-weight: 800;
        cursor: pointer;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-body {
        padding: 13px;
    }

    #nova-desktop-execution-rail [data-execution-panel] {
        min-height: 62px;
        padding: 10px;
        border-radius: 12px;
        background: rgba(255,255,255,0.06);
        color: #dbeafe;
        font-size: 13px;
        line-height: 1.35;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-actions {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 10px;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-actions button {
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 12px;
        padding: 9px 8px;
        background: rgba(255,255,255,0.08);
        color: #fff;
        font-weight: 800;
        cursor: pointer;
    }

    #nova-desktop-execution-rail .nova-desktop-exec-actions button:hover {
        background: rgba(139,92,246,0.28);
    }
</style>

<section
    id="nova-desktop-execution-rail"
    class="execution-panel desktop-execution execution-section"
    data-rail-panel="execution"
    aria-label="Execution Panel"
>
    <div class="nova-desktop-exec-head">
        <div class="nova-desktop-exec-title">Execution</div>
        <button id="nova-desktop-exec-toggle" class="nova-desktop-exec-toggle" type="button">Hide</button>
    </div>

    <div class="nova-desktop-exec-body">
        <div data-execution-panel>
            <div class="nova-panel-muted">
                No steps yet. Start with <strong>auto-plan &lt;goal&gt;</strong>, then use Run Step.
            </div>
        </div>

        <div class="nova-desktop-exec-actions">
            <button type="button" data-exec-fill="run step">Run Step</button>
            <button type="button" data-exec-fill="run all">Run All</button>
            <button type="button" data-exec-fill="stop">Stop</button>
        </div>
    </div>
</section>

<script>
(function () {
    const MARK = "NOVA_DESKTOP_EXECUTION_RAIL_CONTAINER_RESTORE_SAFE_20260702";
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
        const rail = document.getElementById("nova-desktop-execution-rail");
        const toggle = document.getElementById("nova-desktop-exec-toggle");

        if (toggle && rail) {
            toggle.addEventListener("click", () => {
                rail.classList.toggle("is-collapsed");
                toggle.textContent = rail.classList.contains("is-collapsed") ? "Show" : "Hide";
            });
        }

        document.querySelectorAll("[data-exec-fill]").forEach(button => {
            button.addEventListener("click", () => {
                setInput(button.getAttribute("data-exec-fill") || "");
            });
        });

        console.log("[NOVA_DESKTOP_EXECUTION_RAIL_CONTAINER_RESTORE_SAFE_20260702] active");
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
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")
    text = text[:idx] + block + "\n" + text[idx:]
    TEMPLATE.write_text(text, encoding="utf-8")
    print("patched", TEMPLATE)
