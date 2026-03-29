(() => {
  "use strict";

  if (window.__novaMainLoaded) return;
  window.__novaMainLoaded = true;

  const Nova = (window.Nova = window.Nova || {});

  async function bootstrap() {
    try {
      Nova.shell?.hydratePreferences?.();
      Nova.shell?.applyTheme?.();
      Nova.shell?.applyPanelState?.();
      Nova.shell?.autoResizeComposer?.();

      if (Nova.sessions?.loadState) {
        await Nova.sessions.loadState();
      }

      if (Nova.memory?.loadMemory) {
        await Nova.memory.loadMemory();
      }

      Nova.ui?.bindEvents?.();
      Nova.render?.renderAll?.();
    } catch (error) {
      console.error("Nova bootstrap failed:", error);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();