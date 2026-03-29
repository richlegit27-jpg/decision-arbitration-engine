document.addEventListener("DOMContentLoaded", () => {
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const messages = document.getElementById("messages");
  const emptyState = document.getElementById("novaEmptyState");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("fileInput");
  const sessionId = "default-session";

  if (!sendBtn) return console.error("❌ sendBtn not found");

  // Chat send
  sendBtn.addEventListener("click", async () => {
    const content = chatInput.value.trim();
    if (!content) return;

    chatInput.value = "";
    if (emptyState) emptyState.style.display = "none";

    const msgDiv = document.createElement("div");
    msgDiv.classList.add("nova-chat-message", "user-message");
    msgDiv.textContent = content;
    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, session_id: sessionId })
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Unknown error");

      if (data.message && data.message.content) {
        const aiDiv = document.createElement("div");
        aiDiv.classList.add("nova-chat-message", "assistant-message");
        aiDiv.textContent = data.message.content;
        messages.appendChild(aiDiv);
        messages.scrollTop = messages.scrollHeight;
      }
    } catch(e) {
      console.error("ERROR:", e);
    }
  });

  // Enter / Ctrl+Enter / Shift+Enter
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      if (e.shiftKey) return; // newline
      e.preventDefault();
      sendBtn.click();
    }
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // Attachments
  uploadBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);

    try {
      const res = await fetch("/api/attachments/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Upload failed");

      // 1️⃣ Render attachment immediately
      const attachDiv = document.createElement("div");
      attachDiv.classList.add("nova-chat-message", "attachment-message");
      const ext = file.name.split(".").pop().toLowerCase();

      if (["png","jpg","jpeg","gif","webp"].includes(ext)) {
        const img = document.createElement("img");
        img.src = data.url;
        img.style.maxWidth = "250px";
        attachDiv.appendChild(img);
      } else if (["mp4","webm","ogg"].includes(ext)) {
        const video = document.createElement("video");
        video.src = data.url;
        video.controls = true;
        video.style.maxWidth = "250px";
        attachDiv.appendChild(video);
      } else {
        const link = document.createElement("a");
        link.href = data.url;
        link.textContent = `Download: ${file.name}`;
        link.target = "_blank";
        attachDiv.appendChild(link);
      }

      messages.appendChild(attachDiv);
      messages.scrollTop = messages.scrollHeight;

      // 2️⃣ Send AI request for image description
      const aiRes = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "",
          session_id: sessionId,
          attachments: [{ filename: file.name, url: data.url }]
        })
      });

      const aiData = await aiRes.json();
      if (aiData.ok && aiData.message && aiData.message.content) {
        const aiDiv = document.createElement("div");
        aiDiv.classList.add("nova-chat-message", "assistant-message");
        aiDiv.textContent = aiData.message.content;
        messages.appendChild(aiDiv);
        messages.scrollTop = messages.scrollHeight;
      }

    } catch(err) {
      console.error("Attachment ERROR:", err);
      alert("Attachment upload failed: " + err.message);
    } finally {
      fileInput.value = "";
    }
  });
});