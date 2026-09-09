(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) {
      el.textContent = "status: " + text;
    }
  }

  function restoreSessionId() {
    const sid =
      localStorage.getItem("nova.session_id") ||
      localStorage.getItem("nova_active_session_id") ||
      localStorage.getItem("nova_session_id") ||
      "";

    if (!sid) return "";

    const input = $("sid");
    if (input) {
      input.value = sid;
    }

    window.__NOVA_ACTIVE_SESSION_ID = sid;
    return sid;
  }

  function markReady() {
    document.documentElement.classList.add("nova-v2-ready");

    const body = document.body;
    if (body) {
      body.classList.add("nova-v2-ready");
    }
  }

  function boot() {
    const sid = restoreSessionId();

    markReady();

    if (typeof window.NovaLoadSessionsV2 === "function") {
      window.NovaLoadSessionsV2();
    }

    console.log("[NOVA Boot V2] ready", {
      session_id: sid || null
    });

    setStatus("ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaBootV2 = boot;
})();

