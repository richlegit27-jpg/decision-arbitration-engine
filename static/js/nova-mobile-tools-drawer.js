(function () {
    "use strict";

    const MOBILE_MAX_WIDTH = 760;

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function isMobile() {
        return window.innerWidth <= MOBILE_MAX_WIDTH;
    }

    function createEl(tag, className, text) {
        const el = document.createElement(tag);

        if (className) {
            el.className = className;
        }

        if (text) {
            el.textContent = text;
        }

        return el;
    }

    function log() {
        try {
            console.log.apply(console, ["[NovaMobileTools]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function ensureStyles() {
        if (qs("#nova-mobile-tools-style")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "nova-mobile-tools-style";
        style.textContent = `
@media (max-width: 760px) {
    .nova-mobile-endgame-actions {
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    }

    .nova-mobile-tools-toggle {
        min-height: 42px;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 999px;
        background:
            linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.14),
                rgba(255, 255, 255, 0.07)
            );
        color: inherit;
        font-weight: 800;
        letter-spacing: 0.01em;
        cursor: pointer;
        box-shadow:
            0 10px 24px rgba(0, 0, 0, 0.22),
            inset 0 1px 0 rgba(255, 255, 255, 0.12);
        -webkit-tap-highlight-color: transparent;
    }

    .nova-mobile-tools-toggle:active {
        transform: scale(0.97);
    }

    .nova-mobile-tools-backdrop {
        position: fixed;
        inset: 0;
        z-index: 130;
        display: none;
        background: rgba(0, 0, 0, 0.48);
        backdrop-filter: blur(6px);
    }

    .nova-mobile-tools-backdrop.is-open {
        display: block;
    }

    .nova-mobile-tools-drawer {
        position: fixed;
        left: 10px;
        right: 10px;
        bottom: 10px;
        z-index: 140;
        display: none;
        max-height: 78vh;
        overflow-y: auto;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 26px;
        background:
            linear-gradient(
                180deg,
                rgba(18, 21, 34, 0.98),
                rgba(8, 10, 18, 0.98)
            );
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.55);
        padding: 14px;
        color: inherit;
    }

    .nova-mobile-tools-drawer.is-open {
        display: block;
    }

    .nova-mobile-tools-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 4px 4px 12px;
    }

    .nova-mobile-tools-title {
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 0.01em;
    }

    .nova-mobile-tools-close {
        width: 34px;
        height: 34px;
        border: 0;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.10);
        color: inherit;
        font-size: 20px;
        cursor: pointer;
    }

    .nova-mobile-tools-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
    }

    .nova-mobile-tool-btn {
        min-height: 76px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.075);
        color: inherit;
        text-align: left;
        padding: 12px;
        cursor: pointer;
    }

    .nova-mobile-tool-btn:active {
        transform: scale(0.98);
    }

    .nova-mobile-tool-label {
        display: block;
        font-size: 14px;
        font-weight: 900;
        margin-bottom: 5px;
    }

    .nova-mobile-tool-desc {
        display: block;
        font-size: 12px;
        opacity: 0.68;
        line-height: 1.35;
    }

    .nova-mobile-tools-status {
        min-height: 18px;
        padding: 10px 4px 0;
        font-size: 12px;
        opacity: 0.72;
    }

    .nova-mobile-tools-panel {
        margin-top: 12px;
    }

    .nova-mobile-panel-card {
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.075);
        padding: 12px;
    }

    .nova-mobile-panel-title {
        font-size: 14px;
        font-weight: 900;
        margin-bottom: 8px;
    }

    .nova-mobile-panel-body {
        font-size: 12px;
        opacity: 0.78;
        line-height: 1.45;
        white-space: pre-wrap;
    }

.nova-mobile-session-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.nova-mobile-session-btn {
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.07);
    color: inherit;
    padding: 10px;
    text-align: left;
    cursor: pointer;
}

.nova-mobile-session-btn:active {
    transform: scale(0.98);
}

.nova-mobile-session-title {
    display: block;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 4px;
}

.nova-mobile-session-meta {
    display: block;
    font-size: 11px;
    opacity: 0.62;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

}
        `.trim();

        document.head.appendChild(style);
    }

    function clickIfExists(selectors) {
        for (const selector of selectors) {
            const el = qs(selector);

            if (el) {
                el.click();
                return true;
            }
        }

        return false;
    }

    function setStatus(text) {
        const status = qs("#nova-mobile-tools-status");

        if (status) {
            status.textContent = text || "";
        }
    }

    function ensurePanelArea() {
        let area = qs("#nova-mobile-tools-panel");

        if (area) {
            return area;
        }

        const drawer = qs("#nova-mobile-tools-drawer");

        area = createEl("div", "nova-mobile-tools-panel", "");
        area.id = "nova-mobile-tools-panel";

        if (drawer) {
            drawer.appendChild(area);
        }

        return area;
    }

function renderPanel(title, bodyText) {
    const area = ensurePanelArea();

    area.innerHTML = "";

    const panel = createEl("div", "nova-mobile-panel-card", "");
    const panelTitle = createEl("div", "nova-mobile-panel-title", title);
    const panelBody = createEl("div", "nova-mobile-panel-body", bodyText);

    panel.appendChild(panelTitle);
    panel.appendChild(panelBody);
    area.appendChild(panel);

    try {
        area.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    } catch (_) {}
}

function renderSessionList(sessions) {
    const area = ensurePanelArea();

    area.innerHTML = "";

    const panel = createEl("div", "nova-mobile-panel-card", "");
    const panelTitle = createEl("div", "nova-mobile-panel-title", "Sessions");
    const list = createEl("div", "nova-mobile-session-list", "");

    sessions.slice(0, 10).forEach(function (session) {
        const id =
            session.id ||
            session.session_id ||
            session.key ||
            "";

        const title =
            session.title ||
            session.name ||
            session.label ||
            id ||
            "Untitled session";

        const updated =
            session.updated_at ||
            session.modified_at ||
            session.created_at ||
            "";

        const btn = createEl("button", "nova-mobile-session-btn", "");
        const label = createEl("span", "nova-mobile-session-title", title);
        const meta = createEl("span", "nova-mobile-session-meta", updated || id);

        btn.type = "button";
        btn.setAttribute("data-mobile-session-id", id);

        btn.appendChild(label);
        btn.appendChild(meta);

        btn.addEventListener("click", function () {
            if (!id) {
                setStatus("Session has no id.");
                return;
            }

            try {
                localStorage.setItem("nova_active_session_id", id);
                window.__novaActiveSessionId = id;
                window.activeSessionId = id;
                window.sessionId = id;
            } catch (_) {}

            setStatus("Session selected: " + title);

            if (typeof window.loadSession === "function") {
                window.loadSession(id);
                return;
            }

            if (typeof window.selectSession === "function") {
                window.selectSession(id);
                return;
            }

            if (
                window.NovaSessionRail &&
                typeof window.NovaSessionRail.selectSession === "function"
            ) {
                window.NovaSessionRail.selectSession(id);
                return;
            }

            renderPanel(
                "Sessions",
                "Selected session:\n" + title + "\n\nRefresh or send a message to continue in this session."
            );
        });

        list.appendChild(btn);
    });

    panel.appendChild(panelTitle);
    panel.appendChild(list);
    area.appendChild(panel);
}

    function openDrawer() {
        const backdrop = qs("#nova-mobile-tools-backdrop");
        const drawer = qs("#nova-mobile-tools-drawer");

        if (backdrop) {
            backdrop.classList.add("is-open");
        }

        if (drawer) {
            drawer.classList.add("is-open");
        }
    }

function renderArtifactList(artifacts) {
    const area = ensurePanelArea();

    area.innerHTML = "";

    const panel = createEl("div", "nova-mobile-panel-card", "");
    const panelTitle = createEl("div", "nova-mobile-panel-title", "Artifacts");
    const list = createEl("div", "nova-mobile-session-list", "");

    artifacts.slice(0, 10).forEach(function (artifact) {
        const title =
            artifact.title ||
            artifact.name ||
            artifact.filename ||
            artifact.id ||
            "Untitled artifact";

        const type =
            artifact.type ||
            artifact.kind ||
            artifact.mime_type ||
            "artifact";

        const url =
            artifact.image_url ||
            artifact.preview ||
            artifact.url ||
            artifact.path ||
            artifact.file_url ||
            "";

        const btn = createEl("button", "nova-mobile-session-btn", "");
        const label = createEl("span", "nova-mobile-session-title", title);
        const meta = createEl("span", "nova-mobile-session-meta", type + (url ? " • tap to open" : ""));

        btn.type = "button";

        btn.appendChild(label);
        btn.appendChild(meta);

        btn.addEventListener("click", function () {
            if (url) {
                window.open(url, "_blank");
                return;
            }

            renderPanel(
                "Artifact",
                "Title: " + title + "\nType: " + type + "\n\nNo openable URL found."
            );
        });

        list.appendChild(btn);
    });

    panel.appendChild(panelTitle);
    panel.appendChild(list);
    area.appendChild(panel);

    try {
        area.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    } catch (_) {}
}

    function closeDrawer() {
        const backdrop = qs("#nova-mobile-tools-backdrop");
        const drawer = qs("#nova-mobile-tools-drawer");

        if (backdrop) {
            backdrop.classList.remove("is-open");
        }

        if (drawer) {
            drawer.classList.remove("is-open");
        }
    }

    function runTool(action) {
if (action === "sessions") {
    renderPanel("Sessions", "Loading sessions...");
    setStatus("Loading sessions...");

    fetch("/api/sessions")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Sessions request failed: " + response.status);
            }

            return response.json();
        })
        .then(function (data) {
            const sessions =
                data.sessions ||
                data.items ||
                data.results ||
                [];

            if (!Array.isArray(sessions) || sessions.length === 0) {
                renderPanel(
                    "Sessions",
                    "No sessions found yet."
                );

                setStatus("No sessions found.");
                return;
            }

            const recent = sessions.slice(0, 8);

            const lines = recent.map(function (session, index) {
                const title =
                    session.title ||
                    session.name ||
                    session.label ||
                    session.id ||
                    "Untitled session";

                const updated =
                    session.updated_at ||
                    session.modified_at ||
                    session.created_at ||
                    "";

                return String(index + 1) + ". " + title + (updated ? "\n   " + updated : "");
            });

renderSessionList(recent);

            setStatus("Sessions loaded.");
        })
        .catch(function (error) {
            console.error("[NovaMobileTools] sessions failed", error);

            renderPanel(
                "Sessions",
                "Sessions failed to load.\n\nCheck /api/sessions."
            );

            setStatus("Sessions failed.");
        });

    return;
}

if (action === "memory") {
    renderPanel("Memory", "Loading memory...");

    setStatus("Loading memory...");

    fetch("/api/runtime/summary")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Memory request failed: " + response.status);
            }

            return response.json();
        })
        .then(function (data) {
            const runtime =
                data.runtime ||
                data.summary ||
                data ||
                {};

            const memory =
                runtime.memory ||
                runtime.memory_context ||
                runtime.relevant_memory ||
                data.memory ||
                data.memory_context ||
                data.relevant_memory ||
                [];

            if (Array.isArray(memory) && memory.length > 0) {
                const recent = memory.slice(0, 8);

                const lines = recent.map(function (item, index) {
                    if (typeof item === "string") {
                        return String(index + 1) + ". " + item;
                    }

                    const title =
                        item.title ||
                        item.label ||
                        item.key ||
                        "Memory " + String(index + 1);

                    const text =
                        item.summary ||
                        item.text ||
                        item.value ||
                        item.content ||
                        "";

                    return String(index + 1) + ". " + title + (text ? "\n   " + text : "");
                });

                renderPanel("Memory", lines.join("\n\n"));
                setStatus("Memory loaded.");
                return;
            }

            const health =
                runtime.runtime_health ||
                runtime.health ||
                data.runtime_health ||
                data.health ||
                "unknown";

            const signal =
                runtime.runtime_signal ||
                runtime.signal ||
                data.runtime_signal ||
                data.signal ||
                "none";

            renderPanel(
                "Memory",
                "No direct memory list found yet.\n\nRuntime memory bridge is reachable.\n\nHealth: " + health +
                    "\nSignal: " + signal +
                    "\n\nNext backend step can expose a clean /api/memory route."
            );

            setStatus("Memory bridge checked.");
        })
        .catch(function (error) {
            console.error("[NovaMobileTools] memory failed", error);

            renderPanel(
                "Memory",
                "Memory failed to load.\n\nChecked /api/runtime/summary.\n\nNext backend step: expose /api/memory or /api/runtime/memory."
            );

            setStatus("Memory failed.");
        });

    return;
}

if (action === "artifacts") {
    renderPanel("Artifacts", "Loading artifacts...");

    setStatus("Loading artifacts...");

    fetch("/api/artifacts")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Artifacts request failed: " + response.status);
            }

            return response.json();
        })
        .then(function (data) {
            const artifacts =
                data.artifacts ||
                data.items ||
                data.results ||
                [];

            if (!Array.isArray(artifacts) || artifacts.length === 0) {
                renderPanel(
                    "Artifacts",
                    "No artifacts found yet."
                );

                setStatus("No artifacts found.");
                return;
            }

            const recent = artifacts.slice(0, 8);

            const lines = recent.map(function (artifact, index) {
                const title =
                    artifact.title ||
                    artifact.name ||
                    artifact.filename ||
                    artifact.id ||
                    "Untitled artifact";

                const type =
                    artifact.type ||
                    artifact.kind ||
                    artifact.mime_type ||
                    "artifact";

                const url =
                    artifact.url ||
                    artifact.path ||
                    artifact.file_url ||
                    "";

                return String(index + 1) + ". " + title +
                    "\n   Type: " + type +
                    (url ? "\n   " + url : "");
            });

renderArtifactList(recent);

            setStatus("Artifacts loaded.");
        })
        .catch(function (error) {
            console.error("[NovaMobileTools] artifacts failed", error);

            renderPanel(
                "Artifacts",
                "Artifacts failed to load.\n\nCheck /api/artifacts."
            );

            setStatus("Artifacts failed.");
        });

    return;
}

