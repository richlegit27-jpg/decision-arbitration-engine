// C:\Users\Owner\nova\static\js\sse.js
function safeJsonParse(s) { try { return JSON.parse(s); } catch { return null; } }

function parseSseFrame(frame) {
  let eventName = "";
  const dataLines = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  const dataStr = dataLines.join("\n").trim();
  const payload = dataStr ? (safeJsonParse(dataStr) || { raw: dataStr }) : null;
  return { eventName, payload };
}

/**
 * Starts SSE stream and returns a stop() function.
 * If stop() is called, the fetch is aborted and the stream ends.
 */
export function startSseStream(url, bodyObj, handlers = {}, opts = {}) {
  const timeoutMs = Number(opts.timeoutMs || 45000);

  const controller = new AbortController();
  let lastDataAt = Date.now();

  const timer = setInterval(() => {
    const age = Date.now() - lastDataAt;
    if (age > timeoutMs) controller.abort("SSE timeout");
  }, 1000);

  const run = (async () => {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyObj),
        signal: controller.signal
      });

      if (!res.ok || !res.body) {
        const txt = await res.text().catch(() => "");
        const maybe = safeJsonParse(txt);
        const rawPreview = (txt || "").toString().slice(0, 280);
        const msg = maybe?.error || maybe?.message || (rawPreview ? rawPreview : `HTTP ${res.status}`);
        throw new Error(msg);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        lastDataAt = Date.now();
        buf += decoder.decode(value, { stream: true });

        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);

          // ignore ping/comment frames
          if (frame.startsWith(":")) continue;

          const { eventName, payload } = parseSseFrame(frame);
          if (!payload) continue;

          if (eventName === "start" && handlers.onStart) handlers.onStart(payload);
          if (eventName === "delta" && payload.delta && handlers.onDelta) handlers.onDelta(payload.delta, payload);

          if (eventName === "done") {
            if (handlers.onDone) handlers.onDone(payload);
            return;
          }

          if (eventName === "error") {
            const msg = payload.error || "Stream error";
            if (handlers.onError) handlers.onError(payload);
            throw new Error(msg);
          }
        }
      }
    } finally {
      clearInterval(timer);
    }
  })();

  return {
    stop: () => controller.abort("SSE stopped"),
    promise: run
  };
}