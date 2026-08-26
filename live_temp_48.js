
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
