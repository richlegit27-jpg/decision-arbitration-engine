
(function () {
    "use strict";

    if (window.__NOVA_MEMORY_TYPED_INPUT_FINAL_20260622__) return;
    window.__NOVA_MEMORY_TYPED_INPUT_FINAL_20260622__ = true;

    function setMemoryStatus(text) {
        const status = document.getElementById("novaMemoryComposeStatus");
        if (status) status.textContent = text || "";
    }

    async function postTypedMemory(text, kind) {
        const clean = String(text || "").trim();
        const safeKind = String(kind || "general").trim() || "general";

        if (!clean) {
            setMemoryStatus("Type something first.");
            return;
        }

        setMemoryStatus("Saving...");

        const payload = {
            text: clean,
            value: clean,
            memory: clean,
            note: clean,
            content: clean,
            kind: safeKind,
            type: safeKind,
            category: safeKind
        };

        const res = await fetch("/api/memory/add", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        let data = null;

        try {
            data = await res.json();
        } catch (_) {}

        if (!res.ok || (data && data.ok === false)) {
            setMemoryStatus("Save failed.");
            return;
        }

        const input = document.getElementById("novaMemoryComposeInput");
        if (input) input.value = "";

        setMemoryStatus("Saved.");

        if (typeof window.loadDesktopMemory === "function") {
            window.loadDesktopMemory();
        } else if (typeof window.NovaLoadDesktopMemory === "function") {
            window.NovaLoadDesktopMemory();
        }

        setTimeout(function () {
            setMemoryStatus("Ctrl+Enter saves too.");
        }, 900);
    }

    function focusMemoryInput(kind) {
        const input = document.getElementById("novaMemoryComposeInput");
        const select = document.getElementById("novaMemoryComposeKind");

        if (select && kind) {
            select.value = kind;
        }

        if (input) {
            input.focus();
        }
    }

    function replacePromptButton(id, kind) {
        const oldButton = document.getElementById(id);
        if (!oldButton || oldButton.dataset.novaTypedMemoryReplaced === "true") return;

        const newButton = oldButton.cloneNode(true);
        newButton.dataset.novaTypedMemoryReplaced = "true";

        newButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            focusMemoryInput(kind);
        });

        oldButton.replaceWith(newButton);
    }

function ensureMemoryTypedInput() {
    const memory = document.querySelector(".memory-section");

    if (!memory) return;

    const oldBox = document.getElementById("novaMemoryComposeBox");

    if (oldBox) {
        oldBox.remove();
    }

    const oldPreferenceBtn = document.getElementById("novaMemoryAddPreferenceBtn");
    const oldProjectBtn = document.getElementById("novaMemoryAddProjectBtn");

    if (oldPreferenceBtn) {
        oldPreferenceBtn.remove();
    }

    if (oldProjectBtn) {
        oldProjectBtn.remove();
    }
}

window.NovaEnsureMemoryTypedInput = ensureMemoryTypedInput;
window.NovaSaveTypedMemory = postTypedMemory;

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureMemoryTypedInput);
} else {
    ensureMemoryTypedInput();
}

setTimeout(ensureMemoryTypedInput, 300);
setTimeout(ensureMemoryTypedInput, 900);
setTimeout(ensureMemoryTypedInput, 1600);
})();
