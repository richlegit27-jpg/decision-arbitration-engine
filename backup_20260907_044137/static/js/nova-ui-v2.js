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

  function scrollChatToBottom() {
    const box =
      $("chat") ||
      $("desktopChatBox") ||
      $("messages");

    if (box) {
      box.scrollTop = box.scrollHeight;
    }
  }

  function openPanel(id) {
    const panel = $(id);
    if (!panel) return;

    panel.classList.add("open");
    panel.removeAttribute("hidden");

    panel.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  function closePanel(id) {
    const panel = $(id);
    if (!panel) return;

    panel.classList.remove("open");
  }

  function togglePanel(id) {
    const panel = $(id);
    if (!panel) return;

    if (panel.classList.contains("open")) {
      closePanel(id);
    } else {
      openPanel(id);
    }
  }

  function bindPanelButton(buttonId, panelId) {
    const btn = $(buttonId);
    if (!btn) return;

    btn.onclick = function (event) {
      event.preventDefault();
      togglePanel(panelId);
    };
  }

  function bindQuickPrompts() {
    const buttons = document.querySelectorAll("[data-prompt]");

    buttons.forEach((btn) => {
      btn.onclick = function (event) {
        event.preventDefault();

        const prompt = String(btn.getAttribute("data-prompt") || "").trim();
        if (!prompt) return;

        if (typeof window.NovaSendTextV2 === "function") {
          window.NovaSendTextV2(prompt);
        }
      };
    });
  }

  function bindClearChat() {
    const btn =
      $("clearChatBtn") ||
      $("desktopClearChatButton");

    const chat =
      $("chat") ||
      $("desktopChatBox") ||
      $("messages");

    if (!btn || !chat) return;

    btn.onclick = function (event) {
      event.preventDefault();

      chat.innerHTML =
        "<div class='msg assistant'><div class='role'>assistant</div><div class='bubble'>Chat cleared locally.</div></div>";

      setStatus("chat cleared");
      scrollChatToBottom();
    };
  }

  function bindEscapeClose() {
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;

      [
        "sessionsPanel",
        "memoryPanel",
        "artifactsPanel",
        "desktopSessionsPanel",
        "desktopMemoryPanel",
        "desktopArtifactsPanel"
      ].forEach(closePanel);
    });
  }

  function bindUi() {
    bindPanelButton("openSessionsBtn", "sessionsPanel");
    bindPanelButton("openMemoryBtn", "memoryPanel");
    bindPanelButton("openArtifactsBtn", "artifactsPanel");

    bindPanelButton("desktopSessionsButton", "desktopSessionsPanel");
    bindPanelButton("desktopMemoryButton", "desktopMemoryPanel");
    bindPanelButton("desktopArtifactsButton", "desktopArtifactsPanel");

    bindQuickPrompts();
    bindClearChat();
    bindEscapeClose();

    scrollChatToBottom();
  }

  function boot() {
    bindUi();
    setStatus("ready");
    console.log("[NOVA UI V2] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaScrollChatV2 = scrollChatToBottom;
  window.NovaOpenPanelV2 = openPanel;
  window.NovaClosePanelV2 = closePanel;
  window.NovaTogglePanelV2 = togglePanel;
})();

