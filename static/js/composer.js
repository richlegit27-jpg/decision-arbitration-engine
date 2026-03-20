document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const stopBtn = document.getElementById("stopBtn");
    const chatMessages = document.getElementById("chatMessages");

    let currentEvent = null;

    sendBtn.addEventListener("click", async () => {
        const text = input.value.trim();
        if(!text) return;

        // Show user message
        const userDiv = document.createElement("div");
        userDiv.textContent = "You: " + text;
        userDiv.style.margin = "4px 0";
        chatMessages.appendChild(userDiv);

        input.value = "";

        // Fake AI reply (replace later with SSE)
        const aiDiv = document.createElement("div");
        aiDiv.textContent = "AI: " + text;
        aiDiv.style.margin = "4px 0";
        aiDiv.style.fontStyle = "italic";
        chatMessages.appendChild(aiDiv);

        chatMessages.scrollTop = chatMessages.scrollHeight;
    });

    stopBtn.addEventListener("click", () => {
        input.value = "";
    });
});