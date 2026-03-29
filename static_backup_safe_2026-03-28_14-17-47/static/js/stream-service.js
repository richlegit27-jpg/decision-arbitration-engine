// C:\Users\Owner\nova\static\js\stream-service.js

(() => {
"use strict"

function createStreamService(options = {}){
  const {
    endpoint = "/api/chat/stream",
    fetchImpl = window.fetch.bind(window),
  } = options

  let controller = null
  let activeRequestId = 0
  let lastDonePayload = null
  let currentMessageId = ""

  let callbacks = {
    onStart: null,
    onMeta: null,
    onToken: null,
    onDone: null,
    onError: null,
    onFinally: null,
  }

  function setCallbacks(next = {}){
    callbacks = {
      ...callbacks,
      ...next,
    }
  }

  function safeCallback(name, ...args){
    try{
      const fn = callbacks?.[name]
      if(typeof fn === "function"){
        return fn(...args)
      }
    }catch(error){
      console.error(`NovaStreamService callback error: ${name}`, error)
    }
    return undefined
  }

  function stop(){
    if(controller){
      controller.abort()
      controller = null
    }
  }

  function splitSseEvents(buffer){
    const normalized = String(buffer || "").replaceAll("\r\n", "\n")
    const parts = normalized.split("\n\n")
    const remainder = parts.pop() ?? ""

    return {
      events: parts,
      remainder,
    }
  }

  function parseSseEventBlock(block){
    const lines = String(block || "").split("\n")
    const dataLines = []
    let eventName = ""

    for(const rawLine of lines){
      const line = String(rawLine || "")

      if(!line.trim()){
        continue
      }

      if(line.startsWith(":")){
        continue
      }

      if(line.startsWith("event:")){
        eventName = line.slice(6).trim()
        continue
      }

      if(line.startsWith("data:")){
        dataLines.push(line.slice(5).trimStart())
      }
    }

    return {
      eventName: eventName.trim(),
      dataText: dataLines.join("\n").trim(),
    }
  }

  function safeJsonParse(text){
    try{
      return JSON.parse(text)
    }catch(_error){
      return null
    }
  }

  function normalizeText(value){
    return String(value ?? "")
  }

  function normalizeAttachments(value){
    if(!Array.isArray(value)){
      return []
    }

    return value
      .filter(Boolean)
      .map((item) => {
        const type = String(item?.type || item?.kind || "").trim().toLowerCase()
        const mimeType = String(item?.mime_type || item?.mime || "").trim().toLowerCase()
        const name = String(item?.name || item?.filename || item?.title || "").trim()
        const url = String(
          item?.url ||
          item?.download_url ||
          item?.href ||
          item?.path ||
          item?.storage_path ||
          ""
        ).trim()
        const previewUrl = String(
          item?.preview_url ||
          item?.preview ||
          item?.thumbnail_url ||
          item?.image_url ||
          item?.url ||
          item?.download_url ||
          item?.href ||
          item?.path ||
          item?.storage_path ||
          ""
        ).trim()

        return {
          ...item,
          type,
          mime_type: mimeType,
          name,
          url,
          preview_url: previewUrl,
        }
      })
  }

  function extractAttachments(payload){
    return normalizeAttachments(
      payload?.attachments ||
      payload?.message_attachments ||
      payload?.response_attachments ||
      payload?.files ||
      payload?.message?.attachments ||
      payload?.response?.attachments ||
      payload?.data?.attachments
    )
  }

  function extractMessageId(payload){
    return String(
      payload?.messageId ||
      payload?.message_id ||
      payload?.assistant_message_id ||
      payload?.id ||
      payload?.message?.id ||
      payload?.message?.message_id ||
      payload?.response?.id ||
      payload?.response?.message_id ||
      ""
    ).trim()
  }

  function extractChatId(payload){
    return String(
      payload?.chat_id ||
      payload?.chatId ||
      payload?.chat?.id ||
      payload?.chat?.chat_id ||
      ""
    ).trim()
  }

  function extractContent(payload){
    if(typeof payload?.content === "string"){
      return payload.content
    }

    if(typeof payload?.response === "string"){
      return payload.response
    }

    if(typeof payload?.message === "string"){
      return payload.message
    }

    if(typeof payload?.text === "string"){
      return payload.text
    }

    if(typeof payload?.delta === "string"){
      return payload.delta
    }

    if(typeof payload?.token === "string"){
      return payload.token
    }

    if(typeof payload?.message?.content === "string"){
      return payload.message.content
    }

    if(typeof payload?.response?.content === "string"){
      return payload.response.content
    }

    return ""
  }

  function isDoneEvent(eventName, payload){
    const name = String(eventName || "").trim().toLowerCase()
    const type = String(payload?.type || payload?.event || "").trim().toLowerCase()

    return (
      name === "done" ||
      name === "final" ||
      name === "complete" ||
      type === "done" ||
      type === "final" ||
      type === "complete"
    )
  }

  function isMetaEvent(eventName, payload){
    const name = String(eventName || "").trim().toLowerCase()
    const type = String(payload?.type || payload?.event || "").trim().toLowerCase()

    return (
      name === "meta" ||
      name === "message" ||
      name === "assistant_message" ||
      name === "assistant-message" ||
      type === "meta" ||
      type === "message" ||
      type === "assistant_message" ||
      type === "assistant-message"
    )
  }

  function isStartEvent(eventName, payload){
    const name = String(eventName || "").trim().toLowerCase()
    const type = String(payload?.type || payload?.event || "").trim().toLowerCase()

    return name === "start" || type === "start"
  }

  function isErrorEvent(eventName, payload){
    const name = String(eventName || "").trim().toLowerCase()
    const type = String(payload?.type || payload?.event || "").trim().toLowerCase()

    return name === "error" || type === "error"
  }

  function isTokenEvent(eventName, payload){
    const name = String(eventName || "").trim().toLowerCase()
    const type = String(payload?.type || payload?.event || "").trim().toLowerCase()

    if(name === "token" || name === "delta" || type === "token" || type === "delta"){
      return true
    }

    return (
      typeof payload?.token === "string" ||
      typeof payload?.delta === "string"
    )
  }

  function buildDonePayload(data = {}){
    const messageId = extractMessageId(data) || currentMessageId

    return {
      ...data,
      ok: true,
      chat_id: extractChatId(data),
      messageId,
      assistant_message_id: messageId,
      content: normalizeText(extractContent(data)),
      attachments: extractAttachments(data),
    }
  }

  function handleEvent(eventName, payload){
    const data = payload || {}
    const extractedMessageId = extractMessageId(data)

    if(extractedMessageId){
      currentMessageId = extractedMessageId
    }

    if(isStartEvent(eventName, data)){
      safeCallback("onStart", {
        ...data,
        chat_id: extractChatId(data),
        messageId: extractedMessageId || currentMessageId,
        assistant_message_id: extractedMessageId || currentMessageId,
      })
      return
    }

    if(isMetaEvent(eventName, data)){
      safeCallback("onMeta", {
        ...data,
        chat_id: extractChatId(data),
        messageId: extractedMessageId || currentMessageId,
        assistant_message_id: extractedMessageId || currentMessageId,
        attachments: extractAttachments(data),
      })
      return
    }

    if(isTokenEvent(eventName, data)){
      const token =
        typeof data?.token === "string"
          ? data.token
          : typeof data?.delta === "string"
            ? data.delta
            : typeof data?.content === "string"
              ? data.content
              : typeof data?.text === "string"
                ? data.text
                : ""

      if(token){
        safeCallback("onToken", token, {
          ...data,
          chat_id: extractChatId(data),
          messageId: extractedMessageId || currentMessageId,
          assistant_message_id: extractedMessageId || currentMessageId,
        })
      }
      return
    }

    if(isDoneEvent(eventName, data)){
      lastDonePayload = buildDonePayload(data)
      safeCallback("onDone", lastDonePayload)
      return
    }

    if(isErrorEvent(eventName, data)){
      safeCallback("onError", data)
      return
    }

    if(typeof data?.content === "string" && !eventName){
      safeCallback("onToken", data.content, {
        ...data,
        chat_id: extractChatId(data),
        messageId: extractedMessageId || currentMessageId,
        assistant_message_id: extractedMessageId || currentMessageId,
      })
    }
  }

  async function readSseStream(response){
    if(!response?.body){
      throw new Error("Streaming response body is missing.")
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while(true){
      const { value, done } = await reader.read()

      if(done){
        break
      }

      buffer += decoder.decode(value, { stream: true })

      const parsed = splitSseEvents(buffer)
      buffer = parsed.remainder

      for(const rawEvent of parsed.events){
        const parsedEvent = parseSseEventBlock(rawEvent)
        const eventName = parsedEvent.eventName
        const dataText = parsedEvent.dataText

        if(!dataText){
          continue
        }

        if(dataText === "[DONE]"){
          handleEvent("done", {})
          continue
        }

        const json = safeJsonParse(dataText)

        if(json){
          handleEvent(eventName, json)
          continue
        }

        handleEvent(eventName || "token", { token: dataText })
      }
    }

    const trailing = decoder.decode()
    if(trailing){
      buffer += trailing
    }

    if(buffer.trim()){
      const parsedEvent = parseSseEventBlock(buffer)
      const eventName = parsedEvent.eventName
      const dataText = parsedEvent.dataText

      if(dataText){
        if(dataText === "[DONE]"){
          handleEvent("done", {})
        }else{
          const json = safeJsonParse(dataText)
          if(json){
            handleEvent(eventName, json)
          }else{
            handleEvent(eventName || "token", { token: dataText })
          }
        }
      }
    }
  }

  async function send(payload = {}){
    stop()

    controller = new AbortController()
    activeRequestId += 1
    const requestId = activeRequestId
    lastDonePayload = null
    currentMessageId = ""

    const requestBody = {
      chat_id: payload.chatId || payload.chat_id || "",
      message: payload.message || "",
      attachments: Array.isArray(payload.attachments)
        ? payload.attachments
        : Array.isArray(payload.files)
          ? payload.files
          : [],
      files: Array.isArray(payload.files)
        ? payload.files
        : Array.isArray(payload.attachments)
          ? payload.attachments
          : [],
    }

    try{
      const response = await fetchImpl(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      })

      if(!response.ok){
        const text = await response.text().catch(() => "")
        throw new Error(`${endpoint} failed (${response.status}) ${text}`)
      }

      await readSseStream(response)

      if(requestId !== activeRequestId){
        return {
          ok: false,
          aborted: true,
        }
      }

      if(lastDonePayload){
        return lastDonePayload
      }

      return {
        ok: true,
        chat_id: String(requestBody.chat_id || "").trim(),
        messageId: currentMessageId,
        assistant_message_id: currentMessageId,
        content: "",
        attachments: [],
      }
    }catch(error){
      if(error?.name === "AbortError"){
        const abortError = new Error("Stream aborted.")
        abortError.name = "AbortError"
        throw abortError
      }

      safeCallback("onError", error)
      throw error
    }finally{
      if(requestId === activeRequestId){
        controller = null
      }
      safeCallback("onFinally")
    }
  }

  return {
    send,
    stop,
    setCallbacks,
  }
}

window.NovaStreamService = {
  create: createStreamService,
  createStreamService,
}

})()