const API_BASE = window.location.origin;

const elSessions = document.getElementById("sessions");
const elThread = document.getElementById("thread");
const elInput = document.getElementById("input");
const elSend = document.getElementById("btnSend");
const elNew = document.getElementById("btnNew");
const elClearAll = document.getElementById("btnClearAll");
const elSearch = document.getElementById("search");
const elStatus = document.getElementById("status");
const elBuild = document.getElementById("buildInfo");

// KB UI
const elFileInput = document.getElementById("fileInput");
const elKbQuery = document.getElementById("kbQuery");
const elKbResults = document.getElementById("kbResults");
const elKbStatus = document.getElementById("kbStatus");

let currentSessionId = null;
let sessions = [];

function escapeHtml(s) {
  return (s || "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

function setStatus(msg) {
  elStatus.textContent = msg || "";
}

function scrollBottom() {
  elThread.scrollTop = elThread.scrollHeight;
}

function msgBubble(role, content) {
  const wrap = document.createElement("div");
  wrap.className = "w-full flex";
  const isUser = role === "user";
  wrap.classList.add(isUser ? "justify-end" : "justify-start");

  const bubble = document.createElement("div");
  bubble.className =
    "max-w-[82%] rounded-2xl px-4 py-3 border " +
    (isUser
      ? "bg-indigo-600/20 border-indigo-500/30"
      : "bg-zinc-900 border-zinc-800");

  if (role === "assistant") {
    bubble.innerHTML = `<div class="prose prose-invert max-w-none">${marked.parse(content || "")}</div>`;
  } else {
    bubble.innerHTML = `<div class="whitespace-pre-wrap">${escapeHtml(content || "")}</div>`;
  }

  wrap.appendChild(bubble);
  return wrap;
}

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res;
}

async function loadHealth() {
  try {
    const res = await api("/api/health");
    const j = await res.json();
    elBuild.textContent = `${j.build || ""} · ${j.model || ""}`;
  } catch {}
}

function renderSessions() {
  elSessions.innerHTML = "";
  sessions.forEach(s => {
    const row = document.createElement("div");
    row.className = "px-2 py-2 rounded-xl hover:bg-zinc-900 flex items-center gap-2 cursor-pointer";

    const left = document.createElement("div");
    left.className = "flex-1 min-w-0";
    const title = document.createElement("div");
    title.className = "text-sm font-medium truncate";
    title.textContent = s.title || "New chat";
    const prev = document.createElement("div");
    prev.className = "text-xs text-zinc-500 truncate";
    prev.textContent = s.preview || "";
    left.appendChild(title);
    left.appendChild(prev);

    const btnPin = document.createElement("button");
    btnPin.className = "text-xs px-2 py-1 rounded-lg border border-zinc-800 hover:bg-zinc-800";
    btnPin.textContent = s.pinned ? "Unpin" : "Pin";
    btnPin.onclick = async (e) => {
      e.stopPropagation();
      await api(`/api/sessions/${s.id}`, { method: "PATCH", body: JSON.stringify({ pinned: !s.pinned }) });
      await refreshSessions();
    };

    const btnDel = document.createElement("button");
    btnDel.className = "text-xs px-2 py-1 rounded-lg border border-zinc-800 hover:bg-zinc-800";
    btnDel.textContent = "Delete";
    btnDel.onclick = async (e) => {
      e.stopPropagation();
      await api(`/api/sessions/${s.id}`, { method: "DELETE" });
      if (currentSessionId === s.id) {
        currentSessionId = null;
        elThread.innerHTML = "";
      }
      await refreshSessions();
    };

    row.onclick = async () => {
      currentSessionId = s.id;
      await loadMessages();
      highlightCurrent();
    };

    row.appendChild(left);
    row.appendChild(btnPin);
    row.appendChild(btnDel);
    elSessions.appendChild(row);
  });

  highlightCurrent();
}

function highlightCurrent() {
  const rows = [...elSessions.children];
  rows.forEach((row, idx) => {
    const s = sessions[idx];
    if (!s) return;
    row.classList.toggle("bg-zinc-900", s.id === currentSessionId);
  });
}

async function refreshSessions() {
  const q = (elSearch.value || "").trim();
  const res = await api(`/api/sessions${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  const j = await res.json();
  sessions = j.sessions || [];
  renderSessions();

  if (!currentSessionId && sessions.length) {
    currentSessionId = sessions[0].id;
    await loadMessages();
    highlightCurrent();
  }
}

async function createSession() {
  const res = await api("/api/sessions", { method: "POST", body: JSON.stringify({ title: "New chat" }) });
  const s = await res.json();
  currentSessionId = s.id;
  await refreshSessions();
  await loadMessages();
  highlightCurrent();
}

async function clearAll() {
  await api("/api/clear", { method: "POST", body: JSON.stringify({}) });
  currentSessionId = null;
  elThread.innerHTML = "";
  await refreshSessions();
}

async function loadMessages() {
  if (!currentSessionId) return;
  const res = await api(`/api/sessions/${currentSessionId}/messages`);
  const j = await res.json();
  const msgs = j.messages || [];
  elThread.innerHTML = "";
  msgs.forEach(m => elThread.appendChild(msgBubble(m.role, m.content)));
  scrollBottom();
}

async function send() {
  setStatus("");
  const text = (elInput.value || "").trim();
  if (!text) return;

  if (!currentSessionId) await createSession();

  elThread.appendChild(msgBubble("user", text));
  scrollBottom();
  elInput.value = "";

  const assistantWrap = msgBubble("assistant", "");
  const assistantBubble = assistantWrap.querySelector(".prose")?.parentElement || assistantWrap;
  elThread.appendChild(assistantWrap);
  scrollBottom();

  try {
    const res = await api(`/api/sessions/${currentSessionId}/messages/stream`, {
      method: "POST",
      body: JSON.stringify({ content: text })
    });

    if (!res.ok) {
      const errText = await res.text();
      setStatus(`❌ HTTP ${res.status} ${errText}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buf = "";
    let out = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";

      for (const part of parts) {
        const line = part.split("\n").find(l => l.startsWith("data:"));
        if (!line) continue;

        const jsonStr = line.slice(5).trim();
        let evt;
        try { evt = JSON.parse(jsonStr); } catch { continue; }

        if (evt.delta) {
          out += evt.delta;
          assistantBubble.innerHTML = `<div class="prose prose-invert max-w-none">${marked.parse(out)}</div>`;
          scrollBottom();
        }
        if (evt.error) setStatus(`❌ ${JSON.stringify(evt.error)}`);
      }
    }

    await refreshSessions();
  } catch {
    setStatus(`❌ Network error: Failed to fetch`);
  }
}

