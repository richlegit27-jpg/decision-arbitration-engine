(() => {
  "use strict";

  if (window.__novaRenderAttachmentsLoaded) return;
  window.__novaRenderAttachmentsLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.attachments = Nova.attachments || {};

  const API = {
    upload: "/api/upload",
  };

  const state = {
    files: [],
    isUploading: false,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function getComposerRoot() {
    return (
      byId("novaComposer") ||
      qs(".nova-composer") ||
      qs(".composer-shell") ||
      qs(".composer-box") ||
      document.body
    );
  }

  function getInputFile() {
    return (
      byId("novaFileInput") ||
      byId("fileInput") ||
      qs('input[type="file"][data-role="nova-attachments"]') ||
      qs('input[type="file"]')
    );
  }

  function getAttachButton() {
    return (
      byId("novaAttachBtn") ||
      byId("attachBtn") ||
      qs('[data-action="attach"]') ||
      qs(".nova-attach-btn")
    );
  }

  function getBar() {
    return (
      byId("novaAttachmentBar") ||
      qs(".nova-attachment-bar")
    );
  }

  function getDropZone() {
    return (
      byId("novaDropZone") ||
      qs(".nova-drop-zone")
    );
  }

  function safeName(name) {
    return String(name || "file")
      .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "")
      .trim() || "file";
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!value) return "0 B";
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }

  function extOf(fileName) {
    const name = String(fileName || "");
    const idx = name.lastIndexOf(".");
    return idx >= 0 ? name.slice(idx + 1).toUpperCase() : "FILE";
  }

  function ensureUi() {
    if (document.getElementById("nova-render-attachments-style")) return;

    const style = document.createElement("style");
    style.id = "nova-render-attachments-style";
    style.textContent = `
      .nova-attachment-bar {
        display: none;
        width: 100%;
        margin: 0 0 10px;
        gap: 8px;
        flex-wrap: wrap;
        align-items: stretch;
      }

      .nova-attachment-bar.is-visible {
        display: flex;
      }

      .nova-attachment-chip {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        min-height: 42px;
        max-width: min(100%, 320px);
        padding: 8px 10px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.06);
        box-shadow: 0 8px 18px rgba(0,0,0,0.14);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
      }

      .nova-attachment-chip-icon {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
        font-weight: 800;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.08);
        flex: 0 0 auto;
      }

      .nova-attachment-chip-body {
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
        flex: 1 1 auto;
      }

      .nova-attachment-chip-name {
        font-size: 0.86rem;
        font-weight: 700;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .nova-attachment-chip-meta {
        font-size: 0.74rem;
        opacity: 0.72;
        line-height: 1.2;
      }

      .nova-attachment-chip-remove {
        appearance: none;
        border: 0;
        background: transparent;
        color: inherit;
        opacity: 0.78;
        cursor: pointer;
        min-width: 28px;
        min-height: 28px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
        flex: 0 0 auto;
        transition: background 0.16s ease, opacity 0.16s ease, transform 0.16s ease;
      }

      .nova-attachment-chip-remove:hover {
        opacity: 1;
        background: rgba(255,255,255,0.08);
        transform: translateY(-1px);
      }

      .nova-drop-zone.is-dragover,
      .composer-box.is-dragover,
      .nova-composer.is-dragover {
        outline: 2px dashed rgba(255,255,255,0.20);
        outline-offset: 3px;
      }

      @media (max-width: 720px) {
        .nova-attachment-bar {
          gap: 7px;
        }

        .nova-attachment-chip {
          max-width: 100%;
          width: 100%;
        }
      }
    `;
    document.head.appendChild(style);

    let bar = getBar();
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "novaAttachmentBar";
      bar.className = "nova-attachment-bar";

      const composer = getComposerRoot();
      if (composer.firstChild) {
        composer.insertBefore(bar, composer.firstChild);
      } else {
        composer.appendChild(bar);
      }
    }
  }

  function fileKey(file) {
    return [
      safeName(file?.name),
      Number(file?.size || 0),
      Number(file?.lastModified || 0),
      String(file?.type || ""),
    ].join("::");
  }

  function dedupeFiles(files) {
    const seen = new Set();
    const out = [];

    for (const file of files) {
      const key = fileKey(file);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(file);
    }

    return out;
  }

  function renderBar() {
    const bar = getBar();
    if (!bar) return;

    if (!state.files.length) {
      bar.classList.remove("is-visible");
      bar.innerHTML = "";
      return;
    }

    bar.classList.add("is-visible");
    bar.innerHTML = state.files
      .map((file, index) => {
        return `
          <div class="nova-attachment-chip" data-index="${index}">
            <div class="nova-attachment-chip-icon">${extOf(file.name)}</div>
            <div class="nova-attachment-chip-body">
              <div class="nova-attachment-chip-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
              <div class="nova-attachment-chip-meta">${formatBytes(file.size)}${file.__uploadedUrl ? " • uploaded" : ""}</div>
            </div>
            <button
              class="nova-attachment-chip-remove"
              type="button"
              data-action="remove-attachment"
              data-index="${index}"
              aria-label="Remove attachment"
              title="Remove attachment"
            >
              ✕
            </button>
          </div>
        `;
      })
      .join("");

    bindBarActions();
  }

  function bindBarActions() {
    const bar = getBar();
    if (!bar) return;

    qsa('[data-action="remove-attachment"]', bar).forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        const index = Number(btn.dataset.index || "-1");
        if (index < 0) return;

        state.files.splice(index, 1);
        renderBar();
        syncToChatState();
      });
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function addFiles(fileList) {
    const incoming = Array.from(fileList || []).filter(Boolean);
    if (!incoming.length) return;

    state.files = dedupeFiles([...state.files, ...incoming]);
    renderBar();
    syncToChatState();
  }

  function clearFiles() {
    state.files = [];
    renderBar();
    syncToChatState();

    const input = getInputFile();
    if (input) {
      input.value = "";
    }
  }

  function syncToChatState() {
    if (!Nova.chat) Nova.chat = {};
    Nova.chat.attachments = state.files.slice();
  }

  async function safeJson(res) {
    try {
      return await res.json();
    } catch {
      return {};
    }
  }

  async function uploadAll() {
    if (!state.files.length) return [];
    if (state.isUploading) return state.files;

    const fileInput = getInputFile();
    const uploadable = state.files.filter((file) => file instanceof File);

    if (!uploadable.length) return state.files;

    state.isUploading = true;
    try {
      const uploaded = [];

      for (const file of uploadable) {
        if (file.__uploadedUrl || file.__uploadedId) {
          uploaded.push(file);
          continue;
        }

        const form = new FormData();
        form.append("file", file);

        let res;
        try {
          res = await fetch(API.upload, {
            method: "POST",
            body: form,
          });
        } catch (err) {
          console.warn("Upload request failed, keeping local attachment only:", err);
          uploaded.push(file);
          continue;
        }

        const data = await safeJson(res);
        if (!res.ok || data.ok === false) {
          console.warn("Upload backend rejected file, keeping local attachment only:", data);
          uploaded.push(file);
          continue;
        }

        file.__uploadedUrl = data.url || data.file_url || "";
        file.__uploadedId = data.id || data.file_id || "";
        uploaded.push(file);
      }

      state.files = dedupeFiles(uploaded);
      renderBar();
      syncToChatState();
      return state.files;
    } finally {
      state.isUploading = false;
      if (fileInput) {
        fileInput.value = "";
      }
    }
  }

  function bindInput() {
    const input = getInputFile();
    if (!input) return;

    if (input.dataset.bound === "1") return;
    input.dataset.bound = "1";

    input.addEventListener("change", (e) => {
      addFiles(e.target.files);
    });
  }

  function bindAttachButton() {
    const btn = getAttachButton();
    const input = getInputFile();

    if (!btn || !input) return;
    if (btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      input.click();
    });
  }

  function bindDragDrop() {
    const target = getDropZone() || getComposerRoot();
    if (!target) return;

    if (target.dataset.dragBound === "1") return;
    target.dataset.dragBound = "1";

    ["dragenter", "dragover"].forEach((eventName) => {
      target.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        target.classList.add("is-dragover");
      });
    });

    ["dragleave", "dragend", "drop"].forEach((eventName) => {
      target.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        target.classList.remove("is-dragover");
      });
    });

    target.addEventListener("drop", (e) => {
      const files = e.dataTransfer?.files;
      if (files && files.length) {
        addFiles(files);
      }
    });
  }

  function bootstrap() {
    ensureUi();
    bindInput();
    bindAttachButton();
    bindDragDrop();
    renderBar();
    syncToChatState();
  }

  Nova.attachments.addFiles = addFiles;
  Nova.attachments.clear = clearFiles;
  Nova.attachments.uploadAll = uploadAll;
  Nova.attachments.getFiles = () => state.files.slice();
  Nova.attachments.state = state;

  document.addEventListener("DOMContentLoaded", bootstrap);
})();