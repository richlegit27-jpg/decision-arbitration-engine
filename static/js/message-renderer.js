// C:\Users\Owner\nova\static\js\message-renderer.js

(() => {
"use strict"

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;")
}

function renderPlainText(text){
  return escapeHtml(text).replace(/\n/g,"<br>")
}

function renderCodeBlock(code, language=""){
  const safeLang = escapeHtml(language)
  const safeCode = escapeHtml(code)

  return `
<div class="message-code-block">
  <div class="message-code-header">
    <span class="message-code-language">${safeLang || "code"}</span>
  </div>
  <pre><code>${safeCode}</code></pre>
</div>
`
}

function renderAssistantMarkdown(text){

  const lines = String(text ?? "").split("\n")
  const blocks = []

  let i = 0

  while(i < lines.length){

    const line = lines[i]

    if(!line.trim()){
      i++
      continue
    }

    const fence = line.match(/^```([a-zA-Z0-9_-]+)?/)

    if(fence){

      let lang = fence[1] || ""
      const code = []

      i++

      if(!lang && i < lines.length && /^[a-zA-Z0-9_-]+$/.test(lines[i].trim())){
        lang = lines[i].trim()
        i++
      }

      while(i < lines.length && !/^```/.test(lines[i])){
        code.push(lines[i])
        i++
      }

      i++

      blocks.push(renderCodeBlock(code.join("\n"), lang))
      continue
    }

    if(/^[-*]\s+/.test(line)){

      const list = []

      while(i < lines.length && /^[-*]\s+/.test(lines[i])){
        list.push(lines[i].replace(/^[-*]\s+/,""))
        i++
      }

      blocks.push(
        `<ul>${list.map(v=>`<li>${escapeHtml(v)}</li>`).join("")}</ul>`
      )

      continue
    }

    if(/^#\s+/.test(line)){
      blocks.push(`<h1>${escapeHtml(line.replace(/^#\s+/,""))}</h1>`)
      i++
      continue
    }

    blocks.push(`<p>${escapeHtml(line)}</p>`)
    i++
  }

  return blocks.join("")
}

function renderMessageContent(message){

  const role = String(message?.role || "assistant")

  if(role !== "assistant"){
    return renderPlainText(message?.content || "")
  }

  if(!message?.content){
    return ""
  }

  return renderAssistantMarkdown(message.content)
}

window.NovaMessageRenderer = {
  escapeHtml,
  renderPlainText,
  renderAssistantMarkdown,
  renderMessageContent
}

})()