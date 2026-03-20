document.addEventListener("DOMContentLoaded", () => {
    console.log("Nova Ultimate 2026 — Ultra Collaboration Loaded 🌟");

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

    let currentUser = prompt("Enter your display name:", "User"+Math.floor(Math.random()*1000));
    let currentSession = "default";

    // ---------------- WebSocket for ultra collaboration ----------------
    const ws = new WebSocket(`ws://127.0.0.1:${backendPort}/ws/session/${currentSession}`);

    ws.addEventListener("open", ()=>console.log("Connected to Ultra Collaboration WS"));

    ws.addEventListener("message", evt=>{
        const msg = JSON.parse(evt.data);
        if(msg.type==="memory_add"){ addMemory(msg.content,false,msg.user); }
        if(msg.type==="chat_add"){ addMessage(msg.role,msg.content,false,msg.user); }
        if(msg.type==="typing"){ showTypingIndicator(msg.user); }
    });

    function broadcast(data){ if(ws.readyState===WebSocket.OPEN) ws.send(JSON.stringify(data)); }

    // ---------------- Memory Panel ----------------
    const memoryItems = [];

    function escapeHTML(str){ return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
    function renderMarkdown(text){ 
        return escapeHTML(text)
            .replace(/```([\s\S]*?)```/g,(m,p)=>`<pre style="background:#111;padding:4px;border-radius:4px;"><code>${p}</code></pre>`)
            .replace(/`([^`]+)`/g,(m,p)=>`<code style="background:#222;padding:2px 4px;border-radius:4px;">${p}</code>`)
            .replace(/!\[([^\]]*)\]\(([^)]+)\)/g,(m,alt,url)=>`<img src="${url}" alt="${alt}" style="max-width:100%;margin:2px 0;">`)
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g,(m,text,url)=>`<a href="${url}" target="_blank">${text}</a>`);
    }

    function renderMemory(){
        panels.memory.innerHTML = "";
        memoryItems.forEach(item=>{
            const div = document.createElement("div");
            div.style.margin="2px 0"; div.style.padding="4px"; div.style.border="1px solid #555"; div.style.borderRadius="4px";
            div.style.cursor="pointer"; div.innerHTML = `<strong>${item.user||"User"}:</strong> ${renderMarkdown(item.text)}`;
            div.addEventListener("click",()=>{ input.value=item.text; input.focus(); });
            panels.memory.appendChild(div);
        });
    }

    function addMemory(text, broadcastRemote=true, user=currentUser){
        memoryItems.push({text,user}); renderMemory();
        if(broadcastRemote) broadcast({type:"memory_add",content:text,user});
        showNotification(`${user} added a memory item`);
    }

    // ---------------- Chat ----------------
    function addMessage(role,content,broadcastRemote=true,user=currentUser){
        const div=document.createElement("div"); div.style.margin="4px 0";
        div.innerHTML=`<strong>${role==="user"?"You":user}:</strong> ${renderMarkdown(content)}`;
        chatMessages.appendChild(div); chatMessages.scrollTop=chatMessages.scrollHeight;
        if(broadcastRemote) broadcast({type:"chat_add",role,content,user});
        showNotification(`${user} sent a message`);
        return div;
    }

    // ---------------- Typing Indicator ----------------
    let typingTimeout;
    function showTypingIndicator(user){
        let indicator=document.getElementById("typingIndicator");
        if(!indicator){
            indicator=document.createElement("div"); indicator.id="typingIndicator";
            indicator.style.fontStyle="italic"; indicator.style.color="#999"; chatMessages.appendChild(indicator);
        }
        indicator.textContent=`${user} is typing...`;
        clearTimeout(typingTimeout);
        typingTimeout=setTimeout(()=>{ indicator.textContent=""; },2000);
    }

    input.addEventListener("input",()=>{ broadcast({type:"typing",user:currentUser}); });

    // ---------------- Notifications ----------------
    function showNotification(msg){
        if(Notification.permission==="granted"){ new Notification(msg); }
    }
    if(Notification.permission!=="granted"){ Notification.requestPermission(); }

    // ---------------- Send / Stream ----------------
    async function sendMessage(text){
        addMessage("user",text); input.value="";
        try{
            const controller=new AbortController(); stopBtn.onclick=()=>controller.abort();
            const res=await fetch(`http://127.0.0.1:${backendPort}/api/chat/stream`,{
                method:"POST", headers:{"Content-Type":"application/json"},
                body:JSON.stringify({content:text,session_id:currentSession,model}),
                signal:controller.signal
            });
            const reader=res.body.getReader(); const decoder=new TextDecoder();
            let aiDiv=addMessage("assistant",""); let done=false;
            while(!done){
                const {value,done:readerDone}=await reader.read(); done=readerDone;
                if(value){ aiDiv.textContent+=decoder.decode(value,{stream:true}); chatMessages.scrollTop=chatMessages.scrollHeight; }
            }
        }catch(err){ addMessage("assistant","Error: Could not reach AI backend."); console.error(err);}
    }

    if(sendBtn) sendBtn.addEventListener("click",()=>{ const t=input.value.trim(); if(t) sendMessage(t); });
    if(stopBtn) stopBtn.addEventListener("click",()=>input.value="");

    // ---------------- Drag & Drop Memory ----------------
    panels.memory.addEventListener("dragover",e=>e.preventDefault());
    panels.memory.addEventListener("drop",e=>{
        e.preventDefault();
        Array.from(e.dataTransfer.files).forEach(file=>{
            const reader=new FileReader();
            reader.onload=evt=> addMemory(`![${file.name}](data:${file.type};base64,${btoa(evt.target.result)})`);
            reader.readAsBinaryString(file);
        });
    });

    // ---------------- Inline Voice/Video Notes ----------------
    function addMediaNote(file,user=currentUser){
        const url=URL.createObjectURL(file);
        const isVideo=file.type.startsWith("video/");
        const isAudio=file.type.startsWith("audio/");
        const elem=document.createElement(isVideo?"video":"audio");
        elem.src=url; elem.controls=true; elem.style.maxWidth="100%";
        const container=document.createElement("div");
        container.innerHTML=`<strong>${user}:</strong> `;
        container.appendChild(elem);
        panels.memory.appendChild(container);
        memoryItems.push({text:file.name,user});
        broadcast({type:"memory_add",content:file.name,user});
    }

    panels.memory.addEventListener("dblclick",()=>{ /* optional quick record trigger */ });
});