// C:\Users\Owner\nova\static\js\chat-api.js

(() => {
"use strict"

async function apiJson(url, options = {}) {

  const res = await fetch(url,{
    credentials:"same-origin",
    ...options
  })

  if(!res.ok){
    const txt = await res.text().catch(()=> "")
    throw new Error(`HTTP ${res.status} ${txt}`)
  }

  const type = res.headers.get("content-type") || ""

  if(type.includes("application/json")){
    return res.json()
  }

  return res.text()
}



async function listChats(){
  return apiJson("/api/chats")
}

async function getChat(chatId){
  return apiJson(`/api/chats/${encodeURIComponent(chatId)}`)
}

async function createChat(){
  return apiJson("/api/chats",{
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({ title:"New chat" })
  })
}

async function renameChat(chatId,title){
  return apiJson(`/api/chats/${encodeURIComponent(chatId)}`,{
    method:"PATCH",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({ title })
  })
}

async function deleteChat(chatId){
  return apiJson(`/api/chats/${encodeURIComponent(chatId)}`,{
    method:"DELETE"
  })
}


async function sendJsonMessage(chatId,message){

  return fetch("/api/chat/stream",{
    method:"POST",
    credentials:"same-origin",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({
      chat_id:chatId,
      message:message
    })
  })

}


async function sendMultipartMessage(chatId,message,files){

  const fd = new FormData()

  fd.append("chat_id",chatId)
  fd.append("message",message)

  for(const f of files){
    fd.append("files",f)
  }

  return fetch("/api/chat/stream",{
    method:"POST",
    body:fd,
    credentials:"same-origin"
  })

}


window.NovaAPI = {

  listChats,
  getChat,
  createChat,
  renameChat,
  deleteChat,
  sendJsonMessage,
  sendMultipartMessage

}

})()