const btn = document.getElementById("sendBtn");
const input = document.getElementById("messageInput");

btn.addEventListener("click", async () => {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";

    try {
        const resp = await fetch("http://127.0.0.1:8743/api/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: "main", message: text })
        });

        // Plain text fallback
        const reply = await resp.text();
        console.log("Assistant reply:", reply);

    } catch (err) {
        console.error("Send failed:", err);
    }
});