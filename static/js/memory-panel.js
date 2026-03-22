document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const memoryPanel = document.getElementById("memoryPanel");
  if (!memoryPanel) return;

  const openBtn =
    document.getElementById("memoryToggleBtnTop") ||
    document.getElementById("toggleMemoryBtn") ||
    document.getElementById("openMemoryBtn");

  const closeBtn =
    document.getElementById("closeMemoryBtn") ||
    document.getElementById("closeMemoryPanelBtn");

  const memoryForm = document.getElementById("memoryForm");
  const memoryKind = document.getElementById("memoryKind");
  const memoryValue = document.getElementById("memoryValue");
  const memoryList = document.getElementById("memoryList");
  const memoryEmpty = document.getElementById("memoryEmpty");
  const refreshMemoryBtn = document.getElementById("refreshMemoryBtn");
  const memoryStatusText = document.getElementById("memoryStatusText");

  function isMobile() {
    return window.innerWidth <= 980;
  }

  function setMemoryStatus(text) {
    if (memoryStatusText) {
      memoryStatusText.textContent = String(text || "Memory panel ready.");
    }
  }

  function getNovaApp() {
    return window.NovaApp || null;
  }

  function getMemoryItems() {
    const app = getNovaApp();
    return Array.isArray(app?.state?.memory) ? app.state.memory : [];
  }

  function openMemoryPanel() {
    if (isMobile()) {
      body.classList.add("mobile-right-open");
      body.classList.remove("mobile-left-open");
      body.classList.add("panel-open");
    } else {
      body.classList.add("memory-open");
    }

    memoryPanel.setAttribute("aria-hidden", "false");
  }

  function closeMemoryPanel() {
    body.classList.remove("mobile-right-open", "panel-open", "memory-open");
    memoryPanel.setAttribute("aria-hidden", "true");
  }

  function toggleMemoryPanel() {
    const isHidden = memoryPanel.getAttribute("aria-hidden") === "true";

    if (isMobile()) {
      if (body.classList.contains("mobile-right-open") || !isHidden) {
        closeMemoryPanel();
      } else {
        openMemoryPanel();
      }
      return;
    }

    if (body.classList.contains("memory-open") || !isHidden) {
      closeMemoryPanel();
    } else {
      openMemoryPanel();
    }
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      return date.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderMemory() {
    if (!memoryList) return;

    const items = getMemoryItems();

    if (memoryEmpty) {
      memoryEmpty.style.display = items.length ? "none" : "";
    }

    if (!items.length) {
      memoryList.innerHTML = "";
      setMemoryStatus("No saved memory yet.");
      return;
    }

    memoryList.innerHTML = items
      .map((item) => {
        return `
          <div class="memory-item" data-memory-id="${escapeHtml(item.id || "")}">
            <div class="memory-item-main">
              <div class="memory-item-kind">${escapeHtml(item.kind || "memory")}</div>
              <div class="memory-item-value">${escapeHtml(item.value || "")}</div>
              <div class="memory-item-meta">${escapeHtml(
                formatTime(item.updated_at || item.created_at || "")
              )}</div>
            </div>

            <div class="memory-item-actions">
              <button
                type="button"
                class="memory-delete-btn"
                data-delete-memory="${escapeHtml(item.id || "")}"
                title="Delete memory"
                aria-label="Delete memory"
              >
                ✕
              </button>
            </div>
          </div>
        `;
      })
      .join("");

    setMemoryStatus(`Loaded ${items.length} memory item${items.length === 1 ? "" : "s"}.`);
  }

  async function refreshMemory() {
    const app = getNovaApp();
    if (!app || typeof app.loadMemory !== "function") {
      setMemoryStatus("Memory system not ready.");
      return;
    }

    try {
      setMemoryStatus("Refreshing memory...");
      await app.loadMemory();
      renderMemory();
    } catch (error) {
      console.error(error);
      setMemoryStatus("Memory refresh failed.");
    }
  }

  async function saveMemory() {
    const app = getNovaApp();
    if (!app || typeof app.addMemory !== "function") {
      setMemoryStatus("Memory system not ready.");
      return;
    }

    const kind = String(memoryKind?.value || "memory").trim();
    const value = String(memoryValue?.value || "").trim();

    if (!value) {
      setMemoryStatus("Enter a memory value first.");
      memoryValue?.focus();
      return;
    }

    try {
      setMemoryStatus("Saving memory...");
      await app.addMemory(kind, value);
      if (memoryValue) {
        memoryValue.value = "";
      }
      renderMemory();
      setMemoryStatus("Memory saved.");
    } catch (error) {
      console.error(error);
      setMemoryStatus("Memory save failed.");
      if (window.NovaToast?.error) {
        window.NovaToast.error(error.message || "Could not save memory.");
      }
    }
  }

  async function removeMemory(id) {
    const app = getNovaApp();
    if (!app || typeof app.deleteMemory !== "function") {
      setMemoryStatus("Memory system not ready.");
      return;
    }

    if (!id) return;

    const ok = window.confirm("Delete this memory?");
    if (!ok) return;

    try {
      setMemoryStatus("Deleting memory...");
      await app.deleteMemory(id);
      renderMemory();
      setMemoryStatus("Memory deleted.");
    } catch (error) {
      console.error(error);
      setMemoryStatus("Delete failed.");
      if (window.NovaToast?.error) {
        window.NovaToast.error(error.message || "Could not delete memory.");
      }
    }
  }

  if (openBtn) {
    openBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleMemoryPanel();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      closeMemoryPanel();
    });
  }

  if (memoryForm) {
    memoryForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      await saveMemory();
    });
  }

  if (refreshMemoryBtn) {
    refreshMemoryBtn.addEventListener("click", async () => {
      await refreshMemory();
    });
  }

  if (memoryList) {
    memoryList.addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-delete-memory]");
      if (!btn) return;

      const id = btn.getAttribute("data-delete-memory");
      await removeMemory(id);
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMemoryPanel();
    }
  });

  document.addEventListener("click", (event) => {
    if (!isMobile()) return;

    const target = event.target;
    const clickedOpenBtn = openBtn && openBtn.contains(target);
    const clickedCloseBtn = closeBtn && closeBtn.contains(target);
    const insidePanel = memoryPanel.contains(target);

    if (clickedOpenBtn || clickedCloseBtn || insidePanel) return;

    if (body.classList.contains("mobile-right-open")) {
      closeMemoryPanel();
    }
  });

  window.addEventListener("resize", () => {
    if (!isMobile()) {
      body.classList.remove("mobile-right-open", "panel-open");
    }
  });

  window.addEventListener("nova:memory-changed", () => {
    renderMemory();
  });

  if (!body.classList.contains("memory-open") && !body.classList.contains("mobile-right-open")) {
    memoryPanel.setAttribute("aria-hidden", "true");
  }

  renderMemory();
});