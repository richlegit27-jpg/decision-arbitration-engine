(() => {
"use strict";

if (window.__novaSidebarLoaded) {
  console.warn("Nova sidebar already loaded.");
  return;
}
window.__novaSidebarLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

const MOBILE_BREAKPOINT = 980;

function byId(id) {
  return document.getElementById(id);
}

function getBody() {
  return document.body;
}

function getSidebar() {
  return byId("sidebar");
}

function getBackdrop() {
  return byId("sidebarBackdrop");
}

function getChatList() {
  return byId("chatList");
}

function getNewChatBtn() {
  return byId("btnNewChat") || byId("newChatBtn");
}

function getToggleButtons() {
  return [
    byId("sidebarToggleBtn"),
    byId("topbarSidebarToggleBtn")
  ].filter(Boolean);
}

function getCloseButtons() {
  return [
    byId("btnCloseSidebar"),
    byId("sidebarCloseBtn")
  ].filter(Boolean);
}

function getSafeFocusTarget() {
  return (
    byId("sidebarToggleBtn")
    || byId("topbarSidebarToggleBtn")
    || byId("messageInput")
    || document.body
  );
}

function focusSafely(element) {
  if (!element || typeof element.focus !== "function") {
    return;
  }

  try {
    element.focus({ preventScroll: true });
  } catch (_) {
    try {
      element.focus();
    } catch (_) {}
  }
}

function moveFocusOutOfSidebar() {
  const sidebar = getSidebar();
  const active = document.activeElement;

  if (!sidebar || !active) {
    return;
  }

  if (!sidebar.contains(active)) {
    return;
  }

  focusSafely(getSafeFocusTarget());
}

function ensureState() {
  app.state = app.state || {};
  app.state.ui = app.state.ui || {};

  if (typeof app.state.ui.sidebarOpen !== "boolean") {
    app.state.ui.sidebarOpen = false;
  }

  return app.state;
}

function isMobileViewport() {
  return window.innerWidth <= MOBILE_BREAKPOINT;
}

function setSidebarOpen(isOpen) {
  const body = getBody();
  const state = ensureState();
  const open = !!isOpen;

  state.ui.sidebarOpen = open;

  if (!open) {
    moveFocusOutOfSidebar();
  }

  body.classList.toggle("sidebar-open", open);
  body.classList.toggle("sidebar-closed", !open && !isMobileViewport());

  const sidebar = getSidebar();
  if (sidebar) {
    if (open) {
      sidebar.removeAttribute("inert");
      sidebar.setAttribute("aria-hidden", "false");
    } else {
      sidebar.setAttribute("inert", "");
      sidebar.setAttribute("aria-hidden", "true");
    }
  }

  const backdrop = getBackdrop();
  if (backdrop) {
    backdrop.hidden = !open;
    backdrop.setAttribute("aria-hidden", open ? "false" : "true");
  }
}

function openSidebar() {
  setSidebarOpen(true);
}

function closeSidebar() {
  setSidebarOpen(false);
}

function toggleSidebar() {
  const state = ensureState();
  setSidebarOpen(!state.ui.sidebarOpen);
}

function syncSidebarToViewport() {
  const state = ensureState();
  const body = getBody();

  if (isMobileViewport()) {
    setSidebarOpen(false);
    body.classList.remove("sidebar-closed");
    return;
  }

  if (state.ui.sidebarOpen) {
    body.classList.remove("sidebar-closed");
    body.classList.add("sidebar-open");
  } else {
    body.classList.remove("sidebar-open");
    body.classList.add("sidebar-closed");
  }

  const sidebar = getSidebar();
  if (sidebar) {
    if (state.ui.sidebarOpen) {
      sidebar.removeAttribute("inert");
      sidebar.setAttribute("aria-hidden", "false");
    } else {
      sidebar.setAttribute("inert", "");
      sidebar.setAttribute("aria-hidden", "true");
    }
  }

  const backdrop = getBackdrop();
  if (backdrop) {
    backdrop.hidden = true;
    backdrop.setAttribute("aria-hidden", "true");
  }
}

function bindClick(el, key, handler) {
  if (!el) return;
  const flag = `novaBound${key}`;
  if (el.dataset[flag] === "1") return;
  el.dataset[flag] = "1";
  el.addEventListener("click", handler);
}

function bindKeydownOnce() {
  if (document.body.dataset.novaSidebarKeybound === "1") {
    return;
  }

  document.body.dataset.novaSidebarKeybound = "1";

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeSidebar();
  });
}

