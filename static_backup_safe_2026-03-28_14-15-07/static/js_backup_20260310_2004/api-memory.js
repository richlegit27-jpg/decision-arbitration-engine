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

async function listMemory(){
  const payload = await fetchJson("/api/memory")
  return {
    ...payload,
    memories: normalizeMemoryList(payload),
    updated_at: payload?.updated_at || null,
  }
}

async function addMemory(items){
  const normalizedItems = Array.isArray(items)
    ? items.map((item) => String(item || "").trim()).filter(Boolean)
    : [String(items || "").trim()].filter(Boolean)

  const payload = await fetchJson(
    "/api/memory",
    jsonOptions("POST", { items: normalizedItems })
  )

  return {
    ...payload,
    memories: normalizeMemoryList(payload),
    updated_at: payload?.updated_at || null,
  }
}

async function deleteMemoryItems(items){
  const normalizedItems = Array.isArray(items)
    ? items.map((item) => String(item || "").trim()).filter(Boolean)
    : [String(items || "").trim()].filter(Boolean)

  const payload = await fetchJson(
    "/api/memory",
    jsonOptions("DELETE", { items: normalizedItems })
  )

  return {
    ...payload,
    memories: normalizeMemoryList(payload),
    updated_at: payload?.updated_at || null,
  }
}

async function clearMemory(){
  const payload = await fetchJson("/api/memory", {
    method: "DELETE",
  })

  return {
    ...payload,
    memories: normalizeMemoryList(payload),
    updated_at: payload?.updated_at || null,
  }
}

window.NovaAPIMemory = {
  listMemory,
  addMemory,
  deleteMemoryItems,
  clearMemory,
}

})()