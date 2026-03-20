document.addEventListener("DOMContentLoaded", () => {
    console.log("Nova Ultimate 2026 — Offline/Hybrid Mode Loaded 🌐");

    const backendPort = window.NOVA_BACKEND_PORT;
    const model = window.DEFAULT_MODEL;
    const input = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatMessages = document.getElementById("chatMessages");
    const panels = {
        memory: document.getElementById("memoryPanel")
    };

    let currentUser = "User"+Math.floor(Math.random()*1000);
    let currentSession = "default";

    // ---------------- Local Storage / Queue ----------------
    let memoryItems = JSON.parse(localStorage.getItem(`nova_memory_${currentSession}`)||"[]");
    let chatQueue = JSON.parse(localStorage.getItem(`nova_queue_${currentSession}`)||"[]");
    let online = navigator.onLine;

    window.addEventListener("online",()=>{ online=true; flushQueue(); console.log("Back Online, syncing..."); });
    window.addEventListener("offline",()=>{ online=false; console.log("Offline mode"); });

    function saveMemory(){ localStorage.setItem(`nova_memory_${currentSession}`, JSON.stringify(memoryItems)); }
    function saveQueue(){ localStorage.setItem(`nova_queue_${currentSession}`, JSON.stringify(chatQueue)); }

    function renderMarkdown(text){
        return text.replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }

    function renderMemory(){
        panels.memory.innerHTML="";
        memoryItems.forEach(item=>{
            const div=document.createElement("div");
            div.style.margin="2px 0"; div.style.padding="4px"; div.style.border="1px solid #555"; div.style.borderRadius="4px";
            div.innerHTML=`<strong>${item.user}:</strong> ${renderMarkdown(item.text)}`;
            panels.memory.appendChild(div);
        });
    }

    function addMemory(text,user=currentUser){
        memoryItems.push({text,user}); saveMemory(); renderMemory();
    }

    function addMessage(role,text){
        const div=document.createElement("div"); div.style.margin="4px 0";
        div.innerHTML=`<strong>${role==="user"?"You":role}:</strong> ${renderMarkdown(text)}`;
        chatMessages.appendChild(div); chatMessages.scrollTop=chatMessages.scrollHeight;
        addMemory(text,role==="user"?currentUser:role);
        return div;
    }

    // ---------------- Send / Queue ----------------
    async function sendMessage(text){
        addMessage("user",text);
        if(!online){
            chatQueue.push(text); saveQueue();
            addMemory("[Queued offline] "+text,currentUser);
            return;
        }
        try{
            const res=await fetch(`http://127.0.0.1:${backendPort}/api/chat/stream`,{
                method:"POST", headers:{"Content-Type":"application/json"},
                body:JSON.stringify({content:text,session_id:currentSession,model})
            });
            const reader=res.body.getReader(); const decoder=new TextDecoder();
            let aiDiv=addMessage("assistant","");
            let done=false;
            while(!done){
                const {value,done:readerDone}=await reader.read(); done=readerDone;
                if(value){ aiDiv.textContent+=decoder.decode(value,{stream:true}); chatMessages.scrollTop=chatMessages.scrollHeight; }
            }
        }catch(err){ console.error(err); addMemory("[Failed send] "+text,currentUser); chatQueue.push(text); saveQueue(); }
    }

    function flushQueue(){
        if(chatQueue.length===0) return;
        const queueCopy = [...chatQueue];
        chatQueue=[]; saveQueue();
        queueCopy.forEach(msg=>sendMessage(msg));
    }

    if(sendBtn) sendBtn.addEventListener("click",()=>{ const t=input.value.trim(); if(t) sendMessage(t); });
    renderMemory();

    // ---------------- Drag & Drop Offline Memory ----------------
    panels.memory.addEventListener("dragover",e=>e.preventDefault());
    panels.memory.addEventListener("drop",e=>{
        e.preventDefault();
        Array.from(e.dataTransfer.files).forEach(file=>{
            const reader=new FileReader();
            reader.onload=evt=> addMemory(`![${file.name}](data:${file.type};base64,${btoa(evt.target.result)})`);
            reader.readAsBinaryString(file);
        });
    });
});