(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function nl2br(text) {
    return escapeHtml(text).replace(/\r?\n/g, "<br>");
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_err) {
      return "";
    }
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function textFromMessage(message) {
    if (!message) return "";
    if (typeof message === "string") return message;
    if (typeof message.content === "string") return message.content;
    if (typeof message.message === "string") return message.message;
    return "";
  }

  function pick(obj, path, fallback) {
    try {
      let cur = obj;
      for (const key of path) {
        if (cur == null) return fallback;
        cur = cur[key];
      }
      return cur ?? fallback;
    } catch (_err) {
      return fallback;
    }
  }

  function coerceBool(value, fallback = false) {
    if (typeof value === "boolean") return value;
    if (value === "true") return true;
    if (value === "false") return false;
    return fallback;
  }

  function getAttachmentList(message) {
    if (!message) return [];
    return safeArray(message.attachments);
  }

  function renderAttachments(message) {
    const attachments = getAttachmentList(message);
    if (!attachments.length) return "";

    const chips = attachments
      .map((item) => {
        const obj = safeObject(item);
        const name = obj.name || obj.filename || obj.title || "attachment";
        const url = obj.url || obj.file_url || obj.src || "";
        const kind = obj.kind || obj.type || "";

        if (url) {
          return `
            <a class="nova-attachment-chip" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">
              ${escapeHtml(name)}
            </a>
          `;
        }

        return `
          <span class="nova-attachment-chip" title="${escapeHtml(kind)}">
            ${escapeHtml(name)}
          </span>
        `;
      })
      .join("");

    return `<div class="nova-message-attachments">${chips}</div>`;
  }

  function buildBadge(label, className, title) {
    return `
      <span class="nova-badge ${escapeHtml(className || "")}"${title ? ` title="${escapeHtml(title)}"` : ""}>
        ${escapeHtml(label)}
      </span>
    `;
  }

  function collectBadges(message, options = {}) {
    const role = message?.role || "assistant";
    const meta = safeObject(message?.meta);
    const debug = safeObject(options.debug);
    const badges = [];

    if (role !== "assistant") {
      return badges;
    }

    const usedFallback = coerceBool(
      meta.used_fallback,
      coerceBool(debug.used_fallback, false)
    );
    if (usedFallback) {
      badges.push(buildBadge("Fallback", "is-fallback"));
    }

    const artifactSaved =
      meta.artifact_saved ??
      debug.artifact_saved ??
      false;

    const artifactSaveReason =
      meta.artifact_save_reason ??
      debug.artifact_save_reason ??
      "";

    const artifactId =
      meta.artifact_id ??
      debug.artifact_id ??
      null;

    const hasArtifactDecision =
      Object.prototype.hasOwnProperty.call(meta, "artifact_saved") ||
      Object.prototype.hasOwnProperty.call(meta, "artifact_save_reason") ||
      Object.prototype.hasOwnProperty.call(debug, "artifact_saved") ||
      Object.prototype.hasOwnProperty.call(debug, "artifact_save_reason");

    if (coerceBool(artifactSaved, false)) {
      let title = artifactSaveReason || "saved";
      if (artifactId) {
        title += ` | ${artifactId}`;
      }
      badges.push(buildBadge("Artifact Saved", "is-artifact-saved", title));
    } else if (hasArtifactDecision) {
      badges.push(
        buildBadge(
          "Artifact Skipped",
          "is-artifact-skipped",
          artifactSaveReason || "not saved"
        )
      );
    }

    const memorySelected =
      Number(debug.memory_selected_count ?? debug.memory_count ?? 0) || 0;
    if (memorySelected > 0) {
      badges.push(
        buildBadge(`Memory ${memorySelected}`, "is-memory", `${memorySelected} memory item(s) used`)
      );
    }

    const pinnedCount = Number(debug.memory_pinned_count ?? 0) || 0;
    if (pinnedCount > 0) {
      badges.push(
        buildBadge(`Pinned ${pinnedCount}`, "is-pinned", `${pinnedCount} pinned item(s)`)
      );
    }

    const webUsed = coerceBool(
      debug.web_used,
      coerceBool(pick(debug, ["web", "used"], false), false)
    );
    if (webUsed) {
      badges.push(buildBadge("Web", "is-web"));
    }

    const documentUsed = coerceBool(
      debug.document_used,
      coerceBool(pick(debug, ["documents", "used"], false), false)
    );
    if (documentUsed) {
      badges.push(buildBadge("Docs", "is-docs"));
    }

    return badges;
  }

  function renderMessageBody(message) {
    const text = textFromMessage(message);
    if (!text) {
      return `<div class="nova-message-markdown"></div>`;
    }

    return `<div class="nova-message-markdown">${nl2br(text)}</div>`;
  }

  function renderMessageCard(message, options = {}) {
    const role = message?.role || "assistant";
    const createdAt = message?.created_at || options.created_at || "";
    const time = formatTime(createdAt);
    const badgeHtml = collectBadges(message, options).join("");
    const roleLabel = role === "user" ? "You" : "Nova";

    return `
      <article class="nova-message nova-message-${escapeHtml(role)}">
        <div class="nova-message-inner">
          <div class="nova-message-topline">
            <div class="nova-message-author">${escapeHtml(roleLabel)}</div>
            ${time ? `<div class="nova-message-time">${escapeHtml(time)}</div>` : ""}
          </div>
          ${badgeHtml ? `<div class="nova-message-badges">${badgeHtml}</div>` : ""}
          ${renderMessageBody(message)}
          ${renderAttachments(message)}
        </div>
      </article>
    `;
  }

  function normalizeIncomingResponse(payload) {
    const root = safeObject(payload);
    const assistant = safeObject(root.assistant_message);
    const rootDebug = safeObject(root.debug);
    const assistantMeta = safeObject(assistant.meta);

    const content =
      typeof assistant.content === "string"
        ? assistant.content
        : typeof root.message === "string"
          ? root.message
          : typeof root.content === "string"
            ? root.content
            : "";

    const normalizedMeta = {
      ...assistantMeta,
      artifact_saved:
        assistantMeta.artifact_saved ??
        rootDebug.artifact_saved ??
        false,
      artifact_save_reason:
        assistantMeta.artifact_save_reason ??
        rootDebug.artifact_save_reason ??
        "",
      artifact_id:
        assistantMeta.artifact_id ??
        rootDebug.artifact_id ??
        null,
      used_fallback:
        assistantMeta.used_fallback ??
        rootDebug.used_fallback ??
        false,
    };

    const normalizedMessage = {
      id: assistant.id || root.message_id || root.id || null,
      role: assistant.role || "assistant",
      content,
      created_at: assistant.created_at || root.created_at || new Date().toISOString(),
      meta: normalizedMeta,
      attachments: safeArray(assistant.attachments),
    };

    const normalizedDebug = {
      ...rootDebug,
      artifact_saved:
        normalizedMeta.artifact_saved === true ||
        normalizedMeta.artifact_saved === "true",
      artifact_save_reason: String(normalizedMeta.artifact_save_reason || ""),
      artifact_id: normalizedMeta.artifact_id || null,
      used_fallback:
        normalizedMeta.used_fallback === true ||
        normalizedMeta.used_fallback === "true",
    };

    return {
      ok: root.ok !== false,
      message: normalizedMessage.content,
      assistant_message: normalizedMessage,
      debug: normalizedDebug,
    };
  }

  function dispatchAssistantResponse(normalizedPayload) {
    try {
      window.dispatchEvent(
        new CustomEvent("nova:assistant-response", {
          detail: normalizedPayload,
        })
      );
    } catch (err) {
      console.warn("Failed to dispatch nova:assistant-response", err);
    }
  }

  const NovaRender = {
    messagesEl: null,
    emptyStateEl: null,

    init() {
      this.messagesEl = $("messages");
      this.emptyStateEl = $("novaEmptyState");
      console.log("nova-render loaded");
      return this;
    },

    ensureReady() {
      if (!this.messagesEl) {
        this.messagesEl = $("messages");
      }
      if (!this.emptyStateEl) {
        this.emptyStateEl = $("novaEmptyState");
      }
    },

    toggleEmptyState() {
      this.ensureReady();
      if (!this.messagesEl || !this.emptyStateEl) return;

      const hasMessages = this.messagesEl.children.length > 0;
      this.emptyStateEl.style.display = hasMessages ? "none" : "";
    },

    clearMessages() {
      this.ensureReady();
      if (!this.messagesEl) return;
      this.messagesEl.innerHTML = "";
      this.toggleEmptyState();
    },

    scrollToBottom() {
      this.ensureReady();
      if (!this.messagesEl) return;
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    },

    appendMessage(message, options = {}) {
      this.ensureReady();
      if (!this.messagesEl) return null;

      const wrapper = document.createElement("div");
      wrapper.className = "nova-message-wrap";
      wrapper.innerHTML = renderMessageCard(message, options);
      this.messagesEl.appendChild(wrapper);
      this.toggleEmptyState();
      this.scrollToBottom();
      return wrapper;
    },

    appendUserMessage(text, createdAt) {
      return this.appendMessage(
        {
          role: "user",
          content: String(text || ""),
          created_at: createdAt || new Date().toISOString(),
          attachments: [],
          meta: {},
        },
        {}
      );
    },

    appendAssistantResponse(payload) {
      const normalized = normalizeIncomingResponse(payload);
      const wrapper = this.appendMessage(normalized.assistant_message, {
        debug: normalized.debug,
      });

      dispatchAssistantResponse(normalized);
      return wrapper;
    },

    renderMessages(items) {
      this.ensureReady();
      if (!this.messagesEl) return;

      this.messagesEl.innerHTML = "";

      safeArray(items).forEach((item) => {
        const msg = safeObject(item);
        const role = msg.role || "assistant";

        this.appendMessage(
          {
            id: msg.id || null,
            role,
            content: textFromMessage(msg),
            created_at: msg.created_at || new Date().toISOString(),
            attachments: safeArray(msg.attachments),
            meta: safeObject(msg.meta),
          },
          {
            debug: safeObject(msg.debug),
          }
        );
      });

      this.toggleEmptyState();
      this.scrollToBottom();
    },

    replaceLastAssistantMessage(payload) {
      this.ensureReady();
      if (!this.messagesEl) {
        return this.appendAssistantResponse(payload);
      }

      const wraps = this.messagesEl.querySelectorAll(".nova-message-wrap");
      for (let i = wraps.length - 1; i >= 0; i -= 1) {
        const node = wraps[i];
        const card = node.querySelector(".nova-message-assistant");
        if (card) {
          node.remove();
          break;
        }
      }

      return this.appendAssistantResponse(payload);
    },

    renderChatResponse(payload) {
      return this.appendAssistantResponse(payload);
    },

    normalizeIncomingResponse,
  };

  window.NovaRender = NovaRender;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      NovaRender.init();
    });
  } else {
    NovaRender.init();
  }
})();