(() => {
"use strict"

window.NovaSidebar = {
  init({ chatStateApi, chatStorageApi }){
    const el = {
      chatList: document.getElementById("chatList"),
      newChatBtn: document.getElementById("newChatBtn"),
    }

    if(!el.chatList || !el.newChatBtn) return

    // ----------------------
    // Render chat list
    // ----------------------
    function renderChatList(){
      el.chatList.innerHTML = ""
      (chatStateApi.state.chats || []).forEach(chat=>{
        const li = document.createElement("li")
        li.className = "chat-item"
        li.textContent = chat.title
        li.dataset.chatId = chat.id

        li.addEventListener("click", ()=>{
          chatStateApi.setActiveChat(chat.id)
          window.dispatchEvent(new CustomEvent("nova:chat-changed",{detail:{chatId:chat.id}}))
        })

        const delBtn = document.createElement("button")
        delBtn.textContent = "✕"
        delBtn.className = "chat-delete-btn"
        delBtn.addEventListener("click", async (e)=>{
          e.stopPropagation()
          if(chatStorageApi && typeof chatStorageApi.deleteChat === "function"){
            await chatStorageApi.deleteChat(chat.id)
          }
          chatStateApi.deleteChat(chat.id)
          renderChatList()
        })

        li.appendChild(delBtn)
        el.chatList.appendChild(li)
      })
    }

    // ----------------------
    // New chat
    // ----------------------
    el.newChatBtn.addEventListener("click", async ()=>{
      el.newChatBtn.disabled = true
      el.newChatBtn.textContent = "Creating..."
      try{
        if(chatStorageApi && typeof chatStorageApi.createAndSaveChat === "function"){
          const chat = await chatStorageApi.createAndSaveChat("New Chat")
          chatStateApi.setActiveChat(chat.id)
        }else{
          const chat = chatStateApi.createChat("New Chat")
          chatStateApi.setActiveChat(chat.id)
        }
      }catch(err){
        console.error("New Chat failed:", err)
        alert("Could not create new chat.")
      }finally{
        el.newChatBtn.disabled = false
        el.newChatBtn.textContent = "+ New Chat"
        renderChatList()
      }

      // Close sidebar on mobile
      if(window.innerWidth <= 980){
        document.body.classList.remove("sidebar-open")
      }
    })

    // ----------------------
    // Listen to chat changes
    // ----------------------
    window.addEventListener("nova:chat-changed", renderChatList)
    window.addEventListener("nova:chat-deleted", renderChatList)

    // Initial render
    renderChatList()
  }
}
})();