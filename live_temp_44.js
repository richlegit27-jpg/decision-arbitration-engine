
(function () {
  "use strict";

  if (window.__NOVA_DESKTOP_SESSION_OPEN_FINAL_20260621__) return;
  window.__NOVA_DESKTOP_SESSION_OPEN_FINAL_20260621__ = true;

  var MARKER = "NOVA_DESKTOP_SESSION_OPEN_FINAL_20260621";

  function log() {
    try {
      console.log.apply(console, ["[Nova Session Open Final]"].concat([].slice.call(arguments)));
    } catch (_) {}
  }

  function setStatusSafe(text) {
    try {
      if (typeof window.setStatus === "function") {
        window.setStatus(text);
        return;
      }
    } catch (_) {}

    var status = document.getElementById("status");
    if (status) status.textContent = text;
  }

  function cleanSid(value) {
    var sid = String(value || "").trim();

    if (!sid) return "";
    if (sid === "[object HTMLInputElement]") return "";
    if (sid === "undefined" || sid === "null") return "";

    return sid;
  }

  function setActiveSessionId(sid) {
    sid = cleanSid(sid);
    if (!sid) return "";

    try {
      localStorage.setItem("nova.session_id", sid);
      localStorage.setItem("nova_active_session_id", sid);
      localStorage.setItem("nova_session_id", sid);
      sessionStorage.setItem("nova_active_session_id", sid);
    } catch (_) {}

    window.__NOVA_ACTIVE_SESSION_ID = sid;

    try {
      if (typeof window.setSessionId === "function") {
        window.setSessionId(sid);
      }
    } catch (_) {}

    return sid;
  }

  function getSessionIdFromElement(el) {
    if (!el) return "";

    var node = el.closest
      ? el.closest("[data-sid], [data-session-id], [data-id], .desktop-session-item, .session-item, a")
      : el;

    if (!node) return "";

    var sid =
      node.getAttribute("data-sid") ||
      node.getAttribute("data-session-id") ||
      node.getAttribute("data-id") ||
      node.dataset?.sid ||
      node.dataset?.sessionId ||
      node.dataset?.id ||
      "";

    if (!sid) {
      var href = node.getAttribute && node.getAttribute("href");
      if (href) {
        try {
          var url = new URL(href, window.location.origin);
          sid =
            url.searchParams.get("session_id") ||
            url.searchParams.get("sid") ||
            url.searchParams.get("session") ||
            "";
        } catch (_) {}
      }
    }

    return cleanSid(sid);
  }

  function normalizeMessages(payload) {
    if (!payload) return [];

    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.messages)) return payload.messages;

    if (payload.session && Array.isArray(payload.session.messages)) {
      return payload.session.messages;
    }

    if (payload.data && Array.isArray(payload.data.messages)) {
      return payload.data.messages;
    }

    if (payload.data && payload.data.session && Array.isArray(payload.data.session.messages)) {
      return payload.data.session.messages;
    }

    if (payload.chat && Array.isArray(payload.chat.messages)) {
      return payload.chat.messages;
    }

    return [];
  }

  function getChatBox() {
    var box =
      document.getElementById("chat") ||
      document.getElementById("messages") ||
      document.getElementById("chatMessages") ||
      document.getElementById("desktopChatMessages") ||
      document.getElementById("desktopMessages") ||
      document.querySelector(".messages") ||
      document.querySelector(".chat-messages") ||
      document.querySelector(".desktop-chat-messages") ||
      document.querySelector("[data-messages]");

    if (box) return box;

    var host =
      document.querySelector(".desktop-chat-container") ||
      document.querySelector(".chat-container") ||
      document.querySelector("main") ||
      document.body;

    box = document.createElement("div");
    box.id = "chat";
    box.className = "messages chat-messages desktop-rescue-messages";
    host.appendChild(box);

    return box;
  }

  function messageRole(msg) {
    var role = String(
      msg?.role ||
      msg?.sender ||
      msg?.type ||
      "assistant"
    ).toLowerCase();

    if (role.includes("user")) return "user";
    if (role.includes("assistant") || role.includes("nova")) return "assistant";

    return role || "assistant";
  }

  function messageText(msg) {
    if (typeof msg === "string") return msg;

    return String(
      msg?.text ||
      msg?.content ||
      msg?.message ||
      msg?.assistant ||
      msg?.response ||
      msg?.user_text ||
      ""
    );
  }

  function renderMessagesDirect(messages) {
    var box = getChatBox();
    var safeMessages = Array.isArray(messages) ? messages : [];

    box.innerHTML = "";

    if (!safeMessages.length) {
      var empty = document.createElement("div");
      empty.className = "msg assistant";
      empty.textContent = "No messages found in this session yet.";
      box.appendChild(empty);
      return true;
    }

    safeMessages.forEach(function (msg, index) {
      var role = messageRole(msg);
      var text = messageText(msg);

      if (!text.trim()) return;

      var wrap = document.createElement("div");
      wrap.className = "msg " + role;
      wrap.setAttribute("data-message-id", "session_" + Date.now() + "_" + index);

      var roleNode = document.createElement("div");
      roleNode.className = "role";
      roleNode.textContent = role === "user" ? "You" : "Nova";

      var body = document.createElement("div");
      body.className = "bubble";
      body.style.whiteSpace = "pre-wrap";
      body.textContent = text;

      wrap.appendChild(roleNode);
      wrap.appendChild(body);
      box.appendChild(wrap);
    });

    try {
      box.scrollTop = box.scrollHeight;
    } catch (_) {}

    return true;
  }

  function chatLooksEmpty() {
    var box = getChatBox();
    if (!box) return true;

    var text = String(box.textContent || "").trim();
    var messageCount = box.querySelectorAll(".msg, .message, [data-message-id]").length;

    return !text && messageCount === 0;
  }

