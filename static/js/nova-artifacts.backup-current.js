(function () {
  "use strict";

  const LOG = "[NovaArtifacts]";
  const API = {
    state: "/api/state",
    artifacts: "/api/artifacts"
  };

  const state = {
    booted: false,
    artifacts: [],
    activeArtifactId: "",
    activeSessionId: ""
  };

  const els = {};

  function log() {
    try {
      console.log(LOG, ...arguments);
    } catch (_) {}
  }

  function warn() {
    try {
      console.warn(LOG, ...arguments);
    } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function trimText(value, max) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!max || text.length <= max) return text;
    return text.slice(0, max - 1).trimEnd() + "â€¦";
  }

  function normalizeUploadUrl(url) {
    if (!url || typeof url !== "string") return "";
    if (url.startsWith("/api/uploads/")) return url;
    if (url.startsWith("/uploads/")) return "/api" + url;
    return url;
  }

  function artifactKindLabel(kind) {
    switch (String(kind || "").toLowerCase()) {
      case "image_generation":
        return "Image";
      case "image_analysis":
        return "Image Analysis";
      case "web_result":
      case "web_fetch":
      case "web":
        return "Web";
      case "video_analysis":
        return "Video";
      case "chat_reply":
        return "Reply";
      case "error":
        return "Error";
      default:
        return "Artifact";
    }
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      return new Date(value).toLocaleString();
    } catch (_) {
      return String(value);
    }
  }

  function normalizeArtifact(raw) {
    const meta = raw && typeof raw.meta === "object" && raw.meta ? raw.meta : {};
    const viewer = raw && typeof raw.viewer === "object" && raw.viewer ? raw.viewer : {};

    const imageUrl =
      normalizeUploadUrl(raw.image_url) ||
      normalizeUploadUrl(viewer.image_url) ||
      normalizeUploadUrl(meta.image_url) ||
      (typeof raw.content === "string" && raw.content.startsWith("/") ? normalizeUploadUrl(raw.content) : "");

    const sourceUrl =
      raw.source_url ||
      viewer.source_url ||
      meta.source_url ||
      meta.url ||
      "";

    const bullets = Array.isArray(raw.bullets)
      ? raw.bullets
      : Array.isArray(viewer.bullets)
      ? viewer.bullets
      : Array.isArray(meta.bullets)
      ? meta.bullets
      : [];

    const summary =
      raw.summary ||
      viewer.summary ||
      meta.summary ||
      "";

    const content =
      raw.content ||
      viewer.body ||
      meta.content ||
      meta.description ||
      "";

    const title =
      raw.title ||
      viewer.title ||
      meta.title ||
      artifactKindLabel(raw.kind);

    return {
      id: raw.id || "",
      session_id: raw.session_id || "",
      kind: raw.kind || "artifact",
      title,
      content,
      preview: trimText(raw.preview || summary || content || title, 180),
      summary,
      bullets,
      image_url: imageUrl,
      video_url: normalizeUploadUrl(raw.video_url || viewer.video_url || meta.video_url || ""),
      audio_url: normalizeUploadUrl(raw.audio_url || viewer.audio_url || meta.audio_url || ""),
      source_url: sourceUrl,
      created_at: raw.created_at || "",
      updated_at: raw.updated_at || "",
      meta,
      viewer: {
        kind: viewer.kind || raw.kind || "artifact",
        title,
        body: content,
        summary,
        bullets,
        image_url: imageUrl,
        video_url: normalizeUploadUrl(viewer.video_url || raw.video_url || meta.video_url || ""),
        audio_url: normalizeUploadUrl(viewer.audio_url || raw.audio_url || meta.audio_url || ""),
        source_url: sourceUrl,
        domain: viewer.domain || meta.domain || "",
        site_name: viewer.site_name || meta.site_name || "",
        description: viewer.description || meta.description || "",
        ssl_verified:
          typeof viewer.ssl_verified === "boolean"
            ? viewer.ssl_verified
            : typeof meta.ssl_verified === "boolean"
            ? meta.ssl_verified
            : null,
        fetched_at: viewer.fetched_at || meta.fetched_at || raw.created_at || ""
      }
    };
  }

  function getArtifactsListEl() {
    return (
      qs("#artifactsList") ||
      qs('[data-panel-list="artifacts"]') ||
      qs(".nova-artifacts-list")
    );
  }

  function getArtifactViewerEl() {
    return (
      qs("#artifactViewer") ||
      qs('[data-panel-viewer="artifacts"]') ||
      qs(".nova-artifact-viewer")
    );
  }

  function renderArtifactsList() {
    const listEl = getArtifactsListEl();
    if (!listEl) {
      warn("artifacts list element not found");
      return;
    }

    if (!state.artifacts.length) {
      listEl.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">No artifacts yet</div>
          <div class="nova-empty-copy">Chat replies, web fetches, and generated images will show up here.</div>
        </div>
      `;
      return;
    }

    listEl.innerHTML = state.artifacts.map((artifact) => {
      const isActive = artifact.id === state.activeArtifactId;
      const hasImage = !!artifact.image_url;
      const kind = artifactKindLabel(artifact.kind);
      return `
        <button
          type="button"
          class="nova-artifact-card${isActive ? " is-active" : ""}"
          data-artifact-id="${escapeHtml(artifact.id)}"
          title="${escapeHtml(artifact.title)}"
        >
          <div class="nova-artifact-card-top">
            <span class="nova-artifact-kind-badge">${escapeHtml(kind)}</span>
            <span class="nova-artifact-time">${escapeHtml(formatTime(artifact.created_at))}</span>
          </div>
          ${
            hasImage
              ? `<div class="nova-artifact-card-thumb-wrap"><img class="nova-artifact-card-thumb" src="${escapeHtml(
                  artifact.image_url
                )}" alt="${escapeHtml(artifact.title)}" loading="lazy" /></div>`
              : ""
          }
          <div class="nova-artifact-card-title">${escapeHtml(trimText(artifact.title, 100))}</div>
          <div class="nova-artifact-card-preview">${escapeHtml(trimText(artifact.preview, 180))}</div>
        </button>
      `;
    }).join("");

    qsa("[data-artifact-id]", listEl).forEach((button) => {
      button.addEventListener("click", function () {
        const artifactId = this.getAttribute("data-artifact-id") || "";
        openArtifactById(artifactId);
      });
    });
  }

  function renderBullets(bullets) {
    if (!Array.isArray(bullets) || !bullets.length) return "";
    const items = bullets
      .map((item) => trimText(item, 240))
      .filter(Boolean)
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    if (!items) return "";
    return `
      <section class="nova-artifact-section">
        <div class="nova-artifact-section-title">Highlights</div>
        <ul class="nova-artifact-bullets">${items}</ul>
      </section>
    `;
  }

  function renderImageBlock(imageUrl, title) {
    if (!imageUrl) return "";
    return `
      <section class="nova-artifact-section">
        <div class="nova-artifact-media-wrap">
          <img class="nova-artifact-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title || "Artifact image")}" />
        </div>
        <div class="nova-artifact-actions">
          <a class="nova-link-btn" href="${escapeHtml(imageUrl)}" target="_blank" rel="noopener">Open image</a>
        </div>
      </section>
    `;
  }

  function renderWebMeta(viewer) {
    const domain = viewer.domain || "";
    const siteName = viewer.site_name || "";
    const description = viewer.description || "";
    const fetchedAt = viewer.fetched_at || "";
    const sslVerified = viewer.ssl_verified;

    const chips = [];
    if (siteName) chips.push(`<span class="nova-meta-chip">${escapeHtml(siteName)}</span>`);
    if (domain) chips.push(`<span class="nova-meta-chip">${escapeHtml(domain)}</span>`);
    if (typeof sslVerified === "boolean") {
      chips.push(
        `<span class="nova-meta-chip">${sslVerified ? "SSL verified" : "SSL fallback"}</span>`
      );
    }

    return `
      <section class="nova-artifact-section">
        <div class="nova-artifact-meta-row">${chips.join("")}</div>
        ${
          description
            ? `<div class="nova-artifact-description">${escapeHtml(trimText(description, 420))}</div>`
            : ""
        }
        ${
          fetchedAt
            ? `<div class="nova-artifact-subtle">Fetched ${escapeHtml(formatTime(fetchedAt))}</div>`
            : ""
        }
      </section>
    `;
  }

  function renderBody(body) {
    const text = String(body || "").trim();
    if (!text) return "";
    const blocks = text
      .split(/\n{2,}/)
      .map((part) => trimText(part, 1000))
      .filter(Boolean)
      .slice(0, 8);

    if (!blocks.length) return "";
    return `
      <section class="nova-artifact-section">
        <div class="nova-artifact-section-title">Content</div>
        <div class="nova-artifact-body">
          ${blocks.map((part) => `<p>${escapeHtml(part)}</p>`).join("")}
        </div>
      </section>
    `;
  }

  function renderArtifactViewer(artifact) {
    const viewerEl = getArtifactViewerEl();
    if (!viewerEl) {
      warn("artifact viewer element not found");
      return;
    }

    if (!artifact) {
      viewerEl.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">Select an artifact</div>
          <div class="nova-empty-copy">Open a saved image, chat reply, or web result here.</div>
        </div>
      `;
      return;
    }

    const viewer = artifact.viewer || {};
    const title = viewer.title || artifact.title || "Artifact";
    const isWeb = ["web_result", "web_fetch", "web"].includes(String(artifact.kind || "").toLowerCase());
    const imageUrl = normalizeUploadUrl(viewer.image_url || artifact.image_url || "");
    const sourceUrl = viewer.source_url || artifact.source_url || "";
    const summary = viewer.summary || artifact.summary || "";
    const body = viewer.body || artifact.content || "";
    const bullets = Array.isArray(viewer.bullets) ? viewer.bullets : artifact.bullets || [];

    viewerEl.innerHTML = `
      <div class="nova-artifact-view">
        <div class="nova-artifact-view-top">
          <div>
            <div class="nova-artifact-view-kind">${escapeHtml(artifactKindLabel(artifact.kind))}</div>
            <h3 class="nova-artifact-view-title">${escapeHtml(title)}</h3>
            <div class="nova-artifact-view-time">${escapeHtml(formatTime(artifact.created_at))}</div>
          </div>
          <div class="nova-artifact-view-top-actions">
            ${
              sourceUrl
                ? `<a class="nova-link-btn" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener">Open source</a>`
                : ""
            }
            ${
              artifact.session_id
                ? `<button type="button" class="nova-link-btn" data-open-session="${escapeHtml(artifact.session_id)}">Open session</button>`
                : ""
            }
          </div>
        </div>

        ${imageUrl ? renderImageBlock(imageUrl, title) : ""}
        ${isWeb ? renderWebMeta(viewer) : ""}
        ${
          summary
            ? `
            <section class="nova-artifact-section">
              <div class="nova-artifact-section-title">Summary</div>
              <div class="nova-artifact-summary">${escapeHtml(trimText(summary, 800))}</div>
            </section>
          `
            : ""
        }
        ${renderBullets(bullets)}
        ${renderBody(body)}
      </div>
    `;

    qsa("[data-open-session]", viewerEl).forEach((button) => {
      button.addEventListener("click", function () {
        const sessionId = this.getAttribute("data-open-session") || "";
        if (!sessionId) return;
        try {
          window.dispatchEvent(
            new CustomEvent("nova:artifact-open-session", {
              detail: {
                sessionId,
                artifactId: artifact.id
              }
            })
          );
        } catch (_) {}
      });
    });
  }

  function openArtifactById(artifactId) {
    const artifact = state.artifacts.find((item) => item.id === artifactId) || null;
    state.activeArtifactId = artifact ? artifact.id : "";
    renderArtifactsList();
    renderArtifactViewer(artifact);
  }

  function applyArtifacts(artifacts, preferredArtifactId) {
    state.artifacts = Array.isArray(artifacts) ? artifacts.map(normalizeArtifact) : [];

    if (preferredArtifactId && state.artifacts.some((item) => item.id === preferredArtifactId)) {
      state.activeArtifactId = preferredArtifactId;
    } else if (
      !state.activeArtifactId ||
      !state.artifacts.some((item) => item.id === state.activeArtifactId)
    ) {
      state.activeArtifactId = state.artifacts[0] ? state.artifacts[0].id : "";
    }

    renderArtifactsList();
    renderArtifactViewer(state.artifacts.find((item) => item.id === state.activeArtifactId) || null);
  }

  async function refreshFromBackend(preferredArtifactId) {
    try {
      const response = await fetch(API.state, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store"
      });
      const data = await response.json();
      applyArtifacts(data.artifacts || [], preferredArtifactId);
      state.activeSessionId = data.active_session_id || "";
      log("refresh complete", {
        artifacts: state.artifacts.length,
        activeArtifactId: state.activeArtifactId
      });
    } catch (error) {
      warn("refresh failed", error);
      renderArtifactsList();
      renderArtifactViewer(null);
    }
  }

  function bindEvents() {
    window.addEventListener("nova:state-updated", function (event) {
      const detail = event && event.detail ? event.detail : {};
      applyArtifacts(detail.artifacts || [], detail.artifactId || "");
    });

    window.addEventListener("nova:artifact-created", function (event) {
      const detail = event && event.detail ? event.detail : {};
      if (Array.isArray(detail.artifacts)) {
        applyArtifacts(detail.artifacts, detail.artifactId || "");
        return;
      }
      refreshFromBackend(detail.artifactId || "");
    });

    window.addEventListener("nova:refresh-artifacts", function () {
      refreshFromBackend();
    });
  }

  function boot() {
    if (state.booted) return;
    state.booted = true;
    bindEvents();
    refreshFromBackend();
    log("boot complete");
  }

  document.addEventListener("DOMContentLoaded", boot);

  window.NovaArtifacts = {
    boot,
    refresh: refreshFromBackend,
    applyArtifacts,
    openArtifactById,
    getState: function () {
      return {
        artifacts: state.artifacts.slice(),
        activeArtifactId: state.activeArtifactId,
        activeSessionId: state.activeSessionId
      };
    }
  };
})();

