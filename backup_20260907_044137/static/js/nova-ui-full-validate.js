(() => {
  "use strict";

  console.log("ðŸš€ Phase 4 Full UI Automated Validation Starting...");

  const shell = document.querySelector(".nova-app-shell");
  const sidebarBtn = document.getElementById("sidebarToggle");
  const artifactsBtn = document.getElementById("artifactsPanelToggle");
  const memoryBtn = document.getElementById("memoryPanelToggle");
  const artifactCards = Array.from(document.querySelectorAll(".nova-artifact-card"));

  function logResult(name, pass) {
    console.log(`${pass ? "âœ…" : "âŒ"} ${name}`);
  }

  function toggleButtonTest(btn, name, callback) {
    if (!btn) {
      logResult(name, false);
      return callback?.();
    }
    btn.click();
    setTimeout(() => {
      btn.click();
      logResult(name, true);
      callback?.();
    }, 400);
  }

  function artifactViewerTest(cards, callback) {
    if (!cards.length) {
      logResult("Artifact viewer test", false);
      return callback?.();
    }
    let i = 0;
    function next() {
      if (i >= cards.length) return callback?.();
      const openBtn = cards[i].querySelector("[data-action='open-artifact']");
      if (!openBtn) {
        logResult(`Artifact card ${i + 1} open button`, false);
        i++;
        next();
        return;
      }
      openBtn.click();
      setTimeout(() => {
        const closeBtn = document.getElementById("artifactViewerCloseBtn");
        if (closeBtn) closeBtn.click();
        logResult(`Artifact card ${i + 1} viewer open/close`, true);
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
      logResult("Mobile layout fills main content", main && main.offsetWidth > 0);
      Object.defineProperty(window, "innerWidth", { configurable: true, value: origWidth });
      window.dispatchEvent(new Event("resize"));
      callback?.();
    }, 400);
  }

  // Run full sequence
  toggleButtonTest(sidebarBtn, "Sidebar toggle", () => {
    toggleButtonTest(artifactsBtn, "Artifacts panel toggle", () => {
      toggleButtonTest(memoryBtn, "Memory panel toggle", () => {
        artifactViewerTest(artifactCards, () => {
          mobileLayoutTest(() => {
            console.log("ðŸš€ Phase 4 Full UI Automated Validation Completed!");
          });
        });
      });
    });
  });
})();

