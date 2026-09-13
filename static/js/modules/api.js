// C:\Users\Owner\nova\static\js\modules\api.js

export async function getJSON(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: {
            Accept: "application/json",
            ...(options.headers || {}),
        },
        cache: "no-store",
    });

    if (!res.ok) {
        const text = await safeReadText(res);
        throw new Error(
            `HTTP ${res.status}${text ? " - " + text : ""}`
        );
    }

    return res.json();
}

export async function createChat() {
    return getJSON("/api/chats/new", {
        method: "POST",
    });
}

export async function renameChat(chatId, title) {
    const res = await fetch(
        `/api/chats/${encodeURIComponent(chatId)}/rename`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({ title }),
        }
    );

    if (!res.ok) {
        const text = await safeReadText(res);
        throw new Error(
            `HTTP ${res.status}${text ? " - " + text : ""}`
        );
    }

    return res.json();
}

export async function deleteChat(chatId) {
    const res = await fetch(
        `/api/chats/${encodeURIComponent(chatId)}`,
        {
            method: "DELETE",
            headers: {
                Accept: "application/json",
            },
        }
    );

    if (!res.ok) {
        const text = await safeReadText(res);
        throw new Error(
            `HTTP ${res.status}${text ? " - " + text : ""}`
        );
    }

    return res.json();
}

export async function loadChats() {
    return getJSON("/api/chats");
}

export async function loadMessages(chatId) {
    return getJSON(
        `/api/chats/${encodeURIComponent(chatId)}`
    );
}

export async function sendMessage({
    chatId,
    message,
    files = [],
}) {
    const hasFiles =
        Array.isArray(files) &&
        files.length > 0;

    if (hasFiles) {
        const form = new FormData();

        if (chatId) {
            form.append("chat_id", chatId);
        }

        form.append("message", message ?? "");

        for (const file of files) {
            form.append("files", file);
        }

        return fetchEventStream("/api/chat/stream", {
            method: "POST",
            body: form,
        });
    }

    return fetchEventStream("/api/chat/stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            chat_id: chatId || "",
            message: message ?? "",
        }),
    });
}

async function safeReadText(res) {
    try {
        return (await res.text()).trim();
    } catch {
        return "";
    }
}

async function fetchEventStream(url, options) {
    const res = await fetch(url, options);

    if (!res.ok) {
        const text = await safeReadText(res);
        throw new Error(
            `HTTP ${res.status}${text ? " - " + text : ""}`
        );
    }

    if (!res.body) {
        throw new Error(
            "Streaming response body missing."
        );
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    return {
        async *events() {
            let buffer = "";

            while (true) {
                const {
                    value,
                    done,
                } = await reader.read();

                if (done) {
                    break;
                }

                buffer += decoder.decode(
                    value,
                    { stream: true }
                );

                let splitIndex;

                while (
                    (splitIndex =
                        buffer.indexOf("\n\n")) !== -1
                ) {
                    const rawBlock = buffer.slice(
                        0,
                        splitIndex
                    );

                    buffer = buffer.slice(
                        splitIndex + 2
                    );

                    const evt =
                        parseSSEBlock(rawBlock);

                    if (evt) {
                        yield evt;
                    }
                }
            }

            buffer += decoder.decode();

            const tail = buffer.trim();

            if (tail) {
                const evt = parseSSEBlock(tail);

                if (evt) {
                    yield evt;
                }
            }
        },
    };
}

function parseSSEBlock(block) {
    if (!block) {
        return null;
    }

    const lines = block.split(/\r?\n/);

    let explicitEventName = "";
    const dataLines = [];

    for (const line of lines) {
        if (line.startsWith("event:")) {
            explicitEventName =
                line.slice(6).trim();

            continue;
        }

        if (line.startsWith("data:")) {
            dataLines.push(
                line.slice(5).trim()
            );
        }
    }

    const rawData = dataLines.join("\n").trim();

    if (!rawData) {
        return null;
    }

    if (rawData === "[DONE]") {
        return {
            event: "done",
            data: {
                type: "done",
                done: true,
            },
        };
    }

    let data;

    try {
        data = JSON.parse(rawData);
    } catch {
        data = {
            content: rawData,
        };
    }

    const payloadType = String(
        data?.type ||
        data?.event ||
        ""
    )
        .trim()
        .toLowerCase();

    const eventName = normalizeEventName(
        explicitEventName,
        payloadType,
        data
    );

    return {
        event: eventName,
        data,
    };
}

function normalizeEventName(
    explicitEventName,
    payloadType,
    data
) {
    const explicit = String(
        explicitEventName || ""
    )
        .trim()
        .toLowerCase();

    if (explicit && explicit !== "message") {
        return explicit;
    }

    if (
        payloadType === "token" ||
        payloadType === "delta" ||
        payloadType === "content_delta" ||
        payloadType === "text_delta"
    ) {
        return "token";
    }

    if (
        payloadType === "done" ||
        payloadType === "complete" ||
        payloadType === "completed" ||
        payloadType === "finished"
    ) {
        return "done";
    }

    if (
        payloadType === "error" ||
        payloadType === "failed" ||
        payloadType === "failure"
    ) {
        return "error";
    }

    if (
        payloadType === "meta" ||
        payloadType === "start" ||
        payloadType === "started" ||
        payloadType === "status"
    ) {
        return "meta";
    }

    if (
        payloadType === "message" ||
        payloadType === "assistant_message" ||
        payloadType === "assistant-message" ||
        payloadType === "final"
    ) {
        return "message";
    }

    if (
        typeof data?.token === "string" ||
        typeof data?.delta === "string"
    ) {
        return "token";
    }

    if (
        typeof data?.content === "string" ||
        typeof data?.text === "string"
    ) {
        return "message";
    }

    return explicit || "message";
}