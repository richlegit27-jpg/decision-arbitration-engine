document.addEventListener("DOMContentLoaded", () => {
    console.log("Nova Dashboard Widgets Loaded 📊");

    const memoryItems = JSON.parse(localStorage.getItem(`nova_memory_default`)||"[]");
    const chatMessages = document.getElementById("chatMessages");
    const dashboard = document.getElementById("dashboard");

    // Create widget containers
    const widgetStats = document.createElement("div"); widgetStats.id="widgetStats"; dashboard.appendChild(widgetStats);
    const widgetGraph = document.createElement("canvas"); widgetGraph.id="widgetGraph"; widgetGraph.height=150; dashboard.appendChild(widgetGraph);

    // ---------------- Stats ----------------
    function updateStats(){
        const totalMemory = memoryItems.length;
        const mediaCount = memoryItems.filter(item=>item.text.match(/!\[.*\]\(data:.+\)/)).length;
        const textCount = totalMemory-mediaCount;
        widgetStats.innerHTML=`<strong>Total Memory:</strong> ${totalMemory} | <strong>Text:</strong> ${textCount} | <strong>Media:</strong> ${mediaCount}`;
    }
    updateStats();

    // ---------------- Simple Graph ----------------
    function renderGraph(){
        const ctx = widgetGraph.getContext("2d");
        ctx.clearRect(0,0,widgetGraph.width,widgetGraph.height);
        const messages = Array.from(chatMessages.children);
        const userCount = messages.filter(m=>m.textContent.startsWith("You:")).length;
        const aiCount = messages.filter(m=>m.textContent.startsWith("AI:")).length;
        const total = userCount+aiCount;
        const barWidth = 50;
        ctx.fillStyle="var(--accent)";
        ctx.fillRect(30,widgetGraph.height-50,barWidth,(userCount/Math.max(1,total))*100);
        ctx.fillStyle="var(--accent-2)";
        ctx.fillRect(120,widgetGraph.height-50,barWidth,(aiCount/Math.max(1,total))*100);
        ctx.fillStyle="var(--text)"; ctx.fillText("User",35,widgetGraph.height-10); ctx.fillText("AI",125,widgetGraph.height-10);
    }
    renderGraph();

    // ---------------- Live Updates ----------------
    const observer = new MutationObserver(()=>{
        updateStats(); renderGraph();
    });
    observer.observe(chatMessages,{childList:true});

    // Optional: extend to multiple sessions, token count, typing indicators, etc.
});