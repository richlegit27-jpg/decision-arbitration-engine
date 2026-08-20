
const API_KEY = "testkey123";
const LS_SID = "nova.session_id";

const $ = (id) => document.getElementById(id);
const chat = $("chat");
const input = $("input");
const status = $("status");
const meta = $("meta");
const sidEl = $("sid");
const sendBtn = $("sendBtn");
const attachBtn = $("attachBtn");
const desktopFileInput = $("desktopFileInput");
const desktopAttachmentChip = $("desktopAttachmentChip");

let novaChatAbortController = null;

let pendingDesktopAttachments = [];
const newSessionBtn = $("newSessionBtn");
const newProjectBtn = $("newProjectBtn");
const desktopProjectList = $("desktopProjectList");


function esc(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

    function setStatus(s) {
      status.textContent = "status: " + s;
    }

    function setMeta(summaryText) {
      meta.textContent = "summary: " + ((summaryText || "").length) + " chars";
    }

    function autoScroll() {
      try {
        chat.scrollTop = chat.scrollHeight;
      } catch (e) {}
    }

function addMsg(role, text, meta = {}) {
  const wrap = document.createElement("div");
wrap.className = "msg " + role;
wrap.setAttribute(
  "data-message-id",
  "live_" + Date.now() + "_" + Math.random().toString(16).slice(2)
);

  const r = document.createElement("div");
  r.className = "role";
  r.textContent = role;

  const b = document.createElement("div");
  b.className = "bubble";
  b.textContent = text || "";

  // attach meta for source system
  wrap._meta = meta;

  wrap.appendChild(r);
  wrap.appendChild(b);
  chat.appendChild(wrap);
  autoScroll();
  return wrap;
}

function getSessionId() {
  const el = document.getElementById("sid");
  return (el && el.value ? el.value : "").trim();
}

function setSessionId(v) {
  const sid = (v || "").trim();

  const el = document.getElementById("sid");
  if (el) el.value = sid;

  try {
    localStorage.setItem(LS_SID, sid);
    localStorage.setItem("nova_active_session_id", sid);
    localStorage.setItem("nova_session_id", sid);
    sessionStorage.setItem("nova_active_session_id", sid);
  } catch (e) {}

  window.__NOVA_ACTIVE_SESSION_ID = sid;
}

function cleanVisibleAssistantText(text) {
  return String(text || "")
    .replace(/<[^>]*>/g, "")
    .trim();
}

function ensureLocalSessionId() {
  const sid = getSessionId();
  if (sid) return sid;

  const saved = localStorage.getItem(LS_SID);
  if (saved) {
    setSessionId(saved);
    return saved;
  }

  return "";
}

async function fetchJsonOrNull(url, options) {
  const response = await fetch(url, options || {});
  const raw = await response.text();

  if (!response.ok) {
    console.warn("[Nova Desktop] non-OK JSON endpoint", response.status, url, raw.slice(0, 120));
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn("[Nova Desktop] endpoint returned non-JSON", url, raw.slice(0, 120));
    return null;
  }
}

    function openDesktopMemoryPanel() {
      const panel = document.querySelector(".tools");
      const memory = document.querySelector(".memory-section");

      if (panel) {
        panel.style.display = "flex";
      }

      if (memory && typeof memory.scrollIntoView === "function") {
        memory.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    // NOVA_DESKTOP_SESSIONS_LIST_20260610
    function normalizeSessionListPayload(data) {
      if (!data) return [];
      if (Array.isArray(data)) return data;
      if (Array.isArray(data.sessions)) return data.sessions;
      if (Array.isArray(data.items)) return data.items;
      if (Array.isArray(data.data)) return data.data;
      return [];
    }

function getSessionTitle(session) {
  var title = String(session.title || "").trim();

  if (title && title.toLowerCase() !== "new chat") {
    return title;
  }

  return session.name
    || session.summary
    || session.last_message
    || session.preview
    || session.id
    || session.session_id
    || "Untitled session";
}

    function getSessionIdFromObject(session) {
      return session.id
        || session.session_id
        || session.client_session_id
        || "";
    }


    // NOVA_DESKTOP_MEMORY_PANEL_20260610
    function normalizeMemoryPayload(data) {
      if (!data) return [];
      if (Array.isArray(data)) return data;
      if (Array.isArray(data.memory)) return data.memory;
      if (Array.isArray(data.items)) return data.items;
      if (Array.isArray(data.data)) return data.data;
      return [];
    }

    function getMemoryText(item) {
      return item.text
        || item.content
        || item.value
        || item.memory
        || item.summary
        || safeRenderText(item);
    }

    function getMemoryKind(item) {
      return item.kind
        || item.category
        || item.type
        || item.source
        || "memory";
    }

    
    async function loadDesktopMemoryLegacy() {
      const list = $("desktopMemoryList");
      const count = $("desktopMemoryCount");

      if (list) {
        list.innerHTML = "";
        const loading = document.createElement("div");
        loading.className = "session-placeholder";
        loading.textContent = "Loading memory...";
        list.appendChild(loading);
      }

      try {
        const data = await fetchJsonOrNull("/api/memory");
        const items = normalizeDesktopMemoryItems(data);
        renderDesktopMemoryItems(items, data);
      } catch (error) {
        if (count) count.textContent = "0";

        if (list) {
          list.innerHTML = "";
          const failed = document.createElement("div");
          failed.className = "session-placeholder";
          failed.textContent = "Could not load memory.";
          list.appendChild(failed);
        }

        console.warn("[Nova Desktop] memory load failed", error);
      }
    }

    // NOVA_DESKTOP_EXECUTION_STATUS_20260610
    async function loadDesktopExecutionStatus() {
      const statusLabel = $("executionStatusLabel");
      const executionPercent = $("executionPercentLabel");
      const plannerPercent = $("plannerPercentLabel");
      const overallReadiness = $("overallReadinessLabel");
      const note = $("executionNote");

      try {
        const data = await fetchJsonOrNull("/api/backend/readiness");
        if (!data) throw new Error("Readiness endpoint did not return JSON");

        const exec = Number(data.execution_percent || 0);
        const planner = Number(data.planner_percent || 0);
        const overall = Number(data.overall_backend_readiness || 0);

        if (statusLabel) {
          statusLabel.textContent = exec >= 100 ? "ready" : "partial";
        }

        if (executionPercent) executionPercent.textContent = String(exec) + "%";
        if (plannerPercent) plannerPercent.textContent = String(planner) + "%";
        if (overallReadiness) overallReadiness.textContent = String(overall) + "%";

        if (note) {
          note.textContent = exec >= 100
            ? "Execution backend is ready. Use chat commands like continue, next, run step, run all, stop, or retry."
            : "Execution backend is partially ready. Chat commands may still work, but status is not fully green.";
        }
      } catch (error) {
        if (statusLabel) statusLabel.textContent = "offline";
        if (note) note.textContent = "Could not load execution readiness.";
      }
    }

async function loadDesktopSessions() {

  const list = document.getElementById("desktopSessionList");
  if (!list) return;

  try {
    const data = await fetch("/api/sessions").then(r => r.json());

    const sessions = (data.sessions || data.items || []);

    list.innerHTML = "";

sessions.forEach(session => {
  const sid = session.id;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "desktop-session-item";

btn.innerHTML = `
  <div class="desktop-session-title">${getSessionTitle(session)}</div>
  <div class="desktop-session-meta">${sid}</div>
  <button
    type="button"
    class="desktop-session-rename-btn"
    data-session-id="${sid}">
    Rename
  </button>
`;

const renameBtn = btn.querySelector(".desktop-session-rename-btn");

renameBtn.onclick = async (event) => {
  event.stopPropagation();

  const oldTitle = getSessionTitle(session);
  const nextTitle = prompt("Rename session:", oldTitle);

  if (!nextTitle || !nextTitle.trim()) return;

  try {
    await postJson("/api/sessions/rename", {
      session_id: sid,
      title: nextTitle.trim()
    });

    await loadDesktopSessions();

    if (sid === getSessionId()) {
      setStatus("Renamed to: " + nextTitle.trim());
    }

  } catch (error) {
    console.warn("[session rename failed]", error);
    setStatus("Rename failed");
  }
};

  btn.onclick = async () => {
    setSessionId(sid);
    console.log("[session selected]", sid);
    setStatus("loading session...");

    try {
      if (typeof window.NovaDesktopFetchSession === "function") {
        await window.NovaDesktopFetchSession(sid);
      } else {
        const data = await fetch("/api/sessions/" + encodeURIComponent(sid)).then(r => r.json());
        const sessionData = data.session || data;

if (typeof renderDesktopChatMessagesRescue === "function" && !window.__NOVA_RENDER_LOCK_GLOBAL) {
    window.__NOVA_RENDER_LOCK_GLOBAL = true;
    setTimeout(() => window.__NOVA_RENDER_LOCK_GLOBAL = false, 200);

    renderDesktopChatMessagesRescue(sessionData.messages || []);
}
      }

      setStatus("session selected");
    } catch (error) {
      console.warn("[session selected failed]", error);
      setStatus("session load failed");
    }
  };

  list.appendChild(btn);
});

    console.log("[sessions rendered]", sessions.length);

  } catch (e) {
    console.warn("[loadDesktopSessions failed]", e);
  }
}
window.loadDesktopSessions = loadDesktopSessions;


function startDesktopSessionSync() {
  window.__novaEvents = window.__novaEvents || {
    listeners: {},
    emit(event, data) {
      (this.listeners[event] || []).forEach(fn => fn(data));
    },
    on(event, fn) {
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(fn);
    }
  };

  window.__novaEvents.on("sessions:updated", async () => {
    try {
      const data = await fetchJsonOrNull("/api/sessions");
      if (!data) return;

      const sessions =
        normalizeSessionListPayload(data) ||
        data?.sessions ||
        data?.items ||
        data?.data ||
        (Array.isArray(data) ? data : []);

      __desktopSessionCache = sessions;
      __desktopSessionCacheReady = true;

    } catch (e) {
      console.warn("[SessionSync event] failed", e);
    }
  });
}

function stopDesktopSessionSync() {
  if (__sessionSyncTimer) {
    clearInterval(__sessionSyncTimer);
    __sessionSyncTimer = null;
  }
}

    function refreshDesktopPanels() {
      // NOVA_REFRESH_DESKTOP_PANELS_NOOP_20260610
      // Intentionally no-op. Sessions and memory are opened by the desktop rescue handlers.
      return null;
    }
    
    async function refreshSummaryMeta() {
      // NOVA_DISABLE_MISSING_DESKTOP_SUMMARY_ENDPOINT_20260610
      const summary =
        document.getElementById("desktopSummary") ||
        document.getElementById("summary") ||
        document.querySelector("[data-summary]");

      if (summary && !summary.textContent.trim()) {
        summary.textContent = "No summary yet.";
      }

      return null;
    }

async function newSession() {
  try {
    const data = await fetch("/api/sessions/new", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
      },
      body: JSON.stringify({ title: "New Chat" })
    }).then(r => r.json());

    const sid = data.active_session_id || data.session_id || data.session?.id;

    if (sid) {
      setSessionId(sid);
      localStorage.setItem(LS_SID, sid);
    }

    window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = false;
    window.NOVA_PENDING_NEW_SESSION_ID = "";

    pendingDesktopAttachments = [];

    if (typeof renderDesktopAttachmentChip === "function") {
      renderDesktopAttachmentChip();
    } else if (typeof renderDesktopAttachments === "function") {
      renderDesktopAttachments();
    }

    if (input) {
      input.value = "";
      input.style.height = "auto";
    }

    if (typeof renderDesktopChatMessagesRescue === "function" &&
        !window.__NOVA_RENDER_LOCK_GLOBAL) {

      window.__NOVA_RENDER_LOCK_GLOBAL = true;
      setTimeout(() => window.__NOVA_RENDER_LOCK_GLOBAL = false, 200);

      renderDesktopChatMessagesRescue([]);
    }

    await loadDesktopSessions();
    setStatus("new session ready");
    refreshSummaryMeta();
    refreshDesktopPanels();

  } catch (error) {
    console.warn("[newSession failed]", error);
    setStatus("new session failed");
  }
}

    async function summarizeNow() {
      if (!getSessionId()) {
        // do not create fake frontend session ids
      }

      setStatus("summarizing...");
      summarizeBtn.disabled = true;

      try {
        const j = await Promise.resolve({ ok: false, skipped: true, reason: "desktop summary endpoint disabled" }) /* {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
          },
          body: JSON.stringify({ session_id: getSessionId(), summarize: true })
        }); */

        if (!j) throw new Error("Summarize endpoint did not return JSON");
        setMeta(j.summary || j.text || "");
        addMsg("assistant", j.summary || j.text || "Summary refreshed.");
        setStatus("idle");
      } finally {
        summarizeBtn.disabled = false;
      }
    }

    // NOVA_DESKTOP_ATTACHMENT_PROMPT_CLARITY_20260610
    function clarifyAttachmentPrompt(text, attachments) {
      const clean = String(text || "").trim();
      const hasAttachment = Array.isArray(attachments) && attachments.length > 0;

      if (!hasAttachment) return clean;

      const lower = clean.toLowerCase();

      const vagueAttachmentPrompts = [
        "what is this",
        "what is this?",
        "what's this",
        "whats this",
        "summarize this",
        "summarize this file",
        "read this",
        "explain this",
        "what does this say",
        "what does this file say"
      ];

      if (!clean) {
        return "Summarize the attached file.";
      }

      if (vagueAttachmentPrompts.indexOf(lower) !== -1) {
        return clean + " attached file.";
      }

      return clean;
    }
    // NOVA_DESKTOP_ATTACH_UPLOAD_20260610

function showDesktopAttachmentChip(text) {
  let chip = document.getElementById("desktopAttachmentChip") || desktopAttachmentChip;

  if (!chip) {
    chip = document.createElement("div");
    chip.id = "desktopAttachmentChip";

    const composer = document.querySelector(".composer") || input?.parentElement || document.body;
    if (composer && composer.parentElement) {
      composer.parentElement.insertBefore(chip, composer);
    } else {
      document.body.appendChild(chip);
    }
  }

  chip.hidden = false;
  chip.style.display = "flex";
  chip.style.alignItems = "center";
  chip.style.justifyContent = "space-between";
  chip.style.gap = "10px";
  chip.style.width = "100%";
  chip.style.boxSizing = "border-box";
  chip.style.margin = "8px 0";
  chip.style.padding = "8px 10px";
  chip.style.border = "1px solid rgba(255,255,255,.2)";
  chip.style.borderRadius = "10px";
  chip.style.fontSize = "13px";
  chip.style.opacity = "0.9";

  chip.innerHTML = `
    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${text}</span>
    <button type="button" id="desktopAttachmentDeleteBtn" title="Remove attachment" aria-label="Remove attachment"
      style="border:1px solid rgba(255,255,255,.18);border-radius:999px;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;background:rgba(255,255,255,.12);color:inherit;font-size:18px;line-height:1;font-weight:700;">
      &times;
    </button>
  `;

  const deleteBtn = document.getElementById("desktopAttachmentDeleteBtn");
  if (deleteBtn) {
    deleteBtn.onclick = function (event) {
      event.preventDefault();
      event.stopPropagation();
      clearDesktopAttachments();
      console.log("&#128206; ATTACHMENT REMOVED");
    };
  }

  console.log("&#128206; CHIP SHOWN", chip);
}

function clearDesktopAttachments() {
  pendingDesktopAttachments = [];

const chip = document.getElementById("desktopAttachmentChip") || desktopAttachmentChip;

if (chip) {
  chip.hidden = true;
  chip.style.display = "none";
  chip.innerHTML = "";
}

  if (desktopFileInput) {
    desktopFileInput.value = "";
  }
}

    function normalizeUploadedAttachment(data, file) {
      const uploaded = data || {};
      return {
        filename: uploaded.filename || uploaded.name || (file ? file.name : ""),
        original_filename: uploaded.original_filename || uploaded.filename || (file ? file.name : ""),
        name: uploaded.original_filename || uploaded.filename || (file ? file.name : ""),
        mime_type: uploaded.mime_type || uploaded.content_type || (file ? file.type : ""),
        size: uploaded.size || uploaded.size_bytes || (file ? file.size : 0),
        url: uploaded.url || uploaded.file_url || "",
        file_url: uploaded.file_url || uploaded.url || ""
      };
    }

async function uploadDesktopAttachment(file) {
  if (!file) {
    console.warn("No file passed to uploadDesktopAttachment");
    return;
  }

  console.log("UPLOAD FILE:", file);

  const formData = new FormData();
  formData.append("file", file);


  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData
  });

  const raw = await response.text();
  let data = null;

  try {
    data = JSON.parse(raw);
  } catch (e) {
    console.warn("Non-JSON response:", raw);
  }

  if (!response.ok || data?.ok === false) {
    throw new Error(data?.error || "Upload failed");
  }

