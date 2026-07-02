from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_RAIL_DOCK_RIGHT_PANEL_20260702"

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

style = r'''

<style id="nova-desktop-execution-rail-dock-right-panel-20260702">
/* NOVA_DESKTOP_EXECUTION_RAIL_DOCK_RIGHT_PANEL_20260702
   Dock restored execution panel into desktop right rail instead of floating over the app.
*/
#nova-desktop-execution-rail.nova-exec-docked-right {
    position: relative !important;
    right: auto !important;
    bottom: auto !important;
    width: 100% !important;
    max-width: none !important;
    min-height: 178px !important;
    margin: 10px 0 !important;
    z-index: auto !important;
    box-shadow: none !important;
}

#nova-desktop-execution-rail.nova-exec-docked-right .nova-desktop-exec-head {
    border-radius: 14px 14px 0 0 !important;
}

#nova-desktop-execution-dock-host {
    width: 100% !important;
}
</style>

<script>
(function () {
    const MARK = "NOVA_DESKTOP_EXECUTION_RAIL_DOCK_RIGHT_PANEL_20260702";
    if (window[MARK]) return;
    window[MARK] = true;

    function visibleSize(el) {
        if (!el) return 0;
        const r = el.getBoundingClientRect();
        return Math.max(r.width, 0) * Math.max(r.height, 0);
    }

    function findRightDockHost() {
        const selectors = [
            "#nova-right-rail",
            "#rightRail",
            "#desktopRightRail",
            "#nova-desktop-right-rail",
            "#nova-side-panel",
            "#desktop-side-panel",
            ".right-panel",
            ".desktop-right-panel",
            ".nova-right-panel",
            ".nova-side-panel",
            ".desktop-sidebar",
            ".right-sidebar",
            "aside"
        ];

        const candidates = [];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => candidates.push(el));
        });

        document.querySelectorAll("*").forEach(el => {
            const s = String(el.id + " " + el.className + " " + (el.getAttribute("aria-label") || "")).toLowerCase();
            if (
                s.includes("right") ||
                s.includes("rail") ||
                s.includes("side") ||
                s.includes("panel")
            ) {
                candidates.push(el);
            }
        });

        const unique = [...new Set(candidates)]
            .filter(el => el && el.id !== "nova-desktop-execution-rail")
            .filter(el => {
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                return (
                    r.width >= 180 &&
                    r.height >= 120 &&
                    r.left > window.innerWidth * 0.45 &&
                    cs.display !== "none" &&
                    cs.visibility !== "hidden"
                );
            })
            .sort((a, b) => {
                const ar = a.getBoundingClientRect();
                const br = b.getBoundingClientRect();

                // Prefer visible right-side panels that are not the whole app/body.
                const aScore = ar.left + Math.min(ar.width, 500) + Math.min(ar.height, 900) - visibleSize(a) / 10000;
                const bScore = br.left + Math.min(br.width, 500) + Math.min(br.height, 900) - visibleSize(b) / 10000;
                return bScore - aScore;
            });

        return unique[0] || null;
    }

    function dock() {
        const rail = document.getElementById("nova-desktop-execution-rail");
        if (!rail) return;

        const host = findRightDockHost();

        if (!host) {
            console.warn("[NOVA_DESKTOP_EXECUTION_RAIL_DOCK_RIGHT_PANEL_20260702] no right dock host found; keeping fallback");
            return;
        }

        let dockHost = document.getElementById("nova-desktop-execution-dock-host");
        if (!dockHost) {
            dockHost = document.createElement("div");
            dockHost.id = "nova-desktop-execution-dock-host";
            host.appendChild(dockHost);
        }

        dockHost.appendChild(rail);
        rail.classList.add("nova-exec-docked-right");

        console.log("[NOVA_DESKTOP_EXECUTION_RAIL_DOCK_RIGHT_PANEL_20260702] docked", {
            hostId: host.id,
            hostClass: String(host.className),
            hostTag: host.tagName
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", dock, { once: true });
    } else {
        dock();
    }

    setTimeout(dock, 500);
})();
</script>
'''

if MARKER not in text:
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")
    text = text[:idx] + style + "\n" + text[idx:]

TEMPLATE.write_text(text, encoding="utf-8")
print("patched", TEMPLATE)
