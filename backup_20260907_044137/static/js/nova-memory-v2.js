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

  function esc(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getMemoryItems(data) {
    return (
      data.memory ||
      data.items ||
      data.entries ||
      data.memories ||
      []
    );
  }

  function renderMemory(items) {
    const container = $("desktopMemoryList");
    if (!container) return;

    container.innerHTML = "";

    if (!items.length) {
      container.innerHTML =
        "<div class='session-placeholder'>No memory stored yet.</div>";
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "desktop-memory-item";

      const text =
        item.text ||
        item.memory ||
        item.content ||
        item.value ||
        JSON.stringify(item);

      card.innerHTML =
        "<div class='desktop-memory-text'>" +
        esc(text) +
        "</div>";

      container.appendChild(card);
    });
  }

  async function loadMemory() {
    const container = $("desktopMemoryList");
    if (!container) return;

    container.innerHTML =
      "<div class='session-placeholder'>Loading memory...</div>";

    try {
      setStatus("loading memory");

      const res = await fetch("/api/memory", {
        cache: "no-store"
      });

      const data = await res.json();

      const items = getMemoryItems(data);

      renderMemory(items);

      console.log(
        "[NOVA Memory V2] loaded",
        items.length
      );

      setStatus("memory loaded");

    } catch (error) {
      console.warn(
        "[NOVA Memory V2] failed",
        error
      );

      container.innerHTML =
        "<div class='session-placeholder'>Could not load memory.</div>";

      setStatus("memory failed");
    }
  }

  function bindMemory() {
    const btn =
      $("openMemoryBtn") ||
      $("desktopMemoryButton");

    if (btn) {
      btn.onclick = loadMemory;
    }
  }

  function boot() {
    bindMemory();

    console.log(
      "[NOVA Memory V2] ready"
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      boot
    );
  } else {
    boot();
  }

  window.NovaLoadMemoryV2 = loadMemory;
})();