const attachment = normalizeUploadedAttachment
  ? normalizeUploadedAttachment(data, file)
  : {
      filename: data.filename || data.stored || file.name,
      original_filename: data.original_filename || file.name,
      name: file.name,
      mime_type: data.mime_type || file.type,
      size: data.size || file.size,
      url: data.url || data.file_url,
      file_url: data.file_url || data.url
    };

console.log("&#128206; NORMALIZED ATTACHMENT", attachment);
pendingDesktopAttachments = pendingDesktopAttachments || [];
pendingDesktopAttachments.push(attachment);

if (window.Nova && window.Nova.chat && window.Nova.chat.state) {
    window.Nova.chat.state.pendingAttachments =
        pendingDesktopAttachments.slice();
}

console.log("📎 ATTACHMENT STORED", pendingDesktopAttachments);

  showDesktopAttachmentChip(
    "Attached: <strong>" + (file.name || "file") + "</strong>"
  );

  return attachment;
}

function buildDesktopChatPayload(text, attachments) {
  const forceNew = window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND === true;
const sid = forceNew
  ? (window.NOVA_PENDING_NEW_SESSION_ID || getSessionId())
  : getSessionId();

  const payload = {
    text: text,
    user_text: text,
    message: text,
    attachments: attachments || []
  };

  if (sid) {
    payload.session_id = sid;
    payload.client_session_id = sid;
  }

  if (forceNew) {
    payload.force_new_session = true;
    payload.new_session = true;
  }

  return payload;
}

