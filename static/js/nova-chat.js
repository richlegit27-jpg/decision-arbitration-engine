document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");
  const composerInput = document.getElementById("composerInput");
  const messages = document.getElementById("messages");

  const appendMessage = (role, text, attachments = []) => {
    const msg = document.createElement("div");
    msg.className = `nova-msg ${role}`;
    msg.innerHTML = text;

    attachments.forEach(att => {
      if (att.type === "image") { 
        const img = document.createElement("img"); 
        img.src = att.src; 
        img.className = "nova-msg-attachment"; 
        msg.appendChild(img); 
      }
      if (att.type === "video") { 
        const video = document.createElement("video"); 
        video.src = att.src; 
        video.controls = true; 
        video.className = "nova-msg-attachment"; 
        msg.appendChild(video); 
      }
    });

    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  };

  const sendMessage = async () => {
    const text = composerInput.value.trim();
    if (!text) return;
    appendMessage("user", text);
    composerInput.value = "";

    const placeholder = document.createElement("div");
    placeholder.className = "nova-msg assistant";
    placeholder.textContent = "Nova is thinking...";
    messages.appendChild(placeholder);
    messages.scrollTop = messages.scrollHeight;

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text, session_id: "demo" })
    }).then(r => r.json());

    placeholder.remove();
    appendMessage("assistant", response.message.content, response.message.attachments);
  };

  sendBtn?.addEventListener("click", sendMessage);
  composerInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { 
      e.preventDefault(); 
      sendMessage(); 
    }
  });
});