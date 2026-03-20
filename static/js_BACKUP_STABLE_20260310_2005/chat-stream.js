// C:\Users\Owner\nova\static\js\chat-stream.js

(() => {

"use strict"



async function streamResponse(response, handlers){

  const reader = response.body.getReader()

  const decoder = new TextDecoder()

  let buffer = ""



  while(true){

    const {value,done} = await reader.read()

    if(done) break

    buffer += decoder.decode(value)



    const parts = buffer.split("\n\n")



    while(parts.length > 1){

      const chunk = parts.shift()

      parseEvent(chunk,handlers)

    }



    buffer = parts[0]

  }

}



function parseEvent(raw,handlers){

  const lines = raw.split("\n")

  let event = ""
  let data = ""



  for(const line of lines){

    if(line.startsWith("event:"))
      event = line.slice(6).trim()

    if(line.startsWith("data:"))
      data += line.slice(5).trim()

  }



  if(!data) return



  let payload

  try{
    payload = JSON.parse(data)
  }
  catch{
    return
  }



  if(event === "meta"){
    handlers?.meta?.(payload)
    return
  }



  if(event === "token"){
    handlers?.token?.(payload)
    return
  }



  if(event === "done"){
    handlers?.done?.(payload)
    return
  }

}



window.NovaStream = {

  streamResponse

}

})()