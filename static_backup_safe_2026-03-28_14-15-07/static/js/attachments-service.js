// C:\Users\Owner\nova\static\js\attachments-service.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState

if(!chatStateApi){
  throw new Error("NovaAttachmentsService: window.NovaChatState is required")
}

const { state } = chatStateApi

function makeId(prefix = "attachment"){
  if(window.crypto?.randomUUID){
    return `${prefix}_${window.crypto.randomUUID()}`
  }

  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function ensurePendingAttachments(){
  if(!Array.isArray(state.pendingAttachments)){
    state.pendingAttachments = []
  }

  return state.pendingAttachments
}

function formatBytes(bytes){
  const size = Number(bytes || 0)

  if(size <= 0){
    return "0 B"
  }

  if(size < 1024){
    return `${size} B`
  }

  if(size < 1024 * 1024){
    return `${Math.max(1, Math.round(size / 1024))} KB`
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function getExtension(filename){
  const name = String(filename || "")
  const parts = name.split(".").filter(Boolean)
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ""
}

function inferKind(file){
  const type = String(file?.type || "").toLowerCase()
  const name = String(file?.name || "").toLowerCase()
  const extension = getExtension(name)

  if(type.startsWith("image/")){
    return "image"
  }

  if(type.startsWith("audio/")){
    return "audio"
  }

  if(type.startsWith("video/")){
    return "video"
  }

  if(type === "application/pdf" || extension === "pdf"){
    return "pdf"
  }

  if(
    type.includes("json") ||
    type.includes("javascript") ||
    type.includes("typescript") ||
    type.includes("xml") ||
    type.includes("yaml") ||
    type.includes("html") ||
    type.includes("css") ||
    type.startsWith("text/") ||
    [
      "py",
      "js",
      "ts",
      "tsx",
      "jsx",
      "html",
      "css",
      "json",
      "md",
      "txt",
      "log",
      "csv",
      "yml",
      "yaml",
      "xml",
      "sh",
      "ps1",
      "bat",
      "java",
      "c",
      "cpp",
      "cs",
      "go",
      "rs",
      "php",
      "rb",
      "sql",
    ].includes(extension)
  ){
    return "text"
  }

  return "file"
}

function canReadAsText(file){
  const kind = inferKind(file)
  return kind === "text"
}

function readFileAsDataUrl(file){
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      resolve(String(reader.result || ""))
    }

    reader.onerror = () => {
      reject(new Error(`Could not read ${file?.name || "file"} as data URL`))
    }

    reader.readAsDataURL(file)
  })
}

function readFileAsText(file){
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      resolve(String(reader.result || ""))
    }

    reader.onerror = () => {
      reject(new Error(`Could not read ${file?.name || "file"} as text`))
    }

    reader.readAsText(file)
  })
}

async function normalizeFile(file){
  if(!(file instanceof File)){
    throw new Error("Invalid file")
  }

  const url = await readFileAsDataUrl(file)
  let content = ""

  if(canReadAsText(file)){
    try{
      content = await readFileAsText(file)
    }catch(_error){
      content = ""
    }
  }

  return {
    id: makeId("attachment"),
    name: String(file.name || "attachment"),
    type: String(file.type || "application/octet-stream"),
    size: Number(file.size || 0),
    kind: inferKind(file),
    url,
    content,
  }
}

async function normalizeFiles(fileList){
  const files = Array.from(fileList || []).filter(Boolean)
  const normalized = []

  for(const file of files){
    normalized.push(await normalizeFile(file))
  }

  return normalized
}

function mergeAttachments(nextItems){
  const current = ensurePendingAttachments()
  const safeItems = Array.isArray(nextItems) ? nextItems.filter(Boolean) : []

  state.pendingAttachments = [...current, ...safeItems]
  return state.pendingAttachments
}

function removeAttachmentById(attachmentId){
  state.pendingAttachments = ensurePendingAttachments().filter((item) => {
    return String(item.id) !== String(attachmentId)
  })

  return state.pendingAttachments
}

function clearAttachments(){
  state.pendingAttachments = []
  return state.pendingAttachments
}

