// C:\Users\Owner\nova\static\js\api-stream.js

(() => {
"use strict"

const core = window.NovaAPICore

if(!core){
  throw new Error("NovaAPIStream: window.NovaAPICore is required")
}

const {
  joinUrl,
  safeJsonParse,
  buildHttpError,
  getReplyText,
} = core

function splitSseEvents(buffer){
  const normalized = buffer.replaceAll("\r\n", "\n")
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
      dataLines.push(line.slice(5).trim())
      continue
    }
  }

  return {
    event: eventName,
    payloadText: dataLines.join("\n").trim(),
  }
}

function handleRawStreamPayload(payloadText, handlers = {}, eventName = ""){
  const text = String(payloadText || "").trim()
  if(!text){
    return
  }

  if(text === "[DONE]"){
    handlers.onDone?.({
      done: true,
      event: eventName || "done",
    })
    return
  }

  const parsed = safeJsonParse(text)

  if(parsed && typeof parsed === "object"){
    if(eventName && !parsed.event){
      parsed.event = eventName
    }

    if(
      parsed.done === true ||
      parsed.event === "done" ||
      parsed.type === "done"
    ){
      handlers.onDone?.(parsed)
      return
    }

    const token =
      parsed?.token ??
      parsed?.delta ??
      parsed?.content_delta ??
      parsed?.text_delta ??
      null

    if(token){
      handlers.onToken?.(String(token), parsed)
    }else{
      const replyText = getReplyText(parsed)
      if(replyText && eventName !== "done"){
        handlers.onToken?.(replyText, parsed)
      }
    }

    handlers.onChunk?.(parsed)
    return
  }

  handlers.onToken?.(text, {
    event: eventName || "",
    raw: true,
  })
}

async function readStreamResponse(response, handlers = {}){
  if(!response.ok){
    const text = await response.text()
    throw buildHttpError(response, text)
  }

  const contentType = String(response.headers.get("content-type") || "").toLowerCase()
  const isJsonLike = contentType.includes("application/json")

  if(isJsonLike){
    const text = await response.text()
    const parsed = safeJsonParse(text || "") || {}
    const token = getReplyText(parsed)

    if(token){
      handlers.onToken?.(token, parsed)
    }

    handlers.onDone?.(parsed)
    return
  }

  const reader = response.body?.getReader?.()

  if(!reader){
    const text = await response.text()
    const parsed = safeJsonParse(text || "") || {}
    const token = getReplyText(parsed)

    if(token){
      handlers.onToken?.(token, parsed)
    }

    handlers.onDone?.(parsed)
    return
  }

  const decoder = new TextDecoder()
  let buffer = ""
  let doneCalled = false

  function doneOnce(payload){
    if(doneCalled){
      return
    }
    doneCalled = true
    handlers.onDone?.(payload)
  }

  while(true){
    const result = await reader.read()
    if(result.done){
      break
    }

    buffer += decoder.decode(result.value, { stream: true })

    const { events, remainder } = splitSseEvents(buffer)
    buffer = remainder

    for(const eventBlock of events){
      const { event, payloadText } = parseSseEventBlock(eventBlock)

      if(!payloadText){
        continue
      }

      handleRawStreamPayload(payloadText, {
        ...handlers,
        onDone(payload){
          doneOnce(payload)
        },
      }, event)
    }
  }

  buffer += decoder.decode()

  const trailing = buffer.trim()
  if(trailing){
    if(trailing.includes("\n\n") || trailing.startsWith("data:") || trailing.startsWith("event:")){
      const { events, remainder } = splitSseEvents(`${trailing}\n\n`)

      for(const eventBlock of events){
        const { event, payloadText } = parseSseEventBlock(eventBlock)
        handleRawStreamPayload(payloadText, {
          ...handlers,
          onDone(payload){
            doneOnce(payload)
          },
        }, event)
      }

      if(remainder.trim()){
        const { event, payloadText } = parseSseEventBlock(remainder)
        handleRawStreamPayload(payloadText, {
          ...handlers,
          onDone(payload){
            doneOnce(payload)
          },
        }, event)
      }
    }else{
      const parsed = safeJsonParse(trailing)
      if(parsed && typeof parsed === "object"){
        if(
          parsed.done === true ||
          parsed.event === "done" ||
          parsed.type === "done"
        ){
          doneOnce(parsed)
        }else{
          const token =
            parsed?.token ??
            parsed?.delta ??
            parsed?.content_delta ??
            parsed?.text_delta ??
            getReplyText(parsed)

          if(token){
            handlers.onToken?.(String(token), parsed)
          }

          handlers.onChunk?.(parsed)
        }
      }else{
        handlers.onToken?.(trailing)
      }
    }
  }

  doneOnce()
}

async function streamChat(payload = {}, handlers = {}){
  const body = {
    chat_id: String(payload?.chatId || payload?.chat_id || "default-chat"),
    message: String(payload?.message || ""),
    files: Array.isArray(payload?.files) ? payload.files : [],
    attachments: Array.isArray(payload?.attachments) ? payload.attachments : [],
  }

  const endpoints = [
    "/api/chat/stream",
    "/api/chat_stream",
    "/api/chat",
  ]

  let lastError = null

  for(const endpoint of endpoints){
    const response = await fetch(joinUrl(endpoint), {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: JSON.stringify(body),
      signal: handlers.signal,
    })

    if(response.status === 404){
      lastError = response
      continue
    }

    await readStreamResponse(response, handlers)
    return { ok: true }
  }

  if(lastError){
    const text = await lastError.text()
    throw buildHttpError(lastError, text)
  }

  return { ok: false }
}

async function uploadFiles(files){
  const list = Array.isArray(files) ? files : Array.from(files || [])
  if(!list.length){
    return []
  }

  const formData = new FormData()
  for(const file of list){
    formData.append("files", file)
  }

  const response = await fetch("/api/upload", {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    body: formData,
  })

  const text = await response.text()

  if(!response.ok){
    throw buildHttpError(response, text)
  }

  const json = text ? safeJsonParse(text) : {}
  return Array.isArray(json?.files) ? json.files : (Array.isArray(json) ? json : [])
}

window.NovaAPIStream = {
  splitSseEvents,
  parseSseEventBlock,
  handleRawStreamPayload,
  readStreamResponse,
  streamChat,
  uploadFiles,
}

})()