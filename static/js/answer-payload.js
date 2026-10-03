// C:\Users\Owner\nova\static\js\answer-payload.js

(() => {
"use strict"

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function normalizeText(value){
  return String(value ?? "").replace(/\r\n/g, "\n")
}

function copyText(text){
  return navigator.clipboard.writeText(String(text ?? ""))
}

function renderInline(text){
  let html = escapeHtml(text)

  html = html.replace(/`([^`\n]+)`/g, (_m, code) => {
    return `<code>${escapeHtml(code)}</code>`
  })

  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
  html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>")

  return html
}

function renderParagraphBlock(block){
  const lines = block.split("\n")
  const html = lines.map((line) => renderInline(line)).join("<br>")
  return `<p>${html}</p>`
}

function renderListBlock(block){
  const lines = block.split("\n").filter(Boolean)
  const roots = []
  const stack = []

  lines.forEach((line) => {
    const match = line.match(/^(\s*)([-*+]\s+|\d+\.\s+)(.*)$/)
    if (!match) return

    const indent = match[1].replace(/\t/g, "  ").length
    const type = /^\d/.test(match[2]) ? "ol" : "ul"
    const item = { content: match[3], children: [] }

    while (
      stack.length &&
      (indent < stack[stack.length - 1].indent ||
        (indent === stack[stack.length - 1].indent && type !== stack[stack.length - 1].list.type))
    ) stack.pop()

    let list = stack[stack.length - 1]?.list
    if (!list || indent > stack[stack.length - 1].indent) {
      const parentItem = stack[stack.length - 1]?.lastItem || null
      const container = parentItem ? parentItem.children : roots
      list = container[container.length - 1]
      if (!list || list.type !== type || indent <= list.indent) {
        list = { type, indent, items: [] }
        container.push(list)
      }
      stack.push({ indent, list, lastItem: null })
    }

    list.items.push(item)
    stack[stack.length - 1].lastItem = item
  })

  const renderList = (list) => `<${list.type}>${list.items.map((item) =>
    `<li>${renderInline(item.content)}${item.children.map(renderList).join("")}</li>`
  ).join("")}</${list.type}>`

  return roots.map(renderList).join("")
}

function renderCodeBlock(code, lang = "", messageId = ""){
  const safeLang = escapeHtml(lang || "text")
  const safeCode = escapeHtml(code)
  const key = escapeHtml(`${messageId}__${lang}__${code.slice(0, 40)}`)

  return `
    <div class="answer-code" data-code-block="${key}">
      <div class="answer-code-head">
        <span class="answer-code-lang">${safeLang}</span>
        <button class="answer-code-copy" type="button" data-copy-code="${key}">
          Copy
        </button>
      </div>
      <pre><code>${safeCode}</code></pre>
    </div>
  `
}

function renderTableBlock(block){
  const lines = block.split("\n").filter(Boolean)
  if(lines.length < 2){
    return renderParagraphBlock(block)
  }

  const rows = lines
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|") && line.endsWith("|"))
    .map((line) => line.slice(1, -1).split("|").map((cell) => cell.trim()))

  if(rows.length < 2){
    return renderParagraphBlock(block)
  }

  const header = rows[0]
  const bodyRows = rows.slice(2)

  const thead = `
    <thead>
      <tr>${header.map((cell) => `<th>${renderInline(cell)}</th>`).join("")}</tr>
    </thead>
  `

  const tbody = `
    <tbody>
      ${bodyRows.map((row) => {
        return `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`
      }).join("")}
    </tbody>
  `

  return `
    <div class="answer-table-wrap">
      <table class="answer-table">
        ${thead}
        ${tbody}
      </table>
    </div>
  `
}

function parseBlocks(text){
    const normalized = normalizeText(text)
    const lines = normalized.split("\n")
    const blocks = []

    let i = 0

    while(i < lines.length){
        const line = lines[i]

        if(!line.trim()){
            i += 1
            continue
        }

        const fenceMatch = line.trim().match(
            /^(?:[-*+]\s+|\d+\.\s+)?```([a-zA-Z0-9_-]*)\s*$/
        )

        if(fenceMatch){
            const lang = fenceMatch[1] || ""
            i += 1

            const codeLines = []

            while(
                i < lines.length &&
                !lines[i].trim().startsWith("```")
            ){
                codeLines.push(lines[i])
                i += 1
            }

            if(
                i < lines.length &&
                lines[i].trim().startsWith("```")
            ){
                i += 1
            }

            blocks.push({
                type: "code",
                lang,
                content: codeLines.join("\n"),
            })

            continue
        }

        if(line.trim().startsWith("|")){
            const tableLines = [line]
            i += 1

            while(
                i < lines.length &&
                lines[i].trim().startsWith("|")
            ){
                tableLines.push(lines[i])
                i += 1
            }

            blocks.push({
                type: "table",
                content: tableLines.join("\n"),
            })

            continue
        }

        const headingMatch = line.match(/^\s*(#{1,6})\s+(.+)$/)
        if(headingMatch){
            blocks.push({
                type: "heading",
                level: headingMatch[1].length,
                content: headingMatch[2],
            })
            i += 1
            continue
        }

        if(/^\s*([-*+]\s+|\d+\.\s+)/.test(line)){
            const listLines = [line]
            i += 1

            while(
                i < lines.length &&
                /^\s*([-*+]\s+|\d+\.\s+)/.test(lines[i])
            ){
                listLines.push(lines[i])
                i += 1
            }

            blocks.push({
                type: "list",
                content: listLines.join("\n"),
            })

            continue
        }

        const paraLines = [line]
        i += 1

        while(
            i < lines.length &&
            lines[i].trim() &&
            !lines[i].trim().startsWith("```") &&
            !lines[i].trim().startsWith("|") &&
            !/^\s*([-*+]\s+|\d+\.\s+)/.test(lines[i])
        ){
            paraLines.push(lines[i])
            i += 1
        }

        blocks.push({
            type: "paragraph",
            content: paraLines.join("\n"),
        })
    }

    return blocks
}

function renderAnswerPayload(content, options = {}){
  const text = normalizeText(content)
  const messageId = options.messageId || ""

  if(!text.trim()){
    return `
      <div class="answer-payload">
        <div class="answer-text"><p></p></div>
      </div>
    `
  }

  const blocks = parseBlocks(text)

  const html = blocks.map((block) => {
    if(block.type === "code"){
      return renderCodeBlock(block.content, block.lang, messageId)
    }

    if(block.type === "table"){
      return renderTableBlock(block.content)
    }

    if(block.type === "list"){
      return renderListBlock(block.content)
    }

    if(block.type === "heading"){
      return `<h${block.level}>${renderInline(block.content)}</h${block.level}>`
    }

    return renderParagraphBlock(block.content)
  }).join("")

  return `
    <div class="answer-payload">
      <div class="answer-text">
        ${html}
      </div>
    </div>
  `
}

function bindCopyHandlers(){
  document.addEventListener("click", async (event) => {
    const button = event.target instanceof Element
      ? event.target.closest("[data-copy-code]")
      : null

    if(!button){
      return
    }

    const container = button.closest("[data-code-block]")
    const codeEl = container?.querySelector("pre code")
    if(!codeEl){
      return
    }

    const text = codeEl.textContent || ""
    if(!text){
      return
    }

    try{
      await copyText(text)
      button.classList.add("is-copied")
      button.textContent = "Copied"

      window.setTimeout(() => {
        button.classList.remove("is-copied")
        button.textContent = "Copy"
      }, 1200)
    }catch(_error){
      button.textContent = "Copy failed"
      window.setTimeout(() => {
        button.textContent = "Copy"
      }, 1200)
    }
  })
}

window.NovaAnswerPayload = {
  renderAnswerPayload,
}

bindCopyHandlers()

})()