// ==========================
// MEMORY DETECTION (FIXED)
// ==========================
function isDesktopDirectMemoryMessage(text) {
  const clean = String(text || "").trim().toLowerCase();

  if (!clean) return false;

  return (
    clean.startsWith("remember that ") ||
    clean.startsWith("remember this ") ||
    clean.startsWith("remember ") ||
    clean.startsWith("save this ") ||
    clean.startsWith("save to memory ") ||
    clean.startsWith("store this ") ||
    clean.startsWith("note that ") ||
    clean.startsWith("add to memory ") ||
    clean.includes("what is my current nova focus") ||
    clean.includes("what's my current nova focus") ||
    clean.includes("what is my current project focus") ||
    clean.includes("what's my current project focus") ||
    clean.includes("what are we focused on") ||
    clean.includes("what am i focused on")
  );
}

// REMOVED: duplicate chat pipeline (non-streaming)
// All requests now go through sendText() unified streaming system

// REMOVED: broken duplicate attachment chat pipeline
// All chat now handled by sendText() streaming system

resetDesktopUIState?.();
clearDesktopAttachments?.();

function resetDesktopUIState() {
    pendingDesktopAttachments = [];
    clearDesktopAttachments?.();

    const chip = document.getElementById("desktopAttachmentChip");
    if (chip) {
        chip.hidden = true;
        chip.innerHTML = "";
    }
}

