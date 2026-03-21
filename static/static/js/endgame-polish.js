(() => {
"use strict"

// Quick helpers
function $(id) { return document.getElementById(id) }
function addClass(el, cls){ if(el) el.classList.add(cls) }
function removeClass(el, cls){ if(el) el.classList.remove(cls) }
function toggleClass(el, cls, force){ if(el) el.classList.toggle(cls, force) }

// Panels
const memoryPanel = $("memoryPanel")
const filesPanel = $("filesPanel")
const memoryBackdrop = $("memoryBackdrop")

function openPanel(panel){
  if(panel){
    panel.hidden = false
    addClass(document.body, "panel-open")
  }
  if(memoryBackdrop) memoryBackdrop.hidden = false
}

function closePanel(panel){
  if(panel){
    panel.hidden = true
  }
  if(memoryBackdrop) memoryBackdrop.hidden = true
  removeClass(document.body, "panel-open")
}

// Backdrop click closes all panels
if(memoryBackdrop){
  memoryBackdrop.addEventListener("click", () => {
    closePanel(memoryPanel)
    closePanel(filesPanel)
  })
}

// Sidebar buttons
const btnMemory = $("btnOpenMemory")
if(btnMemory){
  btnMemory.addEventListener("click", () => openPanel(memoryPanel))
}

const btnFiles = $("btnOpenFiles")
if(btnFiles){
  btnFiles.addEventListener("click", () => openPanel(filesPanel))
}

// Close buttons inside panels
const btnCloseMemory = $("btnCloseMemory")
if(btnCloseMemory){
  btnCloseMemory.addEventListener("click", () => closePanel(memoryPanel))
}

// Auto-focus composer textarea on page load
window.addEventListener("DOMContentLoaded", () => {
  const composerInput = $("composerInput")
  if(composerInput){
    composerInput.focus()
  }
})

// Optional: Escape closes panels
document.addEventListener("keydown", (event) => {
  if(event.key === "Escape"){
    closePanel(memoryPanel)
    closePanel(filesPanel)
  }
})

// Smooth animations: add class for transition
addClass(document.body, "endgame-ready")

})()