(function () {
  "use strict";

  console.log("[NOVA Attachments FINAL OWNER] loading");

  const STATE_KEY = "__NOVA_ATTACHMENTS__";

  window[STATE_KEY] = [];

  function $(id) {
    return document.getElementById(id);
  }

  function getSessionId() {
    return String(
      ($("sid") && $("sid").value) ||
      localStorage.getItem("nova_active_session_id") ||
      localStorage.getItem("nova_session_id") ||
      ""
    ).trim();
  }

  function syncGlobals() {
    window.pendingAttachments = window[STATE_KEY];
    window.desktopAttachments = window[STATE_KEY];
    window.__nova_desktop_pending_attachments = window[STATE_KEY];
  }

  function clearAttachments() {
    window[STATE_KEY].length = 0;
    syncGlobals();
    render();
  }

  function getPreviewBox() {
    let box = $("desktopAttachmentPreview");
    if (box) return box;

    const input = $("input");
    const parent = input && input.parentNode ? input.parentNode : document.body;

    box = document.createElement("div");
    box.id = "desktopAttachmentPreview";
    box.className = "nova-attachment-preview";
box.style.width = "100%";
box.style.maxWidth = "100%";
box.style.flex = "0 0 100%";
box.style.boxSizing = "border-box";
    box.style.display = "none";
    box.style.flexWrap = "wrap";
    box.style.gap = "8px";
    box.style.margin = "8px 0";

    parent.insertBefore(box, input || parent.firstChild);
    return box;
  }

  function fileKind(att) {
    const name = String(att.name || att.filename || "").toLowerCase();
    const type = String(att.mime_type || att.type || "").toLowerCase();

    if (type.startsWith("image/") || /\.(png|jpg|jpeg|webp|gif|bmp|svg)$/.test(name)) return "image";
    if (type.includes("pdf") || name.endsWith(".pdf")) return "pdf";
    if (/\.(txt|md|json|js|py|html|css|csv)$/.test(name)) return "text/code";
    if (/\.(doc|docx)$/.test(name)) return "document";
    if (/\.(xls|xlsx|csv)$/.test(name)) return "spreadsheet";
    return "file";
  }

  function icon(att) {
    const kind = fileKind(att);
    if (kind === "image") return "ðŸ–¼ï¸";
    if (kind === "pdf") return "ðŸ“„";
    if (kind === "text/code") return "ðŸ§¾";
    if (kind === "document") return "ðŸ“";
    if (kind === "spreadsheet") return "ðŸ“Š";
    return "ðŸ“Ž";
  }

  function formatSize(size) {
    const n = Number(size || 0);
    if (!n) return "";
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return Math.round(n / 1024) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
  }

  function describeAttachment(att) {
    const name = att.original_filename || att.filename || att.name || "attachment";
    const kind = fileKind(att);
    const size = formatSize(att.size_bytes || att.size);
    const type = att.mime_type || att.type || "";

    return [
      name,
      kind,
      type,
      size
    ].filter(Boolean).join(" Â· ");
  }

  function render() {
    const box = getPreviewBox();
    box.innerHTML = "";

    if (!window[STATE_KEY].length) {
      box.style.display = "none";
      return;
    }

    box.style.display = "flex";

    window[STATE_KEY].forEach((att, index) => {
      const chip = document.createElement("div");
      chip.className = "nova-attachment-chip";
      chip.style.display = "flex";
      chip.style.alignItems = "center";
      chip.style.gap = "8px";
      chip.style.padding = "7px 10px";
      chip.style.borderRadius = "999px";
      chip.style.border = "1px solid rgba(255,255,255,0.22)";
      chip.style.background = "rgba(255,255,255,0.07)";
      chip.style.fontSize = "12px";
      chip.style.maxWidth = "340px";

      const label = document.createElement("span");
      label.title = describeAttachment(att);
      label.style.overflow = "hidden";
      label.style.textOverflow = "ellipsis";
      label.style.whiteSpace = "nowrap";
      label.textContent = icon(att) + " " + describeAttachment(att);

      const del = document.createElement("button");
      del.type = "button";
      del.textContent = "Ã—";
      del.title = "Remove attachment";
      del.style.border = "0";
      del.style.background = "transparent";
      del.style.color = "inherit";
      del.style.cursor = "pointer";
      del.style.fontSize = "16px";
      del.style.lineHeight = "1";
      del.style.opacity = "0.75";

      del.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        window[STATE_KEY].splice(index, 1);
        syncGlobals();
        render();
      });

      chip.appendChild(label);
      chip.appendChild(del);
      box.appendChild(chip);
    });
  }

  function normalizeUpload(data, file) {
    const payload = data.attachment || data.file || data.upload || data;
    const name =
      payload.original_filename ||
      payload.filename ||
      payload.name ||
      file.name;

    const url =
      payload.file_url ||
      payload.url ||
      payload.path ||
      data.file_url ||
      data.url ||
      "";

    const mime =
      payload.mime_type ||
      payload.content_type ||
      payload.type ||
      file.type ||
      "";

    const size =
      payload.size_bytes ||
      payload.size ||
      file.size ||
      0;

    return {
      id: payload.id || payload.attachment_id || payload.file_id || String(Date.now()) + "_" + Math.random(),
      name,
      filename: name,
      original_filename: name,
      url,
      file_url: url,
      mime_type: mime,
      type: mime,
      size,
      size_bytes: size,
      kind: fileKind({ name, mime_type: mime }),
      description: describeAttachment({
        name,
        filename: name,
        original_filename: name,
        mime_type: mime,
        size_bytes: size
      }),
      session_id: getSessionId()
    };
  }

  async function uploadFile(file) {
    const form = new FormData();
    form.append("file", file);

    const sid = getSessionId();
    if (sid) {
      form.append("session_id", sid);
      form.append("client_session_id", sid);
    }

    console.log("[NOVA Attachments FINAL OWNER] uploading", file.name);

    const res = await fetch("/api/upload", {
      method: "POST",
      body: form
    });

    const raw = await res.text();

    let data = {};
    try {
      data = JSON.parse(raw);
    } catch (e) {
      throw new Error("Upload returned non-JSON: " + raw.slice(0, 180));
    }

    if (!res.ok || data.ok === false) {
      throw new Error(data.error || data.message || "Upload failed");
    }

    const att = normalizeUpload(data, file);

    window[STATE_KEY].push(att);
    syncGlobals();
    render();

    console.log("[NOVA Attachments FINAL OWNER] attached", att);
    return att;
  }

  function patchChatFetch() {
    if (window.__NOVA_ATTACHMENT_FINAL_FETCH_PATCH__) return;
    window.__NOVA_ATTACHMENT_FINAL_FETCH_PATCH__ = true;

    const originalFetch = window.fetch;

    window.fetch = async function (url, options) {
      let isChatRequest = false;

      try {
        const target = String(url || "");
        isChatRequest =
          target.includes("/api/chat") &&
          options &&
          typeof options.body === "string";

        if (isChatRequest && window[STATE_KEY].length) {
          const body = JSON.parse(options.body);
          const atts = window[STATE_KEY].slice();

          body.attachments = atts;
          body.files = atts;

          body.attachment_context = atts.map((att) => ({
            name: att.name,
            filename: att.filename,
            original_filename: att.original_filename,
            mime_type: att.mime_type,
            type: att.type,
            size: att.size,
            size_bytes: att.size_bytes,
            url: att.url,
            file_url: att.file_url,
            kind: att.kind,
            description: att.description
          }));

          body.text = String(body.text || body.message || "");
          body.text += "\n\nAttached files:\n" + atts.map((att, i) => {
            return `${i + 1}. ${att.description || describeAttachment(att)}${att.url ? " (" + att.url + ")" : ""}`;
          }).join("\n");

          options.body = JSON.stringify(body);

          console.log("[NOVA Attachments FINAL OWNER] injected attachments", atts);
        }
      } catch (e) {
        console.warn("[NOVA Attachments FINAL OWNER] inject skipped", e);
      }

      const response = await originalFetch.apply(this, arguments);

      if (isChatRequest && response && response.ok) {
        setTimeout(clearAttachments, 50);
      }

      return response;
    };
  }

  function wire() {
    const btn = $("attachBtn");
    const input = $("desktopFileInput");

    if (!btn || !input) {
      console.warn("[NOVA Attachments FINAL OWNER] missing DOM", { btn, input });
      return;
    }

    if (!btn.__novaAttachmentFinalOwnerClick) {
      btn.__novaAttachmentFinalOwnerClick = true;

      btn.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        input.click();
      }, true);
    }

    if (!input.__novaAttachmentFinalOwnerChange) {
      input.__novaAttachmentFinalOwnerChange = true;

      input.addEventListener("change", async function () {
        const files = Array.from(input.files || []);

        for (const file of files) {
          try {
            await uploadFile(file);
          } catch (e) {
            console.error("[NOVA Attachments FINAL OWNER] upload failed", e);
            alert("Attachment failed: " + e.message);
          }
        }

        input.value = "";
      });
    }

    patchChatFetch();
    syncGlobals();
    render();

    window.NovaAttachments = {
      get: () => window[STATE_KEY].slice(),
      clear: clearAttachments,
      render,
      uploadFile
    };

    console.log("[NOVA Attachments FINAL OWNER] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }

  setTimeout(wire, 500);
})();

