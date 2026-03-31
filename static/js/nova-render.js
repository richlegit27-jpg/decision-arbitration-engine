(function () {
  "use strict";

  const RENDER_VERSION = "history-hooks-2026-03-31-001";

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

  function coerceNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function normalizeText(value) {
    if (value == null) return "";
    return String(value).replace(/\r\n/g, "\n").trim();
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

    const historyIncluded = coerceBool(
      meta.history_included,
      coerceBool(debug.history_included, false)
    );
    const historyCount = coerceNumber(
      meta.history_count ??
      debug.history_count ??
      0,
      0
    );

    if (historyIncluded || historyCount > 0) {
      badges.push(
        buildBadge(
          `History ${historyCount}`,
          "is-history",
          historyIncluded
            ? `${historyCount} recent chat message(s) sent to backend`
            : "history badge present but backend did not mark inclusion"
        )
      );
    }

    const memoryUsed = coerceBool(
      meta.memory_used,
      coerceBool(debug.memory_used, false)
    );

    const memorySelected = coerceNumber(
      meta.memory_selected_count ??
      debug.memory_selected_count ??
      debug.memory_count ??
      0,
      0
    );

    if (memoryUsed || memorySelected > 0) {
      const memoryTitles = safeArray(debug.memory_titles).filter(Boolean);
      const title =
        memoryTitles.length > 0
          ? memoryTitles.join(" • ")
          : `${memorySelected} memory item(s) used`;

      badges.push(buildBadge(`Memory ${memorySelected}`, "is-memory", title));
    }

    const pinnedCount = coerceNumber(
      meta.memory_pinned_count ??
      debug.memory_pinned_count ??
      0,
      0
    );

    if (pinnedCount > 0) {
      badges.push(buildBadge(`Pinned ${pinnedCount}`, "is-pinned", `${pinnedCount} pinned item(s)`));
    }

    const artifactRecallCount = coerceNumber(
      meta.artifact_recall_count ??
      debug.artifact_recall_count ??
      debug.memory_relevant_count ??
      debug.artifact_context_count ??
      0,
      0
    );

    if (artifactRecallCount > 0) {
      const recallTitles = safeArray(
        debug.artifact_recall_titles ??
        debug.memory_titles ??
        debug.document_names ??
        []
      ).filter(Boolean);

      badges.push(
        buildBadge(
          `Recall ${artifactRecallCount}`,
          "is-recall",
          recallTitles.length ? recallTitles.join(" • ") : `${artifactRecallCount} saved artifact(s) recalled`
        )
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

    const serviceVersion =
      meta.chat_service_version ||
      debug.chat_service_version ||
      "";

    if (serviceVersion) {
      badges.push(buildBadge(serviceVersion, "is-service-version", "chat service version"));
    }

    return badges;
  }

  function renderMessageBody(message) {
    const text = textFromMessage(message);
    if (!text) {
      return `<div class="nova-message-markdown" data-message-content=""></div>`;
    }

    return `<div class="nova-message-markdown" data-message-content="${escapeHtml(normalizeText(text))}">${nl2br(text)}</div>`;
  }

  function normalizeMessage(message, roleFallback = "assistant") {
    const source = safeObject(message);
    const content = normalizeText(textFromMessage(source));
    const role = normalizeText(source.role || roleFallback).toLowerCase() === "user" ? "user" : "assistant";
    const createdAt = normalizeText(source.created_at) || new Date().toISOString();
    const id = normalizeText(source.id) || "";
    const meta = safeObject(source.meta);
    const attachments = safeArray(source.attachments);

    return {
      id,
      role,
      content,
      created_at: createdAt,
      meta,
      attachments,
    };
  }

  function renderMessageCard(message, options = {}) {
    const normalized = normalizeMessage(message, message?.role || "assistant");
    const role = normalized.role;
    const createdAt = normalized.created_at || options.created_at || "";
    const time = formatTime(createdAt);
    const badgeHtml = collectBadges(normalized, options).join("");
    const roleLabel = role === "user" ? "You" : "Nova";
    const rawText = normalizeText(normalized.content);

    return `
      <article
        class="nova-message nova-message-${escapeHtml(role)}"
        data-role="${escapeHtml(role)}"
        data-message-id="${escapeHtml(normalized.id || "")}"
        data-created-at="${escapeHtml(createdAt)}"
        data-message-text="${escapeHtml(rawText)}"
      >
        <div
          class="nova-message-inner"
          data-role="${escapeHtml(role)}"
          data-message-id="${escapeHtml(normalized.id || "")}"
          data-created-at="${escapeHtml(createdAt)}"
          data-message-text="${escapeHtml(rawText)}"
        >
          <div class="nova-message-topline">
            <div class="nova-message-author">${escapeHtml(roleLabel)}</div>
            ${time ? `<div class="nova-message-time">${escapeHtml(time)}</div>` : ""}
          </div>
          ${badgeHtml ? `<div class="nova-message-badges">${badgeHtml}</div>` : ""}
          ${renderMessageBody(normalized)}
          ${renderAttachments(normalized)}
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
      history_included:
        assistantMeta.history_included ??
        rootDebug.history_included ??
        false,
      history_count:
        assistantMeta.history_count ??
        rootDebug.history_count ??
        0,
      memory_used:
        assistantMeta.memory_used ??
        rootDebug.memory_used ??
        false,
      memory_selected_count:
        assistantMeta.memory_selected_count ??
        rootDebug.memory_selected_count ??
        rootDebug.memory_count ??
        0,
      memory_pinned_count:
        assistantMeta.memory_pinned_count ??
        rootDebug.memory_pinned_count ??
        0,
      artifact_recall_count:
        assistantMeta.artifact_recall_count ??
        rootDebug.artifact_recall_count ??
        rootDebug.memory_relevant_count ??
        rootDebug.artifact_context_count ??
        0,
    };

    const normalizedMessage = normalizeMessage(
      {
        id: assistant.id || root.message_id || root.id || null,
        role: assistant.role || "assistant",
        content,
        created_at: assistant.created_at || root.created_at || new Date().toISOString(),
        meta: normalizedMeta,
        attachments: safeArray(assistant.attachments),
      },
      "assistant"
    );

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
      history_included:
        normalizedMeta.history_included === true ||
        normalizedMeta.history_included === "true",
      history_count: coerceNumber(normalizedMeta.history_count || 0, 0),
      memory_used:
        normalizedMeta.memory_used === true ||
        normalizedMeta.memory_used === "true",
      memory_selected_count: coerceNumber(normalizedMeta.memory_selected_count || 0, 0),
      memory_pinned_count: coerceNumber(normalizedMeta.memory_pinned_count || 0, 0),
      artifact_recall_count: coerceNumber(normalizedMeta.artifact_recall_count || 0, 0),
      render_version: RENDER_VERSION,
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
      console.log("nova-render loaded", RENDER_VERSION);
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

    ensureEmptyStateMounted() {
      this.ensureReady();
      if (!this.messagesEl || !this.emptyStateEl) return;

      if (!this.emptyStateEl.parentElement || this.emptyStateEl.parentElement !== this.messagesEl) {
        this.messagesEl.prepend(this.emptyStateEl);
      }
    },

    getMessageWrappers() {
      this.ensureReady();
      if (!this.messagesEl) return [];
      return Array.from(this.messagesEl.querySelectorAll(".nova-message-wrap"));
    },

    toggleEmptyState() {
      this.ensureReady();
      this.ensureEmptyStateMounted();
      if (!this.messagesEl || !this.emptyStateEl) return;

      const hasMessages = this.getMessageWrappers().length > 0;
      this.emptyStateEl.style.display = hasMessages ? "none" : "";
    },

    clearMessages() {
      this.ensureReady();
      if (!this.messagesEl) return;

      const emptyState = this.emptyStateEl || $("novaEmptyState");
      this.messagesEl.innerHTML = "";

      if (emptyState) {
        this.emptyStateEl = emptyState;
        this.messagesEl.appendChild(emptyState);
      }

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

      const normalized = normalizeMessage(message, message?.role || "assistant");
      const wrapper = document.createElement("div");

      wrapper.className = "nova-message-wrap";
      wrapper.setAttribute("data-role", normalized.role);
      wrapper.setAttribute("data-message-id", normalized.id || "");
      wrapper.setAttribute("data-created-at", normalized.created_at || "");
      wrapper.setAttribute("data-message-text", normalized.content);
      wrapper.innerHTML = renderMessageCard(normalized, options);

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

      this.clearMessages();

      safeArray(items).forEach((item) => {
        const msg = normalizeMessage(item, safeObject(item).role || "assistant");

        this.appendMessage(
          {
            id: msg.id || null,
            role: msg.role,
            content: msg.content,
            created_at: msg.created_at || new Date().toISOString(),
            attachments: safeArray(msg.attachments),
            meta: safeObject(msg.meta),
          },
          {
            debug: safeObject(safeObject(item).debug),
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
        const role =
          node.getAttribute("data-role") ||
          node.querySelector(".nova-message")?.getAttribute("data-role");
        if (role === "assistant") {
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