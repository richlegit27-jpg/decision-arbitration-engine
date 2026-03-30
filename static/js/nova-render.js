(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderMarkdownLite(text) {
    const safe = escapeHtml(text || "");

    return safe
      .replace(/^### (.*)$/gm, "<h3>$1</h3>")
      .replace(/^## (.*)$/gm, "<h2>$1</h2>")
      .replace(/^# (.*)$/gm, "<h1>$1</h1>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/^\- (.*)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
      .replace(/\n/g, "<br>");
  }

  function getMessagesEl() {
    return document.getElementById("messages");
  }

  function getEmptyStateEl() {
    return document.getElementById("novaEmptyState");
  }

  function hideEmptyState() {
    const empty = getEmptyStateEl();
    if (empty) empty.style.display = "none";
  }

  function showEmptyStateIfNeeded() {
    const messages = getMessagesEl();
    const empty = getEmptyStateEl();
    if (!messages || !empty) return;
    empty.style.display = messages.children.length ? "none" : "";
  }

  function makeBadge(text, className = "") {
    const span = document.createElement("span");
    span.className = `nova-message-badge ${className}`.trim();
    span.textContent = text;
    return span;
  }

  function buildBadges(meta = {}) {
    const badges = [];
    const debug = meta.debug || {};

    if (meta.kind === "knowledge" || debug.route === "knowledge") {
      badges.push(makeBadge("KNOWLEDGE", "is-knowledge"));
    }

    if (debug.web_used || Number(debug.search_count || 0) > 0 || Number(debug.fetch_count || 0) > 0) {
      badges.push(makeBadge("WEB", "is-web"));
    }

    if (debug.memory_used) {
      badges.push(makeBadge("MEMORY", "is-memory"));
    }

    const sourceCount =
      Number(debug.usable_count || 0) ||
      Number(debug.source_count || 0) ||
      (Array.isArray(meta.sources) ? meta.sources.length : 0);

    if (sourceCount > 0) {
      badges.push(makeBadge(`SOURCES: ${sourceCount}`, "is-sources"));
    }

    if (meta.kind === "artifact") {
      badges.push(makeBadge("ARTIFACT", "is-artifact"));
    }

    return badges;
  }

  function buildSourcesBlock(sources = []) {
    if (!Array.isArray(sources) || !sources.length) return null;

    const wrap = document.createElement("div");
    wrap.className = "nova-message-sources";

    const title = document.createElement("div");
    title.className = "nova-message-sources-title";
    title.textContent = "Sources";
    wrap.appendChild(title);

    sources.forEach((source, index) => {
      const card = document.createElement("a");
      card.className = "nova-source-card";
      card.href = source.url || "#";
      card.target = "_blank";
      card.rel = "noopener noreferrer";

      const sourceTitle = document.createElement("div");
      sourceTitle.className = "nova-source-card-title";
      sourceTitle.textContent = source.title || `Source ${index + 1}`;

      const sourceUrl = document.createElement("div");
      sourceUrl.className = "nova-source-card-url";
      sourceUrl.textContent = source.url || "";

      card.appendChild(sourceTitle);
      card.appendChild(sourceUrl);
      wrap.appendChild(card);
    });

    return wrap;
  }

  function addMessage(role, text, meta = {}) {
    const messages = getMessagesEl();
    if (!messages) return null;

    hideEmptyState();

    const row = document.createElement("div");
    row.className = `nova-message nova-message-${role}`;

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    const top = document.createElement("div");
    top.className = "nova-message-top";

    const roleEl = document.createElement("div");
    roleEl.className = "nova-message-role";
    roleEl.textContent = role === "user" ? "You" : "Nova";

    const badgesEl = document.createElement("div");
    badgesEl.className = "nova-message-badges";

    const badges = buildBadges(meta);
    badges.forEach((badge) => badgesEl.appendChild(badge));

    top.appendChild(roleEl);
    top.appendChild(badgesEl);

    const body = document.createElement("div");
    body.className = "nova-message-markdown";
    body.innerHTML = renderMarkdownLite(text || "");

    inner.appendChild(top);
    inner.appendChild(body);

    const sourcesBlock = buildSourcesBlock(meta.sources || []);
    if (sourcesBlock) {
      inner.appendChild(sourcesBlock);
    }

    row.appendChild(inner);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;

    return row;
  }

  function clearMessages() {
    const messages = getMessagesEl();
    if (!messages) return;
    messages.innerHTML = "";
    showEmptyStateIfNeeded();
  }

  Nova.render = {
    addMessage,
    clearMessages,
    showEmptyStateIfNeeded,
  };

  document.addEventListener("DOMContentLoaded", showEmptyStateIfNeeded);
})();