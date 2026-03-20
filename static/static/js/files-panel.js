// C:\Users\Owner\nova\static\js\files-panel.js

(() => {
"use strict"

const bootstrap = window.NOVA_BOOTSTRAP || {}
const filesUrl = bootstrap.filesUrl || "/api/files"

const chatStateApi = window.NovaChatState
const attachmentsApi = window.NovaAttachmentsService || null

if(!chatStateApi){
  throw new Error("NovaFilesPanel: window.NovaChatState is required")
}

const { state } = chatStateApi

const el = {
  filesList: document.getElementById("filesList"),
  clearFilesBtn: document.getElementById("clearFilesBtn"),
}

let eventsBound = false
let refreshInFlight = false
let serverFiles = []

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

  if(value < 1024){
    return `${value} B`
  }

  if(value < 1024 * 1024){
    return `${(value / 1024).toFixed(1)} KB`
  }

  if(value < 1024 * 1024 * 1024){
    return `${(value / (1024 * 1024)).toFixed(1)} MB`
  }

  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDate(value){
  if(!value){
    return ""
  }

  const date = new Date(Number(value) * 1000 || value)
  if(Number.isNaN(date.getTime())){
    return ""
  }

  return date.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  })
}

function getIconForType(type = "", name = ""){
  const lowerType = String(type || "").toLowerCase()
  const lowerName = String(name || "").toLowerCase()

  if(lowerType.includes("image/")){
    return "🖼️"
  }

  if(lowerType.includes("pdf") || lowerName.endsWith(".pdf")){
    return "📄"
  }

  if(
    lowerType.includes("json") ||
    lowerType.includes("javascript") ||
    lowerType.includes("python") ||
    lowerType.includes("html") ||
    lowerType.includes("css") ||
    lowerType.includes("xml") ||
    lowerType.includes("text/") ||
    lowerName.endsWith(".py") ||
    lowerName.endsWith(".js") ||
    lowerName.endsWith(".ts") ||
    lowerName.endsWith(".tsx") ||
    lowerName.endsWith(".jsx") ||
    lowerName.endsWith(".html") ||
    lowerName.endsWith(".css") ||
    lowerName.endsWith(".json") ||
    lowerName.endsWith(".txt") ||
    lowerName.endsWith(".md")
  ){
    return "💻"
  }

  if(
    lowerType.includes("zip") ||
    lowerType.includes("compressed") ||
    lowerName.endsWith(".zip") ||
    lowerName.endsWith(".rar") ||
    lowerName.endsWith(".7z")
  ){
    return "🗜️"
  }

  if(lowerType.includes("audio/") || lowerType.includes("video/")){
    return "🎞️"
  }

  return "📎"
}

function getPendingAttachments(){
  return Array.isArray(state.pendingAttachments) ? state.pendingAttachments : []
}

function normalizeServerFile(file){
  if(!file || typeof file !== "object"){
    return null
  }

  return {
    name: String(file.name || ""),
    path: String(file.path || ""),
    size: Number(file.size || 0),
    modified_at: file.modified_at || "",
    content_type: String(file.content_type || ""),
    is_text: !!file.is_text,
  }
}

function getDownloadUrl(name){
  return `${filesUrl}/${encodeURIComponent(String(name || "").trim())}/download`
}

function renderEmptyState(){
  if(!el.filesList){
    return
  }

  el.filesList.innerHTML = `
    <div class="empty-state-card fade-in">
      <div class="empty-icon">📎</div>
      <h3>No files yet</h3>
      <p>Attach files from the composer and uploaded files will appear here.</p>
    </div>
  `
}

function renderPendingSection(pending){
  if(!pending.length){
    return ""
  }

  return `
    <section class="files-panel-section">
      <div class="files-panel-section-header">
        <h3>Pending attachments</h3>
        <span>${pending.length}</span>
      </div>

      <div class="files-panel-list">
        ${pending.map((attachment) => {
          const icon = getIconForType(attachment.type, attachment.name)

          return `
            <article class="file-row fade-in" data-file-id="${escapeHtml(attachment.id)}">
              <div class="file-row-main">
                <span class="file-row-icon">${icon}</span>
                <div class="file-row-copy">
                  <strong class="file-row-name">${escapeHtml(attachment.name || "Unnamed file")}</strong>
                  <small class="file-row-meta">
                    ${escapeHtml(attachment.type || "file")} • ${escapeHtml(formatBytes(attachment.size))}
                  </small>
                </div>
              </div>

              <div class="file-row-actions">
                <button
                  class="file-row-remove btn btn-secondary"
                  type="button"
                  data-remove-file="${escapeHtml(attachment.id)}"
                >Remove</button>
              </div>
            </article>
          `
        }).join("")}
      </div>
    </section>
  `
}

