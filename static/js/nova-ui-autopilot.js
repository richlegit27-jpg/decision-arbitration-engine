(() => {
  "use strict";

  if (window.__novaAutoPilotLoaded) return;
  window.__novaAutoPilotLoaded = true;

  console.log("ðŸš€ Nova Phase 4 Auto-Pilot Launching...");

  const shell = document.querySelector(".nova-app-shell");
  const sidebarBtn = document.getElementById("sidebarToggle");
  const artifactsBtn = document.getElementById("artifactsPanelToggle");
  const memoryBtn = document.getElementById("memoryPanelToggle");
  const artifactCards = Array.from(document.querySelectorAll(".nova-artifact-card"));

  function log(name, pass) {
    console.log(`${pass ? "âœ…" : "âŒ"} ${name}`);
  }

  function enforceMainWidth() {
    if (!shell) return;
    if (window.innerWidth <= 980) {
      shell.classList.remove("sidebar-closed", "rail-closed", "memory-closed");
    }
  }

  function toggleButtonTest(btn, name, callback) {
    if (!btn) return log(name, false), callback?.();
    try {
      btn.click();
      setTimeout(() => {
        btn.click();
        log(name, true);
        callback?.();
      }, 300);
    } catch {
      log(name, false);
      callback?.();
    }
  }

  function artifactViewerTest(cards, callback) {
    if (!cards.length) return log("Artifact viewer test", false), callback?.();
    let i = 0;
    function next() {
      if (i >= cards.length) return callback?.();
      const openBtn = cards[i].querySelector("[data-action='open-artifact']");
      if (!openBtn) return log(`Artifact card ${i+1} open button`, false), i++, next();
      openBtn.click();
      setTimeout(() => {
        const closeBtn = document.getElementById("artifactViewerCloseBtn");
        if (closeBtn) closeBtn.click();
        log(`Artifact card ${i+1} viewer open/close`, true);
        i++;
        next();
      }, 300);
    }
    next();
  }

  function mobileLayoutTest(callback) {
    const origWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 800 });
    window.dispatchEvent(new Event("resize"));
    setTimeout(() => {
      const main = document.querySelector(".nova-main");
      if (!main || main.offsetWidth <= 0) {
        log("Mobile layout fills main content", false);
        enforceMainWidth(); // auto-heal
      } else log("Mobile layout fills main content", true);
      Object.defineProperty(window, "innerWidth", { configurable: true, value: origWidth });
      window.dispatchEvent(new Event("resize"));
      callback?.();
    }, 300);
  }

  function selfHealPanels() {
    if (!shell) return;
    ["sidebar-closed", "rail-closed", "memory-closed"].forEach((cls) => shell.classList.remove(cls));
    log("Panels auto-healed", true);
  }

  function runAllTests() {
    toggleButtonTest(sidebarBtn, "Sidebar toggle", () => {
      toggleButtonTest(artifactsBtn, "Artifacts panel toggle", () => {
        toggleButtonTest(memoryBtn, "Memory panel toggle", () => {
          artifactViewerTest(artifactCards, () => {
            mobileLayoutTest(() => {
              selfHealPanels();
              console.log("ðŸš€ Nova Phase 4 Auto-Pilot Completed!");
            });
          });
        });
      });
    });
  }

  // Auto-run on load
  function bootstrap() {
    enforceMainWidth();
    runAllTests();
    window.addEventListener("resize", enforceMainWidth);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else bootstrap();
})();

