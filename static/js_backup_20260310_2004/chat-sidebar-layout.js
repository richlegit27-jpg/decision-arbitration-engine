// C:\Users\Owner\nova\static\js\chat-sidebar-layout.js

(() => {
"use strict"

function createChatSidebarLayout(options = {}){
  const {
    state,
    elements = {},
    onAfterSync = null,
  } = options

  if(!state){
    throw new Error("NovaChatSidebarLayout: state is required")
  }

  const el = {
    body: elements.body || document.body,
    sidebar: elements.sidebar || null,
    mobileOverlay: elements.mobileOverlay || null,
  }

  function isMobile(){
    return window.innerWidth <= 900
  }

  function syncSidebarState(){
    const open = !!state.sidebarOpen

    if(el.body){
      el.body.classList.toggle("sidebar-open", open)
    }

    if(el.sidebar){
      el.sidebar.setAttribute("data-open", open ? "true" : "false")
    }

    if(el.mobileOverlay){
      el.mobileOverlay.hidden = !(open && isMobile())
    }

    if(typeof onAfterSync === "function"){
      onAfterSync()
    }
  }

  function openSidebar(){
    state.sidebarOpen = true
    syncSidebarState()
  }

  function closeSidebar(){
    state.sidebarOpen = false
    syncSidebarState()
  }

  function toggleSidebar(){
    state.sidebarOpen = !state.sidebarOpen
    syncSidebarState()
  }

  return {
    isMobile,
    syncSidebarState,
    openSidebar,
    closeSidebar,
    toggleSidebar,
  }
}

window.NovaChatSidebarLayout = {
  create: createChatSidebarLayout,
  createChatSidebarLayout,
}

})()