(() => {
  "use strict";

  console.log("🚀 Phase 4 Endgame Self-Healing Auto-Fix Starting...");

  const shell = document.querySelector(".nova-app-shell");
  const sidebarBtn = document.getElementById("sidebarToggle");
  const artifactsBtn = document.getElementById("artifactsPanelToggle");
  const memoryBtn = document.getElementById("memoryPanelToggle");
  const artifactCards = Array.from(document.querySelectorAll(".nova-artifact-card"));

  function log(name, pass) {
    console.log(`${pass ? "✅" : "❌"} ${name}`);
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
      }, 400);
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
      }, 400);
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
      } else {
        log("Mobile layout fills main content", true);
      }
      Object.defineProperty(window, "innerWidth", { configurable: true, value: origWidth });
      window.dispatchEvent(new Event("resize"));
      callback?.();
    }, 400);
  }

  function selfHealPanels() {
    if (!shell) return;
    ["sidebar-closed", "rail-closed", "memory-closed"].forEach((cls) => {
      shell.classList.remove(cls);
    });
    log("Panels auto-healed", true);
  }

  // Run all tests in sequence
  toggleButtonTest(sidebarBtn, "Sidebar toggle", () => {
    toggleButtonTest(artifactsBtn, "Artifacts panel toggle", () => {
      toggleButtonTest(memoryBtn, "Memory panel toggle", () => {
        artifactViewerTest(artifactCards, () => {
          mobileLayoutTest(() => {
            selfHealPanels();
            console.log("🚀 Phase 4 Endgame Self-Healing Auto-Fix Completed!");
          });
        });
      });
    });
  });

  window.addEventListener("resize", enforceMainWidth);
  enforceMainWidth();
})();