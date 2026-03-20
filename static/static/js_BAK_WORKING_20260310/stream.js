
// C:\Users\Owner\nova\static\js\stream.js

(() => {
"use strict"

function parseSSE(chunk){
  const lines = chunk.split("\n")
  const events = []

  let event = { type: "message", data: "" }

  for(const line of lines){
    if(line.startsWith("event:")){
      event.type = line.slice(6).trim()
    } else if(line.startsWith("data:")){
      event.data += line.slice(5).trim()
    } else if(line.trim() === ""){
      if(event.data){
        events.push({ ...event })
      }
      event = { type: "message", data: "" }
    }
  }

  return events
}

async function readStream(response, handlers = {}){
  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  let buffer = ""

  while(true){
    const { done, value } = await reader.read()

    if(done){
      if(handlers.done){
        handlers.done()
      }
      break
    }

    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split("\n\n")
    buffer = parts.pop() || ""

    for(const part of parts){
      const events = parseSSE(part)

      for(const evt of events){
        handleEvent(evt, handlers)
      }
    }
  }
}

function handleEvent(evt, handlers){
  let data = evt.data

  try {
    data = JSON.parse(evt.data)
  } catch {}

  switch(evt.type){

    case "meta":
      handlers.meta?.(data)
      break

    case "token":
      handlers.token?.(data)
      break

    case "done":
      handlers.done?.(data)
      break

    case "error":
      handlers.error?.(data)
      break

    default:
      handlers.message?.(data)
  }
}

async function stream(response, handlers = {}){
  if(!response || !response.body){
    throw new Error("Invalid stream response")
  }

  try{
    await readStream(response, handlers)
  }catch(err){
    if(handlers.error){
      handlers.error(err)
    }else{
      console.error(err)
    }
  }
}

window.NovaStream = {
  stream,
}

})()