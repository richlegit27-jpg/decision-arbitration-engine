// C:\Users\Owner\nova\static\js\workspace-files.js

(() => {
"use strict"

let initialized = false
let panel = null
let stylesInjected = false

function getAttachmentsService(){
  return window.NovaAttachmentsService || null
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function formatBytes(bytes){
  const value = Number(bytes || 0)

  if(!Number.isFinite(value) || value <= 0){
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB", "TB"]
  let size = value
  let unitIndex = 0

  while(size >= 1024 && unitIndex < units.length - 1){
    size /= 1024
    unitIndex += 1
  }

  if(unitIndex === 0){
    return `${Math.round(size)} ${units[unitIndex]}`
  }

  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`
}

function formatFileMeta(file = {}){
  const parts = []
  const size = formatBytes(file?.size || file?.file_size || 0)
  const mimeType = String(file?.mime_type || file?.type || "").trim()
  const createdAt = String(file?.created_at || file?.uploaded_at || "").trim()

  if(size && size !== "0 B"){
    parts.push(size)
  }

  if(mimeType){
    parts.push(mimeType)
  }

  if(createdAt){
    parts.push(createdAt)
  }

  return parts.length ? parts.join(" • ") : "File"
}

function getFileHref(file = {}){
  return String(file?.url || file?.file_url || file?.path || file?.file_path || file?.storage_path || "").trim()
}

function isImageFile(file = {}){
  const mimeType = String(file?.mime_type || file?.type || "").toLowerCase()
  const name = String(file?.name || file?.filename || "").toLowerCase()
  const href = getFileHref(file)

  if(!href){
    return false
  }

  return (
    mimeType.startsWith("image/") ||
    name.endsWith(".png") ||
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".gif") ||
    name.endsWith(".webp") ||
    name.endsWith(".bmp") ||
    name.endsWith(".svg")
  )
}

function injectStyles(){
  if(stylesInjected){
    return
  }

  if(document.getElementById("workspace-files-inline-styles")){
    stylesInjected = true
    return
  }

  const style = document.createElement("style")
  style.id = "workspace-files-inline-styles"
  style.textContent = `
    .workspace-panel{position:fixed;inset:0;z-index:9999}
    .workspace-panel[hidden]{display:none!important}
    .workspace-overlay{position:absolute;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(2px)}
    .workspace-container{position:absolute;top:0;right:0;width:min(560px,92vw);height:100%;background:#111318;color:#e8ecf1;border-left:1px solid rgba(255,255,255,.08);box-shadow:-12px 0 40px rgba(0,0,0,.35);display:flex;flex-direction:column}
    .workspace-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px;border-bottom:1px solid rgba(255,255,255,.08)}
    .workspace-title{font-size:16px;font-weight:700}
    .workspace-body{flex:1;overflow:auto;padding:16px}
    .workspace-file-list{display:flex;flex-direction:column;gap:12px}
    .workspace-file-item{padding:14px;border:1px solid rgba(255,255,255,.08);border-radius:16px;background:rgba(255,255,255,.03);display:flex;flex-direction:column;gap:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.02)}
    .workspace-file-top{display:flex;gap:12px;align-items:flex-start;min-width:0}
    .workspace-file-thumb-wrap{flex:0 0 auto;width:52px;height:52px;border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03)}
    .workspace-file-thumb{display:block;width:100%;height:100%;object-fit:cover}
    .workspace-file-icon{flex:0 0 auto;width:52px;height:52px;border-radius:14px;display:flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);font-size:18px}
    .workspace-file-copy{min-width:0;flex:1}
    .workspace-file-name{font-size:14px;font-weight:700;word-break:break-word;line-height:1.4}
    .workspace-file-meta{font-size:12px;opacity:.72;line-height:1.45;margin-top:3px;word-break:break-word}
    .workspace-file-actions{display:flex;flex-wrap:wrap;gap:8px}
    .workspace-file-open,.workspace-file-attach{align-self:flex-start}
    .workspace-empty{padding:18px;border:1px dashed rgba(255,255,255,.12);border-radius:12px;background:rgba(255,255,255,.02)}
    .workspace-error-detail{margin-top:10px;font-size:12px;color:#ffb4b4;white-space:pre-wrap;word-break:break-word}
  `
  document.head.appendChild(style)
  stylesInjected = true
}

function createPanel(){
  const el = document.createElement("div")
  el.id = "workspaceFilesPanel"
  el.className = "workspace-panel"
  el.hidden = true

  el.innerHTML = `
    <div class="workspace-overlay"></div>

    <div class="workspace-container" role="dialog" aria-modal="true" aria-label="Workspace Files">
      <div class="workspace-header">
        <div class="workspace-title">Workspace Files</div>
        <button id="workspaceCloseBtn" class="sidebar-btn" type="button">Close</button>
      </div>

      <div class="workspace-body">
        <div id="workspaceFileList" class="workspace-file-list">Loading files...</div>
      </div>
    </div>
  `

  return el
}

function bindPanelEvents(){
  if(!panel){
    return
  }

  const closeBtn = panel.querySelector("#workspaceCloseBtn")
  const overlay = panel.querySelector(".workspace-overlay")

  if(closeBtn && closeBtn.dataset.bound !== "true"){
    closeBtn.dataset.bound = "true"
    closeBtn.addEventListener("click", closePanel)
  }

  if(overlay && overlay.dataset.bound !== "true"){
    overlay.dataset.bound = "true"
    overlay.addEventListener("click", closePanel)
  }
}

function ensurePanel(){
  injectStyles()

  if(panel && document.body.contains(panel)){
    return panel
  }

  const existing = document.getElementById("workspaceFilesPanel")

  if(existing){
    panel = existing
    bindPanelEvents()
    return panel
  }

  const root = document.getElementById("workspaceFilesRoot")

  panel = createPanel()

  if(root){
    root.appendChild(panel)
  }else{
    document.body.appendChild(panel)
  }

  bindPanelEvents()
  return panel
}

function attachFileToComposer(file = {}){
  const normalized = {
    id: String(file?.id || file?.attachment_id || file?.file_id || "").trim(),
    attachment_id: String(file?.attachment_id || file?.id || file?.file_id || "").trim(),
    file_id: String(file?.file_id || file?.id || file?.attachment_id || "").trim(),
    name: String(file?.name || file?.filename || "file"),
    filename: String(file?.filename || file?.name || "file"),
    mime_type: String(file?.mime_type || file?.type || "application/octet-stream"),
    type: String(file?.type || file?.mime_type || "application/octet-stream"),
    size: Number(file?.size || file?.file_size || 0),
    file_size: Number(file?.file_size || file?.size || 0),
    url: file?.url || file?.file_url || null,
    path: file?.path || file?.file_path || file?.storage_path || null,
    file_path: file?.file_path || file?.path || file?.storage_path || null,
    storage_path: file?.storage_path || file?.path || file?.file_path || null,
  }

  const attachmentsService = getAttachmentsService()

  if(attachmentsService && typeof attachmentsService.attachExistingFile === "function"){
    attachmentsService.attachExistingFile(normalized)

    if(typeof attachmentsService.renderPendingAttachments === "function"){
      attachmentsService.renderPendingAttachments()
    }

    if(window.NovaComposer?.updateComposerState){
      window.NovaComposer.updateComposerState()
    }

    closePanel()
    return
  }

  if(window.NovaComposer?.setPendingFiles){
    const current = Array.isArray(window.NovaChatState?.state?.pendingAttachments)
      ? window.NovaChatState.state.pendingAttachments.slice()
      : []

    current.push(normalized)
    window.NovaComposer.setPendingFiles(current)
    closePanel()
    return
  }

  console.error("NovaWorkspaceFiles: no attachment path available")
}

function renderFileCard(file, index){
  const name = escapeHtml(file?.name || file?.filename || `File ${index + 1}`)
  const meta = escapeHtml(formatFileMeta(file))
  const href = escapeHtml(getFileHref(file))
  const preview = isImageFile(file)
    ? `
      <div class="workspace-file-thumb-wrap">
        <img class="workspace-file-thumb" src="${href}" alt="${name}" loading="lazy">
      </div>
    `
    : `
      <div class="workspace-file-icon" aria-hidden="true">📄</div>
    `

  return `
    <div class="workspace-file-item">
      <div class="workspace-file-top">
        ${preview}
        <div class="workspace-file-copy">
          <div class="workspace-file-name">${name}</div>
          <div class="workspace-file-meta">${meta}</div>
        </div>
      </div>

      <div class="workspace-file-actions">
        ${href ? `
          <a
            class="workspace-file-open sidebar-btn"
            href="${href}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open
          </a>
        ` : ""}
        <button
          class="workspace-file-attach sidebar-btn"
          data-workspace-index="${index}"
          type="button"
        >
          Attach
        </button>
      </div>
    </div>
  `
}

async function loadFiles(){
  const root = ensurePanel()
  const list = root?.querySelector("#workspaceFileList")

  if(!list){
    return
  }

  list.textContent = "Loading files..."

  try{
    const response = await fetch("/api/files", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    })

    const text = await response.text()

    let payload = null

    try{
      payload = JSON.parse(text)
    }catch(_error){
      payload = null
    }

    if(!response.ok){
      const detail =
        payload?.detail ||
        payload?.error ||
        text ||
        `Request failed: ${response.status}`

      list.innerHTML = `
        <div class="workspace-empty">Failed to load files</div>
        <div class="workspace-error-detail">${escapeHtml(detail)}</div>
      `
      return
    }

    const files = Array.isArray(payload?.files) ? payload.files : []

    if(files.length === 0){
      list.innerHTML = `<div class="workspace-empty">No files uploaded yet</div>`
      return
    }

    list.innerHTML = files.map((file, index) => renderFileCard(file, index)).join("")

    const attachButtons = root.querySelectorAll(".workspace-file-attach")

    attachButtons.forEach((button) => {
      if(button.dataset.bound === "true"){
        return
      }

      button.dataset.bound = "true"
      button.addEventListener("click", () => {
        const index = Number(button.dataset.workspaceIndex)
        const file = files[index]

        if(!file){
          console.error("NovaWorkspaceFiles: file not found for attach")
          return
        }

        attachFileToComposer(file)
      })
    })
  }catch(error){
    console.error("NovaWorkspaceFiles loadFiles error:", error)

    if(list){
      list.innerHTML = `
        <div class="workspace-empty">Failed to load files</div>
        <div class="workspace-error-detail">${escapeHtml(error?.message || "Unknown error")}</div>
      `
    }
  }
}

function openPanel(){
  const root = ensurePanel()
  if(!root){
    return
  }

  root.hidden = false
  void loadFiles()
}

function closePanel(){
  const root = ensurePanel()
  if(!root){
    return
  }

  root.hidden = true
}

function togglePanel(){
  const root = ensurePanel()
  if(!root){
    return
  }

  if(root.hidden){
    openPanel()
  }else{
    closePanel()
  }
}

function bindButton(){
  const btn = document.getElementById("btnWorkspaceFiles")

  if(!btn){
    return
  }

  if(btn.dataset.workspaceBound === "true"){
    return
  }

  btn.dataset.workspaceBound = "true"
  btn.addEventListener("click", togglePanel)
}

function init(){
  ensurePanel()
  bindButton()

  if(initialized){
    return
  }

  initialized = true

  document.addEventListener("keydown", (event) => {
    if(event.key === "Escape" && panel && !panel.hidden){
      closePanel()
    }
  })
}

window.NovaWorkspaceFiles = {
  init,
  open: openPanel,
  close: closePanel,
  toggle: togglePanel,
  reload: loadFiles,
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init, { once: true })
}else{
  init()
}

})()