function renderUploadedSection(files){
  if(!files.length){
    return `
      <section class="files-panel-section">
        <div class="files-panel-section-header">
          <h3>Uploaded files</h3>
          <span>0</span>
        </div>

        <div class="empty-state-card fade-in">
          <div class="empty-icon">🗂️</div>
          <h3>No uploaded files</h3>
          <p>Upload from the composer to populate this list.</p>
        </div>
      </section>
    `
  }

  return `
    <section class="files-panel-section">
      <div class="files-panel-section-header">
        <h3>Uploaded files</h3>
        <span>${files.length}</span>
      </div>

      <div class="files-panel-list">
        ${files.map((file) => {
          const icon = getIconForType(file.content_type, file.name)
          const modified = formatDate(file.modified_at)
          const downloadUrl = getDownloadUrl(file.name)

          return `
            <article class="file-row fade-in" data-server-file="${escapeHtml(file.name)}">
              <div class="file-row-main">
                <span class="file-row-icon">${icon}</span>
                <div class="file-row-copy">
                  <strong class="file-row-name">${escapeHtml(file.name || "Unnamed file")}</strong>
                  <small class="file-row-meta">
                    ${escapeHtml(file.content_type || "file")} • ${escapeHtml(formatBytes(file.size))}${modified ? ` • ${escapeHtml(modified)}` : ""}
                  </small>
                </div>
              </div>

              <div class="file-row-actions">
                <a
                  class="file-row-action-link btn btn-secondary"
                  href="${escapeHtml(downloadUrl)}"
                  target="_blank"
                  rel="noopener noreferrer"
                >Open</a>

                <button
                  class="file-row-remove btn btn-secondary"
                  type="button"
                  data-delete-server-file="${escapeHtml(file.name)}"
                >Delete</button>
              </div>
            </article>
          `
        }).join("")}
      </div>
    </section>
  `
}

function renderFilesPanel(){
  if(!el.filesList){
    return
  }

  const pending = getPendingAttachments()
  const uploaded = Array.isArray(serverFiles) ? serverFiles : []

  if(!pending.length && !uploaded.length){
    renderEmptyState()
    return
  }

  el.filesList.innerHTML = `
    ${renderPendingSection(pending)}
    ${renderUploadedSection(uploaded)}
  `
}

function removePendingAttachment(id){
  if(!id){
    return
  }

  if(attachmentsApi?.removeAttachmentById){
    attachmentsApi.removeAttachmentById(id)
  }else{
    state.pendingAttachments = getPendingAttachments().filter((item) => item.id !== id)
  }

  window.dispatchEvent(new CustomEvent("nova:attachments-changed", {
    detail: getPendingAttachments(),
  }))

  renderFilesPanel()
}

function clearPendingFiles(){
  if(attachmentsApi?.clearAll){
    attachmentsApi.clearAll()
  }else{
    state.pendingAttachments = []
  }

  window.dispatchEvent(new CustomEvent("nova:attachments-changed", {
    detail: [],
  }))

  renderFilesPanel()
}

async function refreshFilesFromServer(){
  if(refreshInFlight){
    return serverFiles
  }

  refreshInFlight = true

  try{
    const response = await fetch(filesUrl, {
      method: "GET",
      credentials: "include",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-store",
    })

    const data = await response.json().catch(() => ({}))

    if(!response.ok){
      throw new Error(data?.error || data?.detail || `HTTP ${response.status}`)
    }

    serverFiles = Array.isArray(data?.files)
      ? data.files.map(normalizeServerFile).filter(Boolean)
      : []

    renderFilesPanel()
    return serverFiles
  }catch(error){
    renderFilesPanel()
    throw error
  }finally{
    refreshInFlight = false
  }
}

async function deleteServerFile(name){
  const fileName = String(name || "").trim()
  if(!fileName){
    return
  }

  const response = await fetch(`${filesUrl}/${encodeURIComponent(fileName)}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Accept": "application/json",
    },
  })

  const data = await response.json().catch(() => ({}))

  if(!response.ok){
    throw new Error(data?.error || data?.detail || `HTTP ${response.status}`)
  }

  serverFiles = serverFiles.filter((file) => file.name !== fileName)
  renderFilesPanel()

  window.dispatchEvent(new CustomEvent("nova:files-refresh"))
}

function handleFilesListClick(event){
  const removePendingBtn = event.target instanceof Element
    ? event.target.closest("[data-remove-file]")
    : null

  if(removePendingBtn){
    const id = removePendingBtn.getAttribute("data-remove-file")
    removePendingAttachment(id)
    return
  }

  const deleteServerBtn = event.target instanceof Element
    ? event.target.closest("[data-delete-server-file]")
    : null

  if(deleteServerBtn){
    const name = deleteServerBtn.getAttribute("data-delete-server-file")
    deleteServerFile(name).catch((error) => {
      window.alert(error?.message || "Could not delete file.")
    })
  }
}

function bindEvents(){
  if(eventsBound){
    return
  }

  el.filesList?.addEventListener("click", handleFilesListClick)
  el.clearFilesBtn?.addEventListener("click", clearPendingFiles)

  window.addEventListener("nova:attachments-changed", () => {
    renderFilesPanel()
  })

  window.addEventListener("nova:files-refresh", () => {
    refreshFilesFromServer().catch(() => {
      // ignore panel refresh failures
    })
  })

  eventsBound = true
}

function init(){
  renderFilesPanel()
  bindEvents()
  refreshFilesFromServer().catch(() => {
    renderFilesPanel()
  })
}

window.NovaFilesPanel = {
  renderFilesPanel,
  clearFiles: clearPendingFiles,
  refreshFilesFromServer,
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init, { once:true })
}else{
  init()
}

})()