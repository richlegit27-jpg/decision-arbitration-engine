// C:\Users\Owner\nova\static\js\events.js
import { state, setCurrentChatId, setStreaming } from "./state.js";
import { apiJson, loadSessions, createSession, loadMessages, clearChat } from "./api.js";
import { startSseStream } from "./sse.js";
import {
  els,
  setStatus,
  clearMessagesUI,
  appendMessage,
  ensureStreamingAssistantPlaceholder,
  updateStreamingAssistant,
  finalizeStreamingAssistant,
  renderSidebar,
  scrollToBottom,
  setRowText
} from "./ui.js";

let activeStreamStop = null;
let sidebarSearch = "";

function stopActiveStream() {
  if (typeof activeStreamStop === "function") {
    try { activeStreamStop(); } catch {}
  }
  activeStreamStop = null;
}

function getLastUserRow() {
  if (!els.messages) return null;
  const rows = Array.from(els.messages.querySelectorAll(".msg-row.user"));
  return rows.length ? rows[rows.length - 1] : null;
}

async function refreshSidebar(selectChatId = null) {
  const sessions = await loadSessions();
  if (selectChatId) setCurrentChatId(selectChatId);

  renderSidebar(
    sessions,
    state.currentChatId,
    async (id) => {
      if (state.isStreaming) return;
      if (!id) return;
      await openChat(id);
    },
    async (id, title) => {
      await apiJson("/api/sessions/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: id, title })
      });
      await refreshSidebar(state.currentChatId);
    },
    async (id) => {
      if (state.isStreaming) return;

      const deletingCurrent = state.currentChatId === id;

      if (deletingCurrent) {
        stopActiveStream();
        clearMessagesUI();
        setStatus("");
      }

      await apiJson("/api/sessions/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: id })
      });

      const sessions2 = await loadSessions();
      if (!sessions2.length) {
        const newId = await createSession("New chat");
        await openChat(newId);
        return;
      }

      if (deletingCurrent) await openChat(sessions2[0].id);
      else await refreshSidebar(state.currentChatId);
    },
    async (id, pinned) => {
      await apiJson("/api/sessions/pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: id, pinned })
      });
      await refreshSidebar(state.currentChatId);
    },
    sidebarSearch
  );
}

export async function openChat(chatId) {
  if (!chatId) return;

  stopActiveStream();

  setCurrentChatId(chatId);
  await refreshSidebar(chatId);

  clearMessagesUI();
  setStatus("");

  const msgs = await loadMessages(chatId);
  for (const m of msgs) {
    if (m.role === "user" || m.role === "assistant" || m.role === "system") {
      appendMessage(m.role, m.content || "", m.id);
    }
  }
  scrollToBottom();
}

async function startChatStream(chatId, message) {
  const cid = (chatId || "").trim();
  const msg = (message || "").trim();

  if (!cid) { setStatus("Missing chat_id"); return; }
  if (!msg) { setStatus("Empty message"); return; }

  stopActiveStream();

  setStreaming(true);
  setStatus("Streaming…");

  // Create the user row immediately; msgid will be filled onStart
  const userRow = appendMessage("user", msg);

  let assistantText = "";
  const assistantMsgId = ensureStreamingAssistantPlaceholder();

  try {
    const stream = startSseStream("/api/chat/stream", { chat_id: cid, message: msg }, {
      onStart: (payload) => {
        if (userRow && payload?.user_msg_id) {
          userRow.dataset.msgid = String(payload.user_msg_id);
        }
      },
      onDelta: (delta) => {
        assistantText += delta;
        updateStreamingAssistant(assistantMsgId, assistantText);
      }
    }, { timeoutMs: 60000 });

    if (stream && typeof stream === "object" && typeof stream.stop === "function" && stream.promise) {
      activeStreamStop = stream.stop;
      await stream.promise;
    } else {
      await stream;
    }

    finalizeStreamingAssistant(assistantMsgId, assistantText);
    setStatus("");
    await refreshSidebar(cid);
  } catch (e) {
    finalizeStreamingAssistant(assistantMsgId, assistantText || "(stream stopped)");
    setStatus(String(e?.message || e || "Stream failed").slice(0, 160));
    console.error(e);
  } finally {
    stopActiveStream();
    setStreaming(false);
  }
}

