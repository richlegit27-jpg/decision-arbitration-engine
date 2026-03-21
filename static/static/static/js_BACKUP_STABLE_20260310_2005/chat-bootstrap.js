// C:\Users\Owner\nova\static\js\chat-bootstrap.js

(() => {
"use strict"

function bootstrapChatApp(init){
  if(typeof init !== "function"){
    throw new Error("NovaChatBootstrap: init function is required")
  }

  async function start(){
    try{
      await init()
    }catch(err){
      console.error("NovaChatApp init error:", err)
    }
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", () => {
      start()
    }, { once: true })
    return
  }

  start()
}

window.NovaChatBootstrap = {
  start: bootstrapChatApp,
  bootstrapChatApp,
}

})()