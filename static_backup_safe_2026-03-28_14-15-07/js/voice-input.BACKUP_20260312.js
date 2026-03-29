// C:\Users\Owner\nova\static\js\voice-input.js

(() => {
"use strict"

function createVoiceInput(options = {}){
  const {
    onTranscript = null,
    onStateChange = null,
  } = options

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition ||
    null

  let recognition = null
  let supported = !!SpeechRecognition
  let listening = false

  function notifyStateChange(){
    if(typeof onStateChange === "function"){
      onStateChange({
        supported,
        listening,
      })
    }
  }

  function buildRecognition(){
    if(!SpeechRecognition){
      return null
    }

    const instance = new SpeechRecognition()
    instance.lang = "en-US"
    instance.continuous = false
    instance.interimResults = true
    instance.maxAlternatives = 1

    instance.onstart = () => {
      listening = true
      notifyStateChange()
    }

    instance.onend = () => {
      listening = false
      notifyStateChange()
    }

    instance.onerror = () => {
      listening = false
      notifyStateChange()
    }

    instance.onresult = (event) => {
      let finalText = ""
      let interimText = ""

      const startIndex = Number(event.resultIndex || 0)

      for(let i = startIndex; i < event.results.length; i += 1){
        const result = event.results[i]
        const text = String(result?.[0]?.transcript || "").trim()

        if(!text){
          continue
        }

        if(result.isFinal){
          finalText += `${text} `
        }else{
          interimText += `${text} `
        }
      }

      const transcript = String(finalText || interimText).trim()

      if(transcript && typeof onTranscript === "function"){
        onTranscript({
          text: transcript,
          isFinal: !!finalText.trim(),
        })
      }
    }

    return instance
  }

  function ensureRecognition(){
    if(!recognition && supported){
      recognition = buildRecognition()
    }
    return recognition
  }

  function start(){
    if(!supported){
      notifyStateChange()
      return false
    }

    const instance = ensureRecognition()
    if(!instance || listening){
      return false
    }

    try{
      instance.start()
      return true
    }catch(_error){
      return false
    }
  }

  function stop(){
    if(!recognition || !listening){
      return false
    }

    try{
      recognition.stop()
      return true
    }catch(_error){
      return false
    }
  }

  function toggle(){
    if(listening){
      return stop()
    }
    return start()
  }

  function getState(){
    return {
      supported,
      listening,
    }
  }

  notifyStateChange()

  return {
    start,
    stop,
    toggle,
    getState,
  }
}

window.NovaVoiceInput = {
  create: createVoiceInput,
  createVoiceInput,
}

})()