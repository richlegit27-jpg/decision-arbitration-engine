document.addEventListener("DOMContentLoaded", () => {
    console.log("Nova Ultimate 2026 — Mobile & Productivity Loaded 📱");

    const input = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatMessages = document.getElementById("chatMessages");
    const panels = {
        memory: document.getElementById("memoryPanel"),
        attachments: document.getElementById("attachmentsPanel")
    };

    let currentUser = "User"+Math.floor(Math.random()*1000);
    let currentSession = "default";

    // ---------------- Keyboard Shortcuts ----------------
    document.addEventListener("keydown", e=>{
        if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); sendBtn.click(); }
        if(e.key==="Enter" && e.shiftKey){ /* allow newline */ }
        if(e.ctrlKey && e.key==="/"){ document.getElementById("sidebar").classList.toggle("collapsed"); }
        if(e.ctrlKey && e.key==="m"){ panels.memory.scrollIntoView({behavior:"smooth"}); input.focus(); }
        if(e.ctrlKey && e.key==="n"){ document.getElementById("toggleNewChat").click(); }
    });

    // ---------------- Touch-Friendly UI ----------------
    Object.values(panels).forEach(p=>{
        p.style.minHeight="120px"; p.style.padding="8px"; p.style.touchAction="manipulation";
    });

    // ---------------- Quick AI Actions ----------------
    panels.memory.addEventListener("contextmenu", e=>{
        e.preventDefault();
        const target = e.target.closest("div");
        if(!target) return;
        const action = prompt("Quick AI Action: summarize/expand/explain", "summarize");
        if(!action) return;
        fetch(`http://127.0.0.1:8750/api/chat`,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({content:`${action}: ${target.textContent}`,session_id:currentSession,model:"gpt-4.1-mini"})
        }).then(r=>r.json()).then(data=>{
            alert("AI Response:\n"+data[1].content);
        });
    });

    // ---------------- Responsive Panels ----------------
    function adjustLayout(){
        if(window.innerWidth<768){
            document.getElementById("main").style.flexDirection="column";
            Object.values(panels).forEach(p=>p.style.width="100%");
        } else {
            document.getElementById("main").style.flexDirection="row";
            Object.values(panels).forEach(p=>p.style.width="300px");
        }
    }
    window.addEventListener("resize", adjustLayout);
    adjustLayout();

    // ---------------- Send Button ----------------
    sendBtn.addEventListener("click", async ()=>{
        const text = input.value.trim(); if(!text) return;
        input.value="";
        const div=document.createElement("div"); div.innerHTML=`<strong>You:</strong> ${text}`;
        chatMessages.appendChild(div); chatMessages.scrollTop=chatMessages.scrollHeight;
        // streaming GPT simulation
        const res=await fetch(`http://127.0.0.1:8750/api/chat/stream`,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({content:text,session_id:currentSession,model:"gpt-4.1-mini"})
        });
        const reader=res.body.getReader(); const decoder=new TextDecoder();
        const aiDiv=document.createElement("div"); aiDiv.innerHTML="<strong>AI:</strong> "; chatMessages.appendChild(aiDiv);
        let done=false;
        while(!done){
            const {value,done:readerDone}=await reader.read(); done=readerDone;
            if(value){ aiDiv.textContent+=decoder.decode(value,{stream:true}); chatMessages.scrollTop=chatMessages.scrollHeight; }
        }
    });
});