function updateAssistantStream(node, text) {
  node._streamBuffer = text;

  const bubble = node.querySelector(".bubble");
  if (!bubble) return;

  // cancel any existing typing safely
  if (bubble._typingAbort) {
    bubble._typingAbort();
  }

  bubble.textContent = "";

  setTimeout(() => {
    typeText(bubble, text);
  }, 150);
}

function typeText(node, text) {
  if (node._typingTimer) {
    clearTimeout(node._typingTimer);
  }

  let i = 0;
  const words = String(text || "").split(" ");
  let aborted = false;

  node.textContent = "";

  node._typingAbort = () => {
    aborted = true;
    clearTimeout(node._typingTimer);
  };

  function delay(word, index) {
    if (index === 0) return 160;
    if (/[.,!?]$/.test(word)) return 140;
    if (word.length > 10) return 90;
    return 35;
  }

  function tick() {
    if (aborted) return;

    if (i < words.length) {
      node.textContent += (i === 0 ? "" : " ") + words[i];

      const d = delay(words[i], i);
      i++;

      node._typingTimer = setTimeout(tick, d);
    }
  }

  tick();
}

function showThinking(node) {
  let dots = 0;
  node.textContent = "thinking";

  const interval = setInterval(() => {
    dots = (dots + 1) % 4;
    node.textContent = "thinking" + ".".repeat(dots);
  }, 300);

  return () => clearInterval(interval);
}

