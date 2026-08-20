
(function () {

async function forceNewChat() {
  window.NOVA_DISABLE_SOURCE_CARD_RENDER_ON_EMPTY_CHAT = true;

  try {
const sidInput = document.getElementById("sid");
if (sidInput) sidInput.value = "";

localStorage.removeItem("nova.session_id");
localStorage.removeItem("nova_active_session_id");
localStorage.removeItem("nova_session_id");

const input = document.getElementById("input");
if (input) input.value = "";

const emptyHtml = `
  <div class="nova-empty-chat">
    <div>
      <div class="nova-empty-chat-title">Nova is ready</div>
      <div class="nova-empty-chat-subtitle">Send a message to begin.</div>
    </div>
  </div>
`;

[
  document.getElementById("chat"),
  document.getElementById("messages"),
  document.getElementById("chatMessages"),
  document.getElementById("desktopMessages"),
  document.getElementById("chat")
].filter(Boolean).forEach(function (node) {
  node.innerHTML = emptyHtml;
});

document.querySelectorAll(
  "[data-nova-forced-source-cards='true'], .nova-source-cards"
).forEach(function (node) {
  node.remove();
});

console.log("[Nova Force New Chat] cleared chat");

  } catch (error) {
    console.warn("[Nova Force New Chat] failed", error);
  }
}

  // Duplicate new chat binding disabled.
  // The real New Session handler is owned by newSession() earlier.

  window.NovaDesktopForceNewChat = forceNewChat;

})();

