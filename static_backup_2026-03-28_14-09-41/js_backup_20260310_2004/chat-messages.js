(() => {
"use strict"

const chatStateApi = window.NovaChatState

if(!chatStateApi){
  throw new Error("NovaChatMessages: window.NovaChatState is required")
}

const { state } = chatStateApi

const el = {
  messages: document.getElementById("messages"),
  messagesScroll: document.getElementById("messagesScroll"),
  emptyState: document.getElementById("emptyState"),
  jumpToLatestBtn: document.getElementById("jumpToLatestBtn"),
}

const SCROLL_LOCK_THRESHOLD = 140
const COPY_FEEDBACK_MS = 1200
const COPY_CODE_FEEDBACK_MS = 1200

let eventsBound = false
let callbacks = {
  onRetry: null,
}

let copiedMessageId = ""
let copyFeedbackTimer = null
let copiedCodeKey = ""
let copyCodeFeedbackTimer = null

function ensureMessagesArray(){
  if(!Array.isArray(state.messages)){
    state.messages = []
  }
  return state.messages
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function getMessageId(message){
  return String(message?.message_id || message?.id || "").trim()
}

function getDistanceFromBottom(){
  if(!el.messagesScroll){
    return 0
  }

  return el.messagesScroll.scrollHeight - el.messagesScroll.scrollTop - el.messagesScroll.clientHeight
}

function isNearBottom(){
  return getDistanceFromBottom() <= SCROLL_LOCK_THRESHOLD
}

function updateUserScrolledState(){
  state.userScrolledUp = !isNearBottom()
  updateJumpButton()
}

function updateJumpButton(){
  if(!el.jumpToLatestBtn){
    return
  }

  const hasMessages = ensureMessagesArray().length > 0
  const hasThinkingIndicator = !!getThinkingIndicatorElement()

  el.jumpToLatestBtn.hidden = (!hasMessages && !hasThinkingIndicator) || !state.userScrolledUp
}

function renderAttachment(att){
  const name = escapeHtml(att?.filename || att?.name || "file")
  const href = String(att?.url || att?.storage_path || "").trim()

  if(href){
    return `
      <a class="message-attachment" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
        ${name}
      </a>
    `
  }

  return `
    <div class="message-attachment">${name}</div>
  `
}

function isCopiedMessage(messageId){
  return String(messageId || "").trim() !== "" && String(messageId || "").trim() === copiedMessageId
}

function makeCodeCopyKey(messageId, codeIndex){
  return `${String(messageId || "").trim()}::${String(codeIndex || 0)}`
}

function isCopiedCodeBlock(messageId, codeIndex){
  return copiedCodeKey !== "" && copiedCodeKey === makeCodeCopyKey(messageId, codeIndex)
}

function renderMessageActions(message){
  const role = String(message?.role || "assistant").toLowerCase() === "user" ? "user" : "assistant"
  const messageId = escapeHtml(getMessageId(message))
  const safeContent = escapeHtml(message?.content || "")
  const isCopied = isCopiedMessage(getMessageId(message))

  const copyLabel = isCopied ? "Copied ✓" : "Copy"
  const copyDisabled = isCopied ? "disabled" : ""

  if(role === "assistant"){
    return `
      <div class="message-actions">
        <button type="button" class="message-action-btn" data-copy-message="${messageId}" ${copyDisabled}>${copyLabel}</button>
        <button type="button" class="message-action-btn" data-retry-message="${safeContent}">Regenerate</button>
        <button type="button" class="message-action-btn" data-delete-message="${messageId}">Delete</button>
      </div>
    `
  }

  return `
    <div class="message-actions">
      <button type="button" class="message-action-btn" data-copy-message="${messageId}" ${copyDisabled}>${copyLabel}</button>
      <button type="button" class="message-action-btn" data-retry-message="${safeContent}">Resend</button>
      <button type="button" class="message-action-btn" data-delete-message="${messageId}">Delete</button>
    </div>
  `
}

function splitByCodeFences(text){
  const source = String(text || "")
  const blocks = []
  const fenceRegex = /```([^\n`]*)\n?([\s\S]*?)```/g

  let lastIndex = 0
  let match = null

  while((match = fenceRegex.exec(source)) !== null){
    if(match.index > lastIndex){
      blocks.push({
        type: "text",
        value: source.slice(lastIndex, match.index),
      })
    }

    blocks.push({
      type: "code",
      language: String(match[1] || "").trim(),
      value: String(match[2] || "").replace(/\s+$/g, ""),
    })

    lastIndex = fenceRegex.lastIndex
  }

  if(lastIndex < source.length){
    blocks.push({
      type: "text",
      value: source.slice(lastIndex),
    })
  }

  if(!blocks.length){
    blocks.push({
      type: "text",
      value: source,
    })
  }

  return blocks
}

function renderInlineMarkdown(text){
  let html = escapeHtml(text || "")

  html = html.replace(/`([^`]+)`/g, (_match, code) => {
    return `<code class="message-inline-code">${escapeHtml(code)}</code>`
  })

  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
  html = html.replace(/(^|[^\*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>")

  return html
}

function renderTextBlock(text){
  const normalized = String(text || "").replace(/\r\n/g, "\n")
  const lines = normalized.split("\n")
  const parts = []

  let paragraphLines = []
  let unorderedItems = []
  let orderedItems = []

  function flushParagraph(){
    if(!paragraphLines.length){
      return
    }

    const paragraphText = paragraphLines.join(" ").replace(/\s+/g, " ").trim()
    if(paragraphText){
      parts.push(`<p>${renderInlineMarkdown(paragraphText)}</p>`)
    }
    paragraphLines = []
  }

  function flushUnordered(){
    if(!unorderedItems.length){
      return
    }

    parts.push(`
      <ul>
        ${unorderedItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join("")}
      </ul>
    `)
    unorderedItems = []
  }

  function flushOrdered(){
    if(!orderedItems.length){
      return
    }

    parts.push(`
      <ol>
        ${orderedItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join("")}
      </ol>
    `)
    orderedItems = []
  }

  function flushAll(){
    flushParagraph()
    flushUnordered()
    flushOrdered()
  }

  for(const rawLine of lines){
    const line = String(rawLine || "")
    const trimmed = line.trim()

    if(!trimmed){
      flushAll()
      continue
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.+)$/)
    if(unorderedMatch){
      flushParagraph()
      flushOrdered()
      unorderedItems.push(unorderedMatch[1].trim())
      continue
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/)
    if(orderedMatch){
      flushParagraph()
      flushUnordered()
      orderedItems.push(orderedMatch[1].trim())
      continue
    }

    flushUnordered()
    flushOrdered()
    paragraphLines.push(trimmed)
  }

  flushAll()

  return parts.join("") || "<p>&nbsp;</p>"
}

function renderCodeBlock(code, language, messageId, codeIndex){
  const safeLanguage = escapeHtml(language || "")
  const safeCode = escapeHtml(code || "")
  const codeKey = makeCodeCopyKey(messageId, codeIndex)
  const copyLabel = isCopiedCodeBlock(messageId, codeIndex) ? "Copied ✓" : "Copy code"

  return `
    <div class="message-code-wrap">
      <div class="message-code-header">
        <span class="message-code-language">${safeLanguage || "code"}</span>
        <button
          type="button"
          class="message-code-copy-btn"
          data-copy-code="${escapeHtml(codeKey)}"
          aria-label="Copy code block"
        >
          ${copyLabel}
        </button>
      </div>
      <pre class="message-code-block"><code>${safeCode}</code></pre>
    </div>
  `
}

function renderMessageContent(message){
  const messageId = getMessageId(message)
  const rawContent = String(message?.content || "")

  if(!rawContent.trim()){
    return "&nbsp;"
  }

  const blocks = splitByCodeFences(rawContent)
  let codeIndex = 0

  return blocks.map(block => {
    if(block.type === "code"){
      const html = renderCodeBlock(block.value, block.language, messageId, codeIndex)
      codeIndex += 1
      return html
    }

    return renderTextBlock(block.value)
  }).join("")
}

function renderMessage(message, index){
  const role = String(message?.role || "assistant").toLowerCase() === "user" ? "user" : "assistant"
  const messageId = escapeHtml(getMessageId(message) || `msg_${index}`)
  const attachments = Array.isArray(message?.attachments) ? message.attachments : []

  return `
    <div class="message-row message-row-${role}">
      <article class="message message-${role}" data-message-id="${messageId}">
        <div class="message-bubble">
          <div class="message-content">${renderMessageContent(message)}</div>
          ${attachments.length ? `<div class="message-attachments">${attachments.map(renderAttachment).join("")}</div>` : ""}
        </div>
        ${renderMessageActions(message)}
      </article>
    </div>
  `
}

function renderThinkingIndicatorMarkup(){
  return `
    <div class="message-row message-row-assistant thinking-row" data-thinking-indicator="true">
      <article class="message message-assistant message-thinking">
        <div class="message-bubble">
          <div class="thinking-indicator" aria-live="polite" aria-label="Nova is thinking">
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
            <span class="thinking-text">Nova is thinking…</span>
          </div>
        </div>
      </article>
    </div>
  `
}

function getMessageElement(messageId){
  if(!el.messages){
    return null
  }

  const safeId = typeof CSS !== "undefined" && typeof CSS.escape === "function"
    ? CSS.escape(String(messageId || ""))
    : String(messageId || "").replace(/"/g, '\\"')

  return el.messages.querySelector(`[data-message-id="${safeId}"]`)
}

function getMessageContentElement(messageId){
  const messageEl = getMessageElement(messageId)
  if(!messageEl){
    return null
  }

  return messageEl.querySelector(".message-content")
}

function getThinkingIndicatorElement(){
  if(!el.messages){
    return null
  }

  return el.messages.querySelector('[data-thinking-indicator="true"]')
}

function showThinkingIndicator(){
  if(!el.messages){
    return
  }

  if(el.emptyState){
    el.emptyState.hidden = true
  }

  removeThinkingIndicator()
  el.messages.insertAdjacentHTML("beforeend", renderThinkingIndicatorMarkup())
  scrollToBottom(true)
}

function removeThinkingIndicator(){
  const thinkingEl = getThinkingIndicatorElement()
  if(thinkingEl){
    thinkingEl.remove()
  }

  const hasMessages = ensureMessagesArray().length > 0
  if(el.emptyState){
    el.emptyState.hidden = hasMessages
  }

  updateJumpButton()
}

function patchMessageContent(messageId, content){
  const contentEl = getMessageContentElement(messageId)
  if(!contentEl){
    return false
  }

  contentEl.innerHTML = renderMessageContent({
    message_id: messageId,
    id: messageId,
    content: content || "",
  }) || "&nbsp;"

  return true
}

function patchMessageActions(message){
  const messageId = getMessageId(message)
  const messageEl = getMessageElement(messageId)
  if(!messageEl){
    return false
  }

  const actionsEl = messageEl.querySelector(".message-actions")
  if(!actionsEl){
    return false
  }

  const temp = document.createElement("div")
  temp.innerHTML = renderMessageActions(message).trim()
  const nextActionsEl = temp.firstElementChild

  if(!nextActionsEl){
    return false
  }

  actionsEl.replaceWith(nextActionsEl)
  return true
}

function refreshMessageContent(messageId){
  const message = findMessageById(messageId)
  if(!message){
    return
  }

  if(!patchMessageContent(messageId, message.content || "")){
    renderMessages()
  }
}

function resetCopyFeedback(){
  copiedMessageId = ""

  if(copyFeedbackTimer){
    clearTimeout(copyFeedbackTimer)
    copyFeedbackTimer = null
  }
}

function setCopyFeedback(messageId){
  copiedMessageId = String(messageId || "").trim()

  if(copyFeedbackTimer){
    clearTimeout(copyFeedbackTimer)
  }

  copyFeedbackTimer = setTimeout(() => {
    const currentId = copiedMessageId
    copiedMessageId = ""
    copyFeedbackTimer = null

    const msg = findMessageById(currentId)
    if(msg){
      patchMessageActions(msg)
    }else{
      renderMessages()
    }
  }, COPY_FEEDBACK_MS)
}

function resetCodeCopyFeedback(){
  copiedCodeKey = ""

  if(copyCodeFeedbackTimer){
    clearTimeout(copyCodeFeedbackTimer)
    copyCodeFeedbackTimer = null
  }
}

function setCodeCopyFeedback(messageId, codeIndex){
  const previousCodeKey = copiedCodeKey
  copiedCodeKey = makeCodeCopyKey(messageId, codeIndex)

  if(copyCodeFeedbackTimer){
    clearTimeout(copyCodeFeedbackTimer)
  }

  copyCodeFeedbackTimer = setTimeout(() => {
    const currentKey = copiedCodeKey
    copiedCodeKey = ""
    copyCodeFeedbackTimer = null

    const [currentMessageId] = String(currentKey || "").split("::")
    if(currentMessageId){
      refreshMessageContent(currentMessageId)
    }else{
      renderMessages()
    }
  }, COPY_CODE_FEEDBACK_MS)

  if(previousCodeKey && previousCodeKey !== copiedCodeKey){
    const [previousMessageId] = String(previousCodeKey).split("::")
    if(previousMessageId){
      refreshMessageContent(previousMessageId)
    }
  }

  refreshMessageContent(messageId)
}

function renderMessages(){
  if(!el.messages){
    return
  }

  const messages = ensureMessagesArray()
  const hasThinkingIndicator = !!getThinkingIndicatorElement()

  if(el.emptyState){
    el.emptyState.hidden = messages.length > 0 || hasThinkingIndicator
  }

  if(!messages.length){
    el.messages.innerHTML = hasThinkingIndicator ? renderThinkingIndicatorMarkup() : ""
    updateJumpButton()
    return
  }

  const thinkingMarkup = hasThinkingIndicator ? renderThinkingIndicatorMarkup() : ""
  el.messages.innerHTML = messages.map(renderMessage).join("") + thinkingMarkup
  updateJumpButton()
}

function syncMessagesFromStorage(messages){
  state.messages = Array.isArray(messages) ? messages.slice() : []
  removeThinkingIndicator()
  resetCodeCopyFeedback()
  renderMessages()
}

function addMessage(message){
  ensureMessagesArray().push(message)
  renderMessages()
}

function clearMessages(){
  state.messages = []
  state.userScrolledUp = false
  resetCopyFeedback()
  resetCodeCopyFeedback()
  removeThinkingIndicator()
  renderMessages()
}

function findMessageById(id){
  const targetId = String(id || "").trim()
  return ensureMessagesArray().find(message => getMessageId(message) === targetId) || null
}

function replaceMessage(id, patch){
  const targetId = String(id || "").trim()
  const messages = ensureMessagesArray()
  const index = messages.findIndex(message => getMessageId(message) === targetId)

  if(index === -1){
    return
  }

  messages[index] = {
    ...messages[index],
    ...patch,
  }

  const updated = messages[index]

  if(!patchMessageContent(targetId, updated.content || "")){
    renderMessages()
    return
  }

  patchMessageActions(updated)
  updateJumpButton()
}

function removeMessage(id){
  const targetId = String(id || "").trim()
  const messages = ensureMessagesArray()

  if(copiedMessageId === targetId){
    resetCopyFeedback()
  }

  if(copiedCodeKey.startsWith(`${targetId}::`)){
    resetCodeCopyFeedback()
  }

  state.messages = messages.filter(message => getMessageId(message) !== targetId)
  renderMessages()
}

function upsertStreamingAssistantMessage(messageId){
  const id = String(messageId || "").trim()
  if(!id){
    return null
  }

  removeThinkingIndicator()

  const existing = findMessageById(id)
  if(existing){
    return existing
  }

  const message = {
    message_id: id,
    id,
    role: "assistant",
    content: "",
    attachments: [],
    created_at: new Date().toISOString(),
  }

  ensureMessagesArray().push(message)

  if(el.messages){
    if(el.emptyState){
      el.emptyState.hidden = true
    }

    el.messages.insertAdjacentHTML("beforeend", renderMessage(message, ensureMessagesArray().length - 1))
    updateJumpButton()
  }else{
    renderMessages()
  }

  return message
}

function appendToStreamingMessage(messageId, token){
  const msg = findMessageById(messageId)
  if(!msg){
    return
  }

  msg.content = String(msg.content || "") + String(token || "")

  if(!patchMessageContent(messageId, msg.content)){
    renderMessages()
    return
  }

  patchMessageActions(msg)
  updateJumpButton()
}

function finishStreamingMessage(){
  removeThinkingIndicator()
  updateJumpButton()
  scrollToBottom(false)
}

function scrollToBottom(force = false){
  if(!el.messagesScroll){
    return
  }

  if(force || !state.userScrolledUp){
    el.messagesScroll.scrollTop = el.messagesScroll.scrollHeight
    state.userScrolledUp = false
    updateJumpButton()
    return
  }

  if(isNearBottom()){
    el.messagesScroll.scrollTop = el.messagesScroll.scrollHeight
    state.userScrolledUp = false
    updateJumpButton()
  }
}

function updateScrollState(){
  updateUserScrolledState()
}

async function copyTextToClipboard(text){
  const value = String(text || "")

  try{
    await navigator.clipboard.writeText(value)
    return
  }catch(_error){
    const temp = document.createElement("textarea")
    temp.value = value
    document.body.appendChild(temp)
    temp.select()
    document.execCommand("copy")
    temp.remove()
  }
}

async function copyMessageById(messageId){
  const msg = findMessageById(messageId)
  if(!msg){
    return
  }

  const text = String(msg.content || "")
  await copyTextToClipboard(text)

  const previousCopiedId = copiedMessageId
  setCopyFeedback(messageId)

  if(previousCopiedId && previousCopiedId !== messageId){
    const previousMsg = findMessageById(previousCopiedId)
    if(previousMsg){
      patchMessageActions(previousMsg)
    }
  }

  patchMessageActions(msg)
}

async function copyCodeBlockByKey(codeKey){
  const [messageId, codeIndexRaw] = String(codeKey || "").split("::")
  const codeIndex = Number(codeIndexRaw)

  const msg = findMessageById(messageId)
  if(!msg){
    return
  }

  const blocks = splitByCodeFences(msg.content || "")
  const codeBlocks = blocks.filter(block => block.type === "code")
  const codeBlock = codeBlocks[Number.isFinite(codeIndex) ? codeIndex : 0]

  if(!codeBlock){
    return
  }

  await copyTextToClipboard(codeBlock.value || "")
  setCodeCopyFeedback(messageId, Number.isFinite(codeIndex) ? codeIndex : 0)
}

function bindEvents({ onRetry } = {}){
  callbacks.onRetry = onRetry || callbacks.onRetry

  if(eventsBound || !el.messages){
    return
  }

  el.messages.addEventListener("click", async (event) => {
    const target = event.target instanceof Element ? event.target : null
    if(!target){
      return
    }

    const copyCodeBtn = target.closest("[data-copy-code]")
    if(copyCodeBtn){
      const codeKey = copyCodeBtn.getAttribute("data-copy-code") || ""
      await copyCodeBlockByKey(codeKey)
      return
    }

    const copyBtn = target.closest("[data-copy-message]")
    if(copyBtn){
      const messageId = copyBtn.getAttribute("data-copy-message") || ""
      await copyMessageById(messageId)
      return
    }

    const retryBtn = target.closest("[data-retry-message]")
    if(retryBtn){
      const text = retryBtn.getAttribute("data-retry-message") || ""
      if(typeof callbacks.onRetry === "function"){
        await callbacks.onRetry(text)
      }
      return
    }

    const deleteBtn = target.closest("[data-delete-message]")
    if(deleteBtn){
      const messageId = deleteBtn.getAttribute("data-delete-message") || ""
      removeMessage(messageId)
    }
  })

  el.messagesScroll?.addEventListener("scroll", () => {
    updateUserScrolledState()
  })

  el.jumpToLatestBtn?.addEventListener("click", () => {
    scrollToBottom(true)
  })

  eventsBound = true
  updateJumpButton()
}

window.NovaChatMessages = {
  renderMessages,
  syncMessagesFromStorage,
  addMessage,
  clearMessages,
  findMessageById,
  replaceMessage,
  removeMessage,
  upsertStreamingAssistantMessage,
  appendToStreamingMessage,
  finishStreamingMessage,
  scrollToBottom,
  updateScrollState,
  bindEvents,
  showThinkingIndicator,
  removeThinkingIndicator,
}
})()