// C:\Users\Owner\nova\static\js\chat\sidebar.js

(() => {
  const app = window.NovaApp;
  const state = app.state;
  const ui = app.ui;

  const savedPrompts = [
    { name: "Explain simply", text: "Explain this in simple terms:\n" },
    { name: "Summarize", text: "Summarize the following clearly and briefly:\n" },
    { name: "Python helper", text: "Write clean Python code for this and explain it:\n" },
    { name: "Security review", text: "Analyze this code for security issues and explain the risks:\n" },
    { name: "Debug this", text: "Help me debug this step by step:\n" }
  ];

  const els = {
    chatList: document.querySelector("#chatList"),
    btnNewChat: document.querySelector("#btnNewChat"),
    chatSearch: document.querySelector("#chatSearch"),
    promptLibrary: document.querySelector("#promptLibrary")
  };

  const sidebar = {
    handlers: {
      onNewChat: null,
      onLoadChat: null,
      onRenameChat: null,
      onDeleteChat: null
    },

    bind(handlers) {
      this.handlers = { ...this.handlers, ...(handlers || {}) };

      if (els.btnNewChat) {
        els.btnNewChat.onclick = () => {
          if (typeof this.handlers.onNewChat === "function") {
            this.handlers.onNewChat();
          }
        };
      }

      if (els.chatSearch) {
        els.chatSearch.oninput = (e) => {
          state.currentFilter = e.target.value || "";
          this.renderSidebar();
        };
      }
    },

    setChatsFromServer(sessionList) {
      state.chats = {};
      (sessionList || []).forEach((s) => {
        state.chats[s.id] = {
          title: s.title || "New chat",
          updated: s.updated || "",
          created: s.created || "",
          message_count: s.message_count || 0
        };
      });
      this.renderSidebar();
    },

    filteredChatIds() {
      const ids = Object.keys(state.chats);
      const q = state.currentFilter.trim().toLowerCase();

      ids.sort((a, b) => {
        const au = state.chats[a]?.updated || "";
        const bu = state.chats[b]?.updated || "";
        return String(bu).localeCompare(String(au));
      });

      if (!q) return ids;
      return ids.filter((id) => (state.chats[id]?.title || "").toLowerCase().includes(q));
    },

    renderSidebar() {
      if (!els.chatList) return;
      els.chatList.innerHTML = "";

      this.filteredChatIds().forEach((id) => {
        const item = document.createElement("div");
        item.className = "chat-item";
        if (id === state.currentChat) item.classList.add("active");

        const main = document.createElement("div");
        main.className = "chat-main";
        main.onclick = () => {
          if (typeof this.handlers.onLoadChat === "function") {
            this.handlers.onLoadChat(id);
          }
        };

        const title = document.createElement("div");
        title.className = "chat-title";
        title.textContent = state.chats[id]?.title || "New chat";
        main.appendChild(title);

        const actions = document.createElement("div");
        actions.className = "chat-actions";

        const btnRename = document.createElement("button");
        btnRename.className = "icon-btn";
        btnRename.textContent = "✎";
        btnRename.title = "Rename chat";
        btnRename.onclick = (e) => {
          e.stopPropagation();
          if (typeof this.handlers.onRenameChat === "function") {
            this.handlers.onRenameChat(id);
          }
        };

        const btnDelete = document.createElement("button");
        btnDelete.className = "icon-btn";
        btnDelete.textContent = "✕";
        btnDelete.title = "Delete chat";
        btnDelete.onclick = (e) => {
          e.stopPropagation();
          if (typeof this.handlers.onDeleteChat === "function") {
            this.handlers.onDeleteChat(id);
          }
        };

        actions.appendChild(btnRename);
        actions.appendChild(btnDelete);

        item.appendChild(main);
        item.appendChild(actions);

        els.chatList.appendChild(item);
      });
    },

    renderPromptLibrary() {
      if (!els.promptLibrary) return;
      els.promptLibrary.innerHTML = "";

      savedPrompts.forEach((p) => {
        const item = document.createElement("div");
        item.className = "prompt-item";

        const name = document.createElement("div");
        name.className = "prompt-item-name";
        name.textContent = p.name;

        const text = document.createElement("div");
        text.className = "prompt-item-text";
        text.textContent = p.text.trim();

        item.appendChild(name);
        item.appendChild(text);

        item.onclick = () => {
          const current = ui.getInputValue().trim();
          ui.setInputValue(current ? `${current}\n${p.text}` : p.text);
          ui.autoResizeInput();
          document.querySelector("#messageInput")?.focus();
        };

        els.promptLibrary.appendChild(item);
      });
    }
  };

  window.NovaApp = window.NovaApp || {};
  window.NovaApp.sidebar = sidebar;
})();