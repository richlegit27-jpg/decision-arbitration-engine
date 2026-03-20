// C:\Users\Owner\nova\static\js\chat-render.js

(() => {
"use strict"

function createRenderService(options = {}){
  const {
    state,
    elements = {},
    utils = {},
  } = options

  if(!state){
    throw new Error("NovaChatRender: state is required")
  }

  const el = {
    body: elements.body || document.body,
    chatList: elements.chatList || null,
    messages: elements.messages || null,
    input: elements.input || null,
    sendBtn: elements.sendBtn || null,
    stopBtn: elements.stopBtn || null,
    topbarTitle: elements.topbarTitle || null,
    jumpToLatestBtn: elements.jumpToLatestBtn || null,
    emptyState: elements.emptyState || null,
    emptySuggestions: elements.emptySuggestions || null,
    pendingAttachments: elements.pendingAttachments || null,
    messagesScroll: elements.messagesScroll || null,
  }

  const escapeHtml =
    typeof utils.escapeHtml === "function"
      ? utils.escapeHtml
      : ((value) => String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#039;"))

  const getChatTitle =
    typeof utils.getChatTitle === "function"
      ? utils.getChatTitle
      : ((chat) => String(chat?.title || chat?.name || "New chat").trim() || "New chat")

  const getChatId =
    typeof utils.getChatId === "function"
      ? utils.getChatId
      : ((chat) => String(chat?.chat_id || chat?.id || ""))

  const ensureChatsArray =
    typeof utils.ensureChatsArray === "function"
      ? utils.ensureChatsArray
      : (() => Array.isArray(state.chats) ? state.chats : [])

  const ensureMessagesArray =
    typeof utils.ensureMessagesArray === "function"
      ? utils.ensureMessagesArray
      : (() => Array.isArray(state.messages) ? state.messages : [])

  const getActiveChat =
    typeof utils.getActiveChat === "function"
      ? utils.getActiveChat
      : (() => null)

  function formatInline(text){
    const placeholders = []
    let html = escapeHtml(String(text || ""))

    html = html.replace(/`([^`\n]+)`/g, (_match, code) => {
      const token = `__INLINE_CODE_${placeholders.length}__`
      placeholders.push(`<code>${escapeHtml(code)}</code>`)
      return token
    })

    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label, url) => {
      const safeUrl = escapeHtml(url)
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`
    })

    html = html.replace(/(^|[\s(])(https?:\/\/[^\s<]+)/g, (_match, prefix, url) => {
      const safeUrl = escapeHtml(url)
      return `${prefix}<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`
    })

    placeholders.forEach((snippet, index) => {
      html = html.replace(`__INLINE_CODE_${index}__`, snippet)
    })

    return html
  }

  function formatMessageContent(content, options = {}){
    const raw = String(content || "")
    const isStreaming = Boolean(options.isStreaming)

    if(!raw.trim()){
      return isStreaming
        ? `
          <span class="thinking-dots" aria-hidden="true">
            <span></span><span></span><span></span>
          </span>
        `
        : "&nbsp;"
    }

    const codeBlocks = []
    let working = raw.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_match, language, code) => {
      const token = `__CODE_BLOCK_${codeBlocks.length}__`
      codeBlocks.push({
        token,
        html: `<pre class="message-code-block"><code class="language-${escapeHtml(language || "")}">${escapeHtml(code || "")}</code></pre>`,
      })
      return token
    })

    const lines = working.split("\n")
    const parts = []
    let paragraphLines = []
    let bulletItems = []
    let numberedItems = []

    function flushParagraph(){
      if(!paragraphLines.length){
        return
      }

      const text = paragraphLines.join("\n").trim()
      paragraphLines = []

      if(!text){
        return
      }

      parts.push(`<p>${formatInline(text).replace(/\n/g, "<br>")}</p>`)
    }

    function flushBullets(){
      if(!bulletItems.length){
        return
      }

      parts.push(`<ul>${bulletItems.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ul>`)
      bulletItems = []
    }

    function flushNumbers(){
      if(!numberedItems.length){
        return
      }

      parts.push(`<ol>${numberedItems.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ol>`)
      numberedItems = []
    }

    function flushAll(){
      flushParagraph()
      flushBullets()
      flushNumbers()
    }

    for(const rawLine of lines){
      const line = String(rawLine || "")
      const trimmed = line.trim()

      const codeBlock = codeBlocks.find((item) => item.token === trimmed)
      if(codeBlock && trimmed === codeBlock.token){
        flushAll()
        parts.push(codeBlock.html)
        continue
      }

      if(!trimmed){
        flushAll()
        continue
      }

      if(/^[-*]\s+/.test(trimmed)){
        flushParagraph()
        flushNumbers()
        bulletItems.push(trimmed.replace(/^[-*]\s+/, ""))
        continue
      }

      if(/^\d+\.\s+/.test(trimmed)){
        flushParagraph()
        flushBullets()
        numberedItems.push(trimmed.replace(/^\d+\.\s+/, ""))
        continue
      }

      flushBullets()
      flushNumbers()
      paragraphLines.push(line)
    }

    flushAll()

    let html = parts.join("")
    for(const block of codeBlocks){
      html = html.replace(block.token, block.html)
    }

    if(isStreaming){
      html += `<span class="streaming-cursor" aria-hidden="true"></span>`
    }

    return html || "&nbsp;"
  }

  function patchStreamingMessage(message){
    const messageId = String(message?.id || message?.message_id || "").trim()
    if(!messageId || !el.messages){
      return false
    }

    const article = el.messages.querySelector(`.message[data-message-id="${CSS.escape(messageId)}"]`)
    const contentEl = article?.querySelector?.(".message-content")

    if(!article || !contentEl){
      return false
    }

    article.classList.add("is-streaming")
    contentEl.innerHTML = formatMessageContent(message.content || "", { isStreaming: true })
    return true
  }

  function renderChatList(){
    if(!el.chatList){
      return
    }

    const chats = ensureChatsArray()

    if(!chats.length){
      el.chatList.innerHTML = `<div class="chat-list-empty">No chats yet</div>`
      return
    }

    el.chatList.innerHTML = chats.map((chat) => {
      const chatId = getChatId(chat)
      const isActive = String(state.activeChatId || "") === chatId
      const isRenaming = String(state.renamingChatId || "") === chatId
      const title = escapeHtml(getChatTitle(chat))

      if(isRenaming){
        return `
          <div class="chat-list-item ${isActive ? "is-active" : ""}" data-chat-id="${escapeHtml(chatId)}">
            <input
              class="chat-rename-input"
              data-rename-chat-id="${escapeHtml(chatId)}"
              value="${title}"
              autocomplete="off"
            >
            <div class="chat-item-actions">
              <button type="button" data-action="delete-chat" data-chat-id="${escapeHtml(chatId)}" title="Delete chat">Delete</button>
            </div>
          </div>
        `
      }

      return `
        <div class="chat-list-item ${isActive ? "is-active" : ""}" data-chat-id="${escapeHtml(chatId)}">
          <span class="chat-list-item-title">${title}</span>
          <div class="chat-item-actions">
            <button type="button" data-action="rename-chat" data-chat-id="${escapeHtml(chatId)}" title="Rename chat">Rename</button>
            <button type="button" data-action="delete-chat" data-chat-id="${escapeHtml(chatId)}" title="Delete chat">Delete</button>
          </div>
        </div>
      `
    }).join("")
  }

  function renderMessages(){
    if(!el.messages){
      return
    }

    const messages = ensureMessagesArray()

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

    const lastIndex = messages.length - 1

    el.messages.innerHTML = messages.map((message, index) => {
      const role = String(message.role || "assistant")
      const messageId = escapeHtml(String(message.id || ""))
      const isUser = role === "user"
      const isStreamingAssistant =
        !isUser &&
        state.isStreaming &&
        index === lastIndex

      const contentHtml = formatMessageContent(message.content || "", {
        isStreaming: isStreamingAssistant,
      })

      return `
        <article class="message role-${escapeHtml(role)} ${isStreamingAssistant ? "is-streaming" : ""}" data-message-id="${messageId}">
          <div class="message-avatar">${isUser ? "U" : "N"}</div>
          <div class="message-body">
            <div class="message-content">${contentHtml}</div>
            <div class="message-actions">
              <button type="button" data-action="copy-message" data-message-id="${messageId}" title="Copy message">Copy</button>
              ${isUser ? `<button type="button" data-action="retry-message" data-message-id="${messageId}" title="Retry from this message">Retry</button>` : ""}
              <button type="button" data-action="delete-message" data-message-id="${messageId}" title="Delete message">Delete</button>
            </div>
          </div>
        </article>
      `
    }).join("")
  }

  function renderPendingAttachments(){
    if(!el.pendingAttachments){
      return
    }

    const files = Array.isArray(state.pendingFiles) ? state.pendingFiles : []

    if(!files.length){
      el.pendingAttachments.innerHTML = ""
      return
    }

    el.pendingAttachments.innerHTML = files.map((file, index) => `
      <div class="pending-attachment">
        <span>${escapeHtml(file?.name || `File ${index + 1}`)}</span>
        <button type="button" data-remove-pending-index="${index}" title="Remove file">×</button>
      </div>
    `).join("")
  }

  function updateComposerState(){
    const text = String(el.input?.value || "").trim()
    const hasFiles = Array.isArray(state.pendingFiles) && state.pendingFiles.length > 0
    const canSend = (!state.isStreaming) && (Boolean(text) || hasFiles)

    if(el.sendBtn){
      el.sendBtn.disabled = !canSend
    }

    if(el.stopBtn){
      el.stopBtn.hidden = !state.isStreaming
      el.stopBtn.disabled = !state.isStreaming
    }
  }

  function updateTopbar(){
    if(!el.topbarTitle){
      return
    }
    el.topbarTitle.textContent = getChatTitle(getActiveChat?.() || null)
  }

  function updateJumpButton(){
    if(!el.jumpToLatestBtn || !el.messagesScroll){
      return
    }

    const distanceFromBottom =
      el.messagesScroll.scrollHeight - el.messagesScroll.scrollTop - el.messagesScroll.clientHeight

    el.jumpToLatestBtn.hidden = distanceFromBottom < 160
  }

  function renderAll(){
    renderChatList()
    renderMessages()
    renderPendingAttachments()
    updateComposerState()
    updateTopbar()
    updateJumpButton()
  }

  return {
    formatMessageContent,
    patchStreamingMessage,
    renderChatList,
    renderMessages,
    renderPendingAttachments,
    updateComposerState,
    updateTopbar,
    updateJumpButton,
    renderAll,
  }
}

window.NovaChatRender = {
  create: createRenderService,
  createRenderService,
}

})()