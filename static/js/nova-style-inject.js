(() => {
  "use strict";

  if (window.__novaStyleInjectLoaded) return;
  window.__novaStyleInjectLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.styles = Nova.styles || {};

  function safeText(value) {
    if (Nova.utils && typeof Nova.utils.safeText === "function") {
      return Nova.utils.safeText(value);
    }
    return String(value ?? "").trim();
  }

  function ensureStyleTag(id, cssText) {
    const styleId = safeText(id);
    if (!styleId || !cssText) return null;

    let tag = document.getElementById(styleId);
    if (!tag) {
      tag = document.createElement("style");
      tag.id = styleId;
      tag.setAttribute("data-nova-style", "true");
      document.head.appendChild(tag);
    }

    if (tag.textContent !== cssText) {
      tag.textContent = cssText;
    }

    return tag;
  }

  function injectWebResultStyles() {
    return ensureStyleTag(
      "nova-style-web-results",
      `
.message-sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.message-sources-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.72;
  margin-bottom: 10px;
}

.message-sources-list {
  display: grid;
  gap: 10px;
}

.source-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 12px 14px;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.source-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

.source-card-title {
  display: inline-block;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  color: inherit;
  text-decoration: none;
  word-break: break-word;
}

.source-card-title:hover {
  text-decoration: underline;
}

.source-card-domain {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.68;
  word-break: break-word;
}

.source-card-snippet {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.45;
  opacity: 0.9;
  word-break: break-word;
}
      `.trim()
    );
  }

  function injectMemoryPolishStyles() {
    return ensureStyleTag(
      "nova-style-memory-polish",
      `
.memory-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  padding: 14px;
  margin-bottom: 10px;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease,
    opacity 0.18s ease;
}

.memory-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.055);
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16);
}

.memory-card.is-deleting {
  opacity: 0.6;
  transform: scale(0.992);
  pointer-events: none;
}

.memory-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.memory-kind {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.08);
}

.memory-time {
  font-size: 12px;
  opacity: 0.7;
}

.memory-value {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.memory-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.memory-delete-btn {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease,
    opacity 0.16s ease;
}

.memory-delete-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
}

.memory-delete-btn:disabled {
  opacity: 0.65;
  cursor: default;
}

.memory-empty-state {
  border: 1px dashed rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 18px 16px;
  text-align: center;
}

.memory-empty-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
}

.memory-empty-subtitle {
  font-size: 13px;
  opacity: 0.72;
  line-height: 1.45;
}
      `.trim()
    );
  }

  function injectMessagePolishStyles() {
    return ensureStyleTag(
      "nova-style-message-polish",
      `
.message {
  margin: 0 0 14px;
}

.message-shell {
  border-radius: 18px;
  padding: 14px 15px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
}

.user-message .message-shell {
  background: rgba(255, 255, 255, 0.08);
}

.assistant-message .message-shell,
.system-message .message-shell {
  background: rgba(255, 255, 255, 0.04);
}

.message-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.message-role {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.82;
}

.message-time {
  font-size: 12px;
  opacity: 0.62;
  white-space: nowrap;
}

.message-body {
  min-height: 20px;
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-content > :first-child {
  margin-top: 0;
}

.message-content > :last-child {
  margin-bottom: 0;
}

.message-content pre {
  overflow: auto;
  border-radius: 14px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.22);
}

.message-content code {
  word-break: break-word;
}

.message-placeholder {
  opacity: 0.55;
  letter-spacing: 0.08em;
}

.message-router-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.message-router-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.08);
}

.message-router-reason {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.05);
  opacity: 0.88;
}

.message-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.message-copy-btn {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease,
    opacity 0.16s ease;
}

.message-copy-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
}
      `.trim()
    );
  }

  function injectAttachedFileStyles() {
    return ensureStyleTag(
      "nova-style-attached-files",
      `
.attached-file-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  padding: 10px 12px;
  margin-bottom: 8px;
}

.attached-file-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.attached-file-name {
  font-size: 13px;
  font-weight: 700;
  word-break: break-word;
}

.attached-file-size {
  font-size: 12px;
  opacity: 0.68;
}

.attached-file-remove {
  appearance: none;
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: inherit;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    background 0.16s ease,
    opacity 0.16s ease;
}

.attached-file-remove:hover {
  transform: scale(1.04);
  background: rgba(255, 255, 255, 0.14);
}
      `.trim()
    );
  }

  function injectEmptyStateStyles() {
    return ensureStyleTag(
      "nova-style-empty-states",
      `
.nova-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42vh;
  padding: 24px 14px;
}

.nova-empty-state-card {
  width: min(100%, 620px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 22px;
  padding: 26px 22px;
  text-align: center;
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.16);
}

.nova-empty-state-title {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 8px;
}

.nova-empty-state-subtitle {
  font-size: 14px;
  line-height: 1.6;
  opacity: 0.74;
}
      `.trim()
    );
  }

  function injectActionButtonStyles() {
    return ensureStyleTag(
      "nova-style-actions",
      `
.nova-action-btn.secondary,
.session-action-btn,
.memory-delete-btn,
.message-copy-btn {
  -webkit-tap-highlight-color: transparent;
}

.nova-action-btn.secondary {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;
}

.nova-action-btn.secondary:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.14);
}

.session-action-btn {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  border-radius: 10px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease,
    opacity 0.16s ease;
}

.session-action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
}

.session-action-btn.danger:hover:not(:disabled) {
  background: rgba(255, 80, 80, 0.14);
}

.session-action-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
      `.trim()
    );
  }

  function injectAll() {
    injectWebResultStyles();
    injectMemoryPolishStyles();
    injectMessagePolishStyles();
    injectAttachedFileStyles();
    injectEmptyStateStyles();
    injectActionButtonStyles();
  }

  Nova.styles = {
    ...Nova.styles,
    ensureStyleTag,
    injectWebResultStyles,
    injectMemoryPolishStyles,
    injectMessagePolishStyles,
    injectAttachedFileStyles,
    injectEmptyStateStyles,
    injectActionButtonStyles,
    injectAll,
  };
})();