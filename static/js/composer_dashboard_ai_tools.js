document.addEventListener("DOMContentLoaded",()=>{
    console.log("Nova AI Tools Suite Loaded 🤖");

    const panels={
        memory:document.getElementById("memoryPanel"),
        chat:document.getElementById("chatMessages")
    };
    const backendPort=window.NOVA_BACKEND_PORT;
    const model="gpt-4.1-mini";
    const currentSession="default";

    // ---------------- Helper: AI Request ----------------
    async function aiRequest(prompt){
        try{
            const res=await fetch(`http://127.0.0.1:${backendPort}/api/chat`,{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({content:prompt,session_id:currentSession,model})
            });
            const data=await res.json();
            return data[1].content;
        }catch(e){ console.error(e); return "Error: AI request failed"; }
    }

    // ---------------- Context Menu for Memory ----------------
    panels.memory.addEventListener("contextmenu", async e=>{
        e.preventDefault();
        const target=e.target.closest("div");
        if(!target) return;
        const action=prompt("AI Action: summarize/translate/explain/execute","summarize");
        if(!action) return;
        const result=await aiRequest(`${action}: ${target.textContent}`);
        alert(`AI Result:\n${result}`);
        if(action==="summarize"||action==="translate"||action==="explain"){
            target.innerHTML+=`<div style="margin-top:2px;color:#0ff;">[AI ${action}]: ${result}</div>`;
        }
    });

    // ---------------- Keyboard Shortcut for Selected Text ----------------
    document.addEventListener("keydown",async e=>{
        if(e.ctrlKey && e.key==="a"){ // Ctrl+A = AI Summarize selection
            const sel=window.getSelection().toString();
            if(sel){
                e.preventDefault();
                const result=await aiRequest(`summarize: ${sel}`);
                alert("AI Summary:\n"+result);
            }
        }
    });

    // ---------------- Prebuilt Dashboard Widgets ----------------
    function updateTokenUsage(){
        const chatMsgs=panels.chat.children;
        const totalTokens=Array.from(chatMsgs).reduce((acc,m)=>acc+m.textContent.length,0);
        const widget=document.getElementById("memoryStats");
        if(widget) widget.textContent=`Tokens approx: ${totalTokens}`;
    }
    const observer=new MutationObserver(updateTokenUsage);
    observer.observe(panels.chat,{childList:true});
});