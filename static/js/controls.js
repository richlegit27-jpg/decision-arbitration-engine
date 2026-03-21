(() => {
"use strict";

if (window.__novaSidebarLoaded) {
  console.warn("Nova sidebar already loaded.");
  return;
}
window.__novaSidebarLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function getSidebar() {
  return byId("sidebar");
}

function getChatList() {
  return byId("chatList");
}

function getNewChatBtn() {
  return byId("btnNewChat") || byId("newChatBtn");
}

function getToggleBtn() {
  return byId("sidebarToggleBtn");
}

function getTopbarToggleBtn() {
  return byId("topbarSidebarToggleBtn");
}

function getCloseBtn() {
  return byId("btnCloseSidebar") || byId("sidebarCloseBtn");
}

function getTopBar() {
  return (
    byId("topBar")
    || document.querySelector(".top-bar")
    || document.querySelector(".chat-topbar")
    || document.querySelector(".app-topbar")
    || document.querySelector(".header-bar")
    || document.querySelector("header")
  );
}

function isMobile() {
  return window.innerWidth <= 820;
}

function ensureAppState() {
  app.state = app.state || {};

  if (!Array.isArray(app.state.chats)) {
    app.state.chats = [];
  }

  if (!app.state.messagesByChatId || typeof app.state.messagesByChatId !== "object") {
    app.state.messagesByChatId = {};
  }

  if (!app.state.ui || typeof app.state.ui !== "object") {
    app.state.ui = {
      sidebarOpen: false,
      memoryOpen: false
    };
  }

  if (typeof app.state.ui.sidebarOpen !== "boolean") {
    app.state.ui.sidebarOpen = false;
  }

  return app.state;
}

function notifyError(message) {
  const text = message || "Something went wrong.";
  if (window.NovaToast && typeof window.NovaToast.error === "function") {
    window.NovaToast.error(text);
    return;
  }
  console.error(text);
}

function getActiveChatId() {
  if (typeof app.getActiveChatId === "function") {
    return app.getActiveChatId();
  }
  return ensureAppState().activeChatId || null;
}

function getMessagesForChat(chatId) {
  const appState = ensureAppState();
  const messages = appState.messagesByChatId?.[chatId];
  return Array.isArray(messages) ? messages : [];
}

function getAllToggleButtons() {
  return [getToggleBtn(), getTopbarToggleBtn()].filter(Boolean);
}

function syncAria() {
  const sidebar = getSidebar();

  if (!sidebar) return;

  const open = isMobile()
    ? document.body.classList.contains("sidebar-open")
    : !document.body.classList.contains("sidebar-collapsed");

  sidebar.setAttribute("aria-hidden", open ? "false" : "true");

  getAllToggleButtons().forEach((button) => {
    button.setAttribute("aria-expanded", open ? "true" : "false");
  });
}

function ensureTopbarSidebarButton() {
  const topBar = getTopBar();
  if (!topBar) return;

  if (getTopbarToggleBtn()) return;

  const button = document.createElement("button");
  button.type = "button";
  button.id = "topbarSidebarToggleBtn";
  button.className = "icon-btn nova-topbar-sidebar-btn";
  button.title = "Toggle sidebar";
  button.setAttribute("aria-label", "Toggle sidebar");
  button.innerHTML = `
    <span class="nova-topbar-sidebar-icon" aria-hidden="true">☰</span>
    <span class="nova-topbar-sidebar-text">Chats</span>
  `;

  topBar.insertBefore(button, topBar.firstChild);
}

function openSidebar() {
  ensureAppState();

  if (isMobile()) {
    document.body.classList.add("sidebar-open");
    document.body.classList.remove("sidebar-collapsed");
  } else {
    document.body.classList.remove("sidebar-collapsed");
  }

  app.state.ui.sidebarOpen = true;
  syncAria();
}

function closeSidebar() {
  ensureAppState();

  const sidebar = getSidebar();
  const active = document.activeElement;
  const fallbackFocus = getTopbarToggleBtn() || getToggleBtn();

  if (sidebar && active instanceof HTMLElement && sidebar.contains(active)) {
    active.blur();
    if (fallbackFocus instanceof HTMLElement) {
      fallbackFocus.focus({ preventScroll: true });
    }
  }

  if (isMobile()) {
    document.body.classList.remove("sidebar-open");
  } else {
    document.body.classList.add("sidebar-collapsed");
  }

  app.state.ui.sidebarOpen = false;
  syncAria();
}

function toggleSidebar() {
  if (isMobile()) {
    if (document.body.classList.contains("sidebar-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
    return;
  }

  if (document.body.classList.contains("sidebar-collapsed")) {
    openSidebar();
  } else {
    closeSidebar();
  }
}

function setActiveChat(chatId) {
  if (!chatId) return;

  if (typeof app.setActiveChat === "function") {
    app.setActiveChat(chatId);
  } else {
    const appState = ensureAppState();
    appState.activeChatId = chatId;
    document.dispatchEvent(new CustomEvent("nova:chat-changed", { detail: { chatId } }));

    if (typeof app.renderMessages === "function") {
      app.renderMessages({ forceScroll: true });
    }

    renderSidebar();
  }

  if (isMobile()) {
    closeSidebar();
  }
}

function chatMetaText(chat) {
  const count =
    Number(chat?.message_count) ||
    getMessagesForChat(String(chat?.id || "")).length ||
    0;

  return count === 1 ? "1 message" : `${count} messages`;
}

function buildActionButton(symbol, title, action) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "icon-btn sidebar-mini-action";
  button.textContent = symbol;
  button.title = title;
  button.dataset.sidebarAction = action;
  return button;
}

function buildItem(chat) {
  const row = document.createElement("div");
  row.className = "chat-list-row";
  row.dataset.chatId = String(chat?.id || "");

  const button = document.createElement("button");
  button.type = "button";
  button.className = "chat-list-item";
  button.dataset.chatId = String(chat?.id || "");

  if (String(getActiveChatId() || "") === String(chat?.id || "")) {
    button.classList.add("active");
  }

  const title = document.createElement("div");
  title.className = "chat-list-item-title";
  title.textContent = String(chat?.title || "Untitled");

  const meta = document.createElement("div");
  meta.className = "chat-list-item-meta";
  meta.textContent = chatMetaText(chat);

  button.appendChild(title);
  button.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "chat-list-actions";
  actions.appendChild(buildActionButton("✎", "Rename chat", "rename"));
  actions.appendChild(buildActionButton("🗑", "Delete chat", "delete"));

  row.appendChild(button);
  row.appendChild(actions);

  return row;
}

function renderSidebar() {
  const list = getChatList();
  if (!list) return;

  const appState = ensureAppState();
  list.innerHTML = "";

  if (!Array.isArray(appState.chats) || !appState.chats.length) {
    const empty = document.createElement("div");
    empty.className = "chat-list-empty";
    empty.textContent = "No chats yet.";
    list.appendChild(empty);
    syncAria();
    return;
  }

  appState.chats.forEach((chat) => {
    list.appendChild(buildItem(chat));
  });

  syncAria();
}

async function handleNewChatButtonClick(event) {
  event.preventDefault();
  event.stopPropagation();

  try {
    if (app.controls && typeof app.controls.createNewChat === "function") {
      await app.controls.createNewChat();
      renderSidebar();
      if (isMobile()) {
        closeSidebar();
      }
      return;
    }

    notifyError("Create chat is not ready.");
  } catch (error) {
    console.error(error);
    notifyError(error?.message || "Failed to create chat.");
  }
}

async function handleSidebarListClick(event) {
  const actionButton = event.target.closest("[data-sidebar-action]");
  const chatButton = event.target.closest(".chat-list-item[data-chat-id]");

  if (actionButton) {
    event.preventDefault();
    event.stopPropagation();

    const row = actionButton.closest("[data-chat-id]");
    const chatId = String(row?.dataset.chatId || "").trim();
    const action = String(actionButton.dataset.sidebarAction || "").trim();

    if (!chatId || !action) return;

    try {
      if (action === "rename" && app.controls && typeof app.controls.renameChatById === "function") {
        await app.controls.renameChatById(chatId);
        renderSidebar();
        return;
      }

      if (action === "delete" && app.controls && typeof app.controls.deleteChatById === "function") {
        await app.controls.deleteChatById(chatId);
        renderSidebar();
      }
    } catch (error) {
      console.error(error);
      notifyError(error?.message || "Sidebar action failed.");
    }
    return;
  }

  if (chatButton) {
    const chatId = String(chatButton.dataset.chatId || "").trim();
    if (!chatId) return;
    setActiveChat(chatId);
  }
}

function bindToggle(button) {
  if (!button || button.dataset.boundSidebar === "1") {
    return;
  }

  button.dataset.boundSidebar = "1";
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleSidebar();
  });
}

function bindEvents() {
  const newChatBtn = getNewChatBtn();
  const closeBtn = getCloseBtn();
  const chatList = getChatList();

  if (newChatBtn && newChatBtn.dataset.boundSidebar !== "1") {
    newChatBtn.dataset.boundSidebar = "1";
    newChatBtn.addEventListener("click", handleNewChatButtonClick);
  }

  bindToggle(getToggleBtn());
  bindToggle(getTopbarToggleBtn());

  if (closeBtn && closeBtn.dataset.boundSidebar !== "1") {
    closeBtn.dataset.boundSidebar = "1";
    closeBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      closeSidebar();
    });
  }

  if (chatList && chatList.dataset.boundSidebar !== "1") {
    chatList.dataset.boundSidebar = "1";
    chatList.addEventListener("click", handleSidebarListClick);
  }

  if (!document.body.dataset.sidebarOutsideBound) {
    document.body.dataset.sidebarOutsideBound = "1";

    document.addEventListener("click", (event) => {
      if (!isMobile()) return;
      if (!document.body.classList.contains("sidebar-open")) return;

      const sidebar = getSidebar();
      const target = event.target;

      if (!(target instanceof Node)) return;
      if (sidebar && sidebar.contains(target)) return;

      for (const btn of getAllToggleButtons()) {
        if (btn.contains(target)) return;
      }

      closeSidebar();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && isMobile() && document.body.classList.contains("sidebar-open")) {
        closeSidebar();
      }
    });

    window.addEventListener("resize", () => {
      if (isMobile()) {
        document.body.classList.remove("sidebar-collapsed");
      } else {
        document.body.classList.remove("sidebar-open");

        if (app.state?.ui?.sidebarOpen === false) {
          document.body.classList.add("sidebar-collapsed");
        }
      }

      syncAria();
    });
  }
}

