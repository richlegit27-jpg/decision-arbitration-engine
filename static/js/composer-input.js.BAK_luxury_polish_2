// C:\Users\Owner\nova\static\js\composer-input.js

(() => {
"use strict"

function createComposerInput(options = {}){
  const {
    elements = {},
    onSubmit = null,
    onStateChange = null,
  } = options

  const el = {
    input: elements.input || null,
    emptySuggestions: elements.emptySuggestions || null,
  }

  function autoResizeInput(){
    if(!el.input){
      return
    }

    el.input.style.height = "auto"
    el.input.style.height = `${Math.min(el.input.scrollHeight, 220)}px`
  }

  function focusInput(){
    el.input?.focus()
  }

  function getInputValue(){
    return String(el.input?.value || "")
  }

  function getTrimmedInputValue(){
    return getInputValue().trim()
  }

  function setInputValue(text){
    if(!el.input){
      return
    }

    el.input.value = String(text || "")
    autoResizeInput()

    if(typeof onStateChange === "function"){
      onStateChange()
    }
  }

  function clearInput(){
    setInputValue("")
  }

  async function handleKeyDown(event){
    if(event.key !== "Enter"){
      return
    }

    if(event.shiftKey){
      return
    }

    event.preventDefault()

    if(typeof onSubmit === "function"){
      await onSubmit()
    }
  }

  function handleInput(){
    autoResizeInput()

    if(typeof onStateChange === "function"){
      onStateChange()
    }
  }

  function handleSuggestionClick(event){
    const btn = event.target.closest(".empty-suggestion")
    if(!btn){
      return
    }

    setInputValue(btn.textContent || "")
    focusInput()
  }

  function bindEvents(){
    el.input?.addEventListener("input", handleInput)
    el.input?.addEventListener("keydown", handleKeyDown)
    el.emptySuggestions?.addEventListener("click", handleSuggestionClick)

    autoResizeInput()
  }

  return {
    bindEvents,
    autoResizeInput,
    focusInput,
    getInputValue,
    getTrimmedInputValue,
    setInputValue,
    clearInput,
  }
}

window.NovaComposerInput = {
  create: createComposerInput,
  createComposerInput,
}

})()