function notifyAttachmentsChanged(){
  window.dispatchEvent(
    new CustomEvent("nova:attachments-changed", {
      detail: ensurePendingAttachments(),
    })
  )
}

function createNativePicker(options = {}){
  return new Promise((resolve) => {
    const input = document.createElement("input")
    input.type = "file"
    input.multiple = options.multiple !== false

    if(options.accept){
      input.accept = String(options.accept)
    }

    input.style.position = "fixed"
    input.style.left = "-9999px"
    input.style.width = "1px"
    input.style.height = "1px"
    input.style.opacity = "0"

    document.body.appendChild(input)

    input.addEventListener("change", async () => {
      try{
        const items = await normalizeFiles(input.files)
        resolve(items)
      }catch(error){
        console.error("NovaAttachmentsService picker failed:", error)
        resolve([])
      }finally{
        input.remove()
      }
    }, { once: true })

    input.addEventListener("cancel", () => {
      input.remove()
      resolve([])
    }, { once: true })

    input.click()
  })
}

async function openPicker(options = {}){
  const items = await createNativePicker(options)

  if(items.length){
    mergeAttachments(items)
    notifyAttachmentsChanged()
  }

  return items
}

async function addFiles(fileList){
  const items = await normalizeFiles(fileList)

  if(items.length){
    mergeAttachments(items)
    notifyAttachmentsChanged()
  }

  return items
}

async function addFromEvent(event){
  const files = event?.target?.files || event?.dataTransfer?.files || []
  return addFiles(files)
}

function getAttachments(){
  return ensurePendingAttachments()
}

function getAttachmentById(attachmentId){
  return ensurePendingAttachments().find((item) => {
    return String(item.id) === String(attachmentId)
  }) || null
}

function getPreviewMarkup(item){
  if(!item){
    return ""
  }

  const kind = String(item.kind || "")
  const name = String(item.name || "Attachment")
  const size = formatBytes(item.size)

  if(kind === "image" && item.url){
    return `
      <div class="attachment-preview attachment-preview-image">
        <div class="attachment-preview-thumb-wrap">
          <img
            src="${item.url}"
            alt="${name}"
            class="attachment-preview-thumb"
            loading="lazy"
          >
        </div>
        <div class="attachment-preview-meta">
          <div class="attachment-preview-name">${name}</div>
          <div class="attachment-preview-size">${size}</div>
        </div>
      </div>
    `
  }

  if(kind === "audio"){
    return `
      <div class="attachment-preview attachment-preview-audio">
        <div class="attachment-preview-icon">🎙️</div>
        <div class="attachment-preview-meta">
          <div class="attachment-preview-name">${name}</div>
          <div class="attachment-preview-size">${size}</div>
        </div>
      </div>
    `
  }

  if(kind === "pdf"){
    return `
      <div class="attachment-preview attachment-preview-pdf">
        <div class="attachment-preview-icon">📄</div>
        <div class="attachment-preview-meta">
          <div class="attachment-preview-name">${name}</div>
          <div class="attachment-preview-size">${size}</div>
        </div>
      </div>
    `
  }

  if(kind === "text"){
    return `
      <div class="attachment-preview attachment-preview-text">
        <div class="attachment-preview-icon">📝</div>
        <div class="attachment-preview-meta">
          <div class="attachment-preview-name">${name}</div>
          <div class="attachment-preview-size">${size}</div>
        </div>
      </div>
    `
  }

  return `
    <div class="attachment-preview attachment-preview-file">
      <div class="attachment-preview-icon">📎</div>
      <div class="attachment-preview-meta">
        <div class="attachment-preview-name">${name}</div>
        <div class="attachment-preview-size">${size}</div>
      </div>
    </div>
  `
}

window.NovaAttachmentsService = {
  openPicker,
  addFiles,
  addFromEvent,
  getAttachments,
  getAttachmentById,
  getPreviewMarkup,
  removeAttachmentById,
  clearAttachments,
  notifyAttachmentsChanged,
  formatBytes,
  inferKind,
}

})()