function renderChatList() {
  const chatList = getChatList();
  if (!chatList) return;

  ensureState();
  const chats = Array.isArray(app.state.chats) ? app.state.chats : [];

  chatList.innerHTML = "";

  if (!chats.length) {
    const empty = document.createElement("div");
    empty.className = "sidebar-empty";
    empty.textContent = "No chats yet";
    chatList.appendChild(empty);
    return;
  }

  chats.forEach((chat, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "chat-list-item";
    item.dataset.chatId = String(chat.id || "");

    const title =
      String(chat.title || "").trim() ||
      `Chat ${index + 1}`;

    item.textContent = title;

    bindClick(item, "ChatItem", () => {
      if (!chat.id) return;

      app.state.activeChatId = chat.id;

      if (typeof app.renderApp === "function") {
        app.renderApp();
      } else if (typeof app.renderMessages === "function") {
        app.renderMessages();
      }

      if (isMobileViewport()) {
        closeSidebar();
      }
    });

    chatList.appendChild(item);
  });
}

function createNewChat() {
  ensureState();

  if (typeof app.createNewChat === "function") {
    app.createNewChat();
  } else {
    const newChat = {
      id: `chat_${Date.now()}`,
      title: "New Chat",
      created_at: new Date().toISOString()
    };

    app.state.chats = Array.isArray(app.state.chats) ? app.state.chats : [];
    app.state.messagesByChatId =
      app.state.messagesByChatId && typeof app.state.messagesByChatId === "object"
        ? app.state.messagesByChatId
        : {};

    app.state.chats.unshift(newChat);
    app.state.messagesByChatId[newChat.id] = [];
    app.state.activeChatId = newChat.id;
  }

  renderChatList();

  if (typeof app.renderApp === "function") {
    app.renderApp();
  } else if (typeof app.renderMessages === "function") {
    app.renderMessages();
  }

  if (isMobileViewport()) {
    closeSidebar();
  }
}

function bindControls() {
  getToggleButtons().forEach((btn) => {
    bindClick(btn, "SidebarToggle", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleSidebar();
    });
  });

  getCloseButtons().forEach((btn) => {
    bindClick(btn, "SidebarClose", (event) => {
      event.preventDefault();
      event.stopPropagation();
      closeSidebar();
    });
  });

  bindClick(getBackdrop(), "SidebarBackdrop", () => {
    closeSidebar();
  });

  bindClick(getNewChatBtn(), "NewChat", (event) => {
    event.preventDefault();
    event.stopPropagation();
    createNewChat();
  });

  bindKeydownOnce();
}

function exposeApi() {
  app.sidebar = app.sidebar || {};
  app.sidebar.open = openSidebar;
  app.sidebar.close = closeSidebar;
  app.sidebar.toggle = toggleSidebar;
  app.sidebar.render = renderChatList;
  app.sidebar.sync = syncSidebarToViewport;
}

function initSidebar() {
  const sidebar = getSidebar();

  if (!sidebar) {
    console.warn("Nova sidebar: #sidebar not found.");
    return;
  }

  ensureState();
  bindControls();
  exposeApi();
  renderChatList();
  syncSidebarToViewport();

  if (window.__novaSidebarResizeBound !== true) {
    window.__novaSidebarResizeBound = true;
    window.addEventListener("resize", syncSidebarToViewport);
  }

  console.log("Nova sidebar loaded.");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSidebar, { once: true });
} else {
  initSidebar();
}
})();