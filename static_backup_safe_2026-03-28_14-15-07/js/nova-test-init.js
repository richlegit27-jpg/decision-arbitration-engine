(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.test = Nova.test || {};

  const state = Nova.state;

  // ------------------------------
  // Sidebar toggle wiring
  // ------------------------------
  function installPanelToggles() {
    const sidebarBtn = document.getElementById("sidebarToggle");
    if (!sidebarBtn) return;
    sidebarBtn.addEventListener("click", () => {
      const sidebar = document.getElementById("novaSidebar");
      sidebar.classList.toggle("collapsed");
    });
  }

  // ------------------------------
  // Send / Test button handlers
  // ------------------------------
  function initButtons() {
    const sendBtn = document.getElementById("novaSendBtn");
    const testBtn = document.getElementById("novaOneClickTestBtn");
    const composer = document.getElementById("novaComposer");
    const messagesContainer = document.getElementById("novaMessagesList");

    if (sendBtn && composer) {
      sendBtn.addEventListener("click", async () => {
        const content = composer.value.trim();
        if (!content) return;
        await sendMessage(content);
        composer.value = "";
      });
    }

    if (testBtn) {
      testBtn.addEventListener("click", async () => {
        const testContent = "One-Click Test Message";
        await sendMessage(testContent);
      });
    }
  }

  async function sendMessage(content) {
    if (!state.activeSessionId) {
      console.warn("[nova-test-init] no active session");
      return;
    }

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, session_id: state.activeSessionId }),
      });
      const data = await res.json();

      // Append to messages container
      const container = document.getElementById("novaMessagesList");
      if (container) {
        const div = document.createElement("div");
        div.className = "message-bubble assistant";
        div.textContent = content;
        container.appendChild(div);
        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
        // Highlight new message briefly
        div.style.transition = "background 0.5s";
        div.style.background = "rgba(110, 168, 255, 0.3)";
        setTimeout(() => (div.style.background = "transparent"), 600);
      }

      console.log("[nova-test-init] sent message:", data);
    } catch (err) {
      console.error("[nova-test-init] sendMessage error", err);
    }
  }

  // ------------------------------
  // Bootstrap function
  // ------------------------------
  function bootstrap() {
    installPanelToggles();
    initButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();