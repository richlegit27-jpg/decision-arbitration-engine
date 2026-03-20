document.addEventListener("DOMContentLoaded", () => {
    // Panels
    const panels = {
        memory: document.getElementById("memoryPanel"),
        attachments: document.getElementById("attachmentsPanel"),
        exports: document.getElementById("exportsPanel"),
        voice: document.getElementById("voicePanel"),
        images: document.getElementById("imagesPanel"),
        newChat: document.getElementById("newChatPanel")
    };

    // Function to temporarily open a panel and highlight
    const showPanel = (panel, label) => {
        panel.style.display = "block";
        panel.style.transition = "all 0.3s ease";
        panel.style.opacity = 0;
        setTimeout(() => { panel.style.opacity = 1; }, 50);

        // Flash background
        const originalBg = panel.style.background;
        panel.style.background = "#4a90e2";
        setTimeout(() => { panel.style.background = originalBg; }, 800);
    };

    // Demo sequence
    const sequence = async () => {
        const delay = ms => new Promise(res => setTimeout(res, ms));

        // 1️⃣ Show Memory panel
        showPanel(panels.memory);
        panels.memory.innerHTML = "";
        ["You: Hello!", "AI: Welcome to Nova Ultimate 2026 demo!"].forEach(msg => {
            const div = document.createElement("div");
            div.textContent = msg;
            div.className = "memory-item";
            panels.memory.appendChild(div);
        });
        await delay(1200);

        // 2️⃣ Show Attachments panel
        showPanel(panels.attachments);
        panels.attachments.innerHTML = "";
        const fakeFile = new File(["Demo content"], "demo.txt", {type:"text/plain"});
        const addAttachment = window.addAttachment || (() => {});
        addAttachment(fakeFile);
        await delay(1200);

        // 3️⃣ Show Images panel
        showPanel(panels.images);
        panels.images.innerHTML = "";
        const fakeImg = new Image();
        fakeImg.src = "https://via.placeholder.com/120x80.png?text=Demo+Image";
        fakeImg.style.maxWidth = "100%";
        fakeImg.style.borderRadius = "6px";
        panels.images.appendChild(fakeImg);
        await delay(1200);

        // 4️⃣ Show Exports panel
        showPanel(panels.exports);
        await delay(800);

        // 5️⃣ Show Voice panel
        showPanel(panels.voice);
        await delay(800);

        // 6️⃣ Show New Chat panel
        showPanel(panels.newChat);
    };

    sequence();
});