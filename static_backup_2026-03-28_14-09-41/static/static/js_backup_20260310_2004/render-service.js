// C:\Users\Owner\nova\static\js\render-service.js

(() => {
"use strict"

function createRenderService(options = {}){
  const {
    state,
    elements = {},
    utils = {},
    callbacks = {},
  } = options

  if(!state){
    throw new Error("NovaRenderService: state is required")
  }

  const el = {
    messages: elements.messages || null,
    emptyState: elements.emptyState || null,
    topbarTitle: elements.topbarTitle || null,
    chatList: elements.chatList || null,
    pendingAttachments: elements.pendingAttachments || null,
    pendingAttachmentsList: elements.pendingAttachmentsList || null,
    jumpToLatestBtn: elements.jumpToLatestBtn || null,
  }

  const escapeHtml =
    utils.escapeHtml ||
    ((value) => {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;")
    })

  const formatMessageHtml =
    utils.formatMessageHtml ||
    ((content) => escapeHtml(content || "").replace(/\n/g, "<br>"))

  const formatBytes =
    utils.formatBytes ||
    ((bytes) => {
      const size = Number(bytes || 0)

      if(size < 1024){
        return `${size} B`
      }

      if(size < 1024 * 1024){
        return `${(size / 1024).toFixed(1)} KB`
      }

      return `${(size / (1024 * 1024)).toFixed(1)} MB`
    })

  function getChats(){
    return Array.isArray(state.chats) ? state.chats : []
  }

  function getMessages(){
    return Array.isArray(state.messages) ? state.messages : []
  }

  function getPendingFiles(){
    return Array.isArray(state.pendingFiles) ? state.pendingFiles : []
  }

  function renderChatList(){
    if(!el.chatList){
      return
    }

    const chats = getChats()

    if(!chats.length){
      el.chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
      return
    }

    el.chatList.innerHTML = chats.map((chat) => {
      const chatId = String(chat.chat_id || chat.id || "")
      const title = String(chat.title || "New chat")
      const isActive = chatId === state.activeChatId
      const isRenaming = chatId === state.renamingChatId

      return `
        <div class="chat-list-row ${isActive ? "is-active" : ""}" data-chat-row-id="${escapeHtml(chatId)}">
          ${
            isRenaming
              ? `
                <input
                  type="text"
                  class="chat-rename-input"
                  data-rename-chat-id="${escapeHtml(chatId)}"
                  value="${escapeHtml(state.renameDraft || title)}"
                  maxlength="120"
                  autocomplete="off"
                  spellcheck="false"
                >
              `
              : `
                <button
                  type="button"
                  class="chat-list-item ${isActive ? "is-active" : ""}"
                  data-chat-id="${escapeHtml(chatId)}"
                  title="${escapeHtml(title)}"
                >
                  <span class="chat-list-item-title">${escapeHtml(title)}</span>
                </button>
              `
          }
          <button
            type="button"
            class="chat-item-delete"
            data-delete-chat-id="${escapeHtml(chatId)}"
            aria-label="Delete chat"
            title="Delete chat"
          >
            ×
          </button>
        </div>
      `
    }).join("")
  }

  function renderTopbar(){
    if(!el.topbarTitle){
      return
    }

    const activeChat = getChats().find((chat) => {
      return String(chat.chat_id || chat.id || "") === String(state.activeChatId || "")
    })

    el.topbarTitle.textContent = activeChat?.title || "New chat"
  }

  function renderPendingAttachments(){
    if(!el.pendingAttachments || !el.pendingAttachmentsList){
      return
    }

    const files = getPendingFiles()

    if(!files.length){
      el.pendingAttachments.hidden = true
      el.pendingAttachmentsList.innerHTML = ""
      return
    }

    el.pendingAttachments.hidden = false
    el.pendingAttachmentsList.innerHTML = files.map((file, index) => {
      return `
        <div class="pending-attachment-item">
          <div class="pending-attachment-meta">
            <div class="pending-attachment-name">${escapeHtml(file.name || "file")}</div>
            <div class="pending-attachment-size">${escapeHtml(formatBytes(file.size || 0))}</div>
          </div>
          <button
            type="button"
            class="pending-attachment-remove"
            data-remove-pending-index="${index}"
            aria-label="Remove attachment"
            title="Remove attachment"
          >
            ×
          </button>
        </div>
      `
    }).join("")
  }

  function renderMessageAttachments(message){
    const attachments = Array.isArray(message.attachments) ? message.attachments : []
    if(!attachments.length){
      return ""
    }

    return `
      <div class="message-attachments">
        ${attachments.map((attachment) => {
          const name = escapeHtml(attachment.filename || attachment.name || "attachment")
          const size = Number(attachment.file_size || attachment.size || 0)
          const hasUrl = typeof attachment.url === "string" && attachment.url.trim()
          const href = hasUrl ? ` href="${escapeHtml(attachment.url)}" target="_blank" rel="noreferrer"` : ""

          return `
            <${hasUrl ? "a" : "div"}
              class="message-attachment-chip"
              ${hasUrl ? href : ""}
            >
              <span class="message-attachment-name">${name}</span>
              ${size > 0 ? `<span class="message-attachment-size">${escapeHtml(formatBytes(size))}</span>` : ""}
            </${hasUrl ? "a" : "div"}>
          `
        }).join("")}
      </div>
    `
  }

  function renderMessageActions(message, index){
    const messageId = String(message.id || message.message_id || index)
    const role = message.role === "assistant" ? "assistant" : "user"
    const isError = !!message.error
    const canEdit = role === "user"
    const canRegenerate = role === "assistant"
    const canRetry = isError || role === "user"

    return `
      <div class="message-actions" data-message-actions-for="${escapeHtml(messageId)}">
        <button
          type="button"
          class="message-action-btn"
          data-message-action="copy"
          data-message-id="${escapeHtml(messageId)}"
          title="Copy message"
          aria-label="Copy message"
        >
          Copy
        </button>

        ${
          canEdit
            ? `
              <button
                type="button"
                class="message-action-btn"
                data-message-action="edit"
                data-message-id="${escapeHtml(messageId)}"
                title="Edit message"
                aria-label="Edit message"
              >
                Edit
              </button>
            `
            : ""
        }

        ${
          canRegenerate
            ? `
              <button
                type="button"
                class="message-action-btn"
                data-message-action="regenerate"
                data-message-id="${escapeHtml(messageId)}"
                title="Regenerate response"
                aria-label="Regenerate response"
              >
                Regen
              </button>
            `
            : ""
        }

        ${
          canRetry
            ? `
              <button
                type="button"
                class="message-action-btn"
                data-message-action="retry"
                data-message-id="${escapeHtml(messageId)}"
                title="Retry"
                aria-label="Retry"
              >
                Retry
              </button>
            `
            : ""
        }

        <button
          type="button"
          class="message-action-btn is-danger"
          data-message-action="delete"
          data-message-id="${escapeHtml(messageId)}"
          title="Delete message"
          aria-label="Delete message"
        >
          Delete
        </button>
      </div>
    `
  }

  function renderMessages(){
    if(!el.messages){
      return
    }

    const messages = getMessages()

    if(!messages.length){
      el.messages.innerHTML = ""
      if(el.emptyState){
        el.emptyState.hidden = false
      }
      return
    }

    if(el.emptyState){
      el.emptyState.hidden = true
    }

    el.messages.innerHTML = messages.map((message, index) => {
      const messageId = String(message.id || message.message_id || index)
      const role = message.role === "assistant" ? "assistant" : "user"
      const avatar = role === "assistant" ? "N" : "Y"
      const content = formatMessageHtml(message.content || "")
      const isPending = !!message.pending
      const isError = !!message.error

      return `
        <article
          class="message role-${role}${isPending ? " is-pending" : ""}${isError ? " is-error" : ""}"
          data-message-id="${escapeHtml(messageId)}"
        >
          <div class="message-avatar">${avatar}</div>
          <div class="message-main">
            <div class="message-bubble">
              <div class="message-content">${content}</div>
              ${renderMessageAttachments(message)}
            </div>
            ${renderMessageActions(message, index)}
          </div>
        </article>
      `
    }).join("")
  }

  async function copyMessage(messageId){
    const message = getMessages().find((item) => {
      return String(item.id || item.message_id || "") === String(messageId || "")
    })

    if(!message){
      return
    }

    const text = String(message.content || "")
    if(!text){
      return
    }

    try{
      await navigator.clipboard.writeText(text)
      callbacks.onCopiedMessage?.(messageId)
    }catch(error){
      console.error("Nova copyMessage error:", error)
    }
  }

  function bindMessageActionEvents(){
    if(!el.messages){
      return
    }

    el.messages.addEventListener("click", async (event) => {
      const actionBtn = event.target.closest("[data-message-action]")
      if(!actionBtn){
        return
      }

      const action = String(actionBtn.dataset.messageAction || "").trim()
      const messageId = String(actionBtn.dataset.messageId || "").trim()

      if(!action || !messageId){
        return
      }

      if(action === "copy"){
        await copyMessage(messageId)
        return
      }

      if(action === "edit"){
        callbacks.onEditMessage?.(messageId)
        return
      }

      if(action === "regenerate"){
        callbacks.onRegenerateMessage?.(messageId)
        return
      }

      if(action === "retry"){
        callbacks.onRetryMessage?.(messageId)
        return
      }

      if(action === "delete"){
        callbacks.onDeleteMessage?.(messageId)
      }
    })
  }

  function renderAll(){
    renderChatList()
    renderMessages()
    renderTopbar()
    renderPendingAttachments()
  }

  return {
    renderChatList,
    renderMessages,
    renderTopbar,
    renderPendingAttachments,
    renderAll,
    bindMessageActionEvents,
    copyMessage,
  }
}

window.NovaRenderService = {
  create: createRenderService,
}

})()