async function sendText(textOverride) {
  console.log("&#128206; sendText TRIGGERED");

  const liveInput = document.getElementById("input") || document.querySelector("textarea");
  const capturedText = window.__novaLastInputBeforeSend || "";
  const rawText = String(textOverride || capturedText || liveInput?.value || "").trim();

  window.__novaLastInputBeforeSend = "";

  const attachments = pendingDesktopAttachments.slice();
  const text = clarifyAttachmentPrompt(rawText, attachments);

  console.log("&#128206; SEND SNAPSHOT", { rawText, text, attachments });

  if (!text && !attachments.length) return;

  input.value = "";
  input.style.height = "auto";

setStatus("loading...");

novaChatAbortController = new AbortController();

sendBtn.disabled = false;
sendBtn.textContent = "Stop";
sendBtn.dataset.mode = "stop";

addMsg("user", text);
const assistantNode = addMsg("assistant", "");

try {
  console.log("&#128206; CHAT REQUEST START", { text, attachments });

  const forcingNewSession = window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND === true;

  const response = await fetch("/api/chat", {
    signal: novaChatAbortController.signal,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY
    },
    body: JSON.stringify(buildDesktopChatPayload(text, attachments))
  });

if (forcingNewSession) {
  window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = false;
window.NOVA_PENDING_NEW_SESSION_ID = "";
}

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText);
    }

    const raw = await response.text();

    let data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      throw new Error("Invalid JSON from server: " + raw.slice(0, 200));
    }

    const freshSessionId =
      data.session_id ||
      data.active_session_id ||
      data.session?.id ||
      data.assistant_message?.session_id;

    if (freshSessionId && freshSessionId !== "[object HTMLInputElement]") {
      setSessionId(String(freshSessionId));
      console.log("[NOVA sessions] adopted backend session", freshSessionId);

console.log("[Nova Desktop Sessions Button] clicked");

if (typeof loadDesktopSessions === "function") {
  loadDesktopSessions();
}

    }

    renderAssistantMessage(assistantNode, data);

    setStatus("done");
    clearDesktopAttachments();
    refreshSummaryMeta();
    refreshDesktopPanels();

