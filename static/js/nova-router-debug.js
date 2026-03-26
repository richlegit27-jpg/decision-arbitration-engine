(() => {
  "use strict";

  if (window.__novaRouterDebugLite) return;
  window.__novaRouterDebugLite = true;

  const state = window.Nova?.state || {};

  const fab = document.getElementById("routerDebugFab");
  const panel = document.getElementById("routerDebugPanel");
  const closeBtn = document.getElementById("routerDebugClose");
  const content = document.getElementById("routerDebugContent");

  if (!fab || !panel || !content) return;

  function render() {
    const route = state.lastRoute || {};

    content.innerHTML = `
      <div><b>lane:</b> ${route.lane || "-"}</div>
      <div><b>mode:</b> ${route.mode || "-"}</div>
      <div><b>contract:</b> ${route.contract || "-"}</div>
      <div><b>model:</b> ${route.model || "-"}</div>
      <div><b>latency:</b> ${route.latency_ms || 0} ms</div>

      <hr>

      <div><b>reason:</b></div>
      <div style="opacity:.7;margin-bottom:8px;">
        ${route.reason || "-"}
      </div>

      <div><b>tools:</b></div>
      <div style="opacity:.7;margin-bottom:8px;">
        ${(route.tools || []).join(", ") || "-"}
      </div>

      <div><b>memory used:</b></div>
      <div style="opacity:.7;">
        ${
          (route.memory_used || []).map(m =>
            `<div>• ${m.kind} (${m.score}) → ${m.value}</div>`
          ).join("") || "-"
        }
      </div>
    `;
  }

  fab.onclick = () => {
    panel.style.display = "block";
    render();
  };

  closeBtn.onclick = () => {
    panel.style.display = "none";
  };

  // hook into stream/chat updates safely
  const originalSet = Object.getOwnPropertyDescriptor(state, "lastRoute");

  let _route = state.lastRoute;

  Object.defineProperty(state, "lastRoute", {
    get() {
      return _route;
    },
    set(val) {
      _route = val;
      if (panel.style.display === "block") {
        render();
      }
    }
  });
})();