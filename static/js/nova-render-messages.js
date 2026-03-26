(() => {
  "use strict";

  if (window.__novaRenderMessagesLoaded) return;
  window.__novaRenderMessagesLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.messages = Nova.messages || {};
  Nova.state = Nova.state || {};
  Nova.dom = Nova.dom || {};
  Nova.render = Nova.render || {};

  const messagesApi = Nova.messages;
  const state = Nova.state;
  const dom = Nova.dom;
  const render = Nova.render;

  const byId =
    dom.byId ||
    function byId(id) {
      return document.getElementById(id);
    };

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value, fallback = "") {
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return fallback;
    return String(value);
  }

  function isFn(value) {
    return typeof value === "function";
  }

  function ensureState() {
    if (!Array.isArray(state.messages)) state.messages = [];
    if (typeof state.lastUserMessage !== "string") state.lastUserMessage = "";
    if (typeof state.isSending !== "boolean") state.isSending = false;
  }

  function escapeHtml(value) {
    return safeString(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDate(value) {
    const raw = safeString(value).trim();
    if (!raw) return "";

    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return "";

    try {
      return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_error) {
      return "";
    }
  }

  function roleLabel(role) {
    const normalized = safeString(role || "assistant").trim().toLowerCase();
    if (normalized === "user") return "You";
    if (normalized === "system") return "System";
    return "Nova";
  }

  function messageClass(role) {
    const normalized = safeString(role || "assistant").trim().toLowerCase();
    if (normalized === "user") return "message message-user";
    if (normalized === "system") return "message message-system";
    return "message message-assistant";
  }

  function getChatMessagesEl() {
    return byId("chatMessages");
  }

  function getEmptyStateEl() {
    return byId("emptyState");
  }

  function preserveEmptyState(container) {
    const empty = getEmptyStateEl();
    if (!container || !empty) return empty;

    if (empty.parentElement === container) {
      empty.remove();
    }

    return empty;
  }

  function splitIntoParagraphs(text) {
    return safeString(text)
      .replace(/\r\n/g, "\n")
      .split("\n");
  }

  function renderMessageBodyHtml(content) {
    const lines = splitIntoParagraphs(content);
    return lines
      .map((line) => {
        if (!line.trim()) {
          return `<div class="message-line"><br></div>`;
        }
        return `<div class="message-line">${escapeHtml(line)}</div>`;
      })
      .join("");
  }

  async function copyText(text, button) {
    const value = safeString(text);
    if (!value.trim()) return;

    const original = button ? button.textContent : "";

    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(value);
      } else {
        const helper = document.createElement("textarea");
        helper.value = value;
        helper.setAttribute("readonly", "true");
        helper.style.position = "fixed";
        helper.style.opacity = "0";
        helper.style.pointerEvents = "none";
        document.body.appendChild(helper);
        helper.focus();
        helper.select();
        document.execCommand("copy");
        helper.remove();
      }

      if (button) {
        button.textContent = "Copied";
        window.setTimeout(() => {
          button.textContent = original || "Copy";
        }, 1200);
      }
    } catch (_error) {
      if (button) {
        button.textContent = "Copy failed";
        window.setTimeout(() => {
          button.textContent = original || "Copy";
        }, 1200);
      }
    }
  }

  function getLastAssistantMessage() {
    const list = safeArray(state.messages);
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const item = list[i];
      if (safeString(item?.role).toLowerCase() === "assistant") {
        return item;
      }
    }
    return null;
  }

  async function regenerateLastAssistantReply(button) {
    if (state.isSending) return;

    const lastUserMessage = safeString(state.lastUserMessage).trim();
    if (!lastUserMessage) return;

    const list = safeArray(state.messages).slice();

    for (let i = list.length - 1; i >= 0; i -= 1) {
      const role = safeString(list[i]?.role).toLowerCase();
      if (role === "assistant" || role === "system") {
        list.splice(i, 1);
        break;
      }
    }

    state.messages = list;

    const original = button ? button.textContent : "";
    if (button) {
      button.disabled = true;
      button.textContent = "Regenerating...";
    }

    try {
      if (isFn(render.renderAll)) {
        render.renderAll();
      }

      if (isFn(render.sendMessage)) {
        await render.sendMessage({ regenerate: true, contentOverride: lastUserMessage });
      }
    } catch (_error) {
      // render.sendMessage already handles UI/system error fallback
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = original || "Regenerate";
      }
    }
  }

  function createMessageArticle(message, index) {
    const role = safeString(message?.role || "assistant").toLowerCase();
    const content = safeString(message?.content || "");
    const createdAt = safeString(message?.created_at || message?.createdAt || "");
    const isAssistant = role === "assistant";
    const article = document.createElement("article");

    article.className = messageClass(role);
    article.setAttribute("data-message-index", String(index));
    article.setAttribute("data-message-role", role);

    article.innerHTML = `
      <div class="message-head">
        <div class="message-role">${escapeHtml(roleLabel(role))}</div>
        <div class="message-time">${escapeHtml(formatDate(createdAt))}</div>
      </div>
      <div class="message-body">
        ${renderMessageBodyHtml(content)}
      </div>
      ${
        isAssistant
          ? `
        <div class="message-actions">
          <button
            type="button"
            class="message-action-btn"
            data-message-action="copy"
            data-message-index="${index}"
          >
            Copy
          </button>
          <button
            type="button"
            class="message-action-btn"
            data-message-action="regenerate"
            data-message-index="${index}"
          >
            Regenerate
          </button>
        </div>
      `
          : ""
      }
    `;

    return article;
  }

  function bindMessageActions(root) {
    if (!root) return;

    root.querySelectorAll("[data-message-action='copy']").forEach((button) => {
      if (button.dataset.novaBoundCopy === "true") return;
      button.dataset.novaBoundCopy = "true";

      button.addEventListener("click", async () => {
        const index = Number(button.getAttribute("data-message-index"));
        const item = safeArray(state.messages)[index];
        await copyText(item?.content || "", button);
      });
    });

    root.querySelectorAll("[data-message-action='regenerate']").forEach((button) => {
      if (button.dataset.novaBoundRegenerate === "true") return;
      button.dataset.novaBoundRegenerate = "true";

      button.addEventListener("click", async () => {
        const item = getLastAssistantMessage();
        if (!item) return;
        await regenerateLastAssistantReply(button);
      });
    });
  }

  function renderMessages() {
    ensureState();

    const container = getChatMessagesEl();
    if (!container) return;

    const emptyState = preserveEmptyState(container);
    const list = safeArray(state.messages);

    container.innerHTML = "";

    if (!list.length) {
      if (emptyState) {
        emptyState.classList.remove("hidden");
        container.appendChild(emptyState);
      }
      return;
    }

    list.forEach((message, index) => {
      const article = createMessageArticle(message, index);
      container.appendChild(article);
    });

    bindMessageActions(container);

    if (emptyState) {
      emptyState.classList.add("hidden");
    }

    container.scrollTop = container.scrollHeight;
  }

  messagesApi.renderMessages = renderMessages;
  messagesApi.copyText = copyText;
  messagesApi.regenerateLastAssistantReply = regenerateLastAssistantReply;
})();