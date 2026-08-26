
(function () {
    "use strict";

    if (window.__NOVA_REAL_DESKTOP_RIGHT_PANEL_SCROLL_FIX_20260622__) return;
    window.__NOVA_REAL_DESKTOP_RIGHT_PANEL_SCROLL_FIX_20260622__ = true;

    function openMemoryFixed() {
        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");
        const memory = document.querySelector(".memory-section");

        if (tools) {
            tools.style.display = "flex";
            tools.style.flexDirection = "column";
        }

        if (memory) {
            memory.hidden = false;
            memory.removeAttribute("hidden");
            memory.style.display = "block";
            memory.style.visibility = "visible";
            memory.style.opacity = "1";

            if (tools && typeof tools.scrollTo === "function") {
                tools.scrollTo({
                    top: Math.max(0, memory.offsetTop - 16),
                    behavior: "smooth"
                });
            }
        }

// NOVA_MEMORY_AUTOLOAD_DISABLED
    }

    function wire() {
        const button = document.getElementById("openMemoryBtn");
        if (!button || button.dataset.novaRealPanelScrollFixed === "true") return;

        button.dataset.novaRealPanelScrollFixed = "true";

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }

            openMemoryFixed();
        }, true);
    }

    window.NovaOpenMemoryFixed = openMemoryFixed;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", wire);
    } else {
        wire();
    }

    setTimeout(wire, 300);
    setTimeout(wire, 1000);
})();
