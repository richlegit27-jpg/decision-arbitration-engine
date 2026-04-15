(function () {
  const TAG = "[NovaArtifacts]";

  function log(...args) {
    console.log(TAG, ...args);
  }

  function warn(...args) {
    console.warn(TAG, ...args);
  }

  const state = {
    artifacts: [],
    activeArtifactId: "",
    booted: false,
  };

  const els = {
    list: null,
    viewer: null,
    empty: null,
  };

  function qs(sel) {
    return document.querySelector(sel);
  }

  function safeText(value) {
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    return safeText(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function kindLabel(kind) {
    const raw = safeText(kind);
    if (!raw) return "artifact";
    return raw.replaceAll("_", " ");
  }

  function formatDate(value) {
    const raw = safeText(value);
    if (!raw) return "";
    try {
      return new Date(raw).toLocaleString();
    } catch {
      return raw;
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });

    if (!res.ok) {
      throw new Error(`Failed to load artifacts (${res.status})`);
    }

    return await res.json();
  }

  function resolveArtifacts(payload) {
    if (Array.isArray(payload?.artifacts)) return payload.artifacts;
    if (Array.isArray(payload?.data?.artifacts)) return payload.data.artifacts;
    if (Array.isArray(payload)) return payload;
    return [];
  }

  function getViewer(artifact) {
    const viewer = artifact?.viewer && typeof artifact.viewer === "object" ? artifact.viewer : {};
    const meta = artifact?.meta && typeof artifact.meta === "object" ? artifact.meta : {};

    return {
      title:
        safeText(viewer.title) ||
        safeText(artifact?.title) ||
        safeText(meta.title) ||
        "Untitled artifact",
      body:
        safeText(viewer.body) ||
        safeText(artifact?.body) ||
        safeText(artifact?.content) ||
        safeText(meta.body) ||
        safeText(meta.summary),
      kind:
        safeText(viewer.kind) ||
        safeText(artifact?.kind) ||
        safeText(meta.kind) ||
        "artifact",
      image_url:
        safeText(viewer.image_url) ||
        safeText(artifact?.image_url) ||
        safeText(meta.image_url),
      video_url:
        safeText(viewer.video_url) ||
        safeText(artifact?.video_url) ||
        safeText(meta.video_url),
      audio_url:
        safeText(viewer.audio_url) ||
        safeText(artifact?.audio_url) ||
        safeText(meta.audio_url),
      source_url:
        safeText(viewer.source_url) ||
        safeText(artifact?.source_url) ||
        safeText(meta.source_url) ||
        safeText(meta.url),
      media_missing:
        Boolean(viewer.media_missing) ||
        Boolean(artifact?.media_missing),
      image_missing:
        Boolean(viewer.image_missing) ||
        Boolean(artifact?.image_missing),
      video_missing:
        Boolean(viewer.video_missing) ||
        Boolean(artifact?.video_missing),
      audio_missing:
        Boolean(viewer.audio_missing) ||
        Boolean(artifact?.audio_missing),
      image_path:
        safeText(viewer.image_path) || safeText(artifact?.image_path),
      video_path:
        safeText(viewer.video_path) || safeText(artifact?.video_path),
      audio_path:
        safeText(viewer.audio_path) || safeText(artifact?.audio_path),
    };
  }

  function groupArtifacts(list) {
    const groups = {};
    list.forEach((artifact) => {
      const group = safeText(artifact?.group) || "Other";
      if (!groups[group]) groups[group] = [];
      groups[group].push(artifact);
    });
    return groups;
  }

  function mediaFallbackHtml(label, pathValue) {
    const pathLine = safeText(pathValue)
      ? `<div class="artifact-media-fallback-path">${escapeHtml(pathValue)}</div>`
      : "";

    return `
      <div class="artifact-media-fallback">
        <div class="artifact-media-fallback-title">${escapeHtml(label)} unavailable</div>
        ${pathLine}
      </div>
    `;
  }

  function renderMedia(viewer) {
    if (viewer.image_url && !viewer.image_missing) {
      return `
        <div class="artifact-media-wrap">
          <img
            class="artifact-media artifact-image"
            src="${escapeHtml(viewer.image_url)}"
            alt="${escapeHtml(viewer.title)}"
            data-fallback="image"
            data-path="${escapeHtml(viewer.image_path)}"
          />
        </div>
      `;
    }

    if (viewer.video_url && !viewer.video_missing) {
      return `
        <div class="artifact-media-wrap">
          <video
            class="artifact-media artifact-video"
            controls
            preload="metadata"
            src="${escapeHtml(viewer.video_url)}"
            data-fallback="video"
            data-path="${escapeHtml(viewer.video_path)}"
          ></video>
        </div>
      `;
    }

    if (viewer.audio_url && !viewer.audio_missing) {
      return `
        <div class="artifact-media-wrap">
          <audio
            class="artifact-media artifact-audio"
            controls
            preload="metadata"
            src="${escapeHtml(viewer.audio_url)}"
            data-fallback="audio"
            data-path="${escapeHtml(viewer.audio_path)}"
          ></audio>
        </div>
      `;
    }

    if (viewer.media_missing || viewer.image_missing) {
      return mediaFallbackHtml("Image", viewer.image_path);
    }
    if (viewer.video_missing) {
      return mediaFallbackHtml("Video", viewer.video_path);
    }
    if (viewer.audio_missing) {
      return mediaFallbackHtml("Audio", viewer.audio_path);
    }

    return "";
  }

  function artifactCardHtml(artifact) {
    const viewer = getViewer(artifact);
    const preview = viewer.body || safeText(artifact?.preview) || "";
    const activeClass = artifact.id === state.activeArtifactId ? " is-active" : "";

    return `
      <button class="artifact-card${activeClass}" data-artifact-id="${escapeHtml(artifact.id || "")}" type="button">
        <div class="artifact-card-top">
          <div class="artifact-card-title">${escapeHtml(viewer.title)}</div>
          <div class="artifact-card-kind">${escapeHtml(kindLabel(viewer.kind))}</div>
        </div>
        <div class="artifact-card-preview">${escapeHtml(preview.slice(0, 160))}</div>
        <div class="artifact-card-time">${escapeHtml(formatDate(artifact.updated_at || artifact.created_at))}</div>
      </button>
    `;
  }

  function getActiveArtifact() {
    return state.artifacts.find((item) => item.id === state.activeArtifactId) || null;
  }

  function renderList() {
    if (!els.list) return;

    if (!state.artifacts.length) {
      els.list.innerHTML = `<div class="artifact-empty-list">No artifacts yet.</div>`;
      return;
    }

    const groups = groupArtifacts(state.artifacts);
    let html = "";

    Object.keys(groups).forEach((group) => {
      html += `
        <div class="artifact-group">
          <div class="artifact-group-title">${escapeHtml(group)}</div>
          ${groups[group].map(artifactCardHtml).join("")}
        </div>
      `;
    });

    els.list.innerHTML = html;
  }

  function renderViewer() {
    if (!els.viewer) return;

    const artifact = getActiveArtifact();
    if (!artifact) {
      els.viewer.innerHTML = `
        <div class="artifact-view-empty">
          <div class="artifact-view-empty-title">No artifact selected</div>
        </div>
      `;
      return;
    }

    const viewer = getViewer(artifact);
    const mediaHtml = renderMedia(viewer);
    const sourceHtml = viewer.source_url
      ? `<div class="artifact-view-source"><a href="${escapeHtml(viewer.source_url)}" target="_blank" rel="noreferrer">Open source</a></div>`
      : "";

    const actionsHtml = `
      <div class="artifact-view-actions">
        <button type="button" class="artifact-action-btn" data-artifact-action="send_to_chat">Send to chat</button>
        <button type="button" class="artifact-action-btn" data-artifact-action="copy_text">Copy text</button>
        ${viewer.image_url ? `<button type="button" class="artifact-action-btn" data-artifact-action="use_image">Use image</button>` : ""}
        <button type="button" class="artifact-action-btn" data-artifact-action="analyze">Analyze</button>
      </div>
    `;

    els.viewer.innerHTML = `
      <div class="artifact-view">
        <div class="artifact-view-header">
          <div class="artifact-view-title">${escapeHtml(viewer.title)}</div>
          <div class="artifact-view-kind">${escapeHtml(kindLabel(viewer.kind))}</div>
        </div>
        ${actionsHtml}
        ${mediaHtml}
        <div class="artifact-view-body">${escapeHtml(viewer.body || "")}</div>
        ${sourceHtml}
      </div>
    `;

    bindMediaFallbacks();
    bindViewerActions();
  }

  function bindMediaFallbacks() {
    if (!els.viewer) return;

    const mediaEls = els.viewer.querySelectorAll("[data-fallback]");
    mediaEls.forEach((node) => {
      const fallbackType = safeText(node.getAttribute("data-fallback")) || "Media";
      const fallbackPath = safeText(node.getAttribute("data-path"));

      node.addEventListener("error", function () {
        const wrap = node.closest(".artifact-media-wrap");
        if (!wrap) return;

        wrap.outerHTML = mediaFallbackHtml(
          fallbackType.charAt(0).toUpperCase() + fallbackType.slice(1),
          fallbackPath
        );
      });
    });
  }

  async function openArtifact(artifactId) {
    const id = String(artifactId || "").trim();
    if (!id) return;

    const artifact = state.artifacts.find((a) => String(a.id) === id);
    if (!artifact) return;

    const sessionId = String(artifact.session_id || "").trim();

    if (sessionId && typeof window.openSessionFromBackend === "function") {
      try {
        await window.openSessionFromBackend(sessionId);
      } catch (err) {
        console.warn("[NovaArtifacts] session restore failed", err);
      }
    }

    state.activeArtifactId = id;
    renderList();
    renderViewer();
  }

  function setActiveArtifact(id) {
    state.activeArtifactId = safeText(id);
    renderList();
    renderViewer();
  }

  function pushArtifactToChat(text) {
    if (typeof window.NovaArtifactChatAction === "function") {
      window.NovaArtifactChatAction(text);
      return true;
    }

    const composer =
      document.querySelector('textarea[name="message"]') ||
      document.querySelector("#composer-input") ||
      document.querySelector("[data-composer-input]");

    if (!composer) return false;

    composer.value = text;
    composer.dispatchEvent(new Event("input", { bubbles: true }));
    composer.focus();
    return true;
  }

  async function copyTextToClipboard(text) {
    const value = safeText(text);
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
    } catch (err) {
      warn("copy failed", err);
    }
  }

  function buildArtifactPrompt(artifact, mode) {
    const viewer = getViewer(artifact);
    const title = safeText(viewer.title);
    const body = safeText(viewer.body);
    const imageUrl = safeText(viewer.image_url);
    const sourceUrl = safeText(viewer.source_url);
    const kind = safeText(viewer.kind);

    if (mode === "send_to_chat") {
      return [
        `Use this saved artifact in the current chat.`,
        title ? `Title: ${title}` : "",
        kind ? `Type: ${kind}` : "",
        body ? `Content: ${body}` : "",
        imageUrl ? `Image URL: ${imageUrl}` : "",
        sourceUrl ? `Source URL: ${sourceUrl}` : "",
      ].filter(Boolean).join("\n");
    }

    if (mode === "use_image") {
      return [
        `Use this saved image in the current chat.`,
        title ? `Title: ${title}` : "",
        imageUrl ? `Image URL: ${imageUrl}` : "",
      ].filter(Boolean).join("\n");
    }

    if (mode === "analyze") {
      return [
        `Analyze this saved artifact and tell me the important parts.`,
        title ? `Title: ${title}` : "",
        kind ? `Type: ${kind}` : "",
        body ? `Content: ${body}` : "",
        imageUrl ? `Image URL: ${imageUrl}` : "",
        sourceUrl ? `Source URL: ${sourceUrl}` : "",
      ].filter(Boolean).join("\n");
    }

    return body || title;
  }

  async function handleArtifactAction(action) {
    const artifact = getActiveArtifact();
    if (!artifact) return;

    const viewer = getViewer(artifact);

    if (action === "copy_text") {
      await copyTextToClipboard(viewer.body || artifact.preview || viewer.title);
      return;
    }

    if (action === "send_to_chat") {
      pushArtifactToChat(buildArtifactPrompt(artifact, "send_to_chat"));
      return;
    }

    if (action === "use_image") {
      pushArtifactToChat(buildArtifactPrompt(artifact, "use_image"));
      return;
    }

    if (action === "analyze") {
      pushArtifactToChat(buildArtifactPrompt(artifact, "analyze"));
    }
  }

  function bindViewerActions() {
    if (!els.viewer) return;

    els.viewer.querySelectorAll("[data-artifact-action]").forEach((btn) => {
      btn.addEventListener("click", async function () {
        const action = safeText(btn.getAttribute("data-artifact-action"));
        if (!action) return;
        await handleArtifactAction(action);
      });
    });
  }

  function bindListClicks() {
    if (!els.list) return;

    els.list.addEventListener("click", function (event) {
      const card = event.target.closest("[data-artifact-id]");
      if (!card) return;
      openArtifact(card.getAttribute("data-artifact-id"));
    });
  }

  async function loadArtifacts() {
    try {
      const payload = await apiGet("/api/artifacts");
      state.artifacts = resolveArtifacts(payload);

      if (!state.activeArtifactId && state.artifacts.length) {
        state.activeArtifactId = safeText(state.artifacts[0].id);
      } else if (
        state.activeArtifactId &&
        !state.artifacts.some((item) => item.id === state.activeArtifactId)
      ) {
        state.activeArtifactId = state.artifacts.length ? safeText(state.artifacts[0].id) : "";
      }

      renderList();
      renderViewer();
    } catch (err) {
      warn("loadArtifacts failed", err);
      if (els.list) {
        els.list.innerHTML = `<div class="artifact-empty-list">Failed to load artifacts.</div>`;
      }
      if (els.viewer) {
        els.viewer.innerHTML = `<div class="artifact-view-empty"><div class="artifact-view-empty-title">Artifacts unavailable</div></div>`;
      }
    }
  }

  function boot() {
    els.list = qs("[data-artifacts-list]") || qs("#artifacts-list");
    els.viewer = qs("[data-artifact-viewer]") || qs("#artifact-viewer");
    els.empty = qs("[data-artifacts-empty]") || qs("#artifacts-empty");

    bindListClicks();
    loadArtifacts();
    state.booted = true;
    log("boot complete", { artifacts: state.artifacts.length });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  window.NovaArtifacts = {
    reload: loadArtifacts,
    setActiveArtifact,
    openArtifact,
    getState: function () {
      return { ...state };
    },
  };
})();