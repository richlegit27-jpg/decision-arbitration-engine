
(function () {
    "use strict";

    if (window.__NOVA_MEMORY_CONTROL_CENTER_V1_20260622__) return;
    window.__NOVA_MEMORY_CONTROL_CENTER_V1_20260622__ = true;

    let novaMemoryItems = [];
    let novaMemoryFilter = "all";
    let novaMemorySearch = "";

    function escapeMemory(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getMemoryText(item) {
        return String(
            item.text ||
            item.value ||
            item.fact ||
            item.content ||
            item.memory ||
            item.summary ||
            item.title ||
            item.note ||
            ""
        ).trim();
    }

    function getMemoryId(item) {
        return String(item.id || item.memory_id || item.uuid || item.key || "");
    }

    function getMemoryKind(item) {
        const raw = String(item.kind || item.type || item.category || item.source || "").toLowerCase();
        const text = getMemoryText(item).toLowerCase();

        if (item.pinned || item.pin || item.is_pinned) return "pinned";
        if (raw.includes("preference") || text.includes("prefer") || text.includes("favorite") || text.includes("from now on")) return "preferences";
        if (raw.includes("project") || text.includes("nova") || text.includes("project") || text.includes("phase")) return "project";
        if (raw.includes("person") || raw.includes("people") || text.includes("my name") || text.includes("richard")) return "people";

        return raw || "general";
    }

    function isPinned(item) {
        return Boolean(item.pinned || item.pin || item.is_pinned);
    }

    function normalizeMemoryPayload(data) {
        const candidates = [
            data && data.items,
            data && data.memories,
            data && data.memory,
            data && data.records,
            data && data.data && data.data.items,
            data && data.data && data.data.memories,
            data && data.data && data.data.memory,
            data && data.data && data.data.records,
            data && data.data
        ];

        for (const value of candidates) {
            if (Array.isArray(value)) return value;
        }

        return [];
    }

    function ensureMemoryControlUI() {
        const memory = document.querySelector(".memory-section");
        const list = document.getElementById("desktopMemoryList");

        if (!memory || !list) return;

        const oldControl = memory.querySelector(".nova-memory-control");

if (oldControl) {
    oldControl.remove();
}

        const shell = document.createElement("div");
        shell.className = "nova-memory-control";

        shell.innerHTML = `
            <div class="nova-memory-toolbar">
                <input id="novaMemorySearch" type="search" placeholder="Search memory..." />

                <div class="nova-memory-filters">
                    <button class="nova-memory-filter active" type="button" data-memory-filter="all">All</button>
                    <button class="nova-memory-filter" type="button" data-memory-filter="preferences">Preferences</button>
                    <button class="nova-memory-filter" type="button" data-memory-filter="project">Project</button>
                    <button class="nova-memory-filter" type="button" data-memory-filter="people">People</button>
                </div>

                <div class="nova-memory-actions">
                    <button id="novaMemoryRefreshBtn" class="nova-memory-btn" type="button">Refresh</button>
                </div>
        `;

        list.parentNode.insertBefore(shell, list);
        shell.appendChild(list);

        const search = document.getElementById("novaMemorySearch");
        if (search) {
            search.addEventListener("input", function () {
                novaMemorySearch = search.value || "";
                renderMemoryControlList();
            });
        }

        shell.querySelectorAll("[data-memory-filter]").forEach(function (button) {
            button.addEventListener("click", function () {
                novaMemoryFilter = button.dataset.memoryFilter || "all";

                shell.querySelectorAll("[data-memory-filter]").forEach(function (b) {
                    b.classList.toggle("active", b === button);
                });

                renderMemoryControlList();
            });
        });

        const refresh = document.getElementById("novaMemoryRefreshBtn");

        if (refresh) {
            refresh.addEventListener("click", loadMemoryControlData);
        }
    }

    async function postMemory(url, payload) {
        const res = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload || {})
        });

        let data = null;

        try {
            data = await res.json();
        } catch (_) {}

        if (!res.ok) {
            throw new Error("Request failed: " + url);
        }

        return data;
    }

    async function addMemoryPrompt(kind) {
        const label = kind === "project" ? "Project note" : "Preference";
        const value = prompt("Add " + label + ":");

        if (!value || !value.trim()) return;

        const clean = value.trim();

        try {
            await postMemory("/api/memory/add", {
                text: clean,
                value: clean,
                memory: clean,
                note: clean,
                kind: kind,
                type: kind,
                category: kind
            });

            await loadMemoryControlData();
        } catch (error) {
            alert("Could not add memory yet. Backend may use a different payload.");
        }
    }

    async function pinMemory(item) {
        const id = getMemoryId(item);

        if (!id) {
            alert("This memory has no ID, so it cannot be pinned from the UI yet.");
            return;
        }

        try {
            await postMemory("/api/memory/pin", {
                id: id,
                memory_id: id,
                pinned: !isPinned(item),
                pin: !isPinned(item)
            });

            await loadMemoryControlData();
        } catch (error) {
            alert("Could not pin this memory yet.");
        }
    }

    async function deleteMemory(item) {
        const id = getMemoryId(item);

        if (!id) {
            alert("This memory has no ID, so it cannot be deleted from the UI yet.");
            return;
        }

        if (!confirm("Delete this memory?")) return;

        try {
            await postMemory("/api/memory/delete", {
                id: id,
                memory_id: id
            });

            await loadMemoryControlData();
        } catch (error) {
            alert("Could not delete this memory yet.");
        }
    }

    async function loadMemoryControlData() {
        ensureMemoryControlUI();

        const list = document.getElementById("desktopMemoryList");
        const count = document.getElementById("desktopMemoryCount");

        if (list) {
            list.innerHTML = "<div class='execution-note'>Loading memory...</div>";
        }

        try {
            const res = await fetch("/api/memory", { cache: "no-store" });
            const data = await res.json();

            novaMemoryItems = normalizeMemoryPayload(data);

            if (count) {
                count.textContent = String(novaMemoryItems.length);
            }

            renderMemoryControlList();
        } catch (error) {
            if (list) {
                list.innerHTML = "<div class='execution-note'>Memory failed to load.</div>";
            }

            if (count) {
                count.textContent = "error";
            }
        }
    }

    function renderMemoryControlList() {
        const list = document.getElementById("desktopMemoryList");
        const count = document.getElementById("desktopMemoryCount");

        if (!list) return;

        const q = String(novaMemorySearch || "").trim().toLowerCase();

        let visible = novaMemoryItems.filter(function (item) {
            const text = getMemoryText(item);
            const kind = getMemoryKind(item);

if (novaMemoryFilter !== "all" && kind !== novaMemoryFilter) {
    return false;
}

            if (q) {
                const haystack = (text + " " + kind + " " + JSON.stringify(item)).toLowerCase();
                if (!haystack.includes(q)) return false;
            }

            return true;
        });

        if (count) {
            count.textContent = String(visible.length) + "/" + String(novaMemoryItems.length);
        }

        if (!visible.length) {
            list.innerHTML = "<div class='execution-note'>No matching memories.</div>";
            return;
        }

list.innerHTML = visible.map(function (item, index) {
const text = getMemoryText(item) || JSON.stringify(item, null, 2);
const kind = getMemoryKind(item);
const id = getMemoryId(item);

    return `
        <article class="nova-memory-card" data-memory-index="${index}">
            <div class="nova-memory-card-top">
                <div class="nova-memory-pill-row">
                    <span class="nova-memory-pill">${esc(labelForKind(kind))}</span>
                    ${id ? "<span class='nova-memory-pill'>ID</span>" : ""}
                </div>
            </div>

            <div class="nova-memory-card-text">${esc(text)}</div>

            <div class="nova-memory-card-actions">
                <button class="nova-memory-card-action danger" type="button" data-action="delete" data-index="${index}">Delete</button>
            </div>
        </article>
    `;
}).join("");


        list.querySelectorAll("[data-action]").forEach(function (button) {
            button.addEventListener("click", function () {
                const index = Number(button.dataset.index || "-1");
                const item = visible[index];

                if (!item) return;

if (button.dataset.action === "delete") {
    deleteMemory(item);
}
            });
        });
    }

    function bootMemoryControlCenter() {
        ensureMemoryControlUI();
        loadMemoryControlData();
    }

window.NovaLegacyMemoryControlCenter = bootMemoryControlCenter;

// NOVA_LEGACY_MEMORY_CONTROL_CENTER_AUTOBOOT_DISABLED

/*
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootMemoryControlCenter);
} else {
    bootMemoryControlCenter();
}

setTimeout(bootMemoryControlCenter, 400);
setTimeout(bootMemoryControlCenter, 1200);
*/
})();