// NOVA_LEGACY_MEMORY_AUTOLOAD_DISABLED

  } catch (e) {
    console.warn("sendText error:", e);
    assistantNode.textContent = "Error generating response";
    setStatus("error");

  } finally {
    novaChatAbortController = null;
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
    sendBtn.dataset.mode = "send";
    setStatus("ready");
    }
}

function renderMessageWithCodeBlocks(container, text) {
    container.innerHTML = "";

    const raw = String(text || "");

    function safeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function renderMarkdownChunk(value) {
        const chunk = String(value || "");

        if (window.marked && typeof window.marked.parse === "function") {
            return window.marked.parse(chunk);
        }

        return safeHtml(chunk)
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\n/g, "<br>");
    }

    const parts = raw.split(/```([\s\S]*?)```/g);

    parts.forEach((part, index) => {
        if (index % 2 === 0) {
            const div = document.createElement("div");
            div.className = "nova-markdown";
            div.innerHTML = renderMarkdownChunk(part);
            container.appendChild(div);
            return;
        }

        const firstLine = part.split("\n")[0].trim();
        const hasLang = /^[a-zA-Z0-9_-]+$/.test(firstLine);
        const lang = hasLang ? firstLine : "none";
        const codeText = hasLang ? part.split("\n").slice(1).join("\n") : part;

        const pre = document.createElement("pre");
        pre.className = "nova-code-block";

        const code = document.createElement("code");
        code.className = lang !== "none" ? "language-" + lang : "";

if (window.Prism && lang !== "none") {
    code.textContent = codeText;
    setTimeout(() => Prism.highlightElement(code), 0);
} else {
    if (typeof fallbackHighlight === "function") {
        code.innerHTML = fallbackHighlight(codeText, lang);
    } else {
        code.textContent = codeText;
    }
}

const badge = document.createElement("div");
badge.className = "nova-code-lang";
badge.textContent = (lang || "TEXT").toUpperCase();

pre.appendChild(badge);

const copy = document.createElement("button");
copy.type = "button";
copy.className = "nova-code-copy";
copy.textContent = "Copy";

        copy.onclick = async () => {
            await navigator.clipboard.writeText(codeText || "");
            copy.textContent = "Copied";
            setTimeout(() => copy.textContent = "Copy", 900);
        };

        pre.appendChild(copy);
        pre.appendChild(code);
        container.appendChild(pre);
    });
}

/* =========================================================
   renderAssistantMessage
   SINGLE SOURCE OF TRUTH (CLEAN SMFF VERSION)
   ========================================================= */

