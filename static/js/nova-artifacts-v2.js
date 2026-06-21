(function () {
  "use strict";

  if (window.__NOVA_ARTIFACTS_V2_INSTALLED__) return;
  window.__NOVA_ARTIFACTS_V2_INSTALLED__ = true;

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) el.textContent = "status: " + text;
  }

  function esc(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getArtifactContainer() {
    return (
      $("desktopArtifactList") ||
      $("artifactsList") ||
      $("artifactList") ||
      $("artifacts") ||
      document.querySelector("[data-artifacts-list]") ||
      document.querySelector(".artifacts-list") ||
      document.querySelector(".desktop-artifacts-list") ||
      document.querySelector(".artifacts-section .panel-body") ||
      document.querySelector("#artifactsPanel .panel-body")
    );
  }

  function getArtifactCountEl() {
    return (
      $("desktopArtifactCount") ||
      $("artifactCount") ||
      $("artifactsCount")
    );
  }

  function getArtifactItems(data) {
    if (!data || typeof data !== "object") return [];
    if (Array.isArray(data.artifacts)) return data.artifacts;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.data)) return data.data;
    if (Array.isArray(data.results)) return data.results;
    return [];
  }

  function getArtifactTitle(item) {
    return (
      item.title ||
      item.name ||
      item.filename ||
      item.original_filename ||
      item.id ||
      "Untitled artifact"
    );
  }

  function getArtifactText(item) {
    return (
      item.text ||
      item.content ||
      item.summary ||
      item.description ||
      item.preview ||
      ""
    );
  }

  function getArtifactUrl(item) {
    return (
      item.url ||
      item.file_url ||
      item.download_url ||
      item.path ||
      ""
    );
  }

  function isImageArtifact(item, url) {
    const type = String(item.type || item.kind || item.mime_type || "").toLowerCase();
    return (
      type.includes("image") ||
      /\.(png|jpg|jpeg|webp|gif)$/i.test(String(url || ""))
    );
  }

  function renderArtifacts(items) {
    const container = getArtifactContainer();
    if (!container) return;

    const count = getArtifactCountEl();
    if (count) count.textContent = String(items.length || 0);

    container.innerHTML = "";

    if (!items || !items.length) {
      container.innerHTML = "<div class='session-placeholder'>No artifacts yet.</div>";
      return;
    }

    items.forEach(function (item) {
      const title = esc(getArtifactTitle(item));
      const text = esc(getArtifactText(item));
      const url = esc(getArtifactUrl(item));

      const card = document.createElement("div");
      card.className = "desktop-artifact-item";

      let html = `<div class="desktop-artifact-title">${title}</div>`;

      if (isImageArtifact(item, url) && url) {
        html += `<img src="${url}" alt="${title}" style="max-width:100%; border-radius:12px;" />`;
      } else if (text) {
        html += `<div class="desktop-artifact-content">${text}</div>`;
      }

      if (url) {
        html += `<a href="${url}" target="_blank" rel="noopener">Open artifact</a>`;
      }

      card.innerHTML = html;
      container.appendChild(card);
    });
  }

  let loading = false;

  async function loadArtifacts() {
    const container = getArtifactContainer();
    if (!container) return;

    if (loading) return;
    loading = true;

    try {
      setStatus("loading artifacts");

      const res = await fetch("/api/artifacts", { cache: "no-store" });
      const data = await res.json();

      const items = getArtifactItems(data);
      renderArtifacts(items);

      console.log("[NOVA Artifacts V2] loaded", items.length);
      setStatus("artifacts loaded");
    } catch (error) {
      console.warn("[NOVA Artifacts V2] failed", error);

      container.innerHTML =
        "<div class='session-placeholder'>Could not load artifacts.</div>";

      setStatus("artifacts failed");
    } finally {
      loading = false;
    }
  }

  function bindArtifacts() {
    const btn =
      $("openArtifactsBtn") ||
      $("desktopArtifactsButton") ||
      $("artifactsBtn") ||
      document.querySelector("[data-open-artifacts]");

    if (!btn || btn.__novaArtifactsBound) return;
    btn.__novaArtifactsBound = true;

    btn.addEventListener("click", function (event) {
      event.preventDefault();

      loadArtifacts();

      const section =
        document.querySelector(".artifacts-section") ||
        document.querySelector("#artifactsPanel") ||
        document.querySelector("[data-artifacts-panel]");

      if (section) {
        section.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      }
    });
  }

  function boot() {
    bindArtifacts();
    loadArtifacts();
    console.log("[NOVA Artifacts V2] ready");
  }

  window.NovaLoadArtifactsV2 = loadArtifacts;
  window.NovaLoadDesktopArtifacts = loadArtifacts;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();

