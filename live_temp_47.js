
(function () {
    "use strict";

    if (window.__NOVA_MEMORY_TOP_PRIORITY_FINAL_20260622__) return;
    window.__NOVA_MEMORY_TOP_PRIORITY_FINAL_20260622__ = true;

    function keepMemoryAtTop() {
        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");
        const memory = document.querySelector(".memory-section");

        if (!tools || !memory) return;

        memory.hidden = false;
        memory.removeAttribute("hidden");
        memory.style.display = "block";
        memory.style.visibility = "visible";
        memory.style.opacity = "1";
        memory.style.order = "-999";

        if (tools.firstElementChild && tools.firstElementChild !== memory) {
            tools.insertBefore(memory, tools.firstElementChild);
        }

        tools.style.overflowY = "auto";
        tools.style.overflowX = "hidden";
        tools.style.minHeight = "0";
    }

    function openMemoryTop() {
        keepMemoryAtTop();

        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");
        const memory = document.querySelector(".memory-section");

        if (tools && memory && typeof tools.scrollTo === "function") {
            tools.scrollTo({ top: 0, behavior: "smooth" });
        }

        if (typeof window.loadDesktopMemory === "function") {
            window.loadDesktopMemory();
        } else if (typeof window.NovaLoadDesktopMemory === "function") {
            window.NovaLoadDesktopMemory();
        }
    }

    function wire() {
        keepMemoryAtTop();

        const button = document.getElementById("openMemoryBtn");
        if (!button || button.dataset.novaMemoryTopPriorityWired === "true") return;

        button.dataset.novaMemoryTopPriorityWired = "true";

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }

            openMemoryTop();
        }, true);
    }

    window.NovaKeepMemoryAtTop = keepMemoryAtTop;
    window.NovaOpenMemoryTop = openMemoryTop;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", wire);
    } else {
        wire();
    }

    setTimeout(wire, 200);
    setTimeout(wire, 700);
    setTimeout(wire, 1400);
    window.addEventListener("resize", keepMemoryAtTop);
})();
