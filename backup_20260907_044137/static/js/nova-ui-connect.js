document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");
  const chatInput = document.getElementById("chatInput");

  sendBtn.addEventListener("click", () => {
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = "";
    window.Nova.sendMessage(text);
  });

  chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // Auto session creation
  window.Nova = window.Nova || {};
  window.Nova.sessionReady = fetch("/api/session/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "Default Chat" })
  })
    .then(r => r.json())
    .then(data => {
      window.Nova.currentSessionId = data.session.id;
      return data.session.id;
    });
});

