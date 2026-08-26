
(function() {
  'use strict';

  function getDesktopMessageBox() {
    var box = document.getElementById("chat");
    if (box) return box;
    var host = document.querySelector(".desktop-chat-container") || document.querySelector("main") || document.body;
    box = document.createElement("div");
    box.id = "chat";
    box.className = "messages chat-messages desktop-rescue-messages";
    box.style.minHeight = "320px";
    box.style.maxHeight = "60vh";
    box.style.overflowY = "auto";
    box.style.padding = "16px";
    box.style.margin = "12px 0";
    box.style.borderRadius = "18px";
    box.style.background = "rgba(255,255,255,.04)";
    host.appendChild(box);
    return box;
  }

  function makeSourceCards(msg) {
    try {
      var meta = msg && msg.meta && typeof msg.meta === "object" ? msg.meta : {};
      var sources = Array.isArray(meta.sources) ? meta.sources : [];
      if (!sources.length && Array.isArray(msg.sources)) sources = msg.sources;
      if (!sources.length) return null;

      var wrap = document.createElement("div");
      wrap.className = "nova-source-cards nova-desktop-global-source-cards";
      wrap.style.marginTop = "10px";
      wrap.style.display = "grid";
      wrap.style.gap = "8px";

      sources.slice(0, 8).forEach(function(src, index) {
        src = src || {};
        var url = src.url || src.file_url || "#";
        var title = src.title || src.name || "Source " + (index+1);
        var snippet = src.text || src.description || "";

        var card = document.createElement(url ? "a" : "div");
        card.className = "nova-source-card nova-desktop-global-source-card";
        card.style.display = "block";
        card.style.padding = "10px 12px";
        card.style.border = "1px solid rgba(255,255,255,.14)";
        card.style.borderRadius = "12px";
        card.style.background = "rgba(255,255,255,.06)";
        card.style.color = "inherit";
        card.style.textDecoration = "none";
        if (url) { card.href = url; card.target = "_blank"; card.rel = "noopener noreferrer"; }

        var titleEl = document.createElement("div");
        titleEl.className = "nova-source-title";
        titleEl.textContent = title;
        titleEl.style.fontWeight = "700";
        titleEl.style.fontSize = "13px";
        card.appendChild(titleEl);

        if (snippet) {
          var snippetEl = document.createElement("div");
          snippetEl.className = "nova-source-snippet";
          snippetEl.textContent = snippet;
          snippetEl.style.marginTop = "4px";
          snippetEl.style.opacity = ".78";
          snippetEl.style.fontSize = "12px";
          snippetEl.style.lineHeight = "1.35";
          card.appendChild(snippetEl);
        }

        wrap.appendChild(card);
      });

      return wrap;
    } catch (err) { console.warn("[Nova Desktop Final Source Cards] render failed", err); return null; }
  }

window.novaDesktopFinalSourceCardsReady = true;
console.log("[Nova Desktop Final Source Cards] ready");
})();

(function () {
  "use strict";

  const MARKER = "NOVA_DESKTOP_RESCUE_FETCH_MISSING_SESSION_20260611";

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[ch] || ch;
    });
  }

