// C:\Users\Owner\nova\static\js\modules\api.js

export async function getJSON(url) {
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await safeReadText(res);
    throw new Error(`HTTP ${res.status}${text ? " - " + text : ""}`);
  }

  return res.json();
}

export async function createChat() {
  return getJSON("/api/chats/new", {
    method: "POST",
  });
}

export async function renameChat(chatId, title) {
  const res = await fetch(`/api/chats/${encodeURIComponent(chatId)}/rename`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) {
    const text = await safeReadText(res);
    throw new Error(`HTTP ${res.status}${text ? " - " + text : ""}`);
  }

  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`/api/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const text = await safeReadText(res);
    throw new Error(`HTTP ${res.status}${text ? " - " + text : ""}`);
  }

  return res.json();
}

export async function loadChats() {
  return getJSON("/api/chats");
}

export async function loadMessages(chatId) {
  return getJSON(`/api/chats/${encodeURIComponent(chatId)}`);
}

export async function sendMessage({ chatId, message, files = [] }) {
  const hasFiles = Array.isArray(files) && files.length > 0;

  if (hasFiles) {
    const form = new FormData();
    if (chatId) form.append("chat_id", chatId);
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
    headers: { "Content-Type": "application/json" },
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
    throw new Error(`HTTP ${res.status}${text ? " - " + text : ""}`);
  }

  if (!res.body) {
    throw new Error("Streaming response body missing.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  return {
    async *events() {
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let splitIndex;
        while ((splitIndex = buffer.indexOf("\n\n")) !== -1) {
          const rawBlock = buffer.slice(0, splitIndex);
          buffer = buffer.slice(splitIndex + 2);

          const evt = parseSSEBlock(rawBlock);
          if (evt) yield evt;
        }
      }

      const tail = buffer.trim();
      if (tail) {
        const evt = parseSSEBlock(tail);
        if (evt) yield evt;
      }
    },
  };
}

function parseSSEBlock(block) {
  if (!block) return null;

  const lines = block.split(/\r?\n/);
  let eventName = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  let data = null;
  const rawData = dataLines.join("\n");

  if (rawData) {
    try {
      data = JSON.parse(rawData);
    } catch {
      data = { raw: rawData };
    }
  }

  return { event: eventName, data };
}