if (action === "execution") {
    renderPanel("Execution", "Loading execution state...");

    setStatus("Loading execution...");

    fetch("/api/runtime/summary")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Execution request failed: " + response.status);
            }

            return response.json();
        })
        .then(function (data) {
            const runtime =
                data.runtime ||
                data.summary ||
                data ||
                {};

            const execution =
                runtime.execution_state ||
                runtime.execution ||
                runtime.current_execution ||
                data.execution_state ||
                data.execution ||
                data.current_execution ||
                {};

            const status =
                execution.status ||
                execution.state ||
                runtime.execution_status ||
                data.execution_status ||
                "unknown";

            const currentStep =
                execution.current_step ||
                execution.current_task ||
                execution.active_step ||
                execution.title ||
                runtime.current_step ||
                data.current_step ||
                "none";

            const nextMove =
                execution.next_move ||
                execution.next_step ||
                execution.next ||
                runtime.next_move ||
                data.next_move ||
                "none";

            const blocker =
                execution.blocker ||
                execution.current_blocker ||
                execution.error ||
                runtime.blocker ||
                data.blocker ||
                "none";

            renderPanel(
                "Execution",
                "Status: " + status +
                    "\nCurrent: " + currentStep +
                    "\nNext: " + nextMove +
                    "\nBlocker: " + blocker +
                    "\n\nMobile execution is compact view only for now."
            );

            setStatus("Execution status loaded.");
        })
        .catch(function (error) {
            console.error("[NovaMobileTools] execution failed", error);

            renderPanel(
                "Execution",
                "Execution state failed to load.\n\nChecked /api/runtime/summary.\n\nNext backend step: expose a clean /api/execution/state route."
            );

            setStatus("Execution failed.");
        });

    return;
}
        if (action === "runtime") {
            renderPanel("Runtime", "Loading runtime status...");
            setStatus("Loading runtime...");

            fetch("/api/runtime/summary")
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("Runtime request failed: " + response.status);
                    }

                    return response.json();
                })
                .then(function (data) {
                    const runtime =
                        data.runtime ||
                        data.summary ||
                        data ||
                        {};

                    const health =
                        runtime.runtime_health ||
                        runtime.health ||
                        data.runtime_health ||
                        data.health ||
                        "unknown";

                    const signal =
                        runtime.runtime_signal ||
                        runtime.signal ||
                        data.runtime_signal ||
                        data.signal ||
                        "none";

                    const route =
                        runtime.route ||
                        runtime.current_route ||
                        data.route ||
                        data.current_route ||
                        "unknown";

                    const cycle =
                        runtime.cycle_count ||
                        data.cycle_count ||
                        "unknown";

                    renderPanel(
                        "Runtime",
                        "Health: " + health +
                            "\nSignal: " + signal +
                            "\nRoute: " + route +
                            "\nCycle: " + cycle
                    );

                    setStatus("Runtime status loaded.");
                })
                .catch(function (error) {
                    console.error("[NovaMobileTools] runtime failed", error);

                    renderPanel(
                        "Runtime",
                        "Runtime status failed to load.\n\nCheck /api/runtime/summary."
                    );

                    setStatus("Runtime failed.");
                });

            return;
        }
    }

    function makeTool(action, label, desc) {
        const btn = createEl("button", "nova-mobile-tool-btn", "");
        const labelEl = createEl("span", "nova-mobile-tool-label", label);
        const descEl = createEl("span", "nova-mobile-tool-desc", desc);

        btn.type = "button";
        btn.setAttribute("data-mobile-tool", action);

        btn.appendChild(labelEl);
        btn.appendChild(descEl);

        btn.addEventListener("click", function () {
            runTool(action);
        });

        return btn;
    }

    function ensureToggle() {
        let toggle = qs("#nova-mobile-tools-toggle");

        if (toggle) {
            return toggle;
        }

        toggle = createEl("button", "nova-mobile-tools-toggle", "Tools");
        toggle.id = "nova-mobile-tools-toggle";
        toggle.type = "button";

        const actionRow = qs(".nova-mobile-endgame-actions");

        if (actionRow) {
            actionRow.appendChild(toggle);
        } else {
            document.body.appendChild(toggle);
        }

        toggle.addEventListener("click", openDrawer);

        return toggle;
    }

    function ensureDrawer() {
        if (qs("#nova-mobile-tools-drawer")) {
            ensureToggle();
            return;
        }

        const backdrop = createEl("div", "nova-mobile-tools-backdrop", "");
        backdrop.id = "nova-mobile-tools-backdrop";

        const drawer = createEl("div", "nova-mobile-tools-drawer", "");
        drawer.id = "nova-mobile-tools-drawer";

        const header = createEl("div", "nova-mobile-tools-header", "");
        const title = createEl("div", "nova-mobile-tools-title", "Nova Tools");
        const close = createEl("button", "nova-mobile-tools-close", "×");

        close.type = "button";

        const grid = createEl("div", "nova-mobile-tools-grid", "");

        grid.appendChild(makeTool("sessions", "Sessions", "Open saved chats."));
        grid.appendChild(makeTool("memory", "Memory", "View saved context."));
        grid.appendChild(makeTool("artifacts", "Artifacts", "Open saved outputs."));
        grid.appendChild(makeTool("execution", "Execution", "Quick actions."));
        grid.appendChild(makeTool("runtime", "Runtime", "Check Nova status."));

        const status = createEl("div", "nova-mobile-tools-status", "");
        status.id = "nova-mobile-tools-status";

        header.appendChild(title);
        header.appendChild(close);

        drawer.appendChild(header);
        drawer.appendChild(grid);
        drawer.appendChild(status);

        document.body.appendChild(backdrop);
        document.body.appendChild(drawer);

        ensureToggle();

        close.addEventListener("click", closeDrawer);
        backdrop.addEventListener("click", closeDrawer);

        log("tools drawer ready");
    }

    function boot() {
        if (!isMobile()) {
            return;
        }

        ensureStyles();
        ensureDrawer();
    }

    document.addEventListener("DOMContentLoaded", boot);
    window.addEventListener("resize", boot);

    setTimeout(boot, 250);
    setTimeout(boot, 1000);
})();