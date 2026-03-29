// C:\Users\Owner\nova\static\js\stream-service.js

(() => {
"use strict"

function createStreamService(options = {}){
  const {
    endpoint = "/api/chat/stream",
    fetchImpl = window.fetch.bind(window),
  } = options

  let controller = null
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
      .map(item => {
        const type = String(item?.type || item?.kind || "").trim().toLowerCase()
        const mimeType = String(item?.mime_type || item?.mime || "").trim().toLowerCase()
        const name = String(item?.name || item?.filename || item?.title || "").trim()
        const url = String(
          item?.url ||
          item?.download_url ||
          item?.href ||
          item?.path ||
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
      type === "meta" ||
      type === "message" ||
      type === "assistant_message"
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

  function handleEvent(eventName, payload){
    const data = payload || {}

    if(isStartEvent(eventName, data)){
      callbacks.onStart?.({
        ...data,
        messageId: extractMessageId(data),
      })
      return
    }

    if(isMetaEvent(eventName, data)){
      callbacks.onMeta?.({
        ...data,
        messageId: extractMessageId(data),
        assistant_message_id: extractMessageId(data),
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
        callbacks.onToken?.(token)
      }
      return
    }

    if(isDoneEvent(eventName, data)){
      callbacks.onDone?.({
        ...data,
        messageId: extractMessageId(data),
        assistant_message_id: extractMessageId(data),
        content: normalizeText(extractContent(data)),
        attachments: extractAttachments(data),
      })
      return
    }

    if(isErrorEvent(eventName, data)){
      callbacks.onError?.(data)
      return
    }

    if(typeof data?.content === "string" && !eventName){
      callbacks.onToken?.(data.content)
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

      return {
        ok: true,
      }
    }catch(error){
      if(error?.name === "AbortError"){
        throw error
      }

      callbacks.onError?.(error)
      throw error
    }finally{
      controller = null
      callbacks.onFinally?.()
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