function injectSidebarStyles() {
  if (document.getElementById("nova-sidebar-inline-polish")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "nova-sidebar-inline-polish";
  style.textContent = `
    #sidebar{
      position:relative;
      border-right:1px solid var(--line);
      background:linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      backdrop-filter:blur(10px);
    }
    #sidebarToggleBtn,
    #topbarSidebarToggleBtn{
      border:1px solid var(--line);
      background:linear-gradient(135deg, var(--panel), var(--panel-2));
      color:var(--text);
      border-radius:14px;
      box-shadow:0 14px 30px rgba(0,0,0,0.14);
      transition:transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }
    #sidebarToggleBtn:hover,
    #topbarSidebarToggleBtn:hover{
      transform:translateY(-1px);
      box-shadow:0 18px 36px rgba(0,0,0,0.18);
    }
    #topbarSidebarToggleBtn{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:10px 14px;
      margin-right:10px;
      font-weight:700;
      letter-spacing:0.2px;
    }
    .nova-topbar-sidebar-icon{
      font-size:15px;
      line-height:1;
    }
    .nova-topbar-sidebar-text{
      font-size:13px;
      line-height:1;
    }
    #btnCloseSidebar,
    #sidebarCloseBtn{
      border:1px solid var(--line);
      background:var(--panel);
      color:var(--text);
      border-radius:12px;
    }
    .chat-list-row{
      display:grid;
      grid-template-columns:minmax(0,1fr) auto;
      gap:8px;
      align-items:stretch;
      margin-bottom:10px;
    }
    .chat-list-actions{
      display:flex;
      flex-direction:column;
      gap:8px;
      justify-content:center;
    }
    .chat-list-row .chat-list-item{
      min-width:0;
      border:1px solid var(--line);
      border-radius:16px;
      background:var(--panel);
      padding:12px;
      text-align:left;
      color:var(--text);
      transition:transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
      box-shadow:0 10px 24px rgba(0,0,0,0.08);
    }
    .chat-list-row .chat-list-item:hover{
      transform:translateY(-1px);
      box-shadow:0 14px 30px rgba(0,0,0,0.12);
      border-color:rgba(118,169,255,0.28);
    }
    .chat-list-row .chat-list-item.active{
      background:linear-gradient(135deg, rgba(118,169,255,0.16), rgba(139,92,246,0.14));
      border-color:rgba(118,169,255,0.34);
    }
    .chat-list-item-title{
      font-weight:700;
      color:var(--text);
      margin-bottom:6px;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .chat-list-item-meta{
      font-size:12px;
      color:var(--muted);
    }
    .sidebar-mini-action{
      width:34px;
      height:34px;
      min-height:34px;
      border-radius:10px;
      border:1px solid var(--line);
      background:var(--panel-2);
      color:var(--text);
      transition:transform 160ms ease, background 160ms ease;
    }
    .sidebar-mini-action:hover{
      transform:translateY(-1px);
      background:rgba(118,169,255,0.12);
    }
    .chat-list-empty{
      color:var(--muted);
      font-size:13px;
      text-align:center;
      padding:8px 0 2px;
    }
    @media (max-width: 560px){
      #topbarSidebarToggleBtn .nova-topbar-sidebar-text{
        display:none;
      }
      #topbarSidebarToggleBtn{
        padding:10px 12px;
        margin-right:8px;
      }
      .chat-list-row{
        grid-template-columns:minmax(0,1fr);
      }
      .chat-list-actions{
        flex-direction:row;
        justify-content:flex-end;
      }
    }
  `;
  document.head.appendChild(style);
}

function initSidebar() {
  ensureAppState();
  injectSidebarStyles();
  ensureTopbarSidebarButton();
  bindEvents();

  if (isMobile()) {
    document.body.classList.remove("sidebar-collapsed");
    if (app.state.ui.sidebarOpen) {
      document.body.classList.add("sidebar-open");
    } else {
      document.body.classList.remove("sidebar-open");
    }
  } else {
    document.body.classList.remove("sidebar-open");
    if (app.state.ui.sidebarOpen === false) {
      document.body.classList.add("sidebar-collapsed");
    }
  }

  renderSidebar();
  syncAria();
}

app.openSidebar = openSidebar;
app.closeSidebar = closeSidebar;
app.toggleSidebar = toggleSidebar;
app.renderSidebar = renderSidebar;

app.sidebar = {
  initSidebar,
  renderSidebar,
  openSidebar,
  closeSidebar,
  toggleSidebar
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSidebar, { once: true });
} else {
  initSidebar();
}

document.addEventListener("nova:messages-updated", renderSidebar);
document.addEventListener("nova:chat-changed", renderSidebar);
document.addEventListener("nova:app-ready", initSidebar);
})();