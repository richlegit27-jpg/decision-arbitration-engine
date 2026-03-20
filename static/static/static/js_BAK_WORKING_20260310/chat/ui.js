// C:\Users\Owner\nova\static\js\chat\ui.js

(() => {
  const $ = (q) => document.querySelector(q);

  const ui = {
    els: {
      messages: $("#messages"),
      input: $("#messageInput"),
      btnExportMd: $("#btnExportMd"),
      btnExportTxt: $("#btnExportTxt"),
      btnClearChat: $("#btnClearChat"),
      btnStop: $("#btnStop"),
      statusDot: $("#statusDot"),
      statusText: $("#statusText"),
      modelText: $("#modelText")
    },

    setStatus(mode, text) {
      const { statusDot, statusText } = this.els;
      if (!statusDot || !statusText) return;

      statusDot.classList.remove("online", "offline", "thinking");
      if (mode) statusDot.classList.add(mode);
      statusText.textContent = text || "";
    },

    setModelText(text) {
      if (this.els.modelText) this.els.modelText.textContent = text || "";
    },

    autoResizeInput() {
      const input = this.els.input;
      if (!input) return;
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
    },

    getInputValue() {
      return this.els.input ? this.els.input.value : "";
    },

    setInputValue(value) {
      if (this.els.input) this.els.input.value = value || "";
    },

    clearMessages() {
      if (this.els.messages) this.els.messages.innerHTML = "";
    },

    scrollMessagesToBottom() {
      if (!this.els.messages) return;
      this.els.messages.scrollTop = this.els.messages.scrollHeight;
    },

    isNearBottom() {
      const el = this.els.messages;
      if (!el) return true;
      const gap = el.scrollHeight - el.scrollTop - el.clientHeight;
      return gap < 140;
    },

    smartScrollMessages(force = false) {
      if (!this.els.messages) return;
      if (force || this.isNearBottom()) {
        this.scrollMessagesToBottom();
      }
    },

    parseSsePart(part) {
      const lines = String(part || "").split("\n");
      let event = null;
      let data = null;

      for (const line of lines) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        }

        if (line.startsWith("data:")) {
          try {
            data = JSON.parse(line.slice(5));
          } catch (_) {
            data = null;
          }
        }
      }

      return { event, data };
    },

    currentChatTitle(chats, currentChat) {
      return (chats[currentChat]?.title || "nova-chat").replace(/[\\/:*?"<>|]+/g, "_");
    },

    gatherTranscript() {
      const rows = this.els.messages?.querySelectorAll(".msg-row") || [];
      const parts = [];

      rows.forEach((row) => {
        const role = row.dataset.role === "assistant" ? "Nova" : "User";
        const bubble = row.querySelector(".bubble");
        if (!bubble) return;
        const text = bubble.innerText.trim();
        if (!text) return;
        parts.push({ role, text });
      });

      return parts;
    },

    downloadFile(filename, content, type) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },

    exportAsTxt(chats, currentChat) {
      const transcript = this.gatherTranscript();
      if (!transcript.length) return;

      const text = transcript.map((m) => `${m.role}:\n${m.text}`).join("\n\n");
      this.downloadFile(`${this.currentChatTitle(chats, currentChat)}.txt`, text, "text/plain;charset=utf-8");
    },

    exportAsMarkdown(chats, currentChat) {
      const transcript = this.gatherTranscript();
      if (!transcript.length) return;

      const lines = [`# ${this.currentChatTitle(chats, currentChat)}`, ""];
      transcript.forEach((m) => {
        lines.push(`## ${m.role}`);
        lines.push("");
        lines.push(m.text);
        lines.push("");
      });

      this.downloadFile(`${this.currentChatTitle(chats, currentChat)}.md`, lines.join("\n"), "text/markdown;charset=utf-8");
    },

    bindTopbar({ onExportMd, onExportTxt, onClearChat, onStop }) {
      if (this.els.btnExportMd) this.els.btnExportMd.onclick = onExportMd;
      if (this.els.btnExportTxt) this.els.btnExportTxt.onclick = onExportTxt;
      if (this.els.btnClearChat) this.els.btnClearChat.onclick = onClearChat;
      if (this.els.btnStop) this.els.btnStop.onclick = onStop;
    }
  };

  window.NovaApp = window.NovaApp || {};
  window.NovaApp.ui = ui;
})();