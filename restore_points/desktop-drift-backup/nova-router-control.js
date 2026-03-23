(() => {
  "use strict";

  if (window.__novaRouterControlLoaded) return;
  window.__novaRouterControlLoaded = true;

  function byId(id) {
    return document.getElementById(id);
  }

  function openPanel(panelId) {
    const panel = byId(panelId);
    if (!panel) return;
    panel.classList.remove("hidden");
    panel.setAttribute("aria-hidden", "false");
  }

  function closePanel(panelId) {
    const panel = byId(panelId);
    if (!panel) return;
    panel.classList.add("hidden");
    panel.setAttribute("aria-hidden", "true");
  }

  function wire() {
    byId("routerDebugBtn")?.addEventListener("click", () => openPanel("routerDebugPanel"));
    byId("routerToolsBtn")?.addEventListener("click", () => openPanel("routerToolsPanel"));
    byId("closeRouterDebugBtn")?.addEventListener("click", () => closePanel("routerDebugPanel"));
    byId("closeRouterToolsBtn")?.addEventListener("click", () => closePanel("routerToolsPanel"));

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closePanel("routerDebugPanel");
        closePanel("routerToolsPanel");
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire, { once: true });
  } else {
    wire();
  }
})();