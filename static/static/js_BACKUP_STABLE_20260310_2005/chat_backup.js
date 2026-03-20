// C:\Users\Owner\nova\static\js\chat.js
(() => {
  const $ = (id) => document.getElementById(id);

  const sessionsListEl = $("sessionsList");
  const sessionsHintEl = $("sessionsHint");
  const sessionSearchEl = $("sessionSearch");

  const messagesEl = $("messages");
  const messagesScrollEl = $("messagesScroll");
  const emptyStateEl = $("emptyState");

  const composerEl = $("composer");
  const btnSend = $("btnSend");
  const btnNewChat = $("btnNewChat");
  const btnRefreshSessions = $("btnRefreshSessions");
  const btnClearUI = $("btnClearUI");
  const btnStop = $("btnStop");

  const chatTitleEl = $("chatTitle");
  const chatSubEl = $("chatSub");
  const statusDot = $("statusDot");
  const statusText = $("statusText");

  const charCountEl = $("charCount");
  const toastsEl = $("toasts");

  const srcModal = $("srcModal");
  const btnCloseSrc = $("btnCloseSrc");
  const srcTitle = $("srcTitle");
  const srcSub = $("srcSub");
  const srcBody = $("srcBody");

  let sessions = [];
  let activeChatId = null;

  let streamAbort = null;
  let streaming = false;

  // ---------------------------
  // Toasts
  // ---------------------------
  function toast(msg, kind = "info") {
    const el = document.createElement("div");
    el.className =
      "rounded-2xl border border-zinc-800 bg-zinc-950/85 glass px-4 py-3 text-sm shadow-lg flex items-start gap-3 fade-in";
    const badge = document.createElement("div");
    badge.className =
      "mt-0.5 h-2.5 w-2.5 rounded-full " +
      (kind === "error" ? "bg-red-500" : kind === "ok" ? "bg-emerald-500" : "bg-zinc-500");
    const text = document.createElement("div");
    text.className = "text-zinc-200";
    text.textContent = msg;

    el.appendChild(badge);
    el.appendChild(text);
    toastsEl.appendChild(el);

    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "all 250ms ease";
    }, 2400);

    setTimeout(() => el.remove(), 2900);
  }

  // ---------------------------
  // Status
  // ---------------------------
  function setStatus(label, mode = "idle") {
    statusText.textContent = label;
    statusDot.className =
      "inline-block h-2 w-2 rounded-full " +
      (mode === "busy" ? "bg-amber-500" : mode === "ok" ? "bg-emerald-500" : mode === "error" ? "bg-red-500" : "bg-zinc-500");
  }

  // ---------------------------
  // Modal
  // ---------------------------
  function openSourceModal(title, sub, body) {
    srcTitle.textContent = title || "Source";
    srcSub.textContent = sub || "";
    srcBody.textContent = body || "";
    srcModal.classList.remove("modal-hidden");
  }

  function closeSourceModal() {
    srcModal.classList.add("modal-hidden");
  }

  btnCloseSrc?.addEventListener("click", closeSourceModal);
  srcModal?.addEventListener("click", (e) => {
    if (e.target === srcModal) closeSourceModal();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!srcModal.classList.contains("modal-hidden")) return closeSourceModal();
      if (streaming && streamAbort) streamAbort.abort();
    }
  });

  // ---------------------------
  // Helpers
  // ---------------------------
  function escapeHtml(s) {
    return (s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderMarkdown(text) {
    let html = "";
    try { html = marked.parse(text || ""); }
    catch { html = escapeHtml(text || "").replaceAll("\n", "<br/>"); }
    return html;
  }

  function enhanceCodeBlocks(containerEl) {
    const pres = containerEl.querySelectorAll("pre");
    pres.forEach((pre) => {
      if (pre.dataset.novaEnhanced === "1") return;
      pre.dataset.novaEnhanced = "1";

      // highlight.js
      const code = pre.querySelector("code");
      if (code && window.hljs) {
        try { window.hljs.highlightElement(code); } catch {}
      }

      // Copy button
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Copy";
      btn.className =
        "absolute top-2 right-2 rounded-xl px-3 py-1 text-[11px] font-semibold " +
        "bg-zinc-900/70 border border-zinc-700 hover:bg-zinc-900 transition";
      btn.addEventListener("click", async () => {
        const txt = pre.innerText || "";
        try {
          await navigator.clipboard.writeText(txt);
          btn.textContent = "Copied";
          setTimeout(() => (btn.textContent = "Copy"), 1200);
        } catch {
          toast("Clipboard blocked by browser.", "error");
        }
      });

      pre.appendChild(btn);
    });

    if (window.lucide) {
      try { window.lucide.createIcons(); } catch {}
    }
  }

  function fmtBytes(n) {
    if (!Number.isFinite(n) || n <= 0) return "";
    const units = ["B","KB","MB","GB"];
    let i = 0;
    let v = n;
    while (v >= 1024 && i < units.length-1) { v /= 1024; i++; }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
  }

  function fileIcon(name) {
    const ext = (name || "").split(".").pop().toLowerCase();
    if (ext === "pdf") return "file-text";
    if (ext === "doc" || ext === "docx") return "file-text";
    if (ext === "txt" || ext === "md") return "file";
    return "file";
  }

  // ---------------------------
  // Messages
  // ---------------------------
  function clearMessagesUI() {
    messagesEl.innerHTML = "";
    emptyStateEl.style.display = "block";
  }

  function scrollToBottom() {
    messagesScrollEl.scrollTop = messagesScrollEl.scrollHeight;
  }

  function attachCards(meta) {
    const files = meta?.files || meta?.attachments || [];
    if (!Array.isArray(files) || !files.length) return null;

    const wrap = document.createElement("div");
    wrap.className = "mt-2 space-y-2";

    for (const f of files) {
      const name = f.name || f.filename || "file";
      const size = f.size || f.bytes || 0;
      const url = f.url || f.href || null;

      const card = document.createElement("div");
      card.className = "att";

      const left = document.createElement("div");
      left.className = "left min-w-0";

      const ico = document.createElement("div");
      ico.className = "h-9 w-9 rounded-2xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-center";
      ico.innerHTML = `<i data-lucide="${fileIcon(name)}" class="w-4 h-4"></i>`;

      const text = document.createElement("div");
      text.className = "min-w-0";

      const nm = document.createElement("div");
      nm.className = "name";
      nm.textContent = name;

      const mt = document.createElement("div");
      mt.className = "meta";
      mt.textContent = [f.type || "", fmtBytes(size)].filter(Boolean).join(" · ");

      text.appendChild(nm);
      text.appendChild(mt);

      left.appendChild(ico);
      left.appendChild(text);

      const right = document.createElement("div");
      if (url) {
        const btn = document.createElement("a");
        btn.className = "btn";
        btn.textContent = "Open";
        btn.href = url;
        btn.target = "_blank";
        btn.rel = "noreferrer";
        right.appendChild(btn);
      } else {
        const btn = document.createElement("div");
        btn.className = "btn text-zinc-500";
        btn.textContent = "No link";
        right.appendChild(btn);
      }

      card.appendChild(left);
      card.appendChild(right);
      wrap.appendChild(card);
    }

    if (window.lucide) {
      try { window.lucide.createIcons(); } catch {}
    }

    return wrap;
  }

  function citationChips(meta) {
    // expected:
    // meta.citations = [{label:"[1] file.pdf", chunk_id:"...", text:"...", doc:"...", ...}]
    const cits = meta?.citations || meta?.sources || [];
    if (!Array.isArray(cits) || !cits.length) return null;

    const wrap = document.createElement("div");
    wrap.className = "mt-3 flex flex-wrap gap-2";

    cits.slice(0, 12).forEach((c, idx) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.innerHTML = `<span class="dot"></span>${escapeHtml(c.label || `[${idx+1}] Source`)}`;
      chip.addEventListener("click", () => {
        const title = c.doc || c.file || c.label || "Source";
        const sub = c.chunk_id ? `chunk ${c.chunk_id}` : (c.loc || "");
        const body = c.text || c.snippet || "No text in meta yet.";
        openSourceModal(title, sub, body);
      });
      wrap.appendChild(chip);
    });

    return wrap;
  }

  function addMessageBubble(role, text, opts = {}) {
    emptyStateEl.style.display = "none";

    const row = document.createElement("div");
    row.className = "flex " + (role === "user" ? "justify-end" : "justify-start") + " fade-in";

    const wrap = document.createElement("div");
    wrap.className = "relative group max-w-[86%]";

    const bubble = document.createElement("div");
    bubble.className =
      "rounded-2xl border px-4 py-3 text-sm leading-relaxed " +
      (role === "user"
        ? "bg-zinc-100 text-zinc-900 border-white/10"
        : "bg-zinc-900/50 text-zinc-100 border-zinc-800");

    const content = document.createElement("div");
    content.className = "prose prose-invert prose-zinc max-w-none";
    content.innerHTML = role === "assistant"
      ? renderMarkdown(text)
      : escapeHtml(text || "").replaceAll("\n", "<br/>");

    const metaLine = document.createElement("div");
    metaLine.className =
      "mt-2 text-[11px] " + (role === "user" ? "text-zinc-600" : "text-zinc-400");

    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    metaLine.textContent = opts.metaText || time;

    bubble.appendChild(content);
    bubble.appendChild(metaLine);

    // rich meta under assistant bubble
    if (role === "assistant" && opts.meta) {
      const cards = attachCards(opts.meta);
      if (cards) bubble.appendChild(cards);

      const cchips = citationChips(opts.meta);
      if (cchips) bubble.appendChild(cchips);
    }

    wrap.appendChild(bubble);
    row.appendChild(wrap);
    messagesEl.appendChild(row);

    if (role === "assistant") enhanceCodeBlocks(content);

    scrollToBottom();
    return { row, bubble, content, metaLine };
  }

  function setChatHeader(title, subtitle) {
    chatTitleEl.textContent = title || "New chat";
    chatSubEl.textContent = subtitle || "Enter = send · Shift+Enter = newline · Esc stops";
  }

  // ---------------------------
  // API
  // ---------------------------
  async function apiJson(url, opts = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
    if (!res.ok) {
      const msg = (data && (data.error || data.message)) ? (data.error || data.message) : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function loadSessions() {
    setStatus("Loading chats…", "busy");
    try {
      const data = await apiJson("/api/sessions");
      sessions = (data && data.sessions) ? data.sessions : [];
      renderSessions(sessionSearchEl.value || "");
      setStatus("Ready", "ok");
    } catch (e) {
      setStatus("Sessions failed", "error");
      toast(`Failed loading chats: ${e.message}`, "error");
    }
  }

  async function createSession() {
    const data = await apiJson("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ title: "New chat" }),
    });
    return data.id;
  }

  async function loadMessages(chatId) {
    const data = await apiJson(`/api/sessions/${encodeURIComponent(chatId)}/messages`);
    return (data && data.messages) ? data.messages : [];
  }

  // ---------------------------
  // Sessions UI
  // ---------------------------
  function renderSessions(filter = "") {
    sessionsListEl.innerHTML = "";

    const f = (filter || "").trim().toLowerCase();
    const list = f
      ? sessions.filter((s) => (s.title || "").toLowerCase().includes(f))
      : sessions;

    sessionsHintEl.textContent = list.length ? "" : (f ? "No matches." : "No chats yet. Click New.");

    for (const s of list) {
      const btn = document.createElement("button");
      btn.className =
        "w-full text-left rounded-xl px-3 py-2 border transition " +
        (s.id === activeChatId
          ? "bg-zinc-900 border-zinc-700"
          : "bg-transparent border-transparent hover:bg-zinc-900/40 hover:border-zinc-800");

      const top = document.createElement("div");
      top.className = "flex items-center justify-between gap-2";

      const title = document.createElement("div");
      title.className = "text-sm font-semibold truncate";
      title.textContent = s.title || "New chat";

      const right = document.createElement("div");
      right.className = "text-[10px] text-zinc-500 shrink-0";
      const dt = s.updated ? new Date((s.updated || 0) * 1000) : null;
      right.textContent = dt ? dt.toLocaleDateString() : "";

      top.appendChild(title);
      top.appendChild(right);

      const sub = document.createElement("div");
      sub.className = "mt-1 text-xs text-zinc-400 truncate";
      sub.textContent = s.id;

      btn.appendChild(top);
      btn.appendChild(sub);

      btn.addEventListener("click", async () => openChat(s.id, s.title));
      sessionsListEl.appendChild(btn);
    }
  }

  // ---------------------------
  // Open chat
  // ---------------------------
  async function openChat(chatId, titleHint) {
    activeChatId = chatId;

    const title = titleHint || (sessions.find(s => s.id === chatId)?.title) || "New chat";
    setChatHeader(title, "Loading messages…");
    setStatus("Loading…", "busy");

    clearMessagesUI();

    try {
      const msgs = await loadMessages(chatId);
      for (const m of msgs) {
        addMessageBubble(m.role, m.content, { metaText: "", meta: m.meta });
      }
      setChatHeader(title, "Enter = send · Shift+Enter = newline · Esc stops");
      setStatus("Ready", "ok");
      scrollToBottom();
    } catch (e) {
      setStatus("Load failed", "error");
      toast(`Failed loading messages: ${e.message}`, "error");
    }
  }

  // ---------------------------
  // Streaming
  // ---------------------------
  function setStreamingUI(on) {
    streaming = on;
    btnStop.classList.toggle("hidden", !on);
    btnSend.disabled = on;
    composerEl.disabled = on;

    if (on) setStatus("Streaming…", "busy");
    else setStatus("Ready", "ok");
  }

  async function streamChat(userText) {
    if (!activeChatId) {
      activeChatId = await createSession();
      await loadSessions();
      await openChat(activeChatId, "New chat");
    }

    addMessageBubble("user", userText);

    // placeholder assistant bubble
    const a = addMessageBubble("assistant", "…", { metaText: "typing…" });
    a.content.innerHTML = `<span class="text-zinc-400">…</span>`;

    setStreamingUI(true);

    streamAbort = new AbortController();
    const ac = streamAbort;

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: activeChatId, message: userText }),
        signal: ac.signal,
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t.slice(0, 180)}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let buffer = "";
      let fullText = "";

      const flush = () => {
        a.content.innerHTML = renderMarkdown(fullText || "");
        a.metaLine.textContent = "streaming…";
        enhanceCodeBlocks(a.content);
        scrollToBottom();
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        while (true) {
          const idx = buffer.indexOf("\n\n");
          if (idx === -1) break;

          const raw = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);

          const line = raw.split("\n").find(l => l.startsWith("data: "));
          if (!line) continue;

          const jsonStr = line.slice(6);
          let obj = null;
          try { obj = JSON.parse(jsonStr); } catch { obj = null; }
          if (!obj) continue;

          if (obj.delta) {
            if (fullText === "" && a.content.textContent.trim() === "…") a.content.innerHTML = "";
            fullText += obj.delta;
            flush();
          }

          if (obj.done) {
            a.metaLine.textContent = "done";
            flush();
          }
        }
      }

      a.metaLine.textContent = "done";
      setStreamingUI(false);

      await loadSessions();
      renderSessions(sessionSearchEl.value || "");
    } catch (e) {
      if (e.name === "AbortError") toast("Stopped.", "ok");
      else toast(`Stream failed: ${e.message}`, "error");
      a.metaLine.textContent = "stopped";
      setStreamingUI(false);
    } finally {
      streamAbort = null;
    }
  }

  // ---------------------------
  // Composer
  // ---------------------------
  function autosizeTextarea(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  }

  composerEl.addEventListener("input", () => {
    autosizeTextarea(composerEl);
    charCountEl.textContent = String((composerEl.value || "").length);
  });

  composerEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      btnSend.click();
    }
  });

  btnSend.addEventListener("click", async () => {
    const text = (composerEl.value || "").trim();
    if (!text || streaming) return;
    composerEl.value = "";
    composerEl.dispatchEvent(new Event("input"));
    await streamChat(text);
  });

  btnStop.addEventListener("click", () => {
    if (streamAbort) streamAbort.abort();
  });

  btnNewChat.addEventListener("click", async () => {
    if (streaming) return toast("Stop streaming first.", "error");
    const id = await createSession();
    await loadSessions();
    await openChat(id, "New chat");
    composerEl.focus();
  });

  btnRefreshSessions.addEventListener("click", async () => {
    await loadSessions();
    renderSessions(sessionSearchEl.value || "");
  });

  btnClearUI.addEventListener("click", () => {
    clearMessagesUI();
    toast("Cleared UI view (does not delete DB).", "ok");
  });

  sessionSearchEl.addEventListener("input", () => renderSessions(sessionSearchEl.value || ""));

  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      sessionSearchEl.focus();
      sessionSearchEl.select();
    }
    if (e.key === "Escape") {
      if (streaming && streamAbort) streamAbort.abort();
    }
  });

  // ---------------------------
  // Boot
  // ---------------------------
  async function boot() {
    setStatus("Booting…", "busy");
    await loadSessions();

    if (sessions.length) await openChat(sessions[0].id, sessions[0].title);
    else { clearMessagesUI(); setStatus("Ready", "ok"); }

    composerEl.focus();
    toast("UI: attachments + citations ready (shows when meta exists).", "ok");
  }

  boot();
})();