// MOBILE_GLOBAL_HELPERS_FINAL_LOCK_20260604
window.normalizeAssistantTextFromResponse = function(res) {
    if (!res) return "";

    if (typeof res === "string") return res.trim();

    const candidates = [
        res.assistant_message?.text,
        res.assistant_message?.content,
        res.assistantMessage?.text,
        res.assistantMessage?.content,
        res.message?.text,
        res.message?.content,
        res.response?.text,
        res.response?.content,
        res.text,
        res.content,
        res.reply,
        res.answer,
        res.output
    ];

    for (const value of candidates) {
        if (typeof value === "string" && value.trim()) return value.trim();
    }

    if (Array.isArray(res.messages) && res.messages.length) {
        for (let i = res.messages.length - 1; i >= 0; i--) {
            const msg = res.messages[i];
            if (!msg) continue;

            const role = String(msg.role || "").toLowerCase();
            const body = msg.text || msg.content || msg.message;

            if ((role === "assistant" || role === "model" || !role) && typeof body === "string" && body.trim()) {
                return body.trim();
            }
        }
    }

    return "";
};
