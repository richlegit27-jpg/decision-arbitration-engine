// C:\Users\Owner\nova\static\js\api-memory.js

(() => {
"use strict"

const core = window.NovaAPICore

if(!core){
  throw new Error("NovaAPIMemory: window.NovaAPICore is required")
}

const {
  fetchJson,
  jsonOptions,
  normalizeMemoryList,
} = core

function normalizeItems(items){
  return Array.isArray(items)
    ? items.map((item) => String(item || "").trim()).filter(Boolean)
    : [String(items || "").trim()].filter(Boolean)
}

function wrapMemoryPayload(payload){
  return {
    ...payload,
    memories: normalizeMemoryList(payload),
    updated_at: payload?.updated_at || null,
  }
}

async function tryMemoryWrite(method, items){
  const normalizedItems = normalizeItems(items)

  if(!normalizedItems.length){
    return wrapMemoryPayload({ memories: [] })
  }

  const payloadVariants = [
    { items: normalizedItems },
    { memories: normalizedItems },
    { memory_items: normalizedItems },
    { entries: normalizedItems },
    normalizedItems,
  ]

  let lastError = null

  for(const body of payloadVariants){
    try{
      const payload = await fetchJson(
        "/api/memory",
        jsonOptions(method, body)
      )
      return wrapMemoryPayload(payload)
    }catch(error){
      lastError = error
    }
  }

  throw lastError || new Error(`Memory ${method} failed.`)
}

async function listMemory(){
  const payload = await fetchJson("/api/memory")
  return wrapMemoryPayload(payload)
}

async function addMemory(items){
  return await tryMemoryWrite("POST", items)
}

async function deleteMemoryItems(items){
  return await tryMemoryWrite("DELETE", items)
}

async function clearMemory(){
  try{
    const payload = await fetchJson("/api/memory", {
      method: "DELETE",
    })
    return wrapMemoryPayload(payload)
  }catch(_error){
    const payload = await fetchJson(
      "/api/memory",
      jsonOptions("DELETE", { clear_all: true })
    )
    return wrapMemoryPayload(payload)
  }
}

window.NovaAPIMemory = {
  listMemory,
  addMemory,
  deleteMemoryItems,
  clearMemory,
}

})()