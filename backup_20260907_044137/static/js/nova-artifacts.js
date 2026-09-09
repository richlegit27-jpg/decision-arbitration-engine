(function () {
  const state = (window.NovaState = window.NovaState || {});
  state.artifacts = Array.isArray(state.artifacts) ? state.artifacts : [];
  state.activeArtifactId = state.activeArtifactId || "";
  state.activeArtifact = state.activeArtifact || null;

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value) {
    return String(value == null ? "" : value);
  }

  function escapeHtml(value) {
    return safeString(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date.toLocaleString();
    } catch (_) {
      return "";
    }
  }

  function truncate(value, limit = 160) {
    const text = safeString(value).trim();
    if (!text) return "";
    if (text.length <= limit) return text;
    return text.slice(0, Math.max(0, limit - 3)).trimEnd() + "...";
  }

  function isAbsoluteHttpUrl(value) {
    return /^https?:\/\//i.test(safeString(value));
  }

  function normalizeArtifact(raw) {
    const artifact = raw && typeof raw === "object" ? { ...raw } : {};
    const meta = artifact.meta && typeof artifact.meta === "object" ? { ...artifact.meta } : {};
    const viewer = artifact.viewer && typeof artifact.viewer === "object" ? { ...artifact.viewer } : {};

    const kind = safeString(artifact.kind || viewer.kind || "artifact").trim() || "artifact";
    const title =
      safeString(artifact.title || viewer.title || meta.title || meta.domain || "Untitled artifact").trim() ||
      "Untitled artifact";

    const body =
      safeString(
        artifact.body ||
          viewer.body ||
          artifact.content ||
          meta.content ||
          viewer.analysis_text ||
          artifact.summary ||
          artifact.preview
      ).trim();

    const analysisText =
      safeString(viewer.analysis_text || artifact.summary || artifact.preview || meta.description || "").trim();

    const sourceUrl =
      safeString(
        artifact.source_url ||
          viewer.source_url ||
          meta.source_url ||
          meta.url ||
          artifact.url ||
          ""
      ).trim();

    const bullets = safeArray(viewer.bullets).map((item) => safeString(item).trim()).filter(Boolean);
    const links = safeArray(viewer.links.length ? viewer.links : meta.links)
      .map((item) => safeString(item).trim())
      .filter(Boolean);

    const images = safeArray(viewer.images.length ? viewer.images : meta.images)
      .map((item) => safeString(item).trim())
      .filter(Boolean);

    const preview =
      safeString(
        artifact.preview ||
          analysisText ||
          truncate(body, 200)
      ).trim();

    return {
      ...artifact,
      kind,
      title,
      body,
      preview,
      source_url: sourceUrl,
      meta,
      viewer: {
        ...viewer,
        kind,
        title,
        body,
        analysis_text: analysisText,
        bullets,
        links,
        images,
        source_url: sourceUrl,
        image_url: safeString(viewer.image_url || artifact.image_url || meta.image_url || "").trim(),
        video_url: safeString(viewer.video_url || artifact.video_url || meta.video_url || "").trim(),
        audio_url: safeString(viewer.audio_url || artifact.audio_url || meta.audio_url || "").trim(),
      },
    };
  }

  function artifactKindLabel(kind) {
    const value = safeString(kind).replace(/[_-]+/g, " ").trim();
    if (!value) return "Artifact";
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  function renderBullets(bullets) {
    const items = safeArray(bullets).filter(Boolean);
    if (!items.length) return "";
    return (
      '<section class="artifact-view-section">' +
      '<div class="artifact-view-section__title">Highlights</div>' +
      '<ul class="artifact-bullets">' +
      items.map((item) => `<li>${escapeHtml(item)}</li>`).join("") +
      "</ul>" +
      "</section>"
    );
  }

  function renderLinks(links) {
    const items = safeArray(links).filter(Boolean);
    if (!items.length) return "";
    return (
      '<section class="artifact-view-section">' +
      '<div class="artifact-view-section__title">Links</div>' +
      '<div class="artifact-link-list">' +
      items
        .map((href) => {
          const label = truncate(href, 110);
          return (
            `<a class="artifact-link-item" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">` +
            `${escapeHtml(label)}` +
            "</a>"
          );
        })
        .join("") +
      "</div>" +
      "</section>"
    );
  }

  function renderImages(images) {
    const items = safeArray(images).filter((src) => isAbsoluteHttpUrl(src));
    if (!items.length) return "";
    return (
      '<section class="artifact-view-section">' +
      '<div class="artifact-view-section__title">Images</div>' +
      '<div class="artifact-image-grid">' +
      items
        .map(
          (src) =>
            `<a class="artifact-image-card" href="${escapeHtml(src)}" target="_blank" rel="noopener noreferrer">` +
            `<img src="${escapeHtml(src)}" alt="Artifact image" loading="lazy">` +
            "</a>"
        )
        .join("") +
      "</div>" +
      "</section>"
    );
  }

  function renderMedia(viewer) {
    const imageUrl = safeString(viewer.image_url).trim();
    const videoUrl = safeString(viewer.video_url).trim();
    const audioUrl = safeString(viewer.audio_url).trim();

    let html = "";

    if (imageUrl) {
      html +=
        '<section class="artifact-view-section">' +
        '<div class="artifact-view-section__title">Image</div>' +
        `<a class="artifact-media-card" href="${escapeHtml(imageUrl)}" target="_blank" rel="noopener noreferrer">` +
        `<img class="artifact-media-image" src="${escapeHtml(imageUrl)}" alt="Artifact image">` +
        "</a>" +
        "</section>";
    }

    if (videoUrl) {
      html +=
        '<section class="artifact-view-section">' +
        '<div class="artifact-view-section__title">Video</div>' +
        '<div class="artifact-media-card">' +
        `<video class="artifact-media-video" controls preload="metadata" src="${escapeHtml(videoUrl)}"></video>` +
        "</div>" +
        "</section>";
    }

    if (audioUrl) {
      html +=
        '<section class="artifact-view-section">' +
        '<div class="artifact-view-section__title">Audio</div>' +
        '<div class="artifact-media-card">' +
        `<audio class="artifact-media-audio" controls preload="metadata" src="${escapeHtml(audioUrl)}"></audio>` +
        "</div>" +
        "</section>";
    }

    return html;
  }

  function renderBody(body) {
    const text = safeString(body).trim();
    if (!text) return "";
    const paragraphs = text
      .split(/\n{2,}/)
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 40);

    if (!paragraphs.length) return "";

    return (
      '<section class="artifact-view-section">' +
      '<div class="artifact-view-section__title">Content</div>' +
      '<div class="artifact-body">' +
      paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("") +
      "</div>" +
      "</section>"
    );
  }

  function renderMeta(meta, artifact) {
    const rows = [];
    const domain = safeString(meta.domain || "").trim();
    const pageType = safeString(meta.page_type || "").trim();
    const sourceUrl = safeString(artifact.source_url || "").trim();
    const createdAt = formatDate(artifact.created_at || artifact.updated_at || "");
    const statusCode = safeString(meta.status_code || "").trim();

    if (domain) rows.push(["Domain", domain]);
    if (pageType) rows.push(["Page type", pageType]);
    if (statusCode) rows.push(["Status", statusCode]);
    if (createdAt) rows.push(["Saved", createdAt]);

    if (!rows.length && !sourceUrl) return "";

    return (
      '<section class="artifact-view-section">' +
      '<div class="artifact-view-section__title">Details</div>' +
      '<div class="artifact-meta-list">' +
      rows
        .map(
          ([label, value]) =>
            `<div class="artifact-meta-row"><span class="artifact-meta-label">${escapeHtml(label)}</span><span class="artifact-meta-value">${escapeHtml(value)}</span></div>`
        )
        .join("") +
      (sourceUrl
        ? `<div class="artifact-meta-row"><span class="artifact-meta-label">Source</span><a class="artifact-meta-link" href="${escapeHtml(
            sourceUrl
          )}" target="_blank" rel="noopener noreferrer">${escapeHtml(truncate(sourceUrl, 90))}</a></div>`
        : "") +
      "</div>" +
      "</section>"
    );
  }

  function buildArtifactCard(artifact) {
    const active = state.activeArtifactId && artifact.id === state.activeArtifactId;
    const kindLabel = artifactKindLabel(artifact.kind);
    const preview =
      truncate(artifact.preview || artifact.viewer.analysis_text || artifact.body || "", 170) || "No preview yet.";
    const updated = formatDate(artifact.updated_at || artifact.created_at || "");
    const cardClasses = ["artifact-card"];
    if (active) cardClasses.push("artifact-card--active");

    return (
      `<button class="${cardClasses.join(" ")}" type="button" data-artifact-id="${escapeHtml(artifact.id || "")}">` +
      '<div class="artifact-card__top">' +
      `<span class="artifact-card__kind">${escapeHtml(kindLabel)}</span>` +
      (updated ? `<span class="artifact-card__time">${escapeHtml(updated)}</span>` : "") +
      "</div>" +
      `<div class="artifact-card__title">${escapeHtml(artifact.title)}</div>` +
      `<div class="artifact-card__preview">${escapeHtml(preview)}</div>` +
      "</button>"
    );
  }

  function renderArtifactList() {
    const listEl =
      qs("[data-artifact-list]") ||
      qs("#artifacts-list") ||
      qs(".artifacts-list");

    if (!listEl) return;

    const items = safeArray(state.artifacts).map(normalizeArtifact);
    state.artifacts = items;

    if (!items.length) {
      listEl.innerHTML = '<div class="artifact-empty">No artifacts yet.</div>';
      return;
    }

    listEl.innerHTML = items.map(buildArtifactCard).join("");
  }

  function renderArtifactViewer() {
    const viewerEl =
      qs("[data-artifact-viewer]") ||
      qs("#artifact-viewer") ||
      qs(".artifact-viewer");

    if (!viewerEl) return;

    const artifact =
      normalizeArtifact(
        state.activeArtifact ||
          safeArray(state.artifacts).find((item) => item && item.id === state.activeArtifactId) ||
          null
      );

    if (!artifact || !artifact.title) {
      viewerEl.innerHTML = '<div class="artifact-empty">Select an artifact to view it.</div>';
      return;
    }

    const viewer = artifact.viewer || {};
    const meta = artifact.meta || {};
    const kindLabel = artifactKindLabel(artifact.kind);

    viewerEl.innerHTML =
      '<div class="artifact-view">' +
      '<div class="artifact-view-header">' +
      `<div class="artifact-view-header__kind">${escapeHtml(kindLabel)}</div>` +
      `<div class="artifact-view-header__title">${escapeHtml(artifact.title)}</div>` +
      (viewer.analysis_text
        ? `<div class="artifact-view-header__summary">${escapeHtml(viewer.analysis_text)}</div>`
        : "") +
      "</div>" +
      renderBullets(viewer.bullets) +
      renderLinks(viewer.links) +
      renderImages(viewer.images) +
      renderMedia(viewer) +
      renderBody(viewer.body || artifact.body) +
      renderMeta(meta, artifact) +
      "</div>";
  }

  function setActiveArtifactById(artifactId) {
    const id = safeString(artifactId).trim();
    if (!id) return;

    const artifact = safeArray(state.artifacts)
      .map(normalizeArtifact)
      .find((item) => safeString(item.id).trim() === id);

    if (!artifact) return;

    state.activeArtifactId = id;
    state.activeArtifact = artifact;

    renderArtifactList();
    renderArtifactViewer();
  }

  async function fetchArtifacts() {
    try {
      const response = await fetch("/api/artifacts", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Artifacts request failed: ${response.status}`);
      }

      const payload = await response.json();
      const artifacts = safeArray(payload.artifacts || payload.items || payload);
      state.artifacts = artifacts.map(normalizeArtifact);

      if (!state.activeArtifactId && state.artifacts.length) {
        state.activeArtifactId = safeString(state.artifacts[0].id).trim();
        state.activeArtifact = state.artifacts[0];
      } else if (state.activeArtifactId) {
        state.activeArtifact =
          state.artifacts.find((item) => safeString(item.id).trim() === state.activeArtifactId) || state.artifacts[0] || null;
      }

      renderArtifactList();
      renderArtifactViewer();
    } catch (error) {
      console.error("[NovaArtifacts] fetchArtifacts failed", error);
      const listEl = qs("[data-artifact-list]") || qs("#artifacts-list") || qs(".artifacts-list");
      const viewerEl = qs("[data-artifact-viewer]") || qs("#artifact-viewer") || qs(".artifact-viewer");
      if (listEl) listEl.innerHTML = '<div class="artifact-empty">Failed to load artifacts.</div>';
      if (viewerEl) viewerEl.innerHTML = '<div class="artifact-empty">Failed to load artifact viewer.</div>';
    }
  }

  function bindArtifactEvents() {
    document.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-artifact-id]");
      if (button) {
        const artifactId = button.getAttribute("data-artifact-id") || "";
        setActiveArtifactById(artifactId);
        return;
      }

      const refreshButton = event.target.closest("[data-artifacts-refresh]");
      if (refreshButton) {
        await fetchArtifacts();
      }
    });
  }

  function bootstrapFromWindowState() {
    const initialArtifacts = safeArray(
      (window.__NOVA_STATE__ && window.__NOVA_STATE__.artifacts) ||
        window.__INITIAL_STATE__?.artifacts ||
        state.artifacts
    );

    if (initialArtifacts.length) {
      state.artifacts = initialArtifacts.map(normalizeArtifact);
      if (!state.activeArtifactId && state.artifacts.length) {
        state.activeArtifactId = safeString(state.artifacts[0].id).trim();
        state.activeArtifact = state.artifacts[0];
      }
      renderArtifactList();
      renderArtifactViewer();
    }
  }

  function boot() {
    bindArtifactEvents();
    bootstrapFromWindowState();
    fetchArtifacts();
    console.log("[NovaArtifacts] boot complete", {
      artifacts: safeArray(state.artifacts).length,
      activeArtifactId: state.activeArtifactId || "",
    });
  }

  window.NovaArtifacts = {
    boot,
    fetchArtifacts,
    renderArtifactList,
    renderArtifactViewer,
    setActiveArtifactById,
    normalizeArtifact,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();

