(function () {
  "use strict";

  const modules = [];
  let booted = false;

  function register(name, initFn) {
    if (!name || typeof initFn !== "function") return;
    modules.push({ name, initFn });
  }

  async function boot() {
    if (booted) return;
    booted = true;

    console.log("[NOVA RUNTIME] boot starting");

    for (const mod of modules) {
      try {
        await mod.initFn();
        console.log("[NOVA MODULE]", mod.name, "ready");
      } catch (e) {
        console.warn("[NOVA MODULE FAILED]", mod.name, e);
      }
    }

    console.log("[NOVA RUNTIME] boot complete");
  }

  window.NovaRuntime = {
    register,
    boot
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    setTimeout(boot, 0);
  }
})();