function renderAssistantMessage(assistantBubble, data) {
    if (!assistantBubble || assistantBubble.dataset.rendered === "1") {
        return;
    }

    assistantBubble.dataset.rendered = "1";

const assistantMessage = {
    text:
        data.assistant_message?.text ||
        data.text ||
        data.response ||
        "",

    meta: {
        sources:
            data.assistant_message?.meta?.sources ||
            data.sources ||
            []
    },

    image:
        data.image_url ||
        data.assistant_message?.image_url ||
        null
};

    let bubble = assistantBubble.querySelector(".bubble");

    if (!bubble) {
        bubble = document.createElement("div");
        bubble.className = "bubble";
        assistantBubble.appendChild(bubble);
    }

renderMessageWithCodeBlocks(bubble, assistantMessage.text || "");

    const actions = document.createElement("div");
    actions.className = "message-actions";
    actions.style.marginTop = "8px";
    actions.style.display = "flex";
    actions.style.gap = "8px";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.textContent = "Copy";

    copyBtn.onclick = async () => {
        try {
            await navigator.clipboard.writeText(assistantMessage.text || "");
            copyBtn.textContent = "Copied";
            setTimeout(() => {
                copyBtn.textContent = "Copy";
            }, 900);
        } catch (e) {
            copyBtn.textContent = "Copy failed";
        }
    };

    const regenBtn = document.createElement("button");
    regenBtn.type = "button";
    regenBtn.textContent = "Regen";

    regenBtn.onclick = () => {
        const inputEl = document.getElementById("input");
        if (!inputEl) return;

        const lastUser = window.__NOVA_LAST_USER_MESSAGE || inputEl.value || "";
        if (!lastUser) return;

        inputEl.value = lastUser;
        handleSendClick(lastUser);
    };

    actions.appendChild(copyBtn);
    actions.appendChild(regenBtn);
    assistantBubble.appendChild(actions);

    if (assistantMessage.image) {
        const imageWrap = document.createElement("div");
        imageWrap.style.marginTop = "10px";

        const img = document.createElement("img");
        img.src = assistantMessage.image;
        img.style.maxWidth = "100%";
        img.style.borderRadius = "14px";

        imageWrap.appendChild(img);
        assistantBubble.appendChild(imageWrap);
    }
}

/* =========================
   END renderAssistantMessage
   ========================= */

function handleSendClick(prompt = "") {
  if (window.__NOVA_HANDLE_SEND_LOCK__) {
    console.warn("[NOVA send] blocked duplicate handleSendClick");
    return;
  }

  window.__NOVA_HANDLE_SEND_LOCK__ = true;

  Promise.resolve(sendText(prompt))
    .catch((e) => {
      console.warn("[NOVA send] failed", e);
    })
    .finally(() => {
      setTimeout(() => {
        window.__NOVA_HANDLE_SEND_LOCK__ = false;
      }, 500);
    });
}

const summarizeBtn =
    $("summarizeBtn");

if (summarizeBtn) {
    summarizeBtn.addEventListener(
        "click",
        () =>
            summarizeNow().catch(e => {
                setStatus("error");
                alert(e.message || e);
            })
    );
}

    document.querySelectorAll("[data-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        handleSendClick(button.getAttribute("data-prompt") || "");
      });
    });

document.querySelectorAll("[data-nova-quick-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.getAttribute("data-nova-quick-action");

    const prompts = {
      plan: "I want to plan something. Help me organize the next steps.",
      write: "Help me write something."
    };

    handleSendClick(prompts[action] || "");
  });
});

    try {
      const saved = localStorage.getItem(LS_SID);
      if (saved) setSessionId(saved);
    } catch (e) {}

// =========================
// SAFE FINAL INIT BLOCK
// =========================

refreshSummaryMeta();
refreshDesktopPanels();

window.NOVA_DESKTOP_INLINE_SEND_ACTIVE = true;

if (sendBtn && input) {
  sendBtn.addEventListener("mousedown", () => {
    const liveInput = document.getElementById("input") || document.querySelector("textarea");
    window.__novaLastInputBeforeSend = liveInput ? liveInput.value : "";
    console.log("&#128206; CAPTURE BEFORE CLICK", window.__novaLastInputBeforeSend);
  }, true);

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();

  if (window.__NOVA_SEND_CLICK_LOCK__) return;

  window.__NOVA_SEND_CLICK_LOCK__ = true;

  handleSendClick();

  setTimeout(() => {
    window.__NOVA_SEND_CLICK_LOCK__ = false;
  }, 1200);
}, true);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendClick();
    }
  });
}



document.querySelectorAll("[data-nova-quick-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.getAttribute("data-nova-quick-action");

    const prompts = {
      summarize: "Summarize this.",
      plan: "I want to plan something. Help me organize the next steps.",
      write: "Help me write something.",
    };

    handleSendClick(prompts[action] || "");
  });
});

if (attachBtn && desktopFileInput) {
  attachBtn.addEventListener("click", () => {
    desktopFileInput.value = "";
    desktopFileInput.click();
  });

  desktopFileInput.addEventListener("change", () => {
    const file = desktopFileInput.files && desktopFileInput.files[0];
    if (!file) return;

    uploadDesktopAttachment(file).catch((error) => {
      clearDesktopAttachments();
      addMsg("assistant", "Upload error: " + (error.message || error));
    });
  });
}

