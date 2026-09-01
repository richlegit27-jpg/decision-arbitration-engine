// C:\Users\Owner\nova\static\js\chat-messages.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const answerPayloadApi = window.NovaAnswerPayload || null

if(!chatStateApi){
  throw new Error("NovaChatMessages: window.NovaChatState is required")
}

const { state } = chatStateApi

const desktopChatContainer =
  document.getElementById("chat")

const el = {
  messages:
    document.getElementById("messages") ||
    desktopChatContainer ||
    document.querySelector("[data-messages]") ||
    document.querySelector(".chat-messages"),

  messagesScroll:
    document.getElementById("messagesScroll") ||
    desktopChatContainer ||
    document.querySelector("[data-messages]") ||
    document.querySelector(".chat-messages"),

  emptyState: document.getElementById("emptyState"),

  jumpToLatestBtn: document.getElementById("jumpToLatestBtn"),
}


const SCROLL_LOCK_THRESHOLD = 140
const COPY_FEEDBACK_MS = 1200

let eventsBound = false
let copiedMessageId = ""
let copyFeedbackTimer = null

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function formatTime(value){
  if(!value){
    return ""
  }

  try{
    const date = new Date(value)
    if(Number.isNaN(date.getTime())){
      return ""
    }

    return date.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    })
  }catch(_error){
    return ""
  }
}

function isNearBottom(){
  if(!el.messagesScroll){
    return true
  }

  const remaining =
    el.messagesScroll.scrollHeight -
    el.messagesScroll.scrollTop -
    el.messagesScroll.clientHeight

  return remaining <= SCROLL_LOCK_THRESHOLD
}

function scrollToBottom(force = false){
  if(!el.messagesScroll){
    return
  }

  if(force || isNearBottom()){
    el.messagesScroll.scrollTop = el.messagesScroll.scrollHeight
  }
}

function updateJumpButton(){
  if(!el.jumpToLatestBtn || !el.messagesScroll){
    return
  }

  const remaining =
    el.messagesScroll.scrollHeight -
    el.messagesScroll.scrollTop -
    el.messagesScroll.clientHeight

  el.jumpToLatestBtn.classList.toggle("hidden", remaining <= SCROLL_LOCK_THRESHOLD)
}

function parseImageMessage(content){
  const text = String(content || "").trim()

  if(!text.startsWith("[[image]]")){
    return null
  }

  const lines = text
    .split("\n")
    .map((line) => String(line || "").trim())
    .filter(Boolean)

  let imageSrc = ""
  let prompt = ""

  for(const line of lines){
    const lowered = line.toLowerCase()

    if(lowered.startsWith("src:")){
      imageSrc = line.slice(4).trim()
      continue
    }

    if(lowered.startsWith("url:") && !imageSrc){
      imageSrc = line.slice(4).trim()
      continue
    }

    if(lowered.startsWith("prompt:")){
      prompt = line.slice(7).trim()
    }
  }

  if(!imageSrc){
    return null
  }

  return {
    imageSrc,
    prompt,
  }
}

function renderImageMessage(content){
  const parsed = parseImageMessage(content)
  if(!parsed){
    return ""
  }

  const isDataUrl = parsed.imageSrc.startsWith("data:")
  const openLink = isDataUrl
    ? ""
    : `
      <a
        href="${escapeHtml(parsed.imageSrc)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Open image
      </a>
    `

  return `
    <div class="nova-generated-image">
      <div class="nova-generated-image-frame">
        <img
          src="${escapeHtml(parsed.imageSrc)}"
          alt="${escapeHtml(parsed.prompt || "Generated image")}"
          class="nova-generated-image-img"
          loading="lazy"
        >
      </div>

      <div class="nova-generated-image-meta">
        <strong>Generated image</strong>
        ${parsed.prompt ? `<p>${escapeHtml(parsed.prompt)}</p>` : ""}
        ${openLink}
      </div>
    </div>
  `
}

function renderInlineCodeText(text){
    return escapeHtml(text)
        .replace(
            /([A-Za-z_][A-Za-z0-9_]*)\b/g,
            (word) => {
                const keywords = new Set([
                    "if",
                    "else",
                    "elif",
                    "for",
                    "while",
                    "in",
                    "is",
                    "not",
                    "and",
                    "or",
                    "def",
                    "class",
                    "return",
                    "import",
                    "from",
                    "as",
                    "try",
                    "except",
                    "finally",
                    "with",
                    "lambda",
                    "yield",
                    "async",
                    "await",
                    "const",
                    "let",
                    "var",
                    "function",
                    "true",
                    "false",
                    "null",
                    "None",
                    "True",
                    "False",
                ])

                if(keywords.has(word)){
                    return `<span class="nova-code-keyword">${word}</span>`
                }

                return word
            }
        )
}

