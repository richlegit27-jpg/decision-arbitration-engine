(() => {
  "use strict";

  if (window.__novaMemoryLoaded) {
    console.warn("Nova memory already loaded. Skipping duplicate module.");
    return;
  }
  window.__novaMemoryLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  const state = (Nova.state = Nova.state || {});
  const dom = (Nova.dom = Nova.dom || {});
  const api = (Nova.api = Nova.api || {});
  const memory = (Nova.memory = Nova.memory || {});
  const render = (Nova.render = Nova.render || {});

  function byId(id) {
    return document.getElementById(id);
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function safeJsonParse(text, fallback = null) {
    try {
      return JSON.parse(text);
    } catch (_) {
      return fallback;
    }
  }

  async function apiRequest(url, options = {}) {
    if (typeof api.request === "function") {
      return api.request(url, options);
    }

    const requestOptions = {
      method: options.method || "GET",
      headers: {
        ...(options.headers || {}),
      },
      body: options.body,
      credentials: options.credentials || "same-origin",
    };

    if (
      requestOptions.body &&
      !requestOptions.headers["Content-Type"] &&
      !(requestOptions.body instanceof FormData)
    ) {
      requestOptions.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, requestOptions);
    const text = await response.text();
    const data = text ? safeJsonParse(text, null) : null;

    if (!response.ok) {
      const message =
        (data && (data.error || data.message)) ||
        `Request failed: ${response.status} ${response.statusText}`;
      throw new Error(message);
    }

    return data ?? { ok: true };
  }

  async function getJson(url) {
    if (typeof api.get === "function") {
      return api.get(url);
    }
    return apiRequest(url);
  }

  async function postJson(url, payload) {
    if (typeof api.post === "function") {
      return api.post(url, payload || {});
    }
    return apiRequest(url, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    });
  }

  function cacheDom() {
    dom.memoryPanel = dom.memoryPanel || byId("memoryPanel");
    dom.memoryList = dom.memoryList || byId("memoryList");
    dom.memoryInput = dom.memoryInput || byId("memoryInput");
    dom.memoryAddBtn = dom.memoryAddBtn || byId("memoryAddBtn");
    return dom;
  }

  function setBusy(flag) {
    state.memoryBusy = !!flag;

    cacheDom();

    if (dom.memoryInput) {
      dom.memoryInput.disabled = !!flag;
    }

    if (dom.memoryAddBtn) {
      dom.memoryAddBtn.disabled = !!flag;
      dom.memoryAddBtn.textContent = flag ? "Saving..." : "Add";
    }
  }

  function renderAllSafe() {
    if (typeof render.all === "function") {
      render.all();
    } else if (typeof render.memoryImpl === "function") {
      render.memoryImpl();
    }
  }

  async function refresh() {
    const data = await getJson("/api/memory");
    state.memoryItems = asArray(data?.items || data?.memory);
    renderAllSafe();
    return state.memoryItems;
  }

  async function add(value, kind = "note") {
    const trimmed = asString(value, "").trim();
    if (!trimmed) return null;

    setBusy(true);
    try {
      const data = await postJson("/api/memory/add", {
        value: trimmed,
        kind: asString(kind, "note").trim() || "note",
      });

      state.memoryItems = asArray(data?.items || data?.memory || state.memoryItems);

      if (!asArray(state.memoryItems).length) {
        await refresh();
      } else {
        renderAllSafe();
      }

      cacheDom();
      if (dom.memoryInput) {
        dom.memoryInput.value = "";
      }

      return data?.item || null;
    } finally {
      setBusy(false);
    }
  }

  async function remove(itemId) {
    const id = asString(itemId, "").trim();
    if (!id) return false;

    if (!(state.deletingMemoryIds instanceof Set)) {
      state.deletingMemoryIds = new Set();
    }

    if (state.deletingMemoryIds.has(id)) {
      return false;
    }

    state.deletingMemoryIds.add(id);
    renderAllSafe();

    try {
      const data = await postJson("/api/memory/delete", {
        id,
        item_id: id,
      });

      const returnedItems = asArray(data?.items || data?.memory);

      if (returnedItems.length || (data && Array.isArray(data.items))) {
        state.memoryItems = returnedItems;
      } else {
        state.memoryItems = asArray(state.memoryItems).filter(
          (item) => asString(item?.id, "") !== id
        );
      }

      renderAllSafe();

      if (!Array.isArray(data?.items) && !Array.isArray(data?.memory)) {
        await refresh();
      }

      return true;
    } finally {
      state.deletingMemoryIds.delete(id);
      renderAllSafe();
    }
  }

  function handleAddClick() {
    cacheDom();
    const value = asString(dom.memoryInput?.value, "");
    void add(value);
  }

  function bind() {
    cacheDom();

    if (dom.memoryAddBtn && !dom.memoryAddBtn.__novaMemoryBound) {
      dom.memoryAddBtn.__novaMemoryBound = true;
      dom.memoryAddBtn.addEventListener("click", handleAddClick);
    }

    if (dom.memoryInput && !dom.memoryInput.__novaMemoryBound) {
      dom.memoryInput.__novaMemoryBound = true;
      dom.memoryInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          handleAddClick();
        }
      });
    }

    if (dom.memoryList && !dom.memoryList.__novaMemoryDelegatesBound) {
      dom.memoryList.__novaMemoryDelegatesBound = true;
      dom.memoryList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-delete-memory]");
        if (!button) return;

        const itemId = asString(button.getAttribute("data-delete-memory"), "");
        if (!itemId) return;

        try {
          await remove(itemId);
        } catch (error) {
          console.error("Memory delete failed:", error);
        }
      });
    }
  }

  memory.refresh = refresh;
  memory.add = add;
  memory.remove = remove;
  memory.bind = bind;

  bind();
})();