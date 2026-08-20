
(function () {
    "use strict";

    if (window.__NOVA_MEMORY_CONTROL_CENTER_V2_20260622__) return;
    window.__NOVA_MEMORY_CONTROL_CENTER_V2_20260622__ = true;

    let items = [];
    let activeFilter = "all";
    let searchText = "";
    let editId = "";
    let editOriginal = null;

    function esc(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function textOf(item) {
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

    function idOf(item) {
        return String(item.id || item.memory_id || item.uuid || item.key || "");
    }

    function pinnedOf(item) {
        return Boolean(item.pinned || item.pin || item.is_pinned);
    }

    function kindOf(item) {
        const raw = String(item.kind || item.type || item.category || item.source || "").toLowerCase();
        const text = textOf(item).toLowerCase();

        if (raw.includes("preference") || raw === "pref") return "preference";
        if (raw.includes("project")) return "project";
        if (raw.includes("people") || raw.includes("person")) return "people";

        if (text.includes("prefer") || text.includes("favorite") || text.includes("from now on")) return "preference";
        if (text.includes("nova") || text.includes("project") || text.includes("phase")) return "project";
        if (text.includes("richard") || text.includes("my name")) return "people";

        return "general";
    }

    function labelForKind(kind) {
        if (kind === "preference") return "Preference";
        if (kind === "project") return "Project";
        if (kind === "people") return "People";
        return "General";
    }

    function normalize(data) {
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

    function status(text) {
        const el = document.getElementById("novaMemoryV2Status");
        if (el) el.textContent = text || "";
    }

    async function postJson(url, payload) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload || {})
        });

        let data = null;
        try { data = await res.json(); } catch (_) {}

        if (!res.ok || (data && data.ok === false)) {
            throw new Error(url + " failed");
        }

        return data;
    }

    function cleanupOldMemoryUi(list) {
        document.querySelectorAll(".nova-memory-control, #novaMemoryComposeBox").forEach(function (node) {
            if (list && node.contains(list)) {
                node.parentNode.insertBefore(list, node);
            }
            node.remove();
        });
    }

    function ensureUi() {
        const memory = document.querySelector(".memory-section");
        const list = document.getElementById("desktopMemoryList");

        if (!memory || !list) return null;

        cleanupOldMemoryUi(list);

        let shell = document.getElementById("novaMemoryV2");
        if (shell) return shell;

        shell = document.createElement("div");
        shell.id = "novaMemoryV2";
        shell.className = "nova-memory-v2";

shell.innerHTML = `
    <div class="nova-memory-v2-compose">
        <textarea id="novaMemoryV2Input" placeholder="Type what you want Nova to remember..."></textarea>

        <div class="nova-memory-v2-row">
            <select id="novaMemoryV2Kind">
                <option value="preference">Preference</option>
                <option value="project">Project Note</option>
                <option value="people">People</option>
                <option value="general">General</option>
            </select>

            <button id="novaMemoryV2SaveBtn" class="nova-memory-v2-btn" type="button">Save</button>
        </div>

        <div id="novaMemoryV2Status">Ctrl+Enter saves too.</div>
    </div>
`;
        list.parentNode.insertBefore(shell, list);

        shell.appendChild(list);

const oldShell = memory.querySelector(".memory-card-shell");

if (oldShell && oldShell !== shell) {
    oldShell.style.display = "none";
}

const oldCompose = memory.querySelector("#novaMemoryComposeBox");

if (oldCompose) {
    oldCompose.remove();
}


        const input = document.getElementById("novaMemoryV2Input");
        const kind = document.getElementById("novaMemoryV2Kind");
        const save = document.getElementById("novaMemoryV2SaveBtn");
        const cancel = document.getElementById("novaMemoryV2CancelBtn");
        const search = document.getElementById("novaMemoryV2Search");

        save?.addEventListener("click", saveMemory);
        cancel?.addEventListener("click", clearEditMode);

        input?.addEventListener("keydown", function (event) {
            if (event.ctrlKey && event.key === "Enter") {
                event.preventDefault();
                saveMemory();
            }
        });

        search?.addEventListener("input", function () {
            searchText = search.value || "";
            render();
        });

shell.querySelectorAll("[data-filter]").forEach(function (button) {
    button.addEventListener("click", function () {

        activeFilter = button.dataset.filter || "all";

        shell.querySelectorAll("[data-filter]").forEach(function (b) {
            b.classList.toggle("active", b === button);
        });

        render();
    });
});

        return shell;
    }

    function clearEditMode() {
        editId = "";
        editOriginal = null;

        const input = document.getElementById("novaMemoryV2Input");
        const kind = document.getElementById("novaMemoryV2Kind");
        const save = document.getElementById("novaMemoryV2SaveBtn");
        const cancel = document.getElementById("novaMemoryV2CancelBtn");

        if (input) input.value = "";
        if (kind) kind.value = "preference";
        if (save) save.textContent = "Save";
        if (cancel) cancel.style.display = "none";

        status("Ctrl+Enter saves too.");
    }

    async function saveMemory() {
        const input = document.getElementById("novaMemoryV2Input");
        const kind = document.getElementById("novaMemoryV2Kind");
        const save = document.getElementById("novaMemoryV2SaveBtn");
        const cancel = document.getElementById("novaMemoryV2CancelBtn");

        const clean = String(input ? input.value : "").trim();
        const selectedKind = String(kind ? kind.value : "general").trim() || "general";

        if (!clean) {
            status("Type something first.");
            return;
        }

        const payload = {
            id: editId,
            memory_id: editId,
            text: clean,
            value: clean,
            memory: clean,
            note: clean,
            content: clean,
            kind: selectedKind,
            type: selectedKind,
            category: selectedKind
        };

        status(editId ? "Updating..." : "Saving...");

        try {
            if (editId) {
                await postJson("/api/memory/update", payload);
            } else {
                await postJson("/api/memory/add", payload);
            }

            clearEditMode();
            await load();
            status(editId ? "Updated." : "Saved.");
        } catch (error) {
            status(editId ? "Update failed." : "Save failed.");
        }
    }

    function startEdit(index) {
        const item = filteredItems()[index];
        if (!item) return;

        const id = idOf(item);
        if (!id) {
            status("This memory has no ID, so edit is unavailable.");
            return;
        }

        editId = id;
        editOriginal = item;

        const input = document.getElementById("novaMemoryV2Input");
        const kind = document.getElementById("novaMemoryV2Kind");
        const save = document.getElementById("novaMemoryV2SaveBtn");
        const cancel = document.getElementById("novaMemoryV2CancelBtn");

        if (input) {
            input.value = textOf(item);
            input.focus();
        }

        if (kind) kind.value = kindOf(item);
        if (save) save.textContent = "Update";
        if (cancel) cancel.style.display = "inline-block";

        status("Editing memory. Click Update or Cancel.");
    }

    async function togglePin(index) {
        const item = filteredItems()[index];
        if (!item) return;

        const id = idOf(item);

        if (!id) {
            status("This memory has no ID, so pin is unavailable.");
            return;
        }

        const pinned = !pinnedOf(item);

        try {
            status(pinned ? "Pinning..." : "Unpinning...");

            await postJson("/api/memory/pin", {
                id: id,
                memory_id: id,
                pinned: pinned,
                pin: pinned
            });

            await load();
            status(pinned ? "Pinned." : "Unpinned.");
        } catch (error) {
            status("Pin failed.");
        }
    }

    async function removeMemory(index) {
        const item = filteredItems()[index];
        if (!item) return;

        const id = idOf(item);

        if (!id) {
            status("This memory has no ID, so delete is unavailable.");
            return;
        }

        if (!confirm("Delete this memory?")) return;

        try {
            status("Deleting...");

            await postJson("/api/memory/delete", {
                id: id,
                memory_id: id
            });

            await load();
            status("Deleted.");
        } catch (error) {
            status("Delete failed.");
        }
    }

    async function load() {
        ensureUi();

        const list = document.getElementById("desktopMemoryList");
        const count = document.getElementById("desktopMemoryCount");

        if (list) list.innerHTML = "<div class='execution-note'>Loading memory...</div>";

        try {
            const res = await fetch("/api/memory", { cache: "no-store" });
            const data = await res.json();

            items = normalize(data);

            if (count) count.textContent = String(items.length);

            render();
        } catch (error) {
            if (list) list.innerHTML = "<div class='execution-note'>Memory failed to load.</div>";
            if (count) count.textContent = "error";
        }
    }

function filteredItems() {
    const q = String(searchText || "").trim().toLowerCase();

    return items.filter(function (item) {
        const kind = kindOf(item);
        const text = textOf(item);
        const haystack = (text + " " + kind + " " + JSON.stringify(item)).toLowerCase();

        if (activeFilter !== "all" && kind !== activeFilter) return false;
        if (q && !haystack.includes(q)) return false;

        return true;
    });
}

    function render() {
        const list = document.getElementById("desktopMemoryList");
        const count = document.getElementById("desktopMemoryCount");
        if (!list) return;

        const visible = filteredItems();

        if (count) {
            count.textContent = String(visible.length) + "/" + String(items.length);
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
                const action = button.dataset.action;

                if (action === "delete") {
                    removeMemory(index);
                }
            });
        });
    }

    function boot() {
        ensureUi();
        load();
    }

    window.NovaMemoryV2Boot = boot;
    window.NovaMemoryV2Load = load;
    window.loadDesktopMemory = load;
    window.NovaLoadDesktopMemory = load;
    window.NovaBootMemoryControlCenter = boot;

// NOVA_MEMORY_CONTROL_CENTER_LEGACY_BOOT_DISABLED

})();
