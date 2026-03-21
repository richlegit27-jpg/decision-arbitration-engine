document.addEventListener("DOMContentLoaded", () => {
    console.log("Nova Ultimate 2026 — Multi-Device Collaboration Loaded 🚀");

    const backendPort = window.NOVA_BACKEND_PORT;
    const model = window.DEFAULT_MODEL;

    const input = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const stopBtn = document.getElementById("stopBtn");
    const chatMessages = document.getElementById("chatMessages");

    const panels = {
        memory: document.getElementById("memoryPanel"),
        attachments: document.getElementById("attachmentsPanel"),
        exports: document.getElementById("exportsPanel"),
        voice: document.getElementById("voicePanel"),
        images: document.getElementById("imagesPanel"),
        newChat: document.getElementById("newChatPanel")
    };

    let currentUser = "default";
    let currentSession = "default";

    // ---------------- WebSocket for real-time sync ----------------
    const ws = new WebSocket(`ws://127.0.0.1:${backendPort}/ws/session/${currentSession}`);

    ws.addEventListener("open", () => console.log("Connected to collaboration WebSocket"));
    ws.addEventListener("message", (evt) => {
        const msg = JSON.parse(evt.data);
        if(msg.type === "memory_add"){
            addMemory(msg.content, false); // false = do not broadcast again
        }
        if(msg.type === "chat_add"){
            addMessage(msg.role, msg.content, false);
        }
    });

    function broadcast(data){
        if(ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
    }

    // ---------------- Memory Panel ----------------
    const memoryItems = [];
    function renderMarkdown(text){
        return text.replace(/</g,"&lt;").replace(/>/g,"&gt;"); // simple escape, can extend
    }

    function renderMemory(){
        panels.memory.innerHTML = "";
        memoryItems.forEach(item=>{
            const div = document.createElement("div");
            div.style.margin="2px 0"; div.style.padding="2px 4px"; div.style.border="1px solid #555"; div.style.borderRadius="4px";
            div.style.cursor="pointer"; div.innerHTML = renderMarkdown(item.text);
            div.addEventListener("click", ()=>{ input.value=item.text; input.focus(); });
            panels.memory.appendChild(div);
        });
    }

    function addMemory(text, broadcastRemote=true){
        memoryItems.push({text});
        renderMemory();
        if(broadcastRemote) broadcast({type:"memory_add",content:text});
    }

    // ---------------- Chat ----------------
    function addMessage(role, content, broadcastRemote=true){
        const div = document.createElement("div");
        div.style.margin="4px 0"; div.innerHTML=`<strong>${role==="user"?"You":"AI"}:</strong> ${renderMarkdown(content)}`;
        chatMessages.appendChild(div);
        chatMessages.scrollTop=chatMessages.scrollHeight;
        if(broadcastRemote) broadcast({type:"chat_add",role,content});
        return div;
    }

    // ---------------- Send / Stream ----------------
    async function sendMessage(text){
        addMessage("user", text);
        input.value="";
        try{
            const controller = new AbortController(); stopBtn.onclick = ()=>controller.abort();
            const res = await fetch(`http://127.0.0.1:${backendPort}/api/chat/stream`,{
                method:"POST", headers:{"Content-Type":"application/json"},
                body:JSON.stringify({content:text,session_id:currentSession,model}),
                signal:controller.signal
            });
            const reader = res.body.getReader(); const decoder = new TextDecoder();
            let aiDiv = addMessage("assistant","");
            let done=false;
            while(!done){
                const {value,done:readerDone}=await reader.read(); done=readerDone;
                if(value){ aiDiv.textContent += decoder.decode(value,{stream:true}); chatMessages.scrollTop=chatMessages.scrollHeight; }
            }
        }catch(err){ addMessage("assistant","Error: Could not reach AI backend."); console.error(err);}
    }

    if(sendBtn) sendBtn.addEventListener("click", ()=>{ const t=input.value.trim(); if(t) sendMessage(t); });
    if(stopBtn) stopBtn.addEventListener("click", ()=>input.value="");

    // ---------------- Drag & Drop Memory ----------------
    panels.memory.addEventListener("dragover", e=>e.preventDefault());
    panels.memory.addEventListener("drop", e=>{
        e.preventDefault();
        Array.from(e.dataTransfer.files).forEach(file=>{
            const reader = new FileReader();
            reader.onload = evt=> addMemory(`![${file.name}](data:${file.type};base64,${btoa(evt.target.result)})`);
            reader.readAsBinaryString(file);
        });
    });

});