function getActiveSessionId() {
  try {
    const sidInput = document.getElementById("sid");
    const sidValue = sidInput && sidInput.value ? sidInput.value : "";

    return String(
      (typeof window.getSessionId === "function" && window.getSessionId()) ||
      sidValue ||
      localStorage.getItem("nova_session_id") ||
      localStorage.getItem("nova_active_session_id") ||
      sessionStorage.getItem("nova_session_id") ||
      sessionStorage.getItem("nova_active_session_id") ||
      window.NovaDesktopActiveSessionId ||
      window.novaDesktopActiveSessionId ||
      window.currentSessionId ||
      window.activeSessionId ||
      localStorage.getItem("active_session_id") ||
      ""
    ).trim();
  } catch (_) {
    return "";
  }
}

  function getRescueBox() {
    let box = document.getElementById("chat");
    if (box) return box;

    const host =
      document.querySelector(".desktop-chat-container") ||
      document.querySelector("#desktopChatMessages") ||
      document.querySelector("main") ||
      document.body;

    box = document.createElement("div");
    box.id = "chat";
    box.className = "messages chat-messages desktop-rescue-messages";
    box.style.minHeight = "320px";
    box.style.maxHeight = "60vh";
    box.style.overflowY = "auto";
    box.style.padding = "16px";
    box.style.margin = "12px 0";
    box.style.borderRadius = "18px";
    box.style.background = "rgba(255,255,255,.04)";
    host.appendChild(box);
    return box;
  }

  function attachmentName(attachment) {
    if (!attachment || typeof attachment !== "object") return "";
    return String(
      attachment.original_filename ||
      attachment.filename ||
      attachment.name ||
      attachment.stored_name ||
      "attachment"
    );
  }

  function sourceCardsHtml(message) {
    try {
      const meta = message && typeof message === "object" ? (message.meta || {}) : {};
      const sources = Array.isArray(meta.sources) ? meta.sources : [];
      if (!sources.length) return "";

      return [
        '<div class="nova-source-cards" style="margin-top:10px;display:grid;gap:8px;">',
        sources.map(function (src) {
          const title = esc(src.title || src.source || src.url || "Source");
          const url = esc(src.url || "");
          const snippet = esc(src.snippet || "");
          const source = esc(src.source || "");

const titleHtml = url
  ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + title + '</a>'
  : title;


          return [
            '<div class="nova-source-card" style="padding:10px;border-radius:12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);">',
            '<div style="font-weight:700;">' + titleHtml + '</div>',
            source ? '<div style="opacity:.7;font-size:12px;margin-top:2px;">' + source + '</div>' : '',
            snippet ? '<div style="opacity:.85;font-size:13px;margin-top:6px;">' + snippet + '</div>' : '',
            '</div>'
          ].join("");
        }).join(""),
        '</div>'
      ].join("");
    } catch (_) {
      return "";
    }
  }

  function renderMessagesDirect(session) {
    const box = getRescueBox();
    const messages = Array.isArray(session && session.messages) ? session.messages : [];

    const existingCount = box.querySelectorAll("[data-message-id]").length;
    const sessionId = session && (session.id || session.session_id || session.client_session_id);
    const activeId = getActiveSessionId();

// Skip only stale/non-active session payloads.
if (
  sessionId &&
  activeId &&
  sessionId !== activeId
) {
  console.log("[Nova Desktop Rescue] skipped non-active direct render", {
    session_id: sessionId,
    active_id: activeId,
    existing: existingCount,
    incoming: messages.length
  });
  return existingCount;
}

if (!messages.length) {

  if (
    session &&
    session.meta &&
    session.meta.onboarding &&
    typeof window.renderDesktopOnboarding === "function"
  ) {
    window.renderDesktopOnboarding(session);
    return 0;
  }

  box.innerHTML =
    '<div class="session-placeholder">No messages in this session.</div>';

  return 0;
}

box.innerHTML = "";

messages.forEach(function (message) {

  const role = esc(message.role || "message");
  const id = esc(message.id || "");

  const wrapper = document.createElement("div");
  wrapper.className = "chat-message message " + role;
  wrapper.setAttribute("data-message-id", id);
  wrapper.style.cssText =
    "padding:14px;margin:10px 0;border-radius:14px;background:rgba(255,255,255,.06);";

  const header = document.createElement("div");
  header.style.cssText = "opacity:.65;font-size:12px;margin-bottom:6px;";
  header.textContent = role + (id ? " Â· " + id : "");

  const textDiv = document.createElement("div");
  textDiv.style.whiteSpace = "pre-wrap";
textDiv.textContent = (
  message.text ||
  (message.assistant_message && message.assistant_message.text) ||
  ""
);

  wrapper.appendChild(header);
  wrapper.appendChild(textDiv);

  const imgSrc = message.imageUrl || message.image;
  if (imgSrc) {
    const img = document.createElement("img");
    img.src = imgSrc;
    img.style.cssText = "max-width:100%;border-radius:14px;display:block;margin-top:10px;";
    wrapper.appendChild(img);
  }

  const attachments = Array.isArray(message.attachments) ? message.attachments : [];
  if (attachments.length) {
    const attach = document.createElement("div");
    attach.style.cssText = "margin-top:10px;opacity:.75;font-size:12px;";
    attach.textContent = "Attachments: " + attachments.join(", ");
    wrapper.appendChild(attach);
  }

  box.appendChild(wrapper);
});

    box.scrollTop = box.scrollHeight;
    return messages.length;
  }

  async function fetchAndRenderSession(sessionId) {
    if (!sessionId) return false;

    const response = await fetch("/api/sessions/" + encodeURIComponent(sessionId), {
      headers: { "Accept": "application/json" }
    });

const raw = await response.text();

let data = null;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.warn("Non-JSON response from server:", raw);
  data = null;
}

    if (!response.ok || !data || !data.ok || !data.session) {
      console.warn("[Nova Desktop Rescue] session detail fallback failed", sessionId, data);
      return false;
    }

    const rendered = renderMessagesDirect(data.session);
    console.log("[Nova Desktop Rescue] fetched missing session and rendered messages", {
      session_id: sessionId,
      rendered: rendered
    });
    return rendered > 0;
  }


  function installWrapper() {
    if (window.__novaDesktopRescueFetchMissingSessionInstalled) return;
    window.__novaDesktopRescueFetchMissingSessionInstalled = true;

    const original =
      typeof window.renderDesktopChatMessagesRescue === "function"
        ? window.renderDesktopChatMessagesRescue
        : null;

    console.log("[Nova Desktop Rescue] fetch missing session fallback ready", MARKER);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installWrapper);
  } else {
    installWrapper();
  }

})();
(function () {
  "use strict";

  var MARKER = "NOVA_DESKTOP_ACTIVE_SESSION_404_RECOVERY_20260612";

  function log() {
    try {
      console.log.apply(console, ["[Nova Desktop Active Session Recovery]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function getStoredSessionId() {
    try {
      return (
        localStorage.getItem("nova_active_session_id") ||
        localStorage.getItem("nova_session_id") ||
        sessionStorage.getItem("nova_active_session_id") ||
        sessionStorage.getItem("nova_session_id") ||
        ""
      );
    } catch (_) {
      return "";
    }
  }

  function storeSessionId(sessionId) {
    if (!sessionId) return;

    try {
      localStorage.setItem("nova_active_session_id", sessionId);
      localStorage.setItem("nova_session_id", sessionId);
      sessionStorage.setItem("nova_active_session_id", sessionId);
      sessionStorage.setItem("nova_session_id", sessionId);
    } catch (_) {}

    try {
      window.novaCurrentSessionId = sessionId;
      window.currentSessionId = sessionId;
      window.activeSessionId = sessionId;
    } catch (_) {}
  }

  function normalizeSessionPayload(data) {
    if (!data || typeof data !== "object") return null;

    if (data.session && typeof data.session === "object") {
      return data.session;
    }

    if (data.id || Array.isArray(data.messages)) {
      return data;
    }

    return null;
  }

  function ensureManager(session) {
    if (!session || typeof session !== "object") return null;

    try {
      if (!window.NovaCurrentSessionManager || typeof window.NovaCurrentSessionManager !== "object") {
        window.NovaCurrentSessionManager = {};
      }

      if (!Array.isArray(session.messages)) {
        session.messages = [];
      }

      window.NovaCurrentSessionManager.currentSession = session;
      window.NovaCurrentSessionManager.activeSessionId = session.id || session.session_id || getStoredSessionId();

      return window.NovaCurrentSessionManager;
    } catch (err) {
      console.warn("[Nova Desktop Active Session Recovery] manager hydrate failed", err);
      return null;
    }
  }

function renderSession(session) {
    if (!session || !Array.isArray(session.messages)) return false;

    console.log(
        "[Nova RenderSession] rendering",
        session.id
    );

if (
    session.messages.length === 0
) {
    console.log(
        "[Nova RenderSession] empty session fallback"
    );

    if (typeof window.renderDesktopOnboarding === "function") {
        window.renderDesktopOnboarding(session);
    } else if (
        typeof window.renderDesktopChatMessagesRescue === "function"
    ) {
        window.renderDesktopChatMessagesRescue([
            {
                role: "assistant",
                content:
                    "Welcome to Nova.\n\nStart a conversation and your workspace will appear here."
            }
        ]);
    }

    return true;
}

    try {
        if (
            typeof window.renderDesktopChatMessages === "function"
        ) {
            window.renderDesktopChatMessages(
                session.messages
            );
            return true;
        }
    } catch (err) {
        console.warn(
            "[Nova RenderSession] primary render failed",
            err
        );
    }

    try {
        if (
            typeof window.renderDesktopChatMessagesRescue === "function"
        ) {
            window.renderDesktopChatMessagesRescue(
                session.messages
            );
            return true;
        }
    } catch (err) {
        console.warn(
            "[Nova RenderSession] rescue render failed",
            err
        );
    }

    console.warn(
        "[Nova RenderSession] all renderers failed"
    );

    return false;
}

function startSSE() {
  const source = new EventSource("/api/events/stream");

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data || "{}");

      if (data.type === "sessions:updated") {
        window.__novaEvents.emit("sessions:updated");
      }

    } catch (e) {}
  };

  source.onerror = () => {
    console.warn("[SSE] disconnected, retrying...");
  };
}

function wrapSessionMutation(fn) {
  return async function (...args) {
    const result = await fn.apply(this, args);

    // always notify AFTER successful mutation
    window.__novaEvents.emit("sessions:updated");
    window.__novaChannel?.postMessage({ type: "sessions:updated" });

    return result;
  };
}

function notifySessionsChanged() {
  window.__novaEvents.emit("sessions:updated");
  window.__novaChannel?.postMessage({ type: "sessions:updated" });
}

  async function fetchSession(sessionId) {
    if (!sessionId) return null;

    var response = await fetch("/api/sessions/" + encodeURIComponent(sessionId), {
      method: "GET",
      credentials: "same-origin",
      headers: {
        "Accept": "application/json"
      }
    });

const raw = await response.text();

var data = null;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.warn("Non-JSON response:", raw);
  data = null;
}

if (response.status === 404 && data && data.active_session_id && data.active_session_id !== sessionId) {
  log("stale session recovered", sessionId, "=>", data.active_session_id);
  storeSessionId(data.active_session_id);
  return fetchSession(data.active_session_id);
}

    if (!response.ok) {
      log("session fetch failed", response.status, data);
      return null;
    }

var session = normalizeSessionPayload(data);

if (session) {
window.__NOVA_ACTIVE_SESSION = session;
    session.id = session.id || session.session_id || sessionId;

    storeSessionId(session.id);

    ensureManager(session);

     if (
        Array.isArray(session.messages) &&
        session.messages.length === 0 &&
        session.meta &&
        session.meta.onboarding &&
        typeof window.renderDesktopOnboarding === "function"
    ) {
        window.renderDesktopOnboarding(session);
    } else {
        renderSession(session);
    }

      log(
        "hydrated session",
        session.id,
        "messages:",
        Array.isArray(session.messages) ? session.messages.length : 0
      );
    }
    return session;
  }

  async function recoverDesktopSession() {
    var sessionId = getStoredSessionId();

    if (!sessionId) {
      log("no stored session id");
      return;
    }

    await fetchSession(sessionId);
  }

  window.novaDesktopRecoverActiveSession_20260612 = recoverDesktopSession;
window.NovaDesktopFetchSession = fetchSession;

  setTimeout(recoverDesktopSession, 250);

  log("ready", MARKER);
})();

