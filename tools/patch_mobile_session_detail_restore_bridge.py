from pathlib import Path

path = Path("static/js/mobile/nova-mobile-sessions.js")
text = path.read_text(encoding="utf-8")

marker = "NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702"

if marker in text:
    print("session detail restore bridge already installed")
    raise SystemExit(0)

patch = r'''

/* ============================================================
 * NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702
 * Safe mobile session switching restore layer.
 * - On session click, fetches /api/sessions/<id>
 * - Confirms detail.id matches clicked id
 * - Stores active session id
 * - Renders restored messages if existing UI does not
 * Does not touch backend, auth, storage, or generation.
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function clean(value) {
        try {
            return String(value || "").trim();
        } catch (e) {
            return "";
        }
    }

    function isLikelySessionId(value) {
        value = clean(value);

        return !!(
            value &&
            value.length >= 6 &&
            (
                value.indexOf("session_") === 0 ||
                value.indexOf("mobile_") === 0 ||
                value.indexOf("volume_") === 0 ||
                value.indexOf("prod_") === 0 ||
                value.indexOf("text_") === 0 ||
                value.indexOf("session_restore_lock_") === 0 ||
                value.indexOf("session_switching_lock_") === 0
            )
        );
    }

    function saveActiveSessionId(sessionId) {
        try {
            window.NOVA_ACTIVE_SESSION_ID = sessionId;
            window.novaActiveSessionId = sessionId;
            window.activeSessionId = sessionId;
        } catch (e) {}

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("active_session_id", sessionId);
            localStorage.setItem("activeSessionId", sessionId);
        } catch (e) {}

        try {
            sessionStorage.setItem("nova_mobile_active_session_id", sessionId);
            sessionStorage.setItem("nova_active_session_id", sessionId);
        } catch (e) {}
    }

    function activeSessionIdFromStorage() {
        var keys = [
            "nova_mobile_active_session_id",
            "nova_active_session_id",
            "active_session_id",
            "activeSessionId"
        ];

        for (var i = 0; i < keys.length; i += 1) {
            try {
                var value = clean(localStorage.getItem(keys[i]));

                if (isLikelySessionId(value)) {
                    return value;
                }
            } catch (e) {}
        }

        return "";
    }

    function sessionIdFromElement(target) {
        try {
            var el = target;

            while (el && el !== document.body && el !== document.documentElement) {
                var candidates = [
                    el.getAttribute && el.getAttribute("data-session-id"),
                    el.getAttribute && el.getAttribute("data-session"),
                    el.getAttribute && el.getAttribute("data-id"),
                    el.dataset && el.dataset.sessionId,
                    el.dataset && el.dataset.session,
                    el.dataset && el.dataset.id,
                    el.id
                ];

                for (var i = 0; i < candidates.length; i += 1) {
                    var value = clean(candidates[i]);

                    if (isLikelySessionId(value)) {
                        return value;
                    }
                }

                el = el.parentElement;
            }
        } catch (e) {}

        return "";
    }

    function fetchSessionDetail(sessionId) {
        return fetch("/api/sessions/" + encodeURIComponent(sessionId), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        }).then(function (res) {
            if (!res || !res.ok) {
                throw new Error("session detail failed " + (res && res.status));
            }

            return res.json();
        }).then(function (data) {
            var session = data && data.session ? data.session : null;

            if (!session || session.id !== sessionId) {
                throw new Error("session detail mismatch");
            }

            return session;
        });
    }

    function findMessagesContainer() {
        var selectors = [
            "#messages",
            "#chatMessages",
            "#chat-messages",
            ".nova-chat-messages",
            ".chat-messages",
            ".messages",
            "[data-chat-messages]"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            try {
                var el = document.querySelector(selectors[i]);

                if (el) {
                    return el;
                }
            } catch (e) {}
        }

        return null;
    }

    function escapeText(value) {
        var div = document.createElement("div");
        div.textContent = clean(value);
        return div.innerHTML;
    }

    function attachmentImageUrl(attachment) {
        try {
            attachment = attachment || {};

            var url = clean(
                attachment.url ||
                attachment.file_url ||
                attachment.image_url ||
                attachment.preview ||
                ""
            );

            var mime = clean(attachment.mime_type || attachment.type || "").toLowerCase();

            if (
                url &&
                (
                    mime.indexOf("image/") === 0 ||
                    url.indexOf(".png") !== -1 ||
                    url.indexOf(".jpg") !== -1 ||
                    url.indexOf(".jpeg") !== -1 ||
                    url.indexOf(".webp") !== -1 ||
                    url.indexOf("/api/uploads/generated_") !== -1
                )
            ) {
                return url;
            }
        } catch (e) {}

        return "";
    }

    function fallbackRenderMessages(session) {
        try {
            var messages = Array.isArray(session.messages) ? session.messages : [];
            var container = findMessagesContainer();

            if (!container || !messages.length) {
                return false;
            }

            container.innerHTML = "";

            messages.forEach(function (msg) {
                msg = msg || {};

                var role = clean(msg.role || "assistant").toLowerCase();
                var body = clean(msg.text || msg.content || msg.message || "");
                var bubble = document.createElement("div");

                bubble.className = "nova-message nova-session-restored-message " + (
                    role === "user" ? "user" : "assistant"
                );

                var html = "";

                if (body) {
                    html += '<div class="nova-message-text">' + escapeText(body) + '</div>';
                }

                var attachments = Array.isArray(msg.attachments) ? msg.attachments : [];

                attachments.forEach(function (attachment) {
                    var imgUrl = attachmentImageUrl(attachment);

                    if (imgUrl) {
                        html += (
                            '<div class="nova-restored-image-wrap">' +
                            '<img alt="Restored image" loading="lazy" decoding="async" src="' +
                            escapeText(imgUrl) +
                            '">' +
                            '</div>'
                        );
                    }
                });

                if (!html) {
                    html = '<div class="nova-message-text"></div>';
                }

                bubble.innerHTML = html;
                container.appendChild(bubble);
            });

            try {
                container.scrollTop = container.scrollHeight;
            } catch (e) {}

            return true;
        } catch (e) {
            return false;
        }
    }

    function updateTitle(session) {
        var title = clean(session.title || "New Chat");

        var selectors = [
            "#session-title",
            "#active-session-title",
            ".session-title",
            ".active-session-title",
            "[data-active-session-title]"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            try {
                var el = document.querySelector(selectors[i]);

                if (el && title) {
                    el.textContent = title;
                }
            } catch (e) {}
        }
    }

    function renderSession(session) {
        try {
            saveActiveSessionId(session.id);
            updateTitle(session);

            var rendered = false;

            var renderers = [
                "NovaMobileRenderSessionMessages",
                "NovaMobileRenderMessages",
                "renderSessionMessages",
                "renderMessages"
            ];

            for (var i = 0; i < renderers.length; i += 1) {
                var fn = window[renderers[i]];

                if (typeof fn === "function") {
                    try {
                        fn(session.messages || [], session);
                        rendered = true;
                        break;
                    } catch (e) {}
                }
            }

            if (!rendered) {
                rendered = fallbackRenderMessages(session);
            }

            try {
                window.dispatchEvent(new CustomEvent("nova:session-restored", {
                    detail: {
                        session_id: session.id,
                        message_count: (session.messages || []).length,
                        fallback_rendered: rendered
                    }
                }));
            } catch (e) {}

            return rendered;
        } catch (e) {
            return false;
        }
    }

    function restoreSession(sessionId) {
        sessionId = clean(sessionId);

        if (!isLikelySessionId(sessionId)) {
            return Promise.resolve(false);
        }

        saveActiveSessionId(sessionId);

        return fetchSessionDetail(sessionId).then(function (session) {
            renderSession(session);

            try {
                console.log("[NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702] restored", sessionId);
            } catch (e) {}

            return true;
        }).catch(function (err) {
            try {
                console.warn("[NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702] restore failed", sessionId, err);
            } catch (e) {}

            return false;
        });
    }

    document.addEventListener("click", function (event) {
        var sessionId = sessionIdFromElement(event.target);

        if (!sessionId) {
            return;
        }

        setTimeout(function () {
            restoreSession(sessionId);
        }, 250);
    }, true);

    window.NovaMobileRestoreSessionDetail = restoreSession;

    setTimeout(function () {
        var active = activeSessionIdFromStorage();

        if (active) {
            restoreSession(active);
        }
    }, 1200);

    try {
        console.log("[NOVA_MOBILE_SESSION_DETAIL_RESTORE_BRIDGE_20260702] active");
    } catch (e) {}
})();
'''

path.write_text(text.rstrip() + "\n" + patch + "\n", encoding="utf-8")
print("patched mobile session detail restore bridge")
