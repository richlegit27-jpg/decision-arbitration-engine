(function () {
  "use strict";

  // =========================
  // NOVA CORE V2 (FAST REBUILD)
  // =========================

  let __nova_send_lock = false;

  const LS_SID = "nova.session_id";
  let sessionId = localStorage.getItem(LS_SID) || "";

  // =========================
  // HELPERS
  // =========================
  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) el.textContent = text;
  }

  function setSessionId(id) {
    if (!id) return;
    sessionId = String(id);
    localStorage.setItem(LS_SID, sessionId);
  }

  function addMsg(role, text) {
    const box =
      $("chatMessages") ||
      $("messages") ||
      document.body;

    const row = document.createElement("div");
    row.className = "message " + role;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text || "";

    row.appendChild(bubble);
    box.appendChild(row);

    box.scrollTop = box.scrollHeight;

    return row;
  }

  // =========================
  // CORE CHAT
  // =========================
  async function sendText(textOverride = "") {
    if (__nova_send_lock) return;
    __nova_send_lock = true;

    const input = $("input") || document.querySelector("textarea");
    const text = String(textOverride || input?.value || "").trim();

    if (!text) {
      __nova_send_lock = false;
      return;
    }

    if (input) input.value = "";

    setStatus("loading...");

    const userNode = addMsg("user", text);
    const assistantNode = addMsg("assistant", "");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "testkey123"
        },
        body: JSON.stringify({
          text,
          session_id: sessionId
        })
      });

      const data = await res.json();

      const reply =
        data?.assistant_message?.text ||
        data?.text ||
        data?.response ||
        "";

      const newSession =
        data?.session_id ||
        data?.active_session_id ||
        data?.session?.id;

      if (newSession) setSessionId(newSession);

      const bubble = assistantNode.querySelector(".bubble");
      if (bubble) bubble.textContent = reply;

      setStatus("done");

    } catch (e) {
      console.warn("[Nova Core V2] error:", e);

      const bubble = assistantNode.querySelector(".bubble");
      if (bubble) bubble.textContent = "Error generating response";

      setStatus("error");

    } finally {
      __nova_send_lock = false;
    }
  }

  // =========================
  // UI BINDINGS
  // =========================
  function bindUI() {
    const sendBtn = $("sendBtn");

    if (sendBtn) {
      sendBtn.onclick = () => sendText();
    }

    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-prompt]");
      if (!btn) return;

      sendText(btn.getAttribute("data-prompt") || "");
    });
  }

  // =========================
  // BOOT
  // =========================
  function boot() {
    bindUI();
    setStatus("ready");
    console.log("[NOVA CORE V2] initialized");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // expose for debugging
  window.sendText = sendText;

})();

