// C:\Users\Owner\nova\static\js\chat-sidebar.js

(() => {
"use strict"

const chatStateApi = window.NovaChatState
const chatStorage = window.NovaChatStorage
const renderApi = window.NovaChatSidebarRender
const layoutApi = window.NovaChatSidebarLayout
const actionsApi = window.NovaChatSidebarActions

if(!chatStateApi){
  throw new Error("NovaChatSidebar: window.NovaChatState is required")
}

if(!chatStorage){
  throw new Error("NovaChatSidebar: window.NovaChatStorage is required")
}

if(!renderApi){
  throw new Error("NovaChatSidebar: window.NovaChatSidebarRender is required")
}

if(!layoutApi){
  throw new Error("NovaChatSidebar: window.NovaChatSidebarLayout is required")
}

if(!actionsApi){
  throw new Error("NovaChatSidebar: window.NovaChatSidebarActions is required")
}

const { state } = chatStateApi

const el = {
  body: document.body,
  sidebar: document.getElementById("sidebar"),
  mobileOverlay: document.getElementById("mobileOverlay"),
  btnSidebarToggle: document.getElementById("btnSidebarToggle"),
  btnCloseSidebar: document.getElementById("btnCloseSidebar"),
  btnNewChat: document.getElementById("btnNewChat"),
  chatList: document.getElementById("chatList"),
  topbarTitle: document.getElementById("topbarTitle"),
}

let eventsBound = false
let callbacks = {
  onAfterCreate: null,
  onAfterSwitch: null,
  onAfterRename: null,
  onAfterDelete: null,
}

const renderController = renderApi.create({
  state,
  elements: {
    chatList: el.chatList,
    topbarTitle: el.topbarTitle,
  },
})

const layoutController = layoutApi.create({
  state,
  elements: {
    body: el.body,
    sidebar: el.sidebar,
    mobileOverlay: el.mobileOverlay,
  },
  onAfterSync(){
    renderController.updateTopbarTitle()
  },
})

function getActionsController(){
  return actionsApi.create({
    state,
    chatStorage,
    renderController,
    layoutController,
    callbacks,
  })
}

let actionsController = getActionsController()

function bindEvents(options = {}){
  callbacks = { ...callbacks, ...options }
  actionsController = getActionsController()

  if(eventsBound){
    return
  }

  el.btnSidebarToggle?.addEventListener("click", () => {
    layoutController.toggleSidebar()
  })

  el.btnCloseSidebar?.addEventListener("click", () => {
    layoutController.closeSidebar()
  })

  el.mobileOverlay?.addEventListener("click", () => {
    layoutController.closeSidebar()
  })

  el.btnNewChat?.addEventListener("click", async () => {
    await actionsController.createNewChat({})
  })

  el.chatList?.addEventListener("click", async (event) => {
    const actionBtn = event.target.closest("[data-action][data-chat-id]")
    if(actionBtn){
      const action = actionBtn.getAttribute("data-action")
      const chatId = actionBtn.getAttribute("data-chat-id") || ""

      if(action === "rename"){
        await actionsController.renameChat(chatId)
        return
      }

      if(action === "delete"){
        await actionsController.deleteChat(chatId)
        return
      }
    }

    const chatBtn = event.target.closest("[data-chat-id].chat-list-item")
    if(chatBtn){
      const chatId = chatBtn.getAttribute("data-chat-id") || ""
      await actionsController.switchChat(chatId)
    }
  })

  window.addEventListener("resize", () => {
    layoutController.syncSidebarState()
  })

  eventsBound = true
  layoutController.syncSidebarState()
  renderController.renderChatList()
}

window.NovaChatSidebar = {
  bindEvents,
  syncSidebarState: layoutController.syncSidebarState,
  renderChatList: renderController.renderChatList,
  createNewChat(options = {}){
    return actionsController.createNewChat(options)
  },
  openSidebar: layoutController.openSidebar,
  closeSidebar: layoutController.closeSidebar,
  toggleSidebar: layoutController.toggleSidebar,
}

})()