(function () {
    "use strict";

    function loadMobileSessions() {
        try {
            return JSON.parse(
                localStorage.getItem(
                    "novaMobileSessions"
                ) || "[]"
            );
        } catch {
            return [];
        }
    }

    function saveMobileSessions(sessions) {
        localStorage.setItem(
            "novaMobileSessions",
            JSON.stringify(
                Array.isArray(sessions)
                    ? sessions
                    : []
            )
        );
    }

    function getSessionLabel() {
        return (
            "Session " +
            new Date().toLocaleTimeString()
        );
    }

    function createSessionObject(id, label) {
        return {
            id,
            label:
                label ||
                getSessionLabel(),
            createdAt: Date.now()
        };
    }

    function addSessionToStorage(session) {
        if (
            !session ||
            !session.id
        ) {
            return;
        }

        const sessions =
            loadMobileSessions();

        const exists =
            sessions.some(function (item) {
                return (
                    item.id === session.id
                );
            });

        if (exists) return;

        sessions.unshift(session);

        saveMobileSessions(
            sessions
        );
    }

    function removeSessionFromStorage(sessionId) {
        saveMobileSessions(
            loadMobileSessions().filter(
                function (session) {
                    return (
                        session.id !==
                        sessionId
                    );
                }
            )
        );
    }

    function renameSessionInStorage(
        sessionId,
        label
    ) {
        const sessions =
            loadMobileSessions().map(
                function (session) {
                    if (
                        session.id ===
                        sessionId
                    ) {
                        session.label =
                            label;
                    }

                    return session;
                }
            );

        saveMobileSessions(
            sessions
        );
    }

    function pinSessionInStorage(sessionId) {
        const sessions =
            loadMobileSessions();

        sessions.sort(function (a, b) {
            if (a.id === sessionId) {
                return -1;
            }

            if (b.id === sessionId) {
                return 1;
            }

            return 0;
        });

        saveMobileSessions(
            sessions
        );
    }

    
function restoreMobileSessionList() {
    const sessionsPanel =
        document.querySelector("#sessionsPanel") ||
        document.querySelector("#mobileSessionsPanel") ||
        document.querySelector("[data-mobile-sessions-panel]") ||
        document.querySelector(".mobile-sessions-panel");

    if (!sessionsPanel) return;

        sessionsPanel
            .querySelectorAll(
                ".mobile-session-row"
            )
            .forEach(function (row) {
                row.remove();
            });

        loadMobileSessions().forEach(
            function (session) {
                sessionsPanel.appendChild(
                    createMobileSessionItem(
                        session.label,
                        session.id
                    )
                );
            }
        );
    }

function switchMobileSession(
    sessionId,
    label
) {
    const sessionsPanel =
        document.querySelector("#sessionsPanel") ||
        document.querySelector("#mobileSessionsPanel") ||
        document.querySelector("[data-mobile-sessions-panel]") ||
        document.querySelector(".mobile-sessions-panel");
        if (!sessionId) return;

        window.__novaActiveSessionId =
            sessionId;

        localStorage.setItem(
            "novaMobileSessionId",
            sessionId
        );

        if (chatContainer) {
            chatContainer.innerHTML =
                "";
        }

        restoreCurrentMessages();

        closePanel(sessionsPanel);

        showToast(
            "Session switched."
        );
    }

    function createMobileSessionItem(
        label,
        sessionId
    ) {
        const wrapper =
            document.createElement(
                "div"
            );

        wrapper.dataset.sessionId =
            sessionId;

        wrapper.className =
            "mobile-session-row";

        const item =
            document.createElement(
                "button"
            );

        item.type = "button";

        item.className =
            "mobile-session-item";

        item.textContent =
            label ||
            "Untitled Session";

        item.addEventListener(
            "click",
            function () {
                switchMobileSession(
                    sessionId,
                    item.textContent
                );
            }
        );

        const actions =
            document.createElement(
                "div"
            );

        actions.className =
            "mobile-session-actions";

        function createActionButton(
            text,
            handler
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";

            button.className =
                "mobile-inline-action";

            button.textContent =
                text;

            button.addEventListener(
                "click",
                function (event) {
                    event.stopPropagation();
                    handler();
                }
            );

            return button;
        }

        const renameBtn =
            createActionButton(
                "Rename",
                function () {
                    const nextName =
                        prompt(
                            "Rename session",
                            item.textContent
                        );

                    if (
                        !nextName ||
                        !nextName.trim()
                    ) {
                        return;
                    }

                    item.textContent =
                        nextName.trim();

                    renameSessionInStorage(
                        sessionId,
                        nextName.trim()
                    );

                    showToast(
                        "Session renamed."
                    );
                }
            );

        const pinBtn =
            createActionButton(
                "Pin",
                function () {
                    wrapper.parentNode?.prepend(
                        wrapper
                    );

                    pinSessionInStorage(
                        sessionId
                    );

                    showToast(
                        "Session pinned."
                    );
                }
            );

        const deleteBtn =
            createActionButton(
                "Delete",
                function () {
                    if (
                        !confirm(
                            "Delete this session?"
                        )
                    ) {
                        return;
                    }

                    wrapper.style.opacity =
                        ".4";

                    setTimeout(
                        function () {
                            wrapper.remove();
                        },
                        160
                    );

                    removeSessionFromStorage(
                        sessionId
                    );

                    showToast(
                        "Session deleted."
                    );
                }
            );

        actions.appendChild(
            renameBtn
        );

        actions.appendChild(
            pinBtn
        );

        actions.appendChild(
            deleteBtn
        );

        wrapper.appendChild(item);
        wrapper.appendChild(actions);

        return wrapper;
    }

function createNewMobileSession() {

    const sessionsPanel =
        document.querySelector("#sessionsPanel") ||
        document.querySelector("#mobileSessionsPanel") ||
        document.querySelector("[data-mobile-sessions-panel]") ||
        document.querySelector(".mobile-sessions-panel");

        window.__novaActiveSessionId =
            "session_" +
            Date.now().toString(16);

        localStorage.setItem(
            "novaMobileSessionId",
            window.__novaActiveSessionId
        );

        if (chatContainer) {
            chatContainer.innerHTML =
                "";
        }

        if (inputEl) {
            inputEl.value = "";

            localStorage.removeItem(
                "novaMobileDraft"
            );

            autoGrowInput();
        }

        showToast(
            "New chat started."
        );

        const session =
            createSessionObject(
                window.__novaActiveSessionId,
                getSessionLabel()
            );

        addSessionToStorage(
            session
        );

        if (sessionsPanel) {
            sessionsPanel.prepend(
                createMobileSessionItem(
                    session.label,
                    session.id
                )
            );
        }
    }

    window.NovaMobileSessions = {
        loadMobileSessions,
        saveMobileSessions,
        getSessionLabel,
        createSessionObject,
        addSessionToStorage,
        removeSessionFromStorage,
        renameSessionInStorage,
        pinSessionInStorage,
        restoreMobileSessionList,
        switchMobileSession,
        createMobileSessionItem,
        createNewMobileSession
    };

})();