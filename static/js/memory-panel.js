document.addEventListener("DOMContentLoaded", () => {
    const panel = document.getElementById("memoryPanel");
    const searchInput = document.createElement("input");
    searchInput.placeholder = "Search memory...";
    searchInput.style.width="100%";
    searchInput.style.marginBottom="8px";
    panel.prepend(searchInput);

    let memory_state = [];

    function renderMemory(items){
        panel.innerHTML = "";
        panel.prepend(searchInput);
        items.forEach(m=>{
            const div = document.createElement("div");
            div.className = "memory-item";
            div.textContent = m.text;
            panel.appendChild(div);
        });
    }

    searchInput.addEventListener("input", async ()=>{
        const query = searchInput.value.trim();
        if(!query){ renderMemory(memory_state); return; }
        const res = await fetch("http://127.0.0.1:8743/api/memory/search", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({query})
        });
        const data = await res.json();
        renderMemory(data);
    });

    window.addMemory = async (text)=>{
        await fetch("http://127.0.0.1:8743/api/memory/add", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({text})
        });
        renderMemory(memory_state);
    };
});