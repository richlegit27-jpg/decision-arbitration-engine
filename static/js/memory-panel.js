(function () {
    "use strict";

    const API_BASE = "";

    function $(id) {
        return document.getElementById(id);
    }

    const panel = $("memoryPanel");
    const list = $("memoryList");
    const openButton = $("btnOpenMemory");
    const closeButton = $("closeMemoryPanelBtn");
    const deleteAllButton = $("deleteAllMemoryBtn");

    async function request(url, options = {}) {
        const response = await fetch(
            API_BASE + url,
            {
                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                },
                ...options
            }
        );

        let payload = null;

        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }

        if (!response.ok) {
            const message =
                payload?.error ||
                payload?.message ||
                `Request failed (${response.status})`;

            throw new Error(message);
        }

        return payload;
    }

    function getMemoryItems(payload) {
        if (!payload) {
            return [];
        }

        if (Array.isArray(payload.data?.memory)) {
            return payload.data.memory;
        }

        if (Array.isArray(payload.data?.items)) {
            return payload.data.items;
        }

        if (Array.isArray(payload.memory)) {
            return payload.memory;
        }

        if (Array.isArray(payload.items)) {
            return payload.items;
        }

        return [];
    }

    function createMemoryItem(memory) {
        const item = document.createElement("div");

        item.className = "memory-item";
        item.dataset.memoryId = memory.id || "";

        const content = document.createElement("div");
        content.className = "memory-item-content";

        const text = document.createElement("div");
        text.className = "memory-item-text";
        text.textContent = memory.text || "";

        const meta = document.createElement("div");
        meta.className = "memory-item-meta";

        const parts = [];

        if (memory.kind) {
            parts.push(memory.kind);
        }

        if (memory.source) {
            parts.push(memory.source);
        }

        meta.textContent = parts.join(" · ");

        content.appendChild(text);

        if (meta.textContent) {
            content.appendChild(meta);
        }

        const actions = document.createElement("div");
        actions.className = "memory-item-actions";

        const deleteButton = document.createElement("button");

        deleteButton.type = "button";
        deleteButton.className = "memory-delete-btn";
        deleteButton.textContent = "Delete";

        deleteButton.addEventListener(
            "click",
            async function () {
                await deleteMemory(memory.id);
            }
        );

        actions.appendChild(deleteButton);

        item.appendChild(content);
        item.appendChild(actions);

        return item;
    }

    function renderMemory(items) {
        if (!list) {
            return;
        }

        list.innerHTML = "";

        if (!items.length) {
            const empty = document.createElement("div");

            empty.className = "memory-empty";
            empty.textContent = "No saved memories.";

            list.appendChild(empty);

            return;
        }

        items.forEach(function (memory) {
            list.appendChild(
                createMemoryItem(memory)
            );
        });
    }

    async function loadMemory() {
        if (!list) {
            return [];
        }

        list.innerHTML = "";

        const loading = document.createElement("div");

        loading.className = "memory-loading";
        loading.textContent = "Loading memory...";

        list.appendChild(loading);

        try {
            const payload = await request(
                "/api/memory",
                {
                    method: "GET"
                }
            );

            const items = getMemoryItems(payload);

            renderMemory(items);

            return items;

        } catch (error) {
            console.error(
                "Failed to load memory:",
                error
            );

            list.innerHTML = "";

            const failure = document.createElement("div");

            failure.className = "memory-error";
            failure.textContent =
                "Failed to load memory.";

            list.appendChild(failure);

            return [];
        }
    }

    async function deleteMemory(memoryId) {
        if (!memoryId) {
            return;
        }

        try {
            const payload = await request(
                "/api/memory/delete",
                {
                    method: "POST",
                    body: JSON.stringify({
                        id: memoryId
                    })
                }
            );

            if (
                payload?.ok === false
            ) {
                throw new Error(
                    payload.error ||
                    payload.message ||
                    "Failed to delete memory."
                );
            }

            await loadMemory();

        } catch (error) {
            console.error(
                "Failed to delete memory:",
                error
            );

            alert(
                error.message ||
                "Failed to delete memory."
            );
        }
    }

    async function deleteAllMemory() {
        const confirmed = window.confirm(
            "Delete all saved memories?"
        );

        if (!confirmed) {
            return;
        }

        try {
            const payload = await request(
                "/api/memory/clear",
                {
                    method: "POST",
                    body: JSON.stringify({})
                }
            );

            if (
                payload?.ok === false
            ) {
                throw new Error(
                    payload.error ||
                    payload.message ||
                    "Failed to clear memories."
                );
            }

            renderMemory([]);

        } catch (error) {
            console.error(
                "Failed to clear memories:",
                error
            );

            alert(
                error.message ||
                "Failed to clear memories."
            );
        }
    }

    function openPanel() {
        if (!panel) {
            return;
        }

        panel.classList.add("open");
        panel.classList.remove("hidden");

        panel.style.display = "";

        loadMemory();
    }

    function closePanel() {
        if (!panel) {
            return;
        }

        panel.classList.remove("open");
        panel.classList.add("hidden");
    }

    if (openButton) {
        openButton.addEventListener(
            "click",
            openPanel
        );
    }

    if (closeButton) {
        closeButton.addEventListener(
            "click",
            closePanel
        );
    }

    if (deleteAllButton) {
        deleteAllButton.addEventListener(
            "click",
            deleteAllMemory
        );
    }

    window.NovaMemoryPanel = {
        open: openPanel,
        close: closePanel,
        load: loadMemory,
        deleteMemory: deleteMemory,
        deleteAll: deleteAllMemory
    };

    console.log(
        "Nova memory panel ready."
    );
})();