(function () {
  "use strict";
  var MARKER = "NOVA_FORCE_DESKTOP_SOURCE_CARDS_DOM_20260612";

  function log() {
    try {
      console.log.apply(console, ["[Nova Force Desktop Source Cards DOM]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function getMessages() {
    try {
      var session = window.NovaCurrentSessionManager && window.NovaCurrentSessionManager.currentSession;
      if (session && Array.isArray(session.messages)) return session.messages;
    } catch (_) {}

    try {
      if (Array.isArray(window.desktopMessages)) return window.desktopMessages;
    } catch (_) {}

    try {
      if (Array.isArray(window.messages)) return window.messages;
    } catch (_) {}

    return [];
  }

  function normalizeSources(msg) {
    if (!msg || typeof msg !== "object") return [];

    var meta = msg.meta && typeof msg.meta === "object" ? msg.meta : {};
    var sources = [];

    if (Array.isArray(meta.sources)) sources = meta.sources;
    else if (Array.isArray(meta.web_sources)) sources = meta.web_sources;
    else if (Array.isArray(meta.citations)) sources = meta.citations;
    else if (Array.isArray(msg.sources)) sources = msg.sources;

    return sources.filter(function (src) {
      if (!src) return false;
      if (typeof src === "string") return !!src.trim();
      if (typeof src === "object") return !!(src.url || src.href || src.link || src.title || src.name);
      return false;
    });
  }

  function sourceTitle(src, index) {
    if (typeof src === "string") return src;
    return (
      src.title ||
      src.name ||
      src.source ||
      src.domain ||
      src.url ||
      src.href ||
      src.link ||
      ("Source " + (index + 1))
    );
  }

  function sourceUrl(src) {
    if (typeof src === "string") {
      return /^https?:\/\//i.test(src) ? src : "";
    }

    return src.url || src.href || src.link || "";
  }

  function hostForUrl(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch (_) {
      return "";
    }
  }

  function escapeText(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function makeCards(msg) {
    var sources = normalizeSources(msg);
    if (!sources.length) return null;

    var wrap = document.createElement("div");
    wrap.className = "nova-source-cards";
    wrap.setAttribute("data-source-card", "true");
    wrap.setAttribute("data-nova-forced-source-cards", "true");

    sources.slice(0, 8).forEach(function (src, index) {
      var title = sourceTitle(src, index);
      var url = sourceUrl(src);
      var host = hostForUrl(url);

      var card = document.createElement(url ? "a" : "div");
      card.className = "nova-source-card";
      card.setAttribute("data-source-card", "true");

      if (url) {
        card.href = url;
        card.target = "_blank";
        card.rel = "noopener noreferrer";
      }

      card.style.display = "block";
      card.style.margin = "8px 0 0";
      card.style.padding = "10px 12px";
      card.style.borderRadius = "12px";
      card.style.border = "1px solid rgba(255,255,255,0.14)";
      card.style.background = "rgba(255,255,255,0.06)";
      card.style.textDecoration = "none";
      card.style.color = "inherit";

      card.innerHTML =
        '<div style="font-size:12px;opacity:.72;margin-bottom:3px;">Source' +
        (host ? " Â· " + escapeText(host) : "") +
        '</div>' +
        '<div style="font-size:14px;font-weight:650;line-height:1.25;">' +
        escapeText(title) +
        '</div>';

      wrap.appendChild(card);
    });

    return wrap;
  }

  function findMessageNodes() {
    return Array.from(document.querySelectorAll(
      ".desktop-message, .message, .chat-message, [data-message-id], [data-role='assistant'], .assistant-message"
    ));
  }

  function findAssistantNodes() {
    return findMessageNodes().filter(function (node) {
      var text = (node.className || "") + " " + Array.from(node.attributes || []).map(function (a) {
        return a.name + "=" + a.value;
      }).join(" ");

      return /assistant/i.test(text) || node.getAttribute("data-role") === "assistant";
    });
  }

  function fallbackContainer() {
    var box =
      document.querySelector("#chat") ||
      document.querySelector("#desktopChatMessages") ||
      document.querySelector(".desktop-chat-messages") ||
      document.querySelector(".desktop-chat-container") ||
      document.querySelector("main") ||
      document.body;

    return box;
  }

  function renderForcedSourceCards() {
    var messages = getMessages();
    var assistantMessages = messages.filter(function (m) {
      return m && m.role === "assistant" && normalizeSources(m).length;
    });

    document.querySelectorAll("[data-nova-forced-source-cards='true']").forEach(function (node) {
      node.remove();
    });

if (!assistantMessages.length) {
  if (window.NOVA_DEBUG_SOURCE_CARDS) {
    log("no assistant messages with sources");
  }
  return 0;
}

    var assistantNodes = findAssistantNodes();
    var rendered = 0;

    assistantMessages.forEach(function (msg, index) {
      var cards = makeCards(msg);
      if (!cards) return;

var target = assistantNodes[index];

if (!target || target === document.body || !target.appendChild) {
  return;
}

if (target.closest && target.closest(".memory-section")) {
  return;
}

if (target.querySelector("[data-nova-forced-source-cards='true']")) {
  return;
}

target.appendChild(cards);

      rendered += 1;
    });

    log("rendered source card groups:", rendered);
    return rendered;
  }

  function wrapRenderFunction(name) {
    try {
      var original = window[name];
      if (typeof original !== "function" || original.__novaSourceCardWrapped) return;

      var wrapped = function () {
        var result = original.apply(this, arguments);
        setTimeout(renderForcedSourceCards, 50);
        setTimeout(renderForcedSourceCards, 250);
        return result;
      };

      wrapped.__novaSourceCardWrapped = true;
      window[name] = wrapped;
      log("wrapped", name);
    } catch (err) {
      console.warn("[Nova Force Desktop Source Cards DOM] wrap failed", name, err);
    }
  }

  window.novaForceDesktopSourceCardsDOM_20260612 = renderForcedSourceCards;


wrapRenderFunction("renderDesktopChatMessages", {
  deferSourceCards: true
});

  setTimeout(renderForcedSourceCards, 500);
  setTimeout(renderForcedSourceCards, 1500);
document.addEventListener("nova:message:rendered", renderForcedSourceCards);

  log("ready", MARKER);
})();
(function () {
  "use strict";

  var MARKER = "NOVA_FORCE_DESKTOP_SOURCE_CARDS_DEDUPE_20260612";

  function log() {
    try {
      console.log.apply(console, ["[Nova Source Card Dedupe]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function messageKey(msg, index) {
    if (!msg || typeof msg !== "object") return "unknown_" + index;
    return String(msg.id || msg.message_id || msg.created_at || msg.text || ("assistant_" + index));
  }

  function normalizeSources(msg) {
    if (!msg || typeof msg !== "object") return [];

    var meta = msg.meta && typeof msg.meta === "object" ? msg.meta : {};
    var sources = [];

    if (Array.isArray(meta.sources)) sources = meta.sources;
    else if (Array.isArray(meta.web_sources)) sources = meta.web_sources;
    else if (Array.isArray(meta.citations)) sources = meta.citations;
    else if (Array.isArray(msg.sources)) sources = msg.sources;

    return sources.filter(function (src) {
      if (!src) return false;
      if (typeof src === "string") return !!src.trim();
      if (typeof src === "object") return !!(src.url || src.href || src.link || src.title || src.name);
      return false;
    });
  }

  function getMessages() {
    try {
      var session = window.NovaCurrentSessionManager && window.NovaCurrentSessionManager.currentSession;
      if (session && Array.isArray(session.messages)) return session.messages;
    } catch (_) {}

    return [];
  }

  function cleanupDuplicates() {
    var seen = {};

    Array.from(document.querySelectorAll("[data-nova-forced-source-cards='true']")).forEach(function (node) {
      var key = node.getAttribute("data-nova-source-message-key") || "";

      if (!key) {
        node.remove();
        return;
      }

      if (seen[key]) {
        node.remove();
        return;
      }

      seen[key] = true;
    });
  }

  function patchExistingRenderer() {
    if (typeof window.novaForceDesktopSourceCardsDOM_20260612 !== "function") {
      return false;
    }

    if (window.novaForceDesktopSourceCardsDOM_20260612.__novaDedupeWrapped) {
      return true;
    }

    var original = window.novaForceDesktopSourceCardsDOM_20260612;

    var wrapped = function () {
      var messages = getMessages();
      var assistantWithSources = messages.filter(function (m) {
        return m && m.role === "assistant" && normalizeSources(m).length;
      });

      var beforeKeys = {};
      Array.from(document.querySelectorAll("[data-nova-forced-source-cards='true']")).forEach(function (node) {
        var key = node.getAttribute("data-nova-source-message-key") || "";
        if (key) beforeKeys[key] = true;
      });

      var result = original.apply(this, arguments);

      Array.from(document.querySelectorAll("[data-nova-forced-source-cards='true']")).forEach(function (node, i) {
        var existing = node.getAttribute("data-nova-source-message-key");
        if (existing) return;

        var msg = assistantWithSources[i] || assistantWithSources[assistantWithSources.length - 1];
        node.setAttribute("data-nova-source-message-key", messageKey(msg, i));
      });

      cleanupDuplicates();

      return result;
    };

    wrapped.__novaDedupeWrapped = true;
    window.novaForceDesktopSourceCardsDOM_20260612 = wrapped;

    log("wrapped forced source card renderer", MARKER);
    return true;
  }

  function boot() {
    if (!patchExistingRenderer()) {
      setTimeout(boot, 250);
      return;
    }

    try {
      window.novaForceDesktopSourceCardsDOM_20260612();
    } catch (_) {}

    cleanupDuplicates();
  }

  boot();
})();
(function () {
  "use strict";

  var MARKER = "NOVA_DESKTOP_LATEST_ONLY_SOURCE_CARDS_20260612";

  function log() {
    try {
      console.log.apply(console, ["[Nova Latest Source Cards Only]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function hasSources(msg) {
    if (!msg || msg.role !== "assistant") return false;

    var meta = msg.meta && typeof msg.meta === "object" ? msg.meta : {};

    return !!(
      (Array.isArray(meta.sources) && meta.sources.length) ||
      (Array.isArray(meta.web_sources) && meta.web_sources.length) ||
      (Array.isArray(meta.citations) && meta.citations.length) ||
      (Array.isArray(msg.sources) && msg.sources.length)
    );
  }

  function getLatestAssistantWithSources() {
    try {
      var session = window.NovaCurrentSessionManager && window.NovaCurrentSessionManager.currentSession;
      var messages = session && Array.isArray(session.messages) ? session.messages : [];

      for (var i = messages.length - 1; i >= 0; i -= 1) {
        if (hasSources(messages[i])) return messages[i];
      }
    } catch (_) {}

    return null;
  }

  function removeOlderSourceGroups() {
    var latest = getLatestAssistantWithSources();
    var latestKey = latest ? String(latest.id || latest.message_id || latest.created_at || latest.text || "") : "";

    var groups = Array.from(document.querySelectorAll("[data-nova-forced-source-cards='true'], .nova-source-cards"));

    if (!latestKey) {
      groups.forEach(function (node) {
        node.remove();
      });
      return;
    }

    groups.forEach(function (node, index) {
      var key = node.getAttribute("data-nova-source-message-key") || "";

      if (!key && index === groups.length - 1) {
        node.setAttribute("data-nova-source-message-key", latestKey);
        return;
      }

      if (key !== latestKey) {
        node.remove();
      }
    });

    var seenLatest = false;

    Array.from(document.querySelectorAll("[data-nova-forced-source-cards='true'], .nova-source-cards")).forEach(function (node) {
      var key = node.getAttribute("data-nova-source-message-key") || "";

      if (key !== latestKey) {
        node.remove();
        return;
      }

      if (seenLatest) {
        node.remove();
        return;
      }

      seenLatest = true;
    });
  }

  function wrapLatestOnly() {
    if (typeof window.novaForceDesktopSourceCardsDOM_20260612 !== "function") {
      setTimeout(wrapLatestOnly, 250);
      return;
    }

    if (window.novaForceDesktopSourceCardsDOM_20260612.__novaLatestOnlyWrapped) {
      return;
    }

    var original = window.novaForceDesktopSourceCardsDOM_20260612;

    var wrapped = function () {
      var result = original.apply(this, arguments);
      removeOlderSourceGroups();
      setTimeout(removeOlderSourceGroups, 50);
      setTimeout(removeOlderSourceGroups, 200);
      return result;
    };

    wrapped.__novaLatestOnlyWrapped = true;
    wrapped.__novaDedupeWrapped = true;

    window.novaForceDesktopSourceCardsDOM_20260612 = wrapped;

    removeOlderSourceGroups();
    log("ready", MARKER);
  }

  wrapLatestOnly();

})();
(function () {
  "use strict";

  var MARKER = "NOVA_DESKTOP_SOURCE_CARD_OBSERVER_PRUNE_20260612";
  var pruneQueued = false;

  function log() {
    try {
      console.log.apply(console, ["[Nova Source Card Observer Prune]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function getGroups() {
    try {
      return Array.from(
        document.querySelectorAll("[data-nova-forced-source-cards='true'], .nova-source-cards")
      ).filter(function (node) {
        return node && node.parentNode;
      });
    } catch (_) {
      return [];
    }
  }

  function pruneNow() {
    pruneQueued = false;

    try {
      var groups = getGroups();

      if (groups.length <= 1) {
        return;
      }

      // Keep the latest group in document order. Remove every older group.
      groups.slice(0, -1).forEach(function (node) {
        try {
          node.remove();
        } catch (_) {}
      });
    } catch (err) {
      console.warn("[Nova Source Card Observer Prune] prune failed", err);
    }
  }

  function queuePrune() {
    if (pruneQueued) {
      return;
    }

    pruneQueued = true;

    try {
      requestAnimationFrame(pruneNow);
    } catch (_) {
      setTimeout(pruneNow, 0);
    }
  }

  function installObserver() {
    try {
      pruneNow();
      setTimeout(pruneNow, 25);
      setTimeout(pruneNow, 100);
      setTimeout(pruneNow, 250);
      setTimeout(pruneNow, 750);

      var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i += 1) {
          var mutation = mutations[i];

          if (!mutation.addedNodes || !mutation.addedNodes.length) {
            continue;
          }

          for (var j = 0; j < mutation.addedNodes.length; j += 1) {
            var node = mutation.addedNodes[j];

            if (!node || node.nodeType !== 1) {
              continue;
            }

            if (
              (node.matches && (
                node.matches("[data-nova-forced-source-cards='true']") ||
                node.matches(".nova-source-cards") ||
                node.matches(".nova-source-card")
              )) ||
              (node.querySelector && (
                node.querySelector("[data-nova-forced-source-cards='true']") ||
                node.querySelector(".nova-source-cards") ||
                node.querySelector(".nova-source-card")
              ))
            ) {
              queuePrune();
              return;
            }
          }
        }
      });

      observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
      });

      window.__novaDesktopSourceCardObserverPrune20260612 = {
        marker: MARKER,
        pruneNow: pruneNow,
        observer: observer
      };

      log("ready", MARKER);
    } catch (err) {
      console.warn("[Nova Source Card Observer Prune] observer install failed", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installObserver, { once: true });
  } else {
    installObserver();
  }

})();

(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function aliasId(realId, aliasIdValue) {
    var real = $(realId);
    if (!real || $(aliasIdValue)) return;
    try {
      real.setAttribute("data-nova-compat-alias", aliasIdValue);
    } catch (_) {}
  }

  function installCompatAliases() {
    aliasId("openSessionsBtn", "desktopSessionsButton");
    aliasId("openMemoryBtn", "desktopMemoryButton");
    aliasId("input", "desktopChatInput");
    aliasId("sendBtn", "desktopSendButton");

    if (typeof window.NovaOpenDesktopSessions !== "function") {
      window.NovaOpenDesktopSessions = function () {
        if (typeof window.NovaDesktopOpenSessionsRescue === "function") {
          return window.NovaDesktopOpenSessionsRescue();
        }

        var button = $("openSessionsBtn");
        if (button) return button.click();
      };
    }

// NOVA_LEGACY_MEMORY_ALIAS_DISABLED

    window.NovaDesktopCompatAliasesReady = true;
  }

  function boot() {
    installCompatAliases();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  console.log("[Nova Desktop Compat Aliases] ready");

})();
(function () {
  "use strict";

  if (window.__novaDesktopGetElementByIdCompatInstalled) return;
  window.__novaDesktopGetElementByIdCompatInstalled = true;

  var originalGetElementById = Document.prototype.getElementById;

  var aliasMap = {
    desktopSessionsButton: "openSessionsBtn",
    desktopMemoryButton: "openMemoryBtn",
    desktopChatInput: "input",
    desktopSendButton: "sendBtn"
  };

  Document.prototype.getElementById = function (id) {
    var found = originalGetElementById.call(this, id);
    if (found) return found;

    var realId = aliasMap[id];
    if (realId) {
      return originalGetElementById.call(this, realId);
    }

    return null;
  };

  console.log("[Nova Desktop getElementById Compat] ready");
})();