function highlightCode(code, lang = ""){
    let html = escapeHtml(code)

    html = html.replace(
        /(["'])(.*?)(\1)/g,
        '<span class="nova-code-string">$1$2$3</span>'
    )

    html = html.replace(
        /\b(\d+(?:\.\d+)?)\b/g,
        '<span class="nova-code-number">$1</span>'
    )

    html = html.replace(
        /([+\-*\/%=<>!&|?:]+)/g,
        '<span class="nova-code-operator">$1</span>'
    )

    html = html.replace(
        /(^|[\s;])(#.*)$/gm,
        '$1<span class="nova-code-comment">$2</span>'
    )

    html = html.replace(
        /\b([A-Za-z_][A-Za-z0-9_]*)(?=\()/g,
        '<span class="nova-code-function">$1</span>'
    )

    return html
}

function renderCodeBlock(content, language = ""){
    const lang = String(language || "text").trim() || "text"
    const safeLang = escapeHtml(lang)
    const safeCode = highlightCode(
        String(content || ""),
        lang
    )

    return `
        <div class="nova-live-code-block">
            <div class="nova-live-code-head">
                <span class="nova-live-code-lang">
                    ${safeLang}
                </span>

                <button
                    class="nova-live-code-copy"
                    type="button"
                    title="Copy code"
                >
                    Copy
                </button>
            </div>

            <pre><code class="language-${safeLang}">${safeCode}</code></pre>
        </div>
    `
}

function renderInlineCodeText(text){
    return escapeHtml(text)
        .replace(
            /([A-Za-z_][A-Za-z0-9_]*)\b/g,
            (word) => {
                const keywords = new Set([
                    "if",
                    "else",
                    "elif",
                    "for",
                    "while",
                    "in",
                    "is",
                    "not",
                    "and",
                    "or",
                    "def",
                    "class",
                    "return",
                    "import",
                    "from",
                    "as",
                    "try",
                    "except",
                    "finally",
                    "with",
                    "lambda",
                    "yield",
                    "async",
                    "await",
                    "const",
                    "let",
                    "var",
                    "function",
                    "true",
                    "false",
                    "null",
                    "None",
                    "True",
                    "False",
                ])

                if(keywords.has(word)){
                    return `<span class="nova-code-keyword">${word}</span>`
                }

                return word
            }
        )
}

function highlightCode(code, lang = ""){
    let html = escapeHtml(code)

    html = html.replace(
        /(["'])(.*?)(\1)/g,
        '<span class="nova-code-string">$1$2$3</span>'
    )

    html = html.replace(
        /\b(\d+(?:\.\d+)?)\b/g,
        '<span class="nova-code-number">$1</span>'
    )

    html = html.replace(
        /([+\-*\/%=<>!&|?:]+)/g,
        '<span class="nova-code-operator">$1</span>'
    )

    html = html.replace(
        /(^|[\s;])(#.*)$/gm,
        '$1<span class="nova-code-comment">$2</span>'
    )

    html = html.replace(
        /\b([A-Za-z_][A-Za-z0-9_]*)(?=\()/g,
        '<span class="nova-code-function">$1</span>'
    )

    return html
}

function renderCodeBlock(content, language = ""){
    const lang = String(language || "text").trim() || "text"
    const safeLang = escapeHtml(lang)
    const safeCode = highlightCode(
        String(content || ""),
        lang
    )

    return `
        <div class="nova-live-code-block">
            <div class="nova-live-code-head">
                <span class="nova-live-code-lang">
                    ${safeLang}
                </span>

                <button
                    class="nova-live-code-copy"
                    type="button"
                    title="Copy code"
                >
                    Copy
                </button>
            </div>

            <pre><code class="language-${safeLang}">${safeCode}</code></pre>
        </div>
    `
}

function renderPlainText(content){
    const text = String(content || "")
        .replace(/\r\n/g, "\n")

    const fence = /(?:^|\n)\s*```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)\n\s*```/g

    let html = ""
    let lastIndex = 0
    let match

    while((match = fence.exec(text))){
        const before = text.slice(
            lastIndex,
            match.index
        )

        if(before.trim()){
            html += before
                .split(/\n{2,}/)
                .map((part) => {
                    return `<p>${escapeHtml(part).replaceAll("\n", "<br>")}</p>`
                })
                .join("")
        }

        html += renderCodeBlock(
            match[2],
            match[1]
        )

        lastIndex = fence.lastIndex
    }

    const tail = text.slice(lastIndex)

    if(tail.trim()){
        html += tail
            .split(/\n{2,}/)
            .map((part) => {
                return `<p>${escapeHtml(part).replaceAll("\n", "<br>")}</p>`
            })
            .join("")
    }

    return `
        <div class="answer-payload">
            <div class="answer-text">
                ${html || "<p></p>"}
            </div>
        </div>
    `
}

function renderMessageBody(message){
    const content = message?.content ?? ""

    if(message?.role === "assistant"){
        const imageMarkup = renderImageMessage(content)

        if(imageMarkup){
            return imageMarkup
        }

        if(
            answerPayloadApi &&
            typeof answerPayloadApi.renderAnswerPayload === "function"
        ){
            return answerPayloadApi.renderAnswerPayload(
                content,
                {
                    messageId: message.id,
                    copiedMessageId,
                }
            )
        }
    }

    return renderPlainText(content)
}

function renderMessageBody(message){
  const content = message?.content ?? ""

  if(message?.role === "assistant"){
    const imageMarkup = renderImageMessage(content)
    if(imageMarkup){
      return imageMarkup
    }

    if(answerPayloadApi && typeof answerPayloadApi.renderAnswerPayload === "function"){
      return answerPayloadApi.renderAnswerPayload(content, {
        messageId: message.id,
        copiedMessageId,
      })
    }
  }

  return renderPlainText(content)
}

function getMessages(){
  return Array.isArray(state.messages) ? state.messages : []
}

function syncMessagesFromStorage(messages, options = {}){

  const incoming =
    Array.isArray(messages)
      ? messages
      : [];

  const current =
    Array.isArray(state.messages)
      ? state.messages
      : [];

  const incomingSessionId = String(
    options.sessionId ||
    ""
  ).trim();

  const activeSessionId = String(
    state.activeChatId ||
    ""
  ).trim();

  console.log(
    "[NovaChatMessages] SYNC REQUEST",
    {
      currentCount: current.length,
      incomingCount: incoming.length,
      incomingSessionId,
      activeSessionId
    }
  );

  /*
   * A different session is an intentional navigation.
   * Never block it just because it contains fewer messages.
   */
  const differentSession =
    !!incomingSessionId &&
    !!activeSessionId &&
    incomingSessionId !== activeSessionId;

  /*
   * Only reject a smaller snapshot when it is for the
   * SAME active session.
   */
  if(
    !differentSession &&
    incoming.length < current.length
  ){

    console.warn(
      "[NovaChatMessages] ignored stale smaller snapshot",
      {
        currentCount: current.length,
        incomingCount: incoming.length,
        sessionId: activeSessionId
      }
    );

    renderMessages();

    return;
  }

  state.messages = incoming;

  if(incomingSessionId){

    state.activeChatId = incomingSessionId;

    if(!state.messagesByChatId){
      state.messagesByChatId = {};
    }

    state.messagesByChatId[incomingSessionId] =
      incoming;
  }

  console.log(
    "[NovaChatMessages] state synchronized",
    {
      count: state.messages.length,
      sessionId:
        state.activeChatId
    }
  );

  renderMessages();
}

function renderMessages(){
  if(!el.messages){
    return
  }
  const messages = getMessages()
  const shouldStick = isNearBottom()

  if(el.emptyState){
    el.emptyState.classList.toggle("hidden", messages.length > 0)
  }

if(!messages.length){
    const activeChatId =
        state?.activeChatId ||
        state?.active_chat_id ||
        ""

    const session =
        Array.isArray(state?.chats)
            ? state.chats.find((chat) => {
                return String(
                    chat?.id ||
                    chat?.chat_id ||
                    ""
                ) === String(activeChatId)
            })
            : null

    if(
        session &&
        session.meta &&
        session.meta.onboarding &&
        typeof window.renderDesktopOnboarding === "function"
    ){
        window.renderDesktopOnboarding(session)
        updateJumpButton()
        return
    }

    el.messages.innerHTML = ""
    updateJumpButton()
    return
}


el.messages.innerHTML = messages.map((message) => {
    const isUser = message.role === "user"

    const isThinking =
      message.status === "thinking" ||
      message.type === "thinking" ||
      message.isThinking === true ||
      String(message.content || "").includes("â—\x8F")

    const roleClass = isUser ? "user" : "assistant"
    const roleLabel = isUser ? "You" : "Nova"
    const time = formatTime(message.created_at)

    return `
      <article class="message-row ${roleClass} ${isThinking ? "thinking-message" : ""} fade-in" data-message-id="${escapeHtml(message.id || "")}">
        <div class="message-avatar ${roleClass}">
          ${isUser ? "Y" : "N"}
        </div>

        <div class="message-card ${roleClass}">
          <div class="message-meta">
            <strong class="message-role">${roleLabel}</strong>
            <span class="message-time">${escapeHtml(time)}</span>
          </div>

          <div class="message-body">
  ${
    isThinking
      ? `
        <div class="nova-thinking-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      `
      : renderMessageBody(message)
  }
</div>

<div class="message-actions">
  <button
    class="message-action-btn"
  type="button"
  data-copy-message="${escapeHtml(message.id || "")}"
>
  ${copiedMessageId === message.id ? "Copied" : "Copy"}
</button>

${
  message.role !== "user"
    ? `
      <button
        class="message-action-btn"
        type="button"
        data-action="regenerate"
        data-message-id="${escapeHtml(message.id || "")}"
        title="Regenerate response"
      >
        Regenerate
      </button>
    `
    : ""
}
</div>
        </div>
      </article>
    `
  }).join("")

  if(shouldStick){
    scrollToBottom(true)
  }

  updateJumpButton()
}

function copyMessageText(messageId){
    const messages = getMessages()

    const message = messages.find((item) => {
        return String(
            item?.message_id ||
            item?.id ||
            ""
        ) === String(messageId)
    })

    if(!message){
        return
    }

    const text = String(
        message.content ??
        message.text ??
        ""
    ).trim()

    if(!text){
        return
    }

    navigator.clipboard.writeText(text).then(() => {
        copiedMessageId = String(messageId)

        renderMessages()

        if(copyFeedbackTimer){
            clearTimeout(copyFeedbackTimer)
        }

        copyFeedbackTimer = window.setTimeout(() => {
            copiedMessageId = ""
            renderMessages()
        }, COPY_FEEDBACK_MS)
    }).catch((error) => {
        console.warn(
            "[Nova Copy] clipboard write failed",
            error
        )
    })
}

function handleMessagesClick(event){
  const target = event.target instanceof Element
    ? event.target.closest("[data-copy-message], [data-action='regenerate']")
    : null

  if(!target){
    return
  }

  if(target.dataset.action === "regenerate"){
    const messageId = target.getAttribute("data-message-id")

    if(typeof window.NovaComposerActions?.regenerateMessage === "function"){
      window.NovaComposerActions.regenerateMessage(messageId)
    }

    return
  }

  const messageId = target.getAttribute("data-copy-message")

  if(!messageId){
    return
  }

  copyMessageText(messageId)
}

function bindEvents(){
    if(eventsBound){
        return
    }

    el.messages?.addEventListener(
        "click",
        async (event) => {
            const codeCopyButton =
                event.target instanceof Element
                    ? event.target.closest(
                        ".nova-live-code-copy"
                    )
                    : null

            if(codeCopyButton){
                const codeBlock =
                    codeCopyButton.closest(
                        ".nova-live-code-block"
                    )

                const codeElement =
                    codeBlock?.querySelector(
                        "pre code"
                    )

                const codeText =
                    codeElement?.textContent || ""

                if(!codeText){
                    return
                }

                try{
                    await navigator.clipboard.writeText(
                        codeText
                    )

                    codeCopyButton.classList.add(
                        "is-copied"
                    )

                    codeCopyButton.textContent =
                        "Copied"

                    window.setTimeout(() => {
                        codeCopyButton.classList.remove(
                            "is-copied"
                        )

                        codeCopyButton.textContent =
                            "Copy"
                    }, 1200)
                }catch(error){
                    console.warn(
                        "[Nova Code Copy] failed",
                        error
                    )

                    codeCopyButton.textContent =
                        "Failed"

                    window.setTimeout(() => {
                        codeCopyButton.textContent =
                            "Copy"
                    }, 1200)
                }

                return
            }

            const target =
                event.target instanceof Element
                    ? event.target.closest(
                        "[data-copy-message], [data-action='regenerate']"
                    )
                    : null

            if(!target){
                return
            }

            if(target.dataset.action === "regenerate"){
                const messageId =
                    target.getAttribute(
                        "data-message-id"
                    )

                if(
                    typeof window
                        .NovaComposerActions
                        ?.regenerateMessage === "function"
                ){
                    window.NovaComposerActions
                        .regenerateMessage(
                            messageId
                        )
                }

                return
            }

            const messageId =
                target.getAttribute(
                    "data-copy-message"
                )

            if(!messageId){
                return
            }

            copyMessageText(messageId)
        }
    )

    el.messagesScroll?.addEventListener(
        "scroll",
        () => {
            updateJumpButton()
        }
    )

    el.jumpToLatestBtn?.addEventListener(
        "click",
        () => {
            scrollToBottom(true)
            updateJumpButton()
        }
    )

    window.addEventListener(
        "nova:messages-changed",
        () => {
            renderMessages()
        }
    )

    window.addEventListener(
        "nova:chat-loaded",
        () => {
            renderMessages()
            scrollToBottom(true)
        }
    )

    eventsBound = true
}

function init(){
  bindEvents()
  renderMessages()
  scrollToBottom(true)
  updateJumpButton()
}

window.NovaChatMessages = {
  renderMessages,
  scrollToBottom,
  updateJumpButton,
  syncMessagesFromStorage,
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init, { once: true })
}else{
  init()
}

})()



