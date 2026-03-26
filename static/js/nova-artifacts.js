(() => {
  "use strict";

  if (window.__novaArtifactsLoaded) return;
  window.__novaArtifactsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.dom = Nova.dom || {};
  Nova.artifacts = Nova.artifacts || {};

  const state = Nova.state;
  const artifactsApi = Nova.artifacts;

  const API = {
    list: "/api/artifacts",
    create: "/api/artifact/create",
    state: "/api/state",
  };

  const byId =
    Nova.dom.byId ||
    function byId(id) {
      return document.getElementById(id);
    };

  const qs =
    Nova.dom.qs ||
    function qs(selector, root = document) {
      return root.querySelector(selector);
    };

  const qsa =
    Nova.dom.qsa ||
    function qsa(selector, root = document) {
      return Array.from(root.querySelectorAll(selector));
    };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function makeId(prefix = "artifact") {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function safeJsonParse(value, fallback = null) {
    if (typeof value !== "string") return fallback;
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });

    const text = await response.text();
    const data = safeJsonParse(text, { ok: response.ok, raw: text });

    if (!response.ok) {
      throw new Error(data?.error || `GET failed: ${url}`);
    }

    return data;
  }

  async function apiPost(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    const text = await response.text();
    const data = safeJsonParse(text, { ok: response.ok, raw: text });

    if (!response.ok) {
      throw new Error(data?.error || `POST failed: ${url}`);
    }

    return data;
  }

  function getActiveSessionId() {
    return (
      state.currentSessionId ||
      state.sessionId ||
      state.activeSessionId ||
      state.selectedSessionId ||
      ""
    );
  }

  function getCurrentRouteMeta() {
    return {
      route_mode:
        state.route_mode ||
        state.routeMode ||
        state.lastRouteMode ||
        state.routerMode ||
        "manual",
      contract:
        state.contract ||
        state.lastContract ||
        state.responseContract ||
        "direct",
    };
  }

  function getArtifactStore() {
    if (!isObject(state.artifacts)) {
      state.artifacts = {};
    }
    return state.artifacts;
  }

  function artifactSortValue(item) {
    return (
      item.updated_at ||
      item.updatedAt ||
      item.created_at ||
      item.createdAt ||
      item.timestamp ||
      ""
    );
  }

  function normalizeArtifact(input, fallbackId = "") {
    if (!input) return null;

    if (typeof input === "string") {
      const now = new Date().toISOString();
      return {
        id: fallbackId || makeId(),
        title: "Untitled Artifact",
        type: "document",
        content: input,
        source_prompt: "",
        route_mode: "manual",
        contract: "direct",
        created_at: now,
        updated_at: now,
        meta: {},
      };
    }

    if (!isObject(input)) return null;

    const now = new Date().toISOString();

    const normalized = {
      id:
        input.id ||
        input.artifact_id ||
        input.uuid ||
        input.key ||
        fallbackId ||
        makeId(),
      title:
        input.title ||
        input.name ||
        input.label ||
        input.filename ||
        "Untitled Artifact",
      type:
        input.type ||
        input.kind ||
        input.artifact_type ||
        input.mime_family ||
        "document",
      content:
        input.content ??
        input.text ??
        input.body ??
        input.markdown ??
        input.value ??
        "",
      source_prompt:
        input.source_prompt ||
        input.prompt ||
        input.source ||
        input.user_prompt ||
        "",
      route_mode:
        input.route_mode ||
        input.routeMode ||
        input.mode ||
        "manual",
      contract:
        input.contract ||
        input.response_contract ||
        input.style_contract ||
        "direct",
      created_at:
        input.created_at ||
        input.createdAt ||
        input.timestamp ||
        now,
      updated_at:
        input.updated_at ||
        input.updatedAt ||
        input.modified_at ||
        input.modifiedAt ||
        input.created_at ||
        input.createdAt ||
        now,
      meta: {},
    };

    if (isObject(input.meta)) {
      normalized.meta = { ...input.meta };
    } else if (isObject(input.metadata)) {
      normalized.meta = { ...input.metadata };
    }

    return normalized;
  }

  function normalizeArtifactMap(input) {
    const output = {};

    if (!input) return output;

    if (Array.isArray(input)) {
      input.forEach((item, index) => {
        const normalized = normalizeArtifact(item, `artifact-${index + 1}`);
        if (normalized?.id) output[normalized.id] = normalized;
      });
      return output;
    }

    if (isObject(input)) {
      Object.entries(input).forEach(([key, value]) => {
        const normalized = normalizeArtifact(value, key);
        if (normalized?.id) output[normalized.id] = normalized;
      });
    }

    return output;
  }

  function replaceArtifacts(nextArtifacts) {
    state.artifacts = normalizeArtifactMap(nextArtifacts);
    return getArtifactStore();
  }

  function mergeArtifacts(nextArtifacts) {
    const store = getArtifactStore();
    const normalizedMap = normalizeArtifactMap(nextArtifacts);

    Object.entries(normalizedMap).forEach(([id, artifact]) => {
      store[id] = {
        ...(store[id] || {}),
        ...artifact,
      };
    });

    return store;
  }

  function getArtifactsArray() {
    return Object.values(getArtifactStore()).sort((a, b) => {
      const aValue = artifactSortValue(a);
      const bValue = artifactSortValue(b);
      return String(bValue).localeCompare(String(aValue));
    });
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
  }

  function truncate(value, max = 280) {
    const text = String(value ?? "");
    if (text.length <= max) return text;
    return `${text.slice(0, max).trim()}…`;
  }

  function getRoot() {
    return (
      byId("novaArtifactsRoot") ||
      byId("artifactsRoot") ||
      qs("[data-artifacts-root]")
    );
  }

  function getListEl() {
    return (
      byId("novaArtifactsList") ||
      byId("artifactsList") ||
      qs("[data-artifacts-list]")
    );
  }

  function getCountEl() {
    return (
      byId("novaArtifactsCount") ||
      byId("artifactsCount") ||
      qs("[data-artifacts-count]")
    );
  }

  function getEmptyEl() {
    return (
      byId("novaArtifactsEmpty") ||
      byId("artifactsEmpty") ||
      qs("[data-artifacts-empty]")
    );
  }

  function getStatusEl() {
    return (
      byId("novaArtifactsStatus") ||
      byId("artifactsStatus") ||
      qs("[data-artifacts-status]")
    );
  }

  function getViewerEls() {
    return {
      viewer:
        byId("novaArtifactViewer") ||
        byId("artifactViewer") ||
        qs("[data-artifact-viewer]"),
      title:
        byId("novaArtifactViewerTitle") ||
        byId("artifactViewerTitle") ||
        qs("[data-artifact-viewer-title]"),
      content:
        byId("novaArtifactViewerContent") ||
        byId("artifactViewerContent") ||
        qs("[data-artifact-viewer-content]"),
      type:
        byId("novaArtifactViewerType") ||
        byId("artifactViewerType") ||
        qs("[data-artifact-viewer-type]"),
      time:
        byId("novaArtifactViewerTime") ||
        byId("artifactViewerTime") ||
        qs("[data-artifact-viewer-time]"),
      close:
        byId("artifactViewerCloseBtn") ||
        byId("novaArtifactViewerClose") ||
        qs("[data-artifact-viewer-close]"),
    };
  }

  function setStatus(message, isError = false) {
    const el = getStatusEl();
    if (!el) return;

    el.textContent = message || "";
    el.dataset.state = isError ? "error" : "idle";
  }

  function cardMarkup(item) {
    const preview = truncate(item.content, 280);
    const type = escapeHtml(item.type || "document");
    const title = escapeHtml(item.title || "Untitled Artifact");
    const updated = escapeHtml(formatDate(item.updated_at || item.created_at || ""));
    const routeMode = escapeHtml(item.route_mode || "manual");
    const contract = escapeHtml(item.contract || "direct");
    const id = escapeHtml(item.id || "");

    return `
      <article class="nova-artifact-card" data-artifact-id="${id}">
        <div class="nova-artifact-card-head">
          <div class="nova-artifact-card-title-wrap">
            <h4 class="nova-artifact-card-title">${title}</h4>
            <div class="nova-artifact-card-meta">
              <span class="nova-artifact-badge">${type}</span>
              <span class="nova-artifact-badge">${routeMode}</span>
              <span class="nova-artifact-badge">${contract}</span>
            </div>
          </div>
          <div class="nova-artifact-card-time">${updated}</div>
        </div>

        <div class="nova-artifact-card-body">
          <pre class="nova-artifact-card-preview">${escapeHtml(preview)}</pre>
        </div>

        <div class="nova-artifact-card-actions">
          <button
            type="button"
            class="nova-artifact-action"
            data-action="open-artifact"
            data-artifact-id="${id}"
          >
            Open
          </button>

          <button
            type="button"
            class="nova-artifact-action"
            data-action="copy-artifact"
            data-artifact-id="${id}"
          >
            Copy
          </button>
        </div>
      </article>
    `;
  }

  function renderArtifacts() {
    const root = getRoot();
    const listEl = getListEl();
    const countEl = getCountEl();
    const emptyEl = getEmptyEl();
    const artifacts = getArtifactsArray();

    if (countEl) {
      countEl.textContent = String(artifacts.length);
    }

    if (!root && !listEl) return;

    if (emptyEl) {
      emptyEl.hidden = artifacts.length > 0;
    }

    if (!listEl) return;

    if (!artifacts.length) {
      listEl.innerHTML = "";
      bindActionButtons();
      syncArtifactsRail();
      return;
    }

    listEl.innerHTML = artifacts.map(cardMarkup).join("");
    bindActionButtons(listEl);
    syncArtifactsRail();
  }

  function syncArtifactsRail() {
    if (typeof state.artifactsOpen !== "boolean") {
      state.artifactsOpen = true;
    }

    window.dispatchEvent(
      new CustomEvent("nova:artifacts-updated", {
        detail: {
          count: getArtifactsArray().length,
        },
      })
    );
  }

  function openArtifactById(artifactId) {
    const item = getArtifactStore()[artifactId];
    if (!item) return;

    state.activeArtifactId = artifactId;

    const viewerEls = getViewerEls();
    if (viewerEls.title) viewerEls.title.textContent = item.title || "Untitled Artifact";
    if (viewerEls.type) viewerEls.type.textContent = item.type || "document";
    if (viewerEls.time) {
      viewerEls.time.textContent = formatDate(item.updated_at || item.created_at || "");
    }
    if (viewerEls.content) {
      viewerEls.content.textContent = String(item.content ?? "");
    }
    if (viewerEls.viewer) {
      viewerEls.viewer.hidden = false;
      viewerEls.viewer.setAttribute("data-open", "true");
    }

    if (state.artifactsOpen === false && Nova.render?.toggleArtifactsPanel) {
      Nova.render.toggleArtifactsPanel();
    }
  }

  function closeArtifactViewer() {
    const viewerEls = getViewerEls();
    if (!viewerEls.viewer) return;
    viewerEls.viewer.hidden = true;
    viewerEls.viewer.setAttribute("data-open", "false");
  }

  async function copyArtifactById(artifactId) {
    const item = getArtifactStore()[artifactId];
    if (!item) return;

    try {
      await navigator.clipboard.writeText(String(item.content ?? ""));
      setStatus(`Copied artifact: ${item.title}`);
    } catch {
      setStatus("Copy failed.", true);
    }
  }

  function bindActionButtons(root = document) {
    qsa("[data-action='open-artifact']", root).forEach((button) => {
      if (button.dataset.boundOpenArtifact === "1") return;
      button.dataset.boundOpenArtifact = "1";
      button.addEventListener("click", () => {
        openArtifactById(button.dataset.artifactId || "");
      });
    });

    qsa("[data-action='copy-artifact']", root).forEach((button) => {
      if (button.dataset.boundCopyArtifact === "1") return;
      button.dataset.boundCopyArtifact = "1";
      button.addEventListener("click", () => {
        copyArtifactById(button.dataset.artifactId || "");
      });
    });

    const viewerEls = getViewerEls();
    if (viewerEls.close && viewerEls.close.dataset.boundArtifactViewerClose !== "1") {
      viewerEls.close.dataset.boundArtifactViewerClose = "1";
      viewerEls.close.addEventListener("click", closeArtifactViewer);
    }
  }

  function finishRender() {
    renderArtifacts();
    bindActionButtons();
    bindMessageSaveButtons(document);
  }

  async function refreshArtifacts() {
    const currentSessionId = getActiveSessionId();
    const storeBefore = { ...getArtifactStore() };
    let nextStore = {};

    try {
      setStatus("Refreshing artifacts...");

      try {
        const response = await apiGet(API.list);
        if (response?.artifacts) {
          nextStore = {
            ...nextStore,
            ...normalizeArtifactMap(response.artifacts),
          };
        }
      } catch (error) {
        console.warn("Nova artifacts: /api/artifacts refresh failed", error);
      }

      try {
        const stateResponse = await apiGet(API.state);
        if (stateResponse?.artifacts) {
          nextStore = {
            ...nextStore,
            ...normalizeArtifactMap(stateResponse.artifacts),
          };
        }

        const sessionArtifacts =
          stateResponse?.sessions?.[currentSessionId]?.artifacts ||
          stateResponse?.session?.artifacts;

        if (sessionArtifacts) {
          nextStore = {
            ...nextStore,
            ...normalizeArtifactMap(sessionArtifacts),
          };
        }
      } catch (error) {
        console.warn("Nova artifacts: /api/state refresh failed", error);
      }

      if (Object.keys(nextStore).length) {
        replaceArtifacts(nextStore);
      } else {
        state.artifacts = storeBefore;
      }

      finishRender();
      setStatus(`Artifacts loaded: ${getArtifactsArray().length}`);
      return getArtifactStore();
    } catch (error) {
      console.error("Nova artifacts refresh failed:", error);
      state.artifacts = storeBefore;
      finishRender();
      setStatus(error.message || "Artifact refresh failed.", true);
      return getArtifactStore();
    }
  }

  function pushLocalArtifacts(items) {
    mergeArtifacts(items);
    finishRender();
    return getArtifactStore();
  }

  function tryCollectArtifactCandidate(value, sink) {
    if (!value) return;

    if (Array.isArray(value)) {
      value.forEach((item) => tryCollectArtifactCandidate(item, sink));
      return;
    }

    if (!isObject(value)) return;

    if (value.artifact) {
      tryCollectArtifactCandidate(value.artifact, sink);
    }

    if (value.artifacts) {
      tryCollectArtifactCandidate(value.artifacts, sink);
    }

    const likelyArtifact =
      value.type === "document" ||
      value.type === "code" ||
      value.type === "markdown" ||
      value.type === "text" ||
      value.kind === "document" ||
      value.artifact_id ||
      ("title" in value &&
        ("content" in value || "text" in value || "body" in value) &&
        ("type" in value || "kind" in value || "route_mode" in value || "contract" in value));

    if (likelyArtifact) {
      const normalized = normalizeArtifact(value);
      if (normalized) sink.push(normalized);
    }

    const nestedKeys = [
      "data",
      "payload",
      "result",
      "response",
      "output",
      "message",
      "final",
      "done",
      "meta",
      "metadata",
    ];

    nestedKeys.forEach((key) => {
      if (value[key]) {
        tryCollectArtifactCandidate(value[key], sink);
      }
    });
  }

  function extractArtifactsFromPayload(payload) {
    const found = [];
    tryCollectArtifactCandidate(payload, found);

    const deduped = {};
    found.forEach((item) => {
      const normalized = normalizeArtifact(item);
      if (normalized?.id) {
        deduped[normalized.id] = normalized;
      }
    });

    return Object.values(deduped);
  }

  async function persistArtifacts(items, options = {}) {
    if (!Array.isArray(items) || !items.length) return [];

    const sessionId =
      options.session_id ||
      options.sessionId ||
      getActiveSessionId() ||
      "";

    const routeMeta = getCurrentRouteMeta();
    const saved = [];

    for (const item of items) {
      const normalized = normalizeArtifact(item);
      if (!normalized) continue;

      const payload = {
        session_id: sessionId,
        title: normalized.title || "Untitled Artifact",
        type: normalized.type || "document",
        content: normalized.content ?? "",
        source_prompt: normalized.source_prompt || "",
        route_mode: normalized.route_mode || routeMeta.route_mode,
        contract: normalized.contract || routeMeta.contract,
      };

      try {
        const response = await apiPost(API.create, payload);
        const created =
          normalizeArtifact(
            response?.artifact ||
              response?.data?.artifact ||
              response?.result?.artifact ||
              response?.created ||
              payload
          ) || normalizeArtifact(payload);

        if (created) {
          mergeArtifacts([created]);
          saved.push(created);
        }
      } catch (error) {
        console.warn("Nova artifacts persist failed for one item:", error);
      }
    }

    finishRender();

    if (saved.length) {
      setStatus(`Artifacts saved: ${saved.length}`);
    }

    return saved;
  }

  async function captureFromPayload(payload, options = {}) {
    const items = extractArtifactsFromPayload(payload);
    if (!items.length) return [];

    pushLocalArtifacts(items);

    const shouldPersist = options.persist !== false && options.skipPersist !== true;
    if (!shouldPersist) {
      return items;
    }

    return persistArtifacts(items, options);
  }

  function extractArtifactFromMessageDom(messageEl) {
    if (!messageEl) return null;

    const explicitTitle =
      messageEl.dataset.artifactTitle ||
      messageEl.getAttribute("data-artifact-title") ||
      "";
    const explicitType =
      messageEl.dataset.artifactType ||
      messageEl.getAttribute("data-artifact-type") ||
      "document";

    const contentEl =
      qs("[data-message-content]", messageEl) ||
      qs(".message-content", messageEl) ||
      qs(".nova-message-content", messageEl) ||
      messageEl;

    const content = contentEl ? contentEl.textContent || "" : "";
    if (!content.trim()) return null;

    return normalizeArtifact({
      title: explicitTitle || "Saved Chat Artifact",
      type: explicitType,
      content,
      source_prompt: state.lastPrompt || "",
      route_mode: getCurrentRouteMeta().route_mode,
      contract: getCurrentRouteMeta().contract,
    });
  }

  async function saveArtifactFromMessageElement(messageEl) {
    const artifact = extractArtifactFromMessageDom(messageEl);
    if (!artifact) {
      setStatus("Could not find message content to save.", true);
      return null;
    }

    const saved = await persistArtifacts([artifact], {
      session_id: getActiveSessionId(),
    });

    await refreshArtifacts();
    return saved[0] || null;
  }

  function bindMessageSaveButtons(root = document) {
    qsa("[data-action='save-artifact']", root).forEach((button) => {
      if (button.dataset.boundSaveArtifact === "1") return;
      button.dataset.boundSaveArtifact = "1";

      button.addEventListener("click", async () => {
        const messageEl =
          button.closest("[data-message-id]") ||
          button.closest(".message") ||
          button.closest(".nova-message");

        button.disabled = true;
        try {
          await saveArtifactFromMessageElement(messageEl);
        } catch (error) {
          console.error("Nova save artifact click failed:", error);
          setStatus(error.message || "Save artifact failed.", true);
        } finally {
          button.disabled = false;
        }
      });
    });
  }

  async function handleChatResponse(payload) {
    return captureFromPayload(payload, {
      session_id:
        payload?.session_id ||
        payload?.sessionId ||
        payload?.data?.session_id ||
        getActiveSessionId(),
      persist: true,
    });
  }

  async function handleStreamEvent(eventName, payload) {
    const normalizedName = String(eventName || "").toLowerCase();

    if (
      normalizedName === "artifact" ||
      normalizedName === "done" ||
      normalizedName === "final" ||
      normalizedName === "result"
    ) {
      return captureFromPayload(payload, {
        session_id:
          payload?.session_id ||
          payload?.sessionId ||
          payload?.data?.session_id ||
          getActiveSessionId(),
        persist: true,
      });
    }

    return [];
  }

  function bindGlobalHooks() {
    document.addEventListener("click", (event) => {
      const saveButton = event.target.closest("[data-action='save-artifact']");
      if (!saveButton) return;
      bindMessageSaveButtons(document);
    });

    window.addEventListener("nova:chat-response", async (event) => {
      try {
        await handleChatResponse(event.detail || {});
      } catch (error) {
        console.warn("Nova artifacts chat capture failed:", error);
      }
    });

    window.addEventListener("nova:stream-event", async (event) => {
      const detail = event.detail || {};
      try {
        await handleStreamEvent(
          detail.event || detail.type || "",
          detail.payload || detail.data || detail
        );
      } catch (error) {
        console.warn("Nova artifacts stream capture failed:", error);
      }
    });

    window.addEventListener("nova:session-changed", () => {
      closeArtifactViewer();
      refreshArtifacts().catch((error) => {
        console.warn("Nova artifact refresh on session change failed:", error);
      });
    });

    window.addEventListener("nova:artifacts-updated", () => {
      bindMessageSaveButtons(document);
    });
  }

  function installPublicApi() {
    artifactsApi.refresh = refreshArtifacts;
    artifactsApi.render = finishRender;
    artifactsApi.merge = pushLocalArtifacts;
    artifactsApi.captureFromPayload = captureFromPayload;
    artifactsApi.persist = persistArtifacts;
    artifactsApi.handleChatResponse = handleChatResponse;
    artifactsApi.handleStreamEvent = handleStreamEvent;
    artifactsApi.saveFromMessageElement = saveArtifactFromMessageElement;
    artifactsApi.bindMessageSaveButtons = bindMessageSaveButtons;
    artifactsApi.open = openArtifactById;
    artifactsApi.close = closeArtifactViewer;
    artifactsApi.copy = copyArtifactById;
    artifactsApi.getAll = () => getArtifactsArray();
    artifactsApi.getMap = () => ({ ...getArtifactStore() });
  }

  async function bootstrap() {
    installPublicApi();
    bindGlobalHooks();
    bindActionButtons();
    bindMessageSaveButtons();
    await refreshArtifacts();
    console.log("Nova artifacts loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      bootstrap().catch((error) => {
        console.error("Nova artifacts bootstrap failed:", error);
      });
    });
  } else {
    bootstrap().catch((error) => {
      console.error("Nova artifacts bootstrap failed:", error);
    });
  }
})();