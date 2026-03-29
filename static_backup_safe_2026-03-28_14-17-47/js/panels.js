document.addEventListener("DOMContentLoaded", () => {
    const backendPort = window.NOVA_BACKEND_PORT;
    const panels = {
        newChat: document.getElementById("newChatPanel")
    };

    panels.newChat.innerHTML = `
        <input id="sessionName" placeholder="Session name" style="margin-bottom:4px;">
        <button id="startNewSession">Start / Switch Session</button>
        <div id="sessionsList"></div>
    `;

    const sessionInput = document.getElementById("sessionName");
    const startBtn = document.getElementById("startNewSession");
    const listDiv = document.getElementById("sessionsList");

    let currentSession = "default";

    async function loadSessions() {
        try {
            const res = await fetch(`http://127.0.0.1:${backendPort}/api/chat/sessions`);
            const sessions = await res.json();
            listDiv.innerHTML = "";
            sessions.forEach(s => {
                const btn = document.createElement("button");
                btn.textContent = s;
                btn.onclick = () => switchSession(s);
                listDiv.appendChild(btn);
            });
        } catch(err) { listDiv.textContent = "Error loading sessions."; }
    }

    async function switchSession(name) {
        currentSession = name;
        sessionInput.value = "";
        // Reload memory panel
        try {
            const res = await fetch(`http://127.0.0.1:${backendPort}/api/chat/history?session_id=${currentSession}`);
            const data = await res.json();
            const memoryPanel = document.getElementById("memoryPanel");
            memoryPanel.innerHTML = "";
            data.forEach(msg => {
                const div = document.createElement("div");
                div.textContent = `${msg.role==="user"?"You: ":"AI: "}${msg.content}`;
                div.className = "memory-item";
                memoryPanel.appendChild(div);
            });
        } catch(err) { console.error(err); }
    }

    startBtn.addEventListener("click", async () => {
        const name = sessionInput.value.trim() || `Session_${Date.now()}`;
        await switchSession(name);
        await loadSessions();
    });

    loadSessions();
});