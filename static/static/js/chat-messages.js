// C:\Users\Owner\nova\static\js\chat-messages.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const answerPayloadApi = window.NovaAnswerPayload || null

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

let eventsBound = false
let copiedMessageId = ""
let copyFeedbackTimer = null

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function formatTime(value){
  if(!value){
    return ""
  }

  try{
    const date = new Date(value)
    if(Number.isNaN(date.getTime())){
      return ""
    }

    return date.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    })
  }catch(_error){
    return ""
  }
}

function isNearBottom(){
  if(!el.messagesScroll){
    return true
  }

  const remaining =
    el.messagesScroll.scrollHeight -
    el.messagesScroll.scrollTop -
    el.messagesScroll.clientHeight

  return remaining <= SCROLL_LOCK_THRESHOLD
}

function scrollToBottom(force = false){
  if(!el.messagesScroll){
    return
  }

  if(force || isNearBottom()){
    el.messagesScroll.scrollTop = el.messagesScroll.scrollHeight
  }
}

function updateJumpButton(){
  if(!el.jumpToLatestBtn || !el.messagesScroll){
    return
  }

  const remaining =
    el.messagesScroll.scrollHeight -
    el.messagesScroll.scrollTop -
    el.messagesScroll.clientHeight

  el.jumpToLatestBtn.classList.toggle("hidden", remaining <= SCROLL_LOCK_THRESHOLD)
}

function parseImageMessage(content){
  const text = String(content || "").trim()

  if(!text.startsWith("[[image]]")){
    return null
  }

  const lines = text
    .split("\n")
    .map((line) => String(line || "").trim())
    .filter(Boolean)

  let imageSrc = ""
  let prompt = ""

  for(const line of lines){
    const lowered = line.toLowerCase()

    if(lowered.startsWith("src:")){
      imageSrc = line.slice(4).trim()
      continue
    }

    if(lowered.startsWith("url:") && !imageSrc){
      imageSrc = line.slice(4).trim()
      continue
    }

    if(lowered.startsWith("prompt:")){
      prompt = line.slice(7).trim()
    }
  }

  if(!imageSrc){
    return null
  }

  return {
    imageSrc,
    prompt,
  }
}

function renderImageMessage(content){
  const parsed = parseImageMessage(content)
  if(!parsed){
    return ""
  }

  const isDataUrl = parsed.imageSrc.startsWith("data:")
  const openLink = isDataUrl
    ? ""
    : `
      <a
        href="${escapeHtml(parsed.imageSrc)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Open image
      </a>
    `

  return `
    <div class="nova-generated-image">
      <div class="nova-generated-image-frame">
        <img
          src="${escapeHtml(parsed.imageSrc)}"
          alt="${escapeHtml(parsed.prompt || "Generated image")}"
          class="nova-generated-image-img"
          loading="lazy"
        >
      </div>

      <div class="nova-generated-image-meta">
        <strong>Generated image</strong>
        ${parsed.prompt ? `<p>${escapeHtml(parsed.prompt)}</p>` : ""}
        ${openLink}
      </div>
    </div>
  `
}

function renderPlainText(content){
  const paragraphs = String(content || "")
    .split(/\n{2,}/)
    .map((part) => `<p>${escapeHtml(part).replaceAll("\n", "<br>")}</p>`)
    .join("")

  return `
    <div class="answer-payload">
      <div class="answer-text">${paragraphs || "<p></p>"}</div>
    </div>
  `
}

function renderMessageBody(message){
  const content = message?.content ?? ""

  if(message?.role === "assistant"){
    const imageMarkup = renderImageMessage(content)
    if(imageMarkup){
      return imageMarkup
    }

    if(answerPayloadApi && typeof answerPayloadApi.renderAnswerPayload === "function"){
      return answerPayloadApi.renderAnswerPayload(content, {
        messageId: message.id,
        copiedMessageId,
      })
    }
  }

  return renderPlainText(content)
}

function getMessages(){
  return Array.isArray(state.messages) ? state.messages : []
}

function renderMessages(){
  if(!el.messages){
    return
  }

  const messages = getMessages()
  const shouldStick = isNearBottom()

  if(el.emptyState){
    el.emptyState.classList.toggle("hidden", messages.length > 0)
  }

  if(!messages.length){
    el.messages.innerHTML = ""
    updateJumpButton()
    return
  }

  el.messages.innerHTML = messages.map((message) => {
    const isUser = message.role === "user"
    const roleClass = isUser ? "user" : "assistant"
    const roleLabel = isUser ? "You" : "Nova"
    const time = formatTime(message.created_at)

    return `
      <article class="message-row ${roleClass} fade-in" data-message-id="${escapeHtml(message.id || "")}">
        <div class="message-avatar ${roleClass}">
          ${isUser ? "Y" : "N"}
        </div>

        <div class="message-card ${roleClass}">
          <div class="message-meta">
            <strong class="message-role">${roleLabel}</strong>
            <span class="message-time">${escapeHtml(time)}</span>
          </div>

          <div class="message-body">
            ${renderMessageBody(message)}
          </div>

          <div class="message-actions">
            <button
              class="message-action-btn"
              type="button"
              data-copy-message="${escapeHtml(message.id || "")}"
            >
              ${copiedMessageId === message.id ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      </article>
    `
  }).join("")

  if(shouldStick){
    scrollToBottom(true)
  }

  updateJumpButton()
}

function copyMessageText(messageId){
  const messages = getMessages()
  const message = messages.find((item) => String(item.id) === String(messageId))

  if(!message){
    return
  }

  const text = String(message.content ?? "").trim()
  if(!text){
    return
  }

  navigator.clipboard.writeText(text).then(() => {
    copiedMessageId = String(messageId)
    renderMessages()

    if(copyFeedbackTimer){
      clearTimeout(copyFeedbackTimer)
    }

    copyFeedbackTimer = window.setTimeout(() => {
      copiedMessageId = ""
      renderMessages()
    }, COPY_FEEDBACK_MS)
  }).catch(() => {
    // ignore clipboard failure
  })
}

function handleMessagesClick(event){
  const target = event.target instanceof Element
    ? event.target.closest("[data-copy-message]")
    : null

  if(!target){
    return
  }

  const messageId = target.getAttribute("data-copy-message")
  if(!messageId){
    return
  }

  copyMessageText(messageId)
}

function bindEvents(){
  if(eventsBound){
    return
  }

  el.messages?.addEventListener("click", handleMessagesClick)

  el.messagesScroll?.addEventListener("scroll", () => {
    updateJumpButton()
  })

  el.jumpToLatestBtn?.addEventListener("click", () => {
    scrollToBottom(true)
    updateJumpButton()
  })

  window.addEventListener("nova:messages-changed", () => {
    renderMessages()
  })

  window.addEventListener("nova:chat-loaded", () => {
    renderMessages()
    scrollToBottom(true)
  })

  eventsBound = true
}

function init(){
  bindEvents()
  renderMessages()
  scrollToBottom(true)
  updateJumpButton()
}

window.NovaChatMessages = {
  renderMessages,
  scrollToBottom,
  updateJumpButton,
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init, { once: true })
}else{
  init()
}

})()