// C:\Users\Owner\nova\static\js\chat-stream.js

(() => {
    "use strict";

    function normalizeType(eventName, payload) {
        return String(
            eventName ||
            payload?.type ||
            payload?.event ||
            ""
        )
            .trim()
            .toLowerCase();
    }

    function extractContent(payload) {
        if (payload == null) {
            return "";
        }

        if (typeof payload === "string") {
            return payload;
        }

        const candidates = [
            payload.content,
            payload.text,
            payload.token,
            payload.delta,
            payload.message?.content,
            payload.message?.text,
            payload.response?.content,
            payload.response?.text,
        ];

        for (const value of candidates) {
            if (typeof value === "string" && value.length > 0) {
                return value;
            }
        }

        return "";
    }

    function dispatchEvent(eventName, payload, handlers) {
        const type = normalizeType(eventName, payload);

        if (
            type === "meta" ||
            type === "start" ||
            type === "started" ||
            type === "status"
        ) {
            handlers?.meta?.(payload);
            return;
        }

        if (
            type === "token" ||
            type === "delta" ||
            type === "content_delta" ||
            type === "text_delta"
        ) {
            handlers?.token?.(payload);
            return;
        }

        if (
            type === "message" ||
            type === "assistant_message" ||
            type === "assistant-message" ||
            type === "final"
        ) {
            handlers?.message?.(payload);

            if (!handlers?.message && handlers?.token) {
                handlers.token(payload);
            }

            return;
        }

        if (
            type === "done" ||
            type === "complete" ||
            type === "completed" ||
            type === "finished"
        ) {
            handlers?.done?.(payload);
            return;
        }

        if (
            type === "error" ||
            type === "failed" ||
            type === "failure"
        ) {
            handlers?.error?.(payload);
            return;
        }

        const content = extractContent(payload);

        if (content && handlers?.token) {
            handlers.token(payload);
        }
    }

    async function streamResponse(response, handlers) {
        if (!response?.body) {
            throw new Error("Streaming response has no readable body.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                break;
            }

            buffer += decoder.decode(value, {
                stream: true,
            });

            const parts = buffer.split(/\r?\n\r?\n/);

            while (parts.length > 1) {
                const chunk = parts.shift();

                if (chunk) {
                    parseEvent(chunk, handlers);
                }
            }

            buffer = parts[0] || "";
        }

        buffer += decoder.decode();

        if (buffer.trim()) {
            parseEvent(buffer, handlers);
        }
    }

    function parseEvent(raw, handlers) {
        const lines = String(raw || "").split(/\r?\n/);

        let eventName = "";
        const dataLines = [];

        for (const line of lines) {
            if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
                continue;
            }

            if (line.startsWith("data:")) {
                dataLines.push(line.slice(5).trim());
            }
        }

        if (dataLines.length === 0) {
            return;
        }

        const data = dataLines.join("\n").trim();

        if (!data || data === "[DONE]") {
            if (data === "[DONE]") {
                handlers?.done?.({
                    done: true,
                });
            }

            return;
        }

        let payload;

        try {
            payload = JSON.parse(data);
        } catch {
            payload = {
                content: data,
            };
        }

        dispatchEvent(eventName, payload, handlers);
    }

    window.NovaStream = {
        streamResponse,
        parseEvent,
        extractContent,
    };
})();