async function startRegenerateStream(chatId) {
  const cid = (chatId || "").trim();
  if (!cid) { setStatus("Missing chat_id"); return; }

  stopActiveStream();

  setStreaming(true);
  setStatus("Regenerating…");

  let assistantText = "";
  const assistantMsgId = ensureStreamingAssistantPlaceholder();

  try {
    const stream = startSseStream("/api/chat/regenerate", { chat_id: cid }, {
      onDelta: (delta) => {
        assistantText += delta;
        updateStreamingAssistant(assistantMsgId, assistantText);
      }
    }, { timeoutMs: 60000 });

    if (stream && typeof stream === "object" && typeof stream.stop === "function" && stream.promise) {
      activeStreamStop = stream.stop;
      await stream.promise;
    } else {
      await stream;
    }

    finalizeStreamingAssistant(assistantMsgId, assistantText);
    setStatus("");
    await refreshSidebar(cid);
  } catch (e) {
    finalizeStreamingAssistant(assistantMsgId, assistantText || "(regenerate stopped)");
    setStatus(String(e?.message || e || "Regenerate failed").slice(0, 160));
    console.error(e);
  } finally {
    stopActiveStream();
    setStreaming(false);
  }
}

async function startEditLastStream(chatId, newText, messageId, userRow) {
  const cid = (chatId || "").trim();
  const msg = (newText || "").trim();
  const mid = Number(messageId || 0);

  if (!cid) { setStatus("Missing chat_id"); return; }
  if (!msg) { setStatus("Empty edit"); return; }

  stopActiveStream();

  setStreaming(true);
  setStatus("Editing…");

  // Update UI user bubble immediately
  if (userRow) setRowText(userRow, msg);

  let assistantText = "";
  const assistantMsgId = ensureStreamingAssistantPlaceholder();

  try {
    const stream = startSseStream("/api/chat/edit_last", { chat_id: cid, message: msg, message_id: mid }, {
      onDelta: (delta) => {
        assistantText += delta;
        updateStreamingAssistant(assistantMsgId, assistantText);
      }
    }, { timeoutMs: 60000 });

    if (stream && typeof stream === "object" && typeof stream.stop === "function" && stream.promise) {
      activeStreamStop = stream.stop;
      await stream.promise;
    } else {
      await stream;
    }

    finalizeStreamingAssistant(assistantMsgId, assistantText);
    setStatus("");
    await openChat(cid); // refresh messages so DB state matches UI
  } catch (e) {
    finalizeStreamingAssistant(assistantMsgId, assistantText || "(edit stopped)");
    setStatus(String(e?.message || e || "Edit failed").slice(0, 160));
    console.error(e);
  } finally {
    stopActiveStream();
    setStreaming(false);
  }
}

async function onSend() {
  if (state.isStreaming) return;
  const input = els.input;
  if (!input) return;

  const text = (input.value || "").trim();
  if (!text) return;

  if (!state.currentChatId) {
    const chatId = await createSession("New chat");
    await openChat(chatId);
  }

  const cid = (state.currentChatId || "").trim();
  if (!cid) { setStatus("No chat selected"); return; }

  input.value = "";
  await startChatStream(cid, text);
}

export function wireEvents() {
  if (els.input) {
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
      }
    });
  }

  if (els.chatSearch) {
    els.chatSearch.addEventListener("input", async (e) => {
      sidebarSearch = String(e.target?.value || "");
      await refreshSidebar(state.currentChatId);
    });
  }

  if (els.btnSend) els.btnSend.addEventListener("click", onSend);

  if (els.btnNewChat) {
    els.btnNewChat.addEventListener("click", async () => {
      if (state.isStreaming) return;
      const chatId = await createSession("New chat");
      await openChat(chatId);
    });
  }

  if (els.btnClear) {
    els.btnClear.addEventListener("click", async () => {
      if (state.isStreaming) return;
      if (!state.currentChatId) return;
      await clearChat(state.currentChatId);
      await openChat(state.currentChatId);
    });
  }

  if (els.btnRegenerate) {
    els.btnRegenerate.addEventListener("click", async () => {
      if (state.isStreaming) return;
      if (!state.currentChatId) return;
      await startRegenerateStream(state.currentChatId);
    });
  }

  // Double-click LAST user message bubble to edit + re-run
  if (els.messages) {
    els.messages.addEventListener("dblclick", async (e) => {
      if (state.isStreaming) return;
      if (!state.currentChatId) return;

      const row = e.target?.closest?.(".msg-row.user");
      if (!row) return;

      const lastUser = getLastUserRow();
      if (!lastUser || lastUser !== row) return; // only last user msg

      const currentText = row.querySelector(".msg-text")?.textContent || "";
      const next = prompt("Edit your last message", currentText);
      if (next === null) return;

      const newText = (next || "").trim();
      if (!newText || newText === currentText.trim()) return;

      const messageId = row.dataset.msgid;
      if (!messageId) {
        setStatus("No message id to edit (send again)");
        return;
      }

      await startEditLastStream(state.currentChatId, newText, messageId, row);
    });
  }
}

export async function boot() {
  await refreshSidebar(null);

  const sessions = await loadSessions();
  if (sessions.length) {
    await openChat(sessions[0].id);
  } else {
    const chatId = await createSession("New chat");
    await openChat(chatId);
  }
}