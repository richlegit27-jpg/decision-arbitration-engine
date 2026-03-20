// C:\Users\Owner\nova\static\js\modules\state.js

export const state = {
  activeChatId: null,
  pendingFiles: [],
  isSending: false,
  isEditing: false,
  editingMessageEl: null,
  lastUserText: "",
  lastAssistantText: "",
};

export function setActiveChatId(chatId) {
  state.activeChatId = chatId || null;
}

export function setPendingFiles(files) {
  state.pendingFiles = Array.isArray(files) ? files : [];
}

export function clearPendingFiles() {
  state.pendingFiles = [];
}

export function setSending(value) {
  state.isSending = Boolean(value);
}

export function setLastTurn(userText, assistantText) {
  state.lastUserText = userText || "";
  state.lastAssistantText = assistantText || "";
}

export function setEditing(value, messageEl = null) {
  state.isEditing = Boolean(value);
  state.editingMessageEl = messageEl || null;
}