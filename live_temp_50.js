
(function () {
    "use strict";

    if (window.__NOVA_RIGHT_PANEL_MEMORY_ONLY_CLEANUP_20260622__) return;
    window.__NOVA_RIGHT_PANEL_MEMORY_ONLY_CLEANUP_20260622__ = true;

    function memoryOnlyCleanup() {
        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");
        const memory = document.querySelector(".memory-section");

        [
            "#novaMissionSummarySection",
            ".nova-mission-summary-section",
            "#novaRightPanelTabs",

        ].forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                el.hidden = true;
                el.style.display = "none";
                el.style.visibility = "hidden";
                el.style.opacity = "0";
                el.style.height = "0";
                el.style.minHeight = "0";
                el.style.maxHeight = "0";
                el.style.overflow = "hidden";
                el.style.padding = "0";
                el.style.margin = "0";
                el.style.border = "0";
            });
        });

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
            memory.style.order = "-9999";

            if (tools && tools.firstElementChild !== memory) {
                tools.insertBefore(memory, tools.firstElementChild);
            }
        }

        if (typeof window.NovaEnsureMemoryTypedInput === "function") {
            window.NovaEnsureMemoryTypedInput();
        }

    }

    window.NovaRightPanelMemoryOnlyCleanup = memoryOnlyCleanup;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", memoryOnlyCleanup);
    } else {
        memoryOnlyCleanup();
    }

    setTimeout(memoryOnlyCleanup, 250);
    setTimeout(memoryOnlyCleanup, 800);
    setTimeout(memoryOnlyCleanup, 1600);
    window.addEventListener("resize", memoryOnlyCleanup);
})();
