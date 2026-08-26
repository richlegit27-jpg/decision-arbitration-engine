
(function () {
    "use strict";

    if (window.__NOVA_TOOLS_PANEL_MEMORY_ONLY_STABLE_20260622__) return;
    window.__NOVA_TOOLS_PANEL_MEMORY_ONLY_STABLE_20260622__ = true;

    let cleanupTimer = null;
    let didInitialMemoryBoot = false;

    function enforceMemoryOnlyStable() {
        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");
        const memory = document.querySelector(".memory-section");

        if (!tools || !memory) return;

        Array.from(tools.children).forEach(function (child) {
    if (
        child === memory ||
        child.classList.contains("execution-section")
    ) {
        child.hidden = false;
        child.removeAttribute("hidden");
        child.style.display = "block";
        child.style.visibility = "visible";
        child.style.opacity = "1";
        child.style.order = "";

        return;
    }

    child.hidden = false;
    child.removeAttribute("hidden");
});


        tools.style.display = "flex";
        tools.style.flexDirection = "column";
        tools.style.overflowY = "auto";
        tools.style.overflowX = "hidden";

        if (!didInitialMemoryBoot && typeof window.NovaMemoryV2Boot === "function") {
            didInitialMemoryBoot = true;
            window.NovaMemoryV2Boot();
        }
    }

    function scheduleCleanup() {
        clearTimeout(cleanupTimer);
        cleanupTimer = setTimeout(enforceMemoryOnlyStable, 80);
    }

    window.NovaEnforceMemoryOnlyRightPanel = enforceMemoryOnlyStable;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", enforceMemoryOnlyStable);
    } else {
        enforceMemoryOnlyStable();
    }



    document.addEventListener("click", function (event) {
        const tools = document.querySelector(".panel.tools") || document.querySelector(".tools");

        if (tools && tools.contains(event.target)) {
            scheduleCleanup();
        }
    }, true);

    window.addEventListener("resize", scheduleCleanup);

    setTimeout(enforceMemoryOnlyStable, 300);
    setTimeout(enforceMemoryOnlyStable, 1000);
})();
