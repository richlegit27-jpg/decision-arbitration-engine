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
  const safe = escapeHtml(text)
  return safe.replace(/\r?\n/g, "<br>")
}

window.NovaMarkdown = {
  render: renderMarkdown,
}
})()