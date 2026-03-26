(() => {
  "use strict";

  if (window.__novaRenderMessagesLoaded) return;
  window.__novaRenderMessagesLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.messages = Nova.messages || {};

  const API = {
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function parseJsonSafe(response) {
    const text = await response.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return {};
    }
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data.error || `GET failed: ${url}`);
    }
    return data;
  }

  function getStateBucket() {
    Nova.state = Nova.state || {};
    if (!Array.isArray(Nova.state.messages)) {
      Nova.state.messages = [];
    }
    if (typeof Nova.state.activeSessionId !== "string") {
      Nova.state.activeSessionId = "";
    }
    return Nova.state;
  }

  function normalizeMessages(payload) {
    const candidates = [
      payload?.messages,
      payload?.chat?.messages,
      payload?.session?.messages,
      payload?.data?.messages,
      payload?.items,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) return value;
    }

    return [];
  }

  function resolveRole(message) {
    const raw = String(
      message?.role ||
      message?.sender ||
      message?.type ||
      "assistant"
    ).toLowerCase().trim();

    if (raw.includes("user")) return "user";
    if (raw.includes("system")) return "system";
    return "assistant";
  }

  function resolveText(message) {
    const direct =
      message?.content ??
      message?.text ??
      message?.message ??
      message?.value ??
      "";

    if (typeof direct === "string") {
      return direct;
    }

    if (Array.isArray(direct)) {
      return direct
        .map((part) => {
          if (typeof part === "string") return part;
          if (part && typeof part.text === "string") return part.text;
          if (part && typeof part.content === "string") return part.content;
          return "";
        })
        .join("\n")
        .trim();
    }

    if (direct && typeof direct === "object") {
      if (typeof direct.text === "string") return direct.text;
      if (typeof direct.content === "string") return direct.content;
    }

    return String(direct || "").trim();
  }

  function resolveMessageId(message, index) {
    return String(
      message?.id ||
      message?.message_id ||
      message?.uuid ||
      `msg-${index}`
    ).trim();
  }

  function formatTimestamp(message) {
    const raw = String(
      message?.created_at ||
      message?.updated_at ||
      message?.timestamp ||
      message?.time ||
      ""
    ).trim();

    if (!raw) return "";

    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return "";

    return date.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function parseBlocks(text) {
    const source = String(text || "");
    const blocks = [];
    const regex = /```([\w-]*)\n?([\s\S]*?)```/g;

    let lastIndex = 0;
    let match;

    while ((match = regex.exec(source)) !== null) {
      const before = source.slice(lastIndex, match.index);
      if (before) {
        blocks.push({ type: "text", value: before });
      }

      blocks.push({
        type: "code",
        language: String(match[1] || "").trim(),
        value: String(match[2] || ""),
      });

      lastIndex = regex.lastIndex;
    }

    const after = source.slice(lastIndex);
    if (after) {
      blocks.push({ type: "text", value: after });
    }

    return blocks.length ? blocks : [{ type: "text", value: source }];
  }

  function renderInline(text) {
    return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");
  }

  function renderTextBlock(text) {
    const cleaned = String(text || "").replace(/\r\n/g, "\n");
    const paragraphs = cleaned
      .split(/\n{2,}/)
      .map((part) => part.trim())
      .filter(Boolean);

    if (!paragraphs.length) {
      return `<p></p>`;
    }

    return paragraphs
      .map((paragraph) => {
        const html = renderInline(paragraph).replace(/\n/g, "<br>");
        return `<p>${html}</p>`;
      })
      .join("");
  }

  function renderMessageBody(text) {
    const blocks = parseBlocks(text);

    return blocks
      .map((block) => {
        if (block.type === "code") {
          const lang = escapeHtml(block.language || "");
          const code = escapeHtml(block.value || "");
          const langTag = lang
            ? `<div class="code-lang">${lang}</div>`
            : "";
          return `
            <div class="message-code-block">
              ${langTag}
              <pre><code>${code}</code></pre>
            </div>
          `;
        }

        return renderTextBlock(block.value || "");
      })
      .join("");
  }

  function getLatestUserMessageIndex(messages) {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (resolveRole(messages[i]) === "user") {
        return i;
      }
    }
    return -1;
  }

  function renderEmptyState() {
    const chatMessages = byId("chatMessages");
    if (!chatMessages) return;

    chatMessages.innerHTML = `
      <div id="emptyState" class="empty-state">
        <div class="empty-state-card">
          <h1>Nova is ready</h1>
          <p>Ask anything, build something, or continue your latest session.</p>
        </div>
      </div>
    `;
  }

  function render() {
    const state = getStateBucket();
    const chatMessages = byId("chatMessages");
    if (!chatMessages) return;

    const messages = Array.isArray(state.messages) ? state.messages : [];
    if (!messages.length) {
      renderEmptyState();
      return;
    }

    const latestUserIndex = getLatestUserMessageIndex(messages);

    chatMessages.innerHTML = messages
      .map((message, index) => {
        const role = resolveRole(message);
        const text = resolveText(message);
        const messageId = resolveMessageId(message, index);
        const timestamp = formatTimestamp(message);
        const showRegenerate = role === "user" && index === latestUserIndex;

        return `
          <article class="message ${escapeHtml(role)}" data-message-id="${escapeHtml(messageId)}">
            <div class="bubble">
              <div class="message-body">${renderMessageBody(text)}</div>
              <div class="message-footer">
                <div class="message-role">${escapeHtml(role)}</div>
                ${timestamp ? `<div class="message-time">${escapeHtml(timestamp)}</div>` : ""}
              </div>
            </div>
            <div class="message-actions">
              <button
                class="icon-btn"
                type="button"
                data-copy-message="${escapeHtml(messageId)}"
                aria-label="Copy message"
                title="Copy message"
              >
                Copy
              </button>
              ${
                showRegenerate
                  ? `
                    <button
                      class="icon-btn"
                      type="button"
                      data-regenerate-from="${escapeHtml(messageId)}"
                      aria-label="Regenerate response"
                      title="Regenerate response"
                    >
                      Regenerate
                    </button>
                  `
                  : ""
              }
            </div>
          </article>
        `;
      })
      .join("");

    requestAnimationFrame(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  }

  async function loadSession(sessionId) {
    const id = String(sessionId || "").trim();
    const state = getStateBucket();

    if (!id) {
      state.activeSessionId = "";
      state.messages = [];
      render();
      return [];
    }

    const payload = await apiGet(API.getChat(id));
    state.activeSessionId = id;
    state.messages = normalizeMessages(payload);
    render();
    return state.messages;
  }

  async function refresh() {
    const state = getStateBucket();
    if (!state.activeSessionId) {
      render();
      return [];
    }

    return loadSession(state.activeSessionId);
  }

  async function copyMessage(messageId) {
    const id = String(messageId || "").trim();
    if (!id) return false;

    const state = getStateBucket();
    const messages = Array.isArray(state.messages) ? state.messages : [];
    const found = messages.find((message, index) => resolveMessageId(message, index) === id);
    if (!found) return false;

    const text = resolveText(found);
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      console.error("Nova copy failed:", error);
      return false;
    }
  }

  async function regenerateFromMessage(messageId) {
    const id = String(messageId || "").trim();
    if (!id) return false;

    const state = getStateBucket();
    const messages = Array.isArray(state.messages) ? state.messages : [];
    const targetIndex = messages.findIndex(
      (message, index) => resolveMessageId(message, index) === id
    );

    if (targetIndex < 0) return false;

    const targetMessage = messages[targetIndex];
    const prompt = resolveText(targetMessage).trim();
    if (!prompt) return false;

    const composerInput = byId("composerInput");
    if (composerInput) {
      composerInput.value = prompt;
      composerInput.focus();
    }

    if (Nova.chat && typeof Nova.chat.sendMessage === "function") {
      await Nova.chat.sendMessage({ regenerate: true, promptOverride: prompt });
      return true;
    }

    if (Nova.chat && typeof Nova.chat.regenerateLast === "function") {
      await Nova.chat.regenerateLast(prompt);
      return true;
    }

    console.warn("Nova regenerate: chat API not available.");
    return false;
  }

  function bindEvents() {
    const chatMessages = byId("chatMessages");
    if (!chatMessages || chatMessages.__novaMessagesBound) return;

    chatMessages.__novaMessagesBound = true;

    chatMessages.addEventListener("click", async (event) => {
      const copyBtn = event.target.closest("[data-copy-message]");
      const regenBtn = event.target.closest("[data-regenerate-from]");

      try {
        if (copyBtn) {
          event.preventDefault();
          const ok = await copyMessage(copyBtn.getAttribute("data-copy-message"));
          if (ok) {
            const previous = copyBtn.textContent;
            copyBtn.textContent = "Copied";
            setTimeout(() => {
              copyBtn.textContent = previous || "Copy";
            }, 1100);
          }
          return;
        }

        if (regenBtn) {
          event.preventDefault();
          const previous = regenBtn.textContent;
          regenBtn.textContent = "Working...";
          regenBtn.disabled = true;

          try {
            await regenerateFromMessage(regenBtn.getAttribute("data-regenerate-from"));
          } finally {
            regenBtn.textContent = previous || "Regenerate";
            regenBtn.disabled = false;
          }
        }
      } catch (error) {
        console.error("Nova message action failed:", error);
      }
    });
  }

  async function bootstrap() {
    bindEvents();
    render();
    return true;
  }

  Nova.messages.render = render;
  Nova.messages.refresh = refresh;
  Nova.messages.loadSession = loadSession;
  Nova.messages.copyMessage = copyMessage;
  Nova.messages.regenerateFromMessage = regenerateFromMessage;
  Nova.messages.bootstrap = bootstrap;

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        bootstrap().catch((error) => {
          console.error("Nova messages DOM bootstrap failed:", error);
        });
      },
      { once: true }
    );
  } else {
    bootstrap().catch((error) => {
      console.error("Nova messages immediate bootstrap failed:", error);
    });
  }
})();