// C:\Users\Owner\nova\static\js\memory-panel.js

(() => {
"use strict"

const api = window.NovaAPI

if(!api){
  throw new Error("NovaMemoryPanel: window.NovaAPI is required")
}

const ui = {
  panel: document.getElementById("memoryPanel"),
  backdrop: document.getElementById("memoryBackdrop"),
  list: document.getElementById("memoryList"),
  status: document.getElementById("memoryStatus"),
  input: document.getElementById("memoryInput"),
  btnOpenSidebar: document.getElementById("btnOpenMemory"),
  btnOpenTopbar: document.getElementById("btnTopbarMemory"),
  btnClose: document.getElementById("btnCloseMemory"),
  btnAdd: document.getElementById("btnAddMemory"),
  btnRefresh: document.getElementById("btnRefreshMemory"),
  btnClear: document.getElementById("btnClearMemory"),
}

const state = {
  isOpen: false,
  isLoading: false,
  lastFocusedElement: null,
}

let eventsBound = false

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function setStatus(text = "", isError = false){
  if(!ui.status){
    return
  }

  ui.status.textContent = String(text || "")
  ui.status.style.color = isError ? "var(--red, #ef4444)" : "var(--muted)"
}

function setLoading(nextValue){
  state.isLoading = !!nextValue

  const controls = [
    ui.btnAdd,
    ui.btnRefresh,
    ui.btnClear,
    ui.btnClose,
    ui.btnOpenSidebar,
    ui.btnOpenTopbar,
  ]

  for(const el of controls){
    if(el){
      el.disabled = state.isLoading
    }
  }

  if(ui.input){
    ui.input.disabled = state.isLoading
  }

  if(ui.panel){
    ui.panel.setAttribute("aria-busy", state.isLoading ? "true" : "false")
  }
}

function renderList(memories = []){
  if(!ui.list){
    return
  }

  const items = Array.isArray(memories) ? memories : []

  if(!items.length){
    ui.list.innerHTML = `<div class="memory-empty">No memory saved.</div>`
    return
  }

  ui.list.innerHTML = items.map((item, index) => {
    const text = String(item || "").trim()
    const safeText = escapeHtml(text)
    const safeValue = encodeURIComponent(text)

    return `
      <div class="memory-item" data-memory-index="${index}">
        <div class="memory-item-text">${safeText}</div>
        <button
          class="memory-item-delete"
          type="button"
          data-memory-delete="${safeValue}"
          aria-label="Delete memory"
          title="Delete memory"
        >
          Delete
        </button>
      </div>
    `
  }).join("")
}

async function refresh(options = {}){
  const { silent = false } = options

  if(!ui.list){
    return []
  }

  try{
    setLoading(true)

    if(!silent){
      setStatus("Loading memory...")
    }

    const payload = await api.listMemory()
    const memories = Array.isArray(payload?.memories) ? payload.memories : []

    renderList(memories)
    setStatus(
      memories.length
        ? `Loaded ${memories.length} memory item${memories.length === 1 ? "" : "s"}.`
        : "No memory saved."
    )

    return memories
  }catch(error){
    console.error("NovaMemoryPanel refresh error:", error)
    renderList([])
    setStatus("Failed to load memory.", true)
    return []
  }finally{
    setLoading(false)
  }
}

async function focusInputSoon(){
  if(!ui.input){
    return
  }

  requestAnimationFrame(() => {
    try{
      ui.input.focus()
      ui.input.setSelectionRange(ui.input.value.length, ui.input.value.length)
    }catch(_error){
    }
  })
}

async function open(){
  if(!ui.panel){
    return
  }

  if(state.isOpen){
    await refresh({ silent: true })
    await focusInputSoon()
    return
  }

  state.lastFocusedElement = document.activeElement instanceof HTMLElement
    ? document.activeElement
    : null

  state.isOpen = true
  ui.panel.hidden = false
  document.body.classList.add("memory-open")

  await refresh()
  await focusInputSoon()
}

function close(){
  if(!ui.panel){
    return
  }

  state.isOpen = false
  ui.panel.hidden = true
  document.body.classList.remove("memory-open")

  if(state.lastFocusedElement && typeof state.lastFocusedElement.focus === "function"){
    try{
      state.lastFocusedElement.focus()
    }catch(_error){
    }
  }

  state.lastFocusedElement = null
}

async function addFromInput(){
  if(!ui.input){
    return
  }

  const raw = String(ui.input.value || "").trim()
  if(!raw){
    setStatus("Enter memory text first.", true)
    ui.input.focus()
    return
  }

  const items = raw
    .split("\n")
    .map(item => String(item || "").trim())
    .filter(Boolean)

  if(!items.length){
    setStatus("Enter memory text first.", true)
    ui.input.focus()
    return
  }

  try{
    setLoading(true)
    setStatus("Adding memory...")

    const payload = await api.addMemory(items)
    const memories = Array.isArray(payload?.memories) ? payload.memories : []

    ui.input.value = ""
    renderList(memories)
    setStatus(`Added ${items.length} memory item${items.length === 1 ? "" : "s"}.`)
    ui.input.focus()
  }catch(error){
    console.error("NovaMemoryPanel add error:", error)
    setStatus("Failed to add memory.", true)
  }finally{
    setLoading(false)
  }
}

async function deleteItem(memoryText){
  const text = String(memoryText || "").trim()
  if(!text){
    return
  }

  try{
    setLoading(true)
    setStatus("Deleting memory...")

    const payload = await api.deleteMemoryItems([text])
    const memories = Array.isArray(payload?.memories) ? payload.memories : []

    renderList(memories)
    setStatus("Memory deleted.")
  }catch(error){
    console.error("NovaMemoryPanel delete error:", error)
    setStatus("Failed to delete memory.", true)
  }finally{
    setLoading(false)
  }
}

async function clearAll(){
  const confirmed = window.confirm("Clear all Nova memory?")
  if(!confirmed){
    return
  }

  try{
    setLoading(true)
    setStatus("Clearing memory...")

    await api.clearMemory()

    renderList([])
    setStatus("All memory cleared.")
  }catch(error){
    console.error("NovaMemoryPanel clear error:", error)
    setStatus("Failed to clear memory.", true)
  }finally{
    setLoading(false)
  }
}

function handleOpenClick(){
  void open()
}

function handleCloseClick(){
  close()
}

function handleEscapeKey(event){
  if(event.key === "Escape" && state.isOpen){
    event.preventDefault()
    close()
  }
}

function bindEvents(){
  if(eventsBound){
    return
  }

  if(ui.btnOpenSidebar){
    ui.btnOpenSidebar.addEventListener("click", handleOpenClick)
  }

  if(ui.btnOpenTopbar){
    ui.btnOpenTopbar.addEventListener("click", handleOpenClick)
  }

  if(ui.btnClose){
    ui.btnClose.addEventListener("click", handleCloseClick)
  }

  if(ui.backdrop){
    ui.backdrop.addEventListener("click", handleCloseClick)
  }

  if(ui.btnRefresh){
    ui.btnRefresh.addEventListener("click", async () => {
      await refresh()
    })
  }

  if(ui.btnAdd){
    ui.btnAdd.addEventListener("click", async () => {
      await addFromInput()
    })
  }

  if(ui.btnClear){
    ui.btnClear.addEventListener("click", async () => {
      await clearAll()
    })
  }

  if(ui.input){
    ui.input.addEventListener("keydown", async event => {
      if(event.key === "Enter" && (event.ctrlKey || event.metaKey)){
        event.preventDefault()
        await addFromInput()
      }
    })
  }

  if(ui.list){
    ui.list.addEventListener("click", async event => {
      const target = event.target instanceof Element ? event.target.closest("[data-memory-delete]") : null
      if(!target){
        return
      }

      const encoded = String(target.getAttribute("data-memory-delete") || "").trim()
      const text = encoded ? decodeURIComponent(encoded) : ""
      if(!text){
        return
      }

      await deleteItem(text)
    })
  }

  document.addEventListener("keydown", handleEscapeKey)

  eventsBound = true
}

function init(){
  bindEvents()
}

window.NovaMemoryPanel = {
  init,
  open,
  close,
  refresh,
  state,
}

})()