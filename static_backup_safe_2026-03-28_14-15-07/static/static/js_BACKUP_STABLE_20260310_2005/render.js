// C:\Users\Owner\nova\static\js\render.js

(() => {
"use strict"

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function renderMessages({ container, messages = [] } = {}){
  if(!container){
    return
  }

  container.innerHTML = ""

  if(!Array.isArray(messages) || messages.length === 0){
    renderEmptyState(container)
    return
  }

  const fragment = document.createDocumentFragment()

  messages.forEach(message => {
    fragment.appendChild(createMessageRow(message))
  })

  container.appendChild(fragment)
  scrollToBottom(container)
}

function renderEmptyState(container){
  const empty = document.createElement("div")
  empty.className = "messages-empty"
  empty.innerHTML = `
    <div class="messages-empty-inner">
      <div class="messages-empty-title">Nova</div>
      <div class="messages-empty-subtitle">Start a new conversation.</div>
    </div>
  `
  container.appendChild(empty)
}

function createMessageRow(message = {}){
  const role = String(message.role || "assistant")
  const row = document.createElement("div")
  row.className = `message-row ${role === "user" ? "user" : "assistant"}`

  const bubble = document.createElement("div")
  bubble.className = "message-bubble"

  const body = document.createElement("div")
  body.className = "message-content"
  body.innerHTML = formatMessageContent(String(message.content || ""))

  bubble.appendChild(body)

  const attachments = Array.isArray(message.attachments) ? message.attachments : []
  if(attachments.length){
    bubble.appendChild(createAttachmentList(attachments))
  }

  const actions = document.createElement("div")
  actions.className = "message-actions"

  if(role === "assistant"){
    actions.appendChild(createActionButton("Copy", "copy"))
    actions.appendChild(createActionButton("Regenerate", "regenerate"))
  }

  if(role === "user"){
    actions.appendChild(createActionButton("Edit", "edit"))
  }

  const createdAt = String(message.created_at || "")
  if(createdAt){
    const meta = document.createElement("div")
    meta.className = "message-meta"
    meta.textContent = formatTimestamp(createdAt)
    bubble.appendChild(meta)
  }

  row.appendChild(bubble)

  if(actions.childNodes.length){
    row.appendChild(actions)
  }

  return row
}

function createActionButton(label, action){
  const btn = document.createElement("button")
  btn.type = "button"
  btn.className = "message-action-btn"
  btn.dataset.action = action
  btn.textContent = label
  return btn
}

function createAttachmentList(items = []){
  const wrap = document.createElement("div")
  wrap.className = "message-attachments"

  items.forEach(item => {
    const card = document.createElement("div")
    card.className = "message-attachment"

    const name = document.createElement("div")
    name.className = "message-attachment-name"
    name.textContent = String(item.name || item.filename || "attachment")

    const meta = document.createElement("div")
    meta.className = "message-attachment-meta"

    const type = String(item.type || item.mime_type || "")
    const size = item.size ? formatBytes(item.size) : ""

    meta.textContent = [type, size].filter(Boolean).join(" · ")

    card.appendChild(name)

    if(meta.textContent){
      card.appendChild(meta)
    }

    wrap.appendChild(card)
  })

  return wrap
}

function formatMessageContent(text){
  const safe = escapeHtml(text)

  return safe
    .replace(/```([\s\S]*?)```/g, (_match, code) => {
      return `<pre class="message-code"><code>${code.trim()}</code></pre>`
    })
    .replace(/`([^`]+)`/g, (_match, code) => {
      return `<code class="message-inline-code">${code}</code>`
    })
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br>")
}

function formatTimestamp(value){
  const date = new Date(value)

  if(Number.isNaN(date.getTime())){
    return ""
  }

  try{
    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    }).format(date)
  }catch{
    return date.toLocaleString()
  }
}

function formatBytes(bytes){
  const n = Number(bytes || 0)

  if(!Number.isFinite(n) || n <= 0){
    return ""
  }

  const units = ["B", "KB", "MB", "GB", "TB"]
  let size = n
  let i = 0

  while(size >= 1024 && i < units.length - 1){
    size /= 1024
    i += 1
  }

  const fixed = size >= 10 || i === 0 ? 0 : 1
  return `${size.toFixed(fixed)} ${units[i]}`
}

function scrollToBottom(container){
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight
  })
}

window.NovaRender = {
  renderMessages,
  escapeHtml,
  formatBytes,
}

})()