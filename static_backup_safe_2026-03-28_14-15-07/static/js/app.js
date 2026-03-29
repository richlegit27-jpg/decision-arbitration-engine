// C:\Users\Owner\nova\static\js\app.js

(() => {
"use strict";

const state = {
  sidebarOpen: true,
  memoryOpen: false
};

const el = {
  body: document.body,
  sidebar: document.getElementById("sidebar"),
  btnCloseSidebar: document.getElementById("btnCloseSidebar"),
  btnNewChat: document.getElementById("btnNewChat"),

  memoryPanel: document.getElementById("memoryPanel"),
  btnOpenMemory: document.getElementById("btnOpenMemory"),
  closeMemoryPanelBtn: document.getElementById("closeMemoryPanelBtn"),

  chatWindow: document.getElementById("chatWindow")
};

/* ---------------- Sidebar ---------------- */

function closeSidebar(){
  if(!el.sidebar) return;
  el.body.classList.remove("sidebar-open");
  state.sidebarOpen = false;
}

function openSidebar(){
  if(!el.sidebar) return;
  el.body.classList.add("sidebar-open");
  state.sidebarOpen = true;
}

/* ---------------- Memory Panel ---------------- */

function openMemory(){
  if(!el.memoryPanel) return;
  el.memoryPanel.classList.add("open");
  el.body.classList.add("panel-open");
  state.memoryOpen = true;
}

function closeMemory(){
  if(!el.memoryPanel) return;
  el.memoryPanel.classList.remove("open");
  el.body.classList.remove("panel-open");
  state.memoryOpen = false;
}

/* ---------------- Chat ---------------- */

function clearChat(){
  if(!el.chatWindow) return;
  el.chatWindow.innerHTML = "";
}

/* ---------------- Events ---------------- */

function bindEvents(){

  if(el.btnCloseSidebar){
    el.btnCloseSidebar.addEventListener("click", closeSidebar);
  }

  if(el.btnOpenMemory){
    el.btnOpenMemory.addEventListener("click", openMemory);
  }

  if(el.closeMemoryPanelBtn){
    el.closeMemoryPanelBtn.addEventListener("click", closeMemory);
  }

  if(el.btnNewChat){
    el.btnNewChat.addEventListener("click", clearChat);
  }

}

/* ---------------- Init ---------------- */

function init(){
  bindEvents();
}

document.addEventListener("DOMContentLoaded", init);

})();