elSend.onclick = send;
elInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});

elNew.onclick = createSession;
elClearAll.onclick = clearAll;
elSearch.addEventListener("input", () => refreshSessions());

// ---------------- KB UI ----------------

function kbSetStatus(msg) {
  elKbStatus.textContent = msg || "";
}

function kbRenderResults(results) {
  elKbResults.innerHTML = "";
  if (!results || !results.length) {
    elKbResults.innerHTML = `<div class="text-xs text-zinc-500">No results</div>`;
    return;
  }
  results.forEach(r => {
    const card = document.createElement("div");
    card.className = "p-2 rounded-lg border border-zinc-800 bg-zinc-950 hover:bg-zinc-900";

    const top = document.createElement("div");
    top.className = "text-xs text-zinc-400";
    top.textContent = `${r.filename} · chunk ${r.chunk_index}`;

    const body = document.createElement("div");
    body.className = "text-xs text-zinc-200 mt-1 whitespace-pre-wrap";
    body.textContent = (r.content || "").slice(0, 220);

    card.appendChild(top);
    card.appendChild(body);
    elKbResults.appendChild(card);
  });
}

let kbTimer = null;
async function kbSearchNow() {
  const q = (elKbQuery.value || "").trim();
  if (!q) { kbRenderResults([]); kbSetStatus(""); return; }

  kbSetStatus("Searching…");
  try {
    const res = await api(`/api/kb/search?q=${encodeURIComponent(q)}`);
    const j = await res.json();
    kbRenderResults(j.results || []);
    kbSetStatus(`${(j.results || []).length} results`);
  } catch {
    kbSetStatus("❌ KB search failed");
  }
}

elKbQuery.addEventListener("input", () => {
  if (kbTimer) clearTimeout(kbTimer);
  kbTimer = setTimeout(kbSearchNow, 200);
});

elFileInput.addEventListener("change", async () => {
  const f = elFileInput.files && elFileInput.files[0];
  if (!f) return;

  kbSetStatus("Uploading…");
  try {
    const fd = new FormData();
    fd.append("file", f);

    const res = await fetch(`${API_BASE}/api/files/upload`, { method: "POST", body: fd });
    const j = await res.json();

    if (!res.ok) {
      kbSetStatus(`❌ Upload failed: ${JSON.stringify(j)}`);
      return;
    }

    kbSetStatus(`Indexed ${j.indexed_chunks} chunks from ${j.file.filename}`);
    elFileInput.value = "";
  } catch {
    kbSetStatus("❌ Upload failed");
  }
});

// boot
loadHealth();
refreshSessions();