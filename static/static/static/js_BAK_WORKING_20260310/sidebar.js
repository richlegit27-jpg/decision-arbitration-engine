// C:\Users\Owner\nova\static\js\sidebar.js

(() => {
"use strict"

function open(sidebarEl, overlayEl){
  sidebarEl?.classList.add("is-open")
  overlayEl?.classList.add("is-visible")
}

function close(sidebarEl, overlayEl){
  sidebarEl?.classList.remove("is-open")
  overlayEl?.classList.remove("is-visible")
}

function toggle(sidebarEl, overlayEl){
  if(!sidebarEl){
    return false
  }

  const isOpen = sidebarEl.classList.contains("is-open")

  if(isOpen){
    close(sidebarEl, overlayEl)
    return false
  }

  open(sidebarEl, overlayEl)
  return true
}

function renderChatList({ container, chats = [], activeChatId = "", onSelect } = {}){
  if(!container){
    return
  }

  container.innerHTML = ""

  if(!Array.isArray(chats) || chats.length === 0){
    const empty = document.createElement("div")
    empty.className = "chat-list-empty"
    empty.textContent = "No chats yet"
    container.appendChild(empty)
    return
  }

  const fragment = document.createDocumentFragment()

  chats.forEach(chat => {
    const item = document.createElement("button")
    item.type = "button"
    item.className = "chat-list-item"
    item.dataset.chatId = String(chat.chat_id || "")

    if(String(chat.chat_id || "") === String(activeChatId || "")){
      item.classList.add("active")
    }

    const title = document.createElement("div")
    title.className = "chat-list-item-title"
    title.textContent = String(chat.title || "New chat")

    const meta = document.createElement("div")
    meta.className = "chat-list-item-meta"
    meta.textContent = formatUpdated(chat.updated)

    item.appendChild(title)
    item.appendChild(meta)

    item.addEventListener("click", () => {
      if(typeof onSelect === "function"){
        onSelect(chat)
      }
    })

    fragment.appendChild(item)
  })

  container.appendChild(fragment)
}

function formatUpdated(value){
  if(!value){
    return ""
  }

  const date = new Date(value)

  if(Number.isNaN(date.getTime())){
    return ""
  }

  try{
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date)
  }catch{
    return date.toLocaleString()
  }
}

window.NovaSidebar = {
  open,
  close,
  toggle,
  renderChatList,
}

})()