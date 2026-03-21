// C:\Users\Owner\nova\static\js\state.js

(() => {
"use strict"

function createState(){
  return {
    chats: [],
    activeChatId: null,
    messages: [],

    isStreaming: false,
    streamingMessage: null,
    pendingUserMessageId: null,

    sidebarOpen: false,

    pendingAttachments: [],

    attachments: {
      pendingFiles: [],
    },
  }
}

window.NovaState = {
  create: createState,
  createState
}

})()