function renderSessionMessages(messages) {
    messages = Array.isArray(messages) ? messages : [];

    if (
        messages.length === 0 &&
        window.__NOVA_ACTIVE_SESSION &&
        window.__NOVA_ACTIVE_SESSION.meta &&
        window.__NOVA_ACTIVE_SESSION.meta.onboarding &&
        typeof window.renderDesktopOnboarding === "function"
    ) {
        console.log(
            "[Nova Session Open Final] onboarding preserved"
        );

        window.renderDesktopOnboarding(
            window.__NOVA_ACTIVE_SESSION
        );

        return true;
    }

    window.__NOVA_RENDER_LOCK_GLOBAL = false;
    window.__NOVA_RESCUE_RENDER_LOCK__ = false;

    try {
      if (typeof window.renderDesktopChatMessagesRescue === "function") {
        window.renderDesktopChatMessagesRescue(messages);

        setTimeout(function () {
          if (chatLooksEmpty()) {
            renderMessagesDirect(messages);
          }
        }, 80);

        return true;
      }
    } catch (error) {
      console.warn("[Nova Session Open Final] rescue render failed", error);
    }

    return renderMessagesDirect(messages);
  }

  function markActiveSessionRow(sid) {
    document.querySelectorAll(".desktop-session-item, .session-item").forEach(function (row) {
      var rowSid = getSessionIdFromElement(row);
      row.classList.toggle("is-active", rowSid === sid);
    });
  }

  async function openSessionFinal(rawSid) {
    var sid = setActiveSessionId(rawSid);

    if (!sid) {
      setStatusSafe("session id missing");
      return false;
    }

    setStatusSafe("loading session...");

    try {
      var response = await fetch("/api/sessions/" + encodeURIComponent(sid), {
        headers: {
          "x-api-key": "testkey123"
        }
      });

      if (!response.ok) {
        throw new Error("Session fetch failed: " + response.status);
      }

      var data = await response.json();
      var session = data.session || data.data?.session || data;
      var messages = normalizeMessages(session);

      if (!messages.length) {
        messages = normalizeMessages(data);
      }

      markActiveSessionRow(sid);
      renderSessionMessages(messages);

      try {
        if (typeof window.refreshSummaryMeta === "function") {
          window.refreshSummaryMeta();
        }
      } catch (_) {}

      try {
        if (typeof window.refreshDesktopPanels === "function") {
          window.refreshDesktopPanels();
        }
      } catch (_) {}

      setStatusSafe("session selected");
      log("opened", sid, "messages:", messages.length);

      return true;
    } catch (error) {
      console.warn("[Nova Session Open Final] open failed", error);
      setStatusSafe("session load failed");
      return false;
    }
  }

  window.NovaDesktopOpenSession = openSessionFinal;
  window.openDesktopSession = openSessionFinal;
  window.openSession = openSessionFinal;

  document.addEventListener("click", function (event) {
    var item = event.target.closest
      ? event.target.closest(".desktop-session-item, .session-item, [data-sid], [data-session-id]")
      : null;

    if (!item) return;

    var sid = getSessionIdFromElement(item);
    if (!sid) return;

    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }

    openSessionFinal(sid);
  }, true);

  async function openSessionFromUrlOnce() {
    try {
      var url = new URL(window.location.href);
      var sid =
        url.searchParams.get("session_id") ||
        url.searchParams.get("sid") ||
        url.searchParams.get("session") ||
        "";

      sid = cleanSid(sid);
      if (!sid) return;

      await openSessionFinal(sid);
    } catch (_) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", openSessionFromUrlOnce);
  } else {
    openSessionFromUrlOnce();
  }

  log("ready", MARKER);
})();
