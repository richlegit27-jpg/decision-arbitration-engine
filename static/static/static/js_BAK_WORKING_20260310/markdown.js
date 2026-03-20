// C:\Users\Owner\nova\static\js\markdown.js

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

function renderMarkdown(text){
  if(!text) return ""

  let safe = escapeHtml(text)

  const lines = safe.split(/\r?\n/)

  let html = ""
  let inList = false

  for(const line of lines){

    if(/^\s*[-*]\s+/.test(line)){
      if(!inList){
        html += "<ul>"
        inList = true
      }

      const item = line.replace(/^\s*[-*]\s+/, "")
      html += `<li>${item}</li>`
      continue
    }

    if(inList){
      html += "</ul>"
      inList = false
    }

    if(line.trim() === ""){
      html += "<br>"
      continue
    }

    html += `<p>${line}</p>`
  }

  if(inList){
    html += "</ul>"
  }

  // bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")

  // inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>")

  return html
}

window.NovaMarkdown = {
  render: renderMarkdown,
}

})()