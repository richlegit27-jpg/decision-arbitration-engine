// C:\Users\Owner\nova\static\js\utils.js

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

function formatBytes(bytes){
  const n = Number(bytes || 0)

  if(!Number.isFinite(n) || n <= 0){
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB", "TB"]
  let size = n
  let i = 0

  while(size >= 1024 && i < units.length - 1){
    size /= 1024
    i += 1
  }

  if(i === 0){
    return `${Math.round(size)} ${units[i]}`
  }

  const rounded = size < 10 ? size.toFixed(1) : Math.round(size)
  return `${rounded} ${units[i]}`
}

function generateId(prefix = "id"){
  const safePrefix = String(prefix || "id").trim() || "id"
  const rand = Math.random().toString(36).slice(2, 10)
  return `${safePrefix}_${Date.now()}_${rand}`
}

function debounce(fn, wait = 150){
  let timeoutId = null

  return function debounced(...args){
    const context = this
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      fn.apply(context, args)
    }, wait)
  }
}

function isElementVisible(element){
  if(!element){
    return false
  }

  const rect = element.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0
}

window.NovaUtils = {
  escapeHtml,
  formatBytes,
  generateId,
  debounce,
  isElementVisible,
}

})()