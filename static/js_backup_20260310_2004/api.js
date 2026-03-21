// C:\Users\Owner\nova\static\js\api.js

(() => {
"use strict"

const core = window.NovaAPICore
const chats = window.NovaAPIChats
const memory = window.NovaAPIMemory
const stream = window.NovaAPIStream

if(!core){
  throw new Error("NovaAPI: window.NovaAPICore is required")
}

if(!chats){
  throw new Error("NovaAPI: window.NovaAPIChats is required")
}

if(!memory){
  throw new Error("NovaAPI: window.NovaAPIMemory is required")
}

if(!stream){
  throw new Error("NovaAPI: window.NovaAPIStream is required")
}

window.NovaAPI = {
  ...core,
  ...chats,
  ...memory,
  ...stream,
}

})()