(() => {
"use strict"

async function waitForNovaAPIs(timeout=3000){
  const start=Date.now()
  while(Date.now()-start<timeout){
    if(window.NovaChatState && window.NovaChatStorage) return { chatStateApi:window.NovaChatState, chatStorageApi:window.NovaChatStorage }
    await new Promise(r=>setTimeout(r,100))
  }
  throw new Error("Nova APIs not ready")
}

if(!window.NovaChatStorage){
  window.NovaChatStorage=(function(){
    const chatStateApi = window.NovaChatState
    const STORAGE_KEY = "nova_chats_storage_v1"
    function loadChats(){ try{ return JSON.parse(localStorage.getItem(STORAGE_KEY)||"[]") }catch(e){console.error(e);return[]} }
    function saveChats(chats){ localStorage.setItem(STORAGE_KEY,JSON.stringify(chats)) }
    async function createAndSaveChat(title="New Chat"){ const chat=chatStateApi.createChat(title); const stored=loadChats(); stored.unshift(chat); saveChats(stored); return chat }
    async function deleteChat(chatId){ const stored=loadChats().filter(c=>c.id!==chatId); saveChats(stored); chatStateApi.deleteChat(chatId) }
    async function loadAllChats(){ const stored=loadChats(); stored.forEach(chat=>{if(!chatStateApi.getChatById(chat.id)) chatStateApi.state.chats.push(chat)}) }
    return { createAndSaveChat, deleteChat, loadAllChats }
  })()
}

(async function launchNovaModules(){
  let apis
  try{ apis = await waitForNovaAPIs() }catch(err){ console.error("Nova bootstrap failed:",err); return }
  const { chatStateApi, chatStorageApi } = apis
  if(window.NovaSidebar) window.NovaSidebar.init({chatStateApi,chatStorageApi})
  if(window.NovaComposer) window.NovaComposer.init({chatStateApi,chatStorageApi})
  if(window.NovaMemoryPanel) window.NovaMemoryPanel.init({chatStateApi})
  if(window.NovaFilesPanel) window.NovaFilesPanel.init({chatStateApi})
  if(window.NovaApp) window.NovaApp.init({chatStateApi,chatStorageApi})
  console.log("Nova frontend fully initialized ✅")
})()
})();