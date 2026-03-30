(function () {
  "use strict";

  const API_BASE = "http://127.0.0.1:5001";

  const state = {
    sessionId: loadSessionId(),
    pendingFiles: [],
    sending: false,
  };

  function loadSessionId() {
    const key = "nova_session_id";
    let value = localStorage.getItem(key);
    if (!value) {
      value = crypto.randomUUID();
      localStorage.setItem(key, value);
    }
    return value;
  }

  function $(id) {
    return document.getElementById(id);
  }

  function getEls() {
    return {
      chatInput: $("chatInput"),
      sendBtn: $("sendBtn"),
      uploadBtn: $("uploadBtn"),
      fileInput: $("fileInput"),
      messages: $("messages"),
      emptyState: $("novaEmptyState"),
    };
  }

  function ensureMessagesContainer() {
    const { messages } = getEls();
    return messages || null;
  }

  function hideEmptyState() {
    const { emptyState } = getEls();
    if (emptyState) emptyState.style.display = "none";
  }

  function showEmptyStateIfNeeded() {
    const { emptyState, messages } = getEls();
    if (!emptyState || !messages) return;
    emptyState.style.display = messages.children.length ? "none" : "";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function nl2br(value) {
    return escapeHtml(value).replace(/\n/g, "<br>");
  }

  function safeUrl(url) {
    const value = String(url || "").trim();
    if (!/^https?:\/\//i.test(value)) return "#";
    return value;
  }

  function hostnameFromUrl(url) {
    try {
      return new URL(url).hostname.replace(/^www\./i, "");
    } catch {
      return "";
    }
  }

  function shortTitle(value, max = 44) {
    const text = String(value || "").trim();
    if (!text) return "Untitled source";
    if (text.length <= max) return text;
    return `${text.slice(0, max - 1)}…`;
  }

  function addMessage(role, text, meta = {}) {
    const messages = ensureMessagesContainer();
    if (!messages) return null;

    hideEmptyState();

    const wrap = document.createElement("div");
    wrap.className = `nova-message nova-message-${role}`;

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    const badges = document.createElement("div");
    badges.className = "nova-message-badges";

    if (meta.route) {
      const badge = document.createElement("span");
      badge.className = "nova-badge";
      badge.textContent = meta.route;
      badges.appendChild(badge);
    }

    if (meta.webUsed) {
      const badge = document.createElement("span");
      badge.className = "nova-badge";
      badge.textContent = "web";
      badges.appendChild(badge);
    }

    if (meta.fetchUsed) {
      const badge = document.createElement("span");
      badge.className = "nova-badge";
      badge.textContent = "fetch";
      badges.appendChild(badge);
    }

    if (badges.children.length) {
      inner.appendChild(badges);
    }

    const body = document.createElement("div");
    body.className = "nova-message-markdown";
    body.innerHTML = nl2br(text || "");
    inner.appendChild(body);

    const sourcesHost = document.createElement("div");
    sourcesHost.className = "nova-sources-host";
    inner.appendChild(sourcesHost);

    wrap.appendChild(inner);
    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;

    return { wrap, body, sourcesHost };
  }

  function setMessageText(ref, text) {
    if (!ref || !ref.body) return;
    ref.body.innerHTML = nl2br(text || "");
  }

  function renderSources(ref, sources) {
    if (!ref || !ref.sourcesHost) return;

    const host = ref.sourcesHost;
    host.innerHTML = "";

    if (!Array.isArray(sources) || !sources.length) return;

    const header = document.createElement("div");
    header.className = "nova-sources-header";

    const title = document.createElement("div");
    title.className = "nova-sources-title";
    title.textContent = "Sources";

    const actions = document.createElement("div");
    actions.className = "nova-sources-actions";

    const openAllBtn = document.createElement("button");
    openAllBtn.type = "button";
    openAllBtn.className = "nova-sources-open-all";
    openAllBtn.textContent = `Open all (${sources.length})`;
    openAllBtn.addEventListener("click", () => {
      sources.forEach((source, index) => {
        const url = safeUrl(source.url);
        if (url === "#") return;
        setTimeout(() => {
          window.open(url, "_blank", "noopener,noreferrer");
        }, index * 120);
      });
    });

    actions.appendChild(openAllBtn);
    header.appendChild(title);
    header.appendChild(actions);
    host.appendChild(header);

    const chips = document.createElement("div");
    chips.className = "nova-source-chips";

    sources.forEach((source, index) => {
      const chip = document.createElement("a");
      chip.className = "nova-source-chip";
      chip.href = safeUrl(source.url);
      chip.target = "_blank";
      chip.rel = "noopener noreferrer";
      chip.title = source.title || source.url || "Source";

      const chipIndex = document.createElement("span");
      chipIndex.className = "nova-source-chip-index";
      chipIndex.textContent = String(index + 1);

      const chipText = document.createElement("span");
      chipText.className = "nova-source-chip-text";
      chipText.textContent = shortTitle(source.title || hostnameFromUrl(source.url) || "Source");

      chip.appendChild(chipIndex);
      chip.appendChild(chipText);
      chips.appendChild(chip);
    });

    host.appendChild(chips);

    const list = document.createElement("div");
    list.className = "nova-sources-list";

    sources.forEach((source, index) => {
      const card = document.createElement("a");
      card.className = "nova-source-card";
      card.href = safeUrl(source.url);
      card.target = "_blank";
      card.rel = "noopener noreferrer";

      const cardTop = document.createElement("div");
      cardTop.className = "nova-source-card-top";

      const number = document.createElement("span");
      number.className = "nova-source-index";
      number.textContent = String(index + 1);

      const domain = document.createElement("span");
      domain.className = "nova-source-domain";
      domain.textContent = hostnameFromUrl(source.url) || "source";

      cardTop.appendChild(number);
      cardTop.appendChild(domain);

      const heading = document.createElement("div");
      heading.className = "nova-source-title-text";
      heading.textContent = source.title || source.url || "Untitled source";

      const desc = document.createElement("div");
      desc.className = "nova-source-desc";
      desc.textContent = source.description || source.url || "";

      card.appendChild(cardTop);
      card.appendChild(heading);
      card.appendChild(desc);

      list.appendChild(card);
    });

    host.appendChild(list);
  }

  function isUrlOnly(text) {
    return /^(https?:\/\/[^\s]+)$/i.test(String(text || "").trim());
  }

  function looksLikeCurrentInfo(text) {
    const t = String(text || "").trim().toLowerCase();
    if (!t) return false;

    const patterns = [
      /\blatest\b/,
      /\brecent\b/,
      /\bcurrent\b/,
      /\bright now\b/,
      /\btoday\b/,
      /\byesterday\b/,
      /\bthis week\b/,
      /\bthis month\b/,
      /\bnews\b/,
      /\bheadline(s)?\b/,
      /\bupdate(s)?\b/,
      /\bwhat('?s| is) happening\b/,
      /\bwhat('?s| is) going on\b/,
      /\bai news\b/,
      /\brelease notes\b/,
      /\bversion\b/,
      /\bprice of\b/,
      /\bstock\b/,
      /\bweather\b/,
      /\bscore\b/,
      /\bwho is\b/,
      /\bwhen is\b/,
      /\bwhere is\b/,
      /\bsearch\b/,
      /\blook up\b/,
      /\bfind\b/,
      /\bnews on\b/,
      /\bstatus of\b/,
      /\btrend(s)?\b/,
      /\btop story\b/,
      /\btop stories\b/,
      /\bresearch\b/,
      /\bnew paper(s)?\b/,
      /\bannouncement(s)?\b/,
      /\blaunch(ed|ing)?\b/,
      /\bup to date\b/,
      /\bupdated\b/,
      /\brefresh\b/
    ];

    return patterns.some((rx) => rx.test(t));
  }

  function looksLikeCreativeTask(text) {
    const t = String(text || "").trim().toLowerCase();
    if (!t) return false;

    const patterns = [
      /\bwrite\b/,
      /\brewrite\b/,
      /\bimprove\b/,
      /\bfix this code\b/,
      /\bmake me\b/,
      /\bcreate\b/,
      /\bbrainstorm\b/,
      /\bhomepage\b/,
      /\bhero section\b/,
      /\bemail\b/,
      /\bpoem\b/,
      /\bstory\b/,
      /\bcopy\b/,
      /\bcaption\b/,
      /\brefactor\b/,
      /\bdebug this\b/,
      /\bsmff\b/
    ];

    return patterns.some((rx) => rx.test(t));
  }

  function detectRoute(text) {
    const value = String(text || "").trim();
    if (!value) return "chat";
    if (isUrlOnly(value)) return "fetch";
    if (looksLikeCurrentInfo(value) && !looksLikeCreativeTask(value)) return "knowledge";
    return "chat";
  }

  async function callJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }

    if (!response.ok) {
      const message =
        (data && (data.error || data.message)) ||
        `${response.status} ${response.statusText}`;
      throw new Error(message);
    }

    return data || {};
  }

  async function sendChat(content) {
    return callJson(`${API_BASE}/api/chat`, {
      content,
      session_id: state.sessionId,
    });
  }

  async function sendFetch(url) {
    return callJson(`${API_BASE}/api/web/fetch`, {
      url,
      session_id: state.sessionId,
    });
  }

  async function sendKnowledge(query) {
    return callJson(`${API_BASE}/api/knowledge`, {
      query,
      session_id: state.sessionId,
      search_limit: 6,
      fetch_limit: 4,
    });
  }

  async function uploadFiles(files) {
    if (!files || !files.length) return [];

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const response = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error((data && data.error) || "Upload failed");
    }

    return (data && data.files) || [];
  }

  function renderPendingFiles() {
    let tray = document.getElementById("novaPendingFilesTray");
    const { chatInput } = getEls();
    if (!chatInput || !chatInput.parentElement) return;

    if (!tray) {
      tray = document.createElement("div");
      tray.id = "novaPendingFilesTray";
      tray.className = "nova-pending-files-tray";
      chatInput.parentElement.insertBefore(tray, chatInput);
    }

    tray.innerHTML = "";

    if (!state.pendingFiles.length) {
      tray.style.display = "none";
      return;
    }

    tray.style.display = "flex";

    state.pendingFiles.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "nova-attachment-chip";

      const label = document.createElement("span");
      label.textContent = file.name;

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "nova-chip-remove";
      remove.textContent = "×";
      remove.addEventListener("click", () => {
        state.pendingFiles.splice(index, 1);
        renderPendingFiles();
      });

      chip.appendChild(label);
      chip.appendChild(remove);
      tray.appendChild(chip);
    });
  }

  async function handleSend() {
    const { chatInput, sendBtn } = getEls();
    if (!chatInput || !sendBtn || state.sending) return;

    const raw = chatInput.value || "";
    const content = raw.trim();

    if (!content && !state.pendingFiles.length) return;

    state.sending = true;
    sendBtn.disabled = true;

    try {
      let finalUserText = content;

      if (state.pendingFiles.length) {
        const uploaded = await uploadFiles(state.pendingFiles);
        const attachmentLines = uploaded.map((f) => `Attachment: ${f.name} ${f.url}`);
        finalUserText = [content, ...attachmentLines].filter(Boolean).join("\n");
        state.pendingFiles = [];
        renderPendingFiles();
      }

      addMessage("user", finalUserText || "[Uploaded file]", { route: "user" });
      chatInput.value = "";

      const route = detectRoute(content);
      const pending = addMessage("assistant", "Thinking...", {
        route,
        webUsed: route === "knowledge",
        fetchUsed: route === "fetch",
      });

      let data;
      if (route === "fetch") {
        data = await sendFetch(content);
      } else if (route === "knowledge") {
        data = await sendKnowledge(content);
      } else {
        data = await sendChat(finalUserText);
      }

      const reply = data.message || data.reply || data.content || "No response returned.";
      setMessageText(pending, reply);

      if (route === "knowledge" && Array.isArray(data.sources)) {
        renderSources(pending, data.sources);
      }

      if (data.debug) {
        console.log("Nova route debug:", data.debug);
      }
    } catch (error) {
      addMessage("assistant", `Error: ${error.message}`, { route: "error" });
    } finally {
      state.sending = false;
      sendBtn.disabled = false;
      chatInput.focus();
      showEmptyStateIfNeeded();
    }
  }

  function bindUpload() {
    const { uploadBtn, fileInput } = getEls();
    if (!uploadBtn || !fileInput) return;

    uploadBtn.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
      const files = Array.from(fileInput.files || []);
      if (!files.length) return;
      state.pendingFiles.push(...files);
      renderPendingFiles();
      fileInput.value = "";
    });
  }

  function bindComposer() {
    const { sendBtn, chatInput } = getEls();
    if (!sendBtn || !chatInput) return;

    sendBtn.addEventListener("click", handleSend);

    chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    });
  }

  function bootstrap() {
    bindComposer();
    bindUpload();
    renderPendingFiles();
    showEmptyStateIfNeeded();
    console.log("nova-composer-bundle loaded");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();