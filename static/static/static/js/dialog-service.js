// C:\Users\Owner\nova\static\js\dialog-service.js

(() => {
"use strict"

function createDialogService(){
  async function confirm(options = {}){
    const {
      title = "Confirm",
      message = "Are you sure?",
    } = options

    return window.confirm(`${title}\n\n${message}`)
  }

  async function prompt(options = {}){
    const {
      title = "Input",
      message = "",
      value = "",
    } = options

    const text = [title, message].filter(Boolean).join("\n\n")
    const result = window.prompt(text, value)
    return result === null ? null : String(result)
  }

  return {
    confirm,
    prompt,
  }
}

window.NovaDialogService = {
  createDialogService,
}

})()