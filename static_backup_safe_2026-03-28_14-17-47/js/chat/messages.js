// C:\Users\Owner\nova\static\js\chat\messages.js

(() => {
  const app = window.NovaApp;
  const ui = app.ui;
  const state = app.state;

  const messages = {
    handlers: {
      onResendFromUserEdit: null,
      onRegenFromLastUser: null
    },

    bind(handlers) {
      this.handlers = { ...this.handlers, ...(handlers || {}) };
    },

    renderEmptyState() {
      const messagesEl = ui.els.messages;
      if (!messagesEl) return;

      if (!messagesEl.querySelector(".msg-row")) {
        messagesEl.innerHTML = `
          <div class="empty-note">
            <strong>Ready.</strong><br><br>
            Start a new message, use one of the prompt shortcuts on the left, export chats, rename chats, delete chats, edit user messages, or press <strong>Esc</strong> while streaming to stop generation.
          </div>
        `;
      }
    },

    renderEmptyStateIfNeeded() {
      this.renderEmptyState();
    },

    formatTime(value) {
      if (!value) return "";
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleString();
    },

    addCopyButtons(container) {
      const blocks = container.querySelectorAll("pre");

      blocks.forEach((block) => {
        if (block.dataset.copyAdded) return;
        block.dataset.copyAdded = "1";

        const btn = document.createElement("button");
        btn.textContent = "copy";

        btn.onclick = async () => {
          try {
            await navigator.clipboard.writeText(block.innerText);
            btn.textContent = "copied";
            setTimeout(() => {
              btn.textContent = "copy";
            }, 1200);
          } catch (_) {}
        };

        btn.style.position = "absolute";
        btn.style.top = "6px";
        btn.style.right = "6px";
        btn.style.fontSize = "12px";
        btn.style.padding = "3px 6px";
        btn.style.border = "none";
        btn.style.borderRadius = "4px";
        btn.style.background = "#444";
        btn.style.color = "#fff";
        btn.style.cursor = "pointer";

        block.style.position = "relative";
        block.appendChild(btn);
      });
    },

    renderMarkdown(el, text) {
      el.innerHTML = marked.parse(text || "");

      if (window.hljs) {
        el.querySelectorAll("pre code").forEach((block) => {
          hljs.highlightElement(block);
        });
      }

      this.addCopyButtons(el);
    },

    setRowMarkdown(row, text) {
      const bubble = row?.querySelector(".bubble");
      if (!bubble) return;
      this.renderMarkdown(bubble, text);
    },

    setRowPlainText(row, text) {
      const bubble = row?.querySelector(".bubble");
      if (!bubble) return;
      bubble.textContent = text || "";
    },

    removeAssistantAfter(row) {
      if (!row) return;
      const next = row.nextElementSibling;
      if (next && next.classList.contains("msg-row") && next.dataset.role === "assistant") {
        next.remove();
      }
    },

    startEditUserRow(row) {
      if (!row || row.dataset.role !== "user" || state.isStreaming) return;

      const bubble = row.querySelector(".bubble");
      const actions = row.querySelector(".msg-actions");
      if (!bubble || !actions) return;
      if (row.dataset.editing === "1") return;

      row.dataset.editing = "1";
      const original = bubble.innerText;

      bubble.innerHTML = `
        <div class="edit-box">
          <textarea class="edit-textarea"></textarea>
          <div class="edit-actions">
            <button class="edit-save">Save + resend</button>
            <button class="edit-cancel">Cancel</button>
          </div>
        </div>
      `;

      const ta = bubble.querySelector(".edit-textarea");
      const saveBtn = bubble.querySelector(".edit-save");
      const cancelBtn = bubble.querySelector(".edit-cancel");

      ta.value = original;
      ta.focus();
      ta.selectionStart = ta.selectionEnd = ta.value.length;

      cancelBtn.onclick = () => {
        row.dataset.editing = "0";
        bubble.textContent = original;
      };

      saveBtn.onclick = async () => {
        const edited = ta.value.trim();
        if (!edited) return;

        row.dataset.editing = "0";
        if (typeof this.handlers.onResendFromUserEdit === "function") {
          await this.handlers.onResendFromUserEdit(row, edited);
        }
      };

      ta.addEventListener("keydown", async (e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          cancelBtn.click();
        }
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          await saveBtn.onclick();
        }
      });

      if (actions) actions.style.display = "none";
    },

    createMessage(role, content, opts = {}) {
      const messagesEl = ui.els.messages;
      if (!messagesEl) return null;

      const empty = messagesEl.querySelector(".empty-note");
      if (empty) empty.remove();

      const row = document.createElement("div");
      row.className = "msg-row";
      row.dataset.role = role;
      row.dataset.created = opts.created || "";

      if (role === "user") row.classList.add("user-row");

      const avatar = document.createElement("div");
      avatar.className = "avatar";
      avatar.textContent = role === "assistant" ? "N" : "U";

      const wrap = document.createElement("div");
      wrap.className = "bubble-wrap";

      const bubble = document.createElement("div");
      bubble.className = "bubble";

      const meta = document.createElement("div");
      meta.className = "msg-meta";
      meta.textContent = this.formatTime(opts.created);

      const actions = document.createElement("div");
      actions.className = "msg-actions";

      const btnCopy = document.createElement("button");
      btnCopy.textContent = "copy";
      btnCopy.onclick = () => {
        navigator.clipboard.writeText(bubble.innerText).catch(() => {});
      };
      actions.appendChild(btnCopy);

      if (role === "user") {
        const btnEdit = document.createElement("button");
        btnEdit.textContent = "edit";
        btnEdit.className = "warn";
        btnEdit.onclick = () => this.startEditUserRow(row);
        actions.appendChild(btnEdit);
      }

      if (role === "assistant") {
        const btnRegen = document.createElement("button");
        btnRegen.textContent = "regen";
        btnRegen.className = "warn";
        btnRegen.onclick = async () => {
          if (typeof this.handlers.onRegenFromLastUser === "function") {
            row.remove();
            this.renderEmptyStateIfNeeded();
            await this.handlers.onRegenFromLastUser();
          }
        };
        actions.appendChild(btnRegen);
      }

      const btnDelete = document.createElement("button");
      btnDelete.textContent = "delete";
      btnDelete.className = "danger";
      btnDelete.onclick = () => {
        if (role === "user") {
          this.removeAssistantAfter(row);
        }
        row.remove();
        this.renderEmptyStateIfNeeded();
      };
      actions.appendChild(btnDelete);

      if (role === "assistant") {
        wrap.appendChild(meta);
        wrap.appendChild(bubble);
        wrap.appendChild(actions);
        row.appendChild(avatar);
        row.appendChild(wrap);
      } else {
        wrap.appendChild(meta);
        wrap.appendChild(bubble);
        wrap.appendChild(actions);
        row.appendChild(wrap);
        row.appendChild(avatar);
      }

      if (role === "assistant") {
        this.renderMarkdown(bubble, content || "");
      } else {
        bubble.textContent = content || "";
      }

      messagesEl.appendChild(row);
      ui.smartScrollMessages(true);

      return row;
    }
  };

  window.NovaApp = window.NovaApp || {};
  window.NovaApp.messages = messages;
})();