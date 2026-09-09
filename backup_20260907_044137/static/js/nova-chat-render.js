// notepad C:\Users\Owner\nova\static\js\nova-chat-render.js
window.Nova = window.Nova || {}; // <- make sure the global exists

window.Nova.sendMessage = async function(text) {
  renderMessage(text, "user");

  // Make sure sessionReady exists
  if (!window.Nova.sessionReady) {
    console.warn("Session promise missing!");
    return;
  }

  const sessionId = await window.Nova.sessionReady;
  if (!sessionId) return console.warn("No session available.");

  // POST to /api/chat
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: text, session_id: sessionId })
  });
  const data = await response.json();

  // Display AI message
  if (data.messages_preview)
    data.messages_preview.forEach(m => window.Nova.renderMessage(m.content, "assistant"));
  if (data.attachments)
    data.attachments.forEach(att => window.Nova.addAttachment(att.url, att.type));
};

// Make sure renderMessage exists
function renderMessage(msg, role = "assistant") {
  const messagesEl = document.getElementById("messages");
  const emptyState = document.getElementById("novaEmptyState");
  if (emptyState) emptyState.style.display = "none";
  const div = document.createElement("div");
  div.className = `nova-msg ${role}`;
  div.textContent = msg;
  messagesEl.appendChild(div);
  setTimeout(() => div.classList.add("show"), 50);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

window.Nova.renderMessage = renderMessage;

