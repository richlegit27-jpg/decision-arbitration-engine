// C:\Users\Owner\nova\static\js\chat\api.js

(() => {
  const api = {
    async getHealth() {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async listSessions() {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async createSession() {
      const res = await fetch("/api/sessions", { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async getMessages(chatId) {
      const res = await fetch(`/api/sessions/${chatId}/messages`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async renameSession(chatId, title) {
      const res = await fetch(`/api/sessions/${chatId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async deleteSession(chatId) {
      const res = await fetch(`/api/sessions/${chatId}`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async clearMessages(chatId) {
      const res = await fetch(`/api/sessions/${chatId}/messages`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },

    async streamMessage(chatId, message, signal) {
      return fetch(`/api/sessions/${chatId}/messages/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
        signal
      });
    }
  };

  window.NovaApp = window.NovaApp || {};
  window.NovaApp.api = api;
})();