// safe data-prompt binding
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    handleSendClick(button.getAttribute("data-prompt") || "");
  });
});

// session restore safe
try {
  const saved = localStorage.getItem(LS_SID);
  if (saved) setSessionId(saved);
} catch (e) {}

refreshSummaryMeta();
refreshDesktopPanels();


// =========================
// SAFE UTILITY FUNCTIONS
// (NO IIFE, NO BRACES PROBLEMS)
// =========================

function normalizeMemoryPayload(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.memory)) return data.memory;
  if (Array.isArray(data.items)) return data.items;
  if (data.data && Array.isArray(data.data.memory)) return data.data.memory;
  if (data.data && Array.isArray(data.data.items)) return data.data.items;
  return [];
}

  function renderMemoryFallback(data) {
    var list = $("desktopMemoryList");
    var count = $("desktopMemoryCount");
    var items = normalizeMemoryPayload(data);

    if (count) count.textContent = String(items.length);

    if (!list) return;

    list.innerHTML = "";

    if (!items.length) {
      var empty = document.createElement("div");
      empty.className = "session-placeholder";
      empty.textContent = "No memory items found.";
      list.appendChild(empty);
      return;
    }

    items.slice(0, 20).forEach(function (item) {
      var row = document.createElement("div");
      row.className = "desktop-memory-item";

      var title = document.createElement("div");
      title.className = "desktop-memory-title";
      title.textContent = item.kind || item.category || item.type || item.title || "Memory";

      var body = document.createElement("div");
      body.className = "desktop-memory-body";
      body.textContent = item.text || item.value || item.content || item.summary || JSON.stringify(item);

      row.appendChild(title);
      row.appendChild(body);
      list.appendChild(row);
    });
  }

async function loadMemory() {
  try {
    var res = await fetch("/api/memory", {
      headers: { "Accept": "application/json" }
    });

    var data = await res.json();

    renderMemoryFallback(data);
    setStatusSafe("memory loaded");

  } catch (error) {
    if (list) {
      list.innerHTML = "";

      var failed = document.createElement("div");
      failed.className = "session-placeholder";
      failed.textContent = "Could not load memory.";

      list.appendChild(failed);
    }

    setStatusSafe("memory failed");
    console.warn("[Nova Desktop Rescue] memory failed", error);
  }
}

  function normalizeSessionPayload(data) {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.sessions)) return data.sessions;
    if (data.data && Array.isArray(data.data.sessions)) return data.data.sessions;
    if (Array.isArray(data.items)) return data.items;
    return [];
  }


  // NOVA_DESKTOP_SESSION_SELECT_LOAD_MESSAGES_20260610
  function getDesktopMessagesContainerRescue() {
    // NOVA_DESKTOP_RESCUE_MESSAGE_CONTAINER_20260610
    var existing =
      document.getElementById("messages") ||
      document.getElementById("chatMessages") ||
      document.getElementById("desktopMessages") ||
      document.getElementById("chat") ||
      document.querySelector(".messages") ||
      document.querySelector(".chat-messages") ||
      document.querySelector("[data-messages]");

    if (existing) return existing;

    var title = document.querySelector(".chat-title");
    var host =
      (title && title.parentElement) ||
      document.querySelector("main") ||
      document.querySelector(".chat") ||
      document.body;

    var box = document.createElement("div");
    box.id = "chat";
    box.className = "messages chat-messages desktop-rescue-messages";
    box.setAttribute("data-messages", "true");

    box.style.minHeight = "320px";
    box.style.maxHeight = "60vh";
    box.style.overflowY = "auto";
    box.style.padding = "16px";
    box.style.margin = "12px 0";
    box.style.border = "1px solid rgba(255,255,255,0.12)";
    box.style.borderRadius = "16px";

    if (title && title.nextSibling) {
      title.parentElement.insertBefore(box, title.nextSibling);
    } else {
      host.appendChild(box);
    }

    return box;
  }

  function normalizeDesktopChatMessagesRescue(data) {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.messages)) return data.messages;
    if (data.data && Array.isArray(data.data.messages)) return data.data.messages;
    if (data.chat && Array.isArray(data.chat.messages)) return data.chat.messages;
    if (data.session && Array.isArray(data.session.messages)) return data.session.messages;
    return [];
  }

