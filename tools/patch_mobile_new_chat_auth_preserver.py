from pathlib import Path

marker = "NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702"

targets = [
    Path("static/js/mobile/nova-mobile-sessions.js"),
    Path("static/js/nova-mobile-app.js"),
]

patch = r'''

/* ============================================================
 * NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702
 * Prevent New Chat from wiping login/auth state.
 * Keeps auth-ish localStorage/sessionStorage keys during new-chat flow
 * and forces /api requests to include credentials.
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var protectUntil = 0;
    var AUTH_KEY_RE = /(auth|login|token|jwt|user|username|email|owner|account|profile|nova_auth|nova_user|nova_owner|local_auth)/i;

    function now() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    function isProtectedNow() {
        return now() < protectUntil;
    }

    function beginProtection(reason) {
        protectUntil = now() + 15000;

        try {
            window.__novaLastAuthProtectReason = reason || "unknown";
        } catch (e) {}
    }

    function safeStores() {
        var stores = [];

        try {
            if (window.localStorage) {
                stores.push(window.localStorage);
            }
        } catch (e) {}

        try {
            if (window.sessionStorage) {
                stores.push(window.sessionStorage);
            }
        } catch (e) {}

        return stores;
    }

    function snapshotAuth() {
        var snap = [];

        safeStores().forEach(function (store, storeIndex) {
            try {
                for (var i = 0; i < store.length; i += 1) {
                    var key = store.key(i);

                    if (!key || !AUTH_KEY_RE.test(String(key))) {
                        continue;
                    }

                    var value = store.getItem(key);

                    if (value !== null && value !== undefined && String(value) !== "") {
                        snap.push({
                            storeIndex: storeIndex,
                            key: key,
                            value: value
                        });
                    }
                }
            } catch (e) {}
        });

        return snap;
    }

    function restoreAuth(snap) {
        if (!snap || !snap.length) {
            return;
        }

        var stores = safeStores();

        snap.forEach(function (item) {
            try {
                var store = stores[item.storeIndex];

                if (!store || !item || !item.key) {
                    return;
                }

                var current = store.getItem(item.key);

                if (current === null || current === undefined || String(current) === "") {
                    store.setItem(item.key, item.value);
                }
            } catch (e) {}
        });
    }

    var lastSnapshot = snapshotAuth();

    function refreshSnapshot() {
        var snap = snapshotAuth();

        if (snap && snap.length) {
            lastSnapshot = snap;
        }

        return lastSnapshot;
    }

    function looksLikeNewChatTarget(target) {
        try {
            var node = target;

            for (var depth = 0; node && depth < 6; depth += 1) {
                var text = String(node.textContent || "").toLowerCase();
                var id = String(node.id || "").toLowerCase();
                var cls = String(node.className || "").toLowerCase();
                var aria = String(node.getAttribute && node.getAttribute("aria-label") || "").toLowerCase();
                var title = String(node.getAttribute && node.getAttribute("title") || "").toLowerCase();

                var joined = [text, id, cls, aria, title].join(" ");

                if (
                    joined.indexOf("new chat") !== -1 ||
                    joined.indexOf("new-chat") !== -1 ||
                    joined.indexOf("new_session") !== -1 ||
                    joined.indexOf("new-session") !== -1 ||
                    joined.indexOf("create session") !== -1
                ) {
                    return true;
                }

                node = node.parentElement;
            }
        } catch (e) {}

        return false;
    }

    try {
        document.addEventListener("pointerdown", function (event) {
            if (looksLikeNewChatTarget(event.target)) {
                refreshSnapshot();
                beginProtection("new-chat-pointerdown");
            }
        }, true);

        document.addEventListener("click", function (event) {
            if (looksLikeNewChatTarget(event.target)) {
                var snap = refreshSnapshot();
                beginProtection("new-chat-click");

                setTimeout(function () {
                    restoreAuth(snap);
                }, 0);

                setTimeout(function () {
                    restoreAuth(snap);
                }, 300);

                setTimeout(function () {
                    restoreAuth(snap);
                }, 1200);
            }
        }, true);
    } catch (e) {}

    safeStores().forEach(function (store) {
        try {
            var originalClear = store.clear.bind(store);
            var originalRemoveItem = store.removeItem.bind(store);

            store.clear = function () {
                var snap = refreshSnapshot();

                originalClear();

                if (isProtectedNow()) {
                    restoreAuth(snap);
                }
            };

            store.removeItem = function (key) {
                if (isProtectedNow() && key && AUTH_KEY_RE.test(String(key))) {
                    return;
                }

                return originalRemoveItem(key);
            };
        } catch (e) {}
    });

    try {
        var originalFetch = window.fetch;

        if (typeof originalFetch === "function") {
            window.fetch = function (input, init) {
                var url = "";

                try {
                    url = typeof input === "string" ? input : String(input && input.url || "");
                } catch (e) {
                    url = "";
                }

                var isApi = url.indexOf("/api/") === 0 || url.indexOf(window.location.origin + "/api/") === 0;
                var isNewSession = url.indexOf("/api/sessions") !== -1 || url.indexOf("/api/chat") !== -1;

                if (isApi) {
                    init = init || {};
                    init.credentials = init.credentials || "include";

                    if (isNewSession) {
                        refreshSnapshot();
                        beginProtection("api-session-or-chat");
                    }
                }

                return originalFetch(input, init).then(function (response) {
                    if (isNewSession) {
                        var snap = lastSnapshot;

                        setTimeout(function () {
                            restoreAuth(snap);
                        }, 0);

                        setTimeout(function () {
                            restoreAuth(snap);
                        }, 500);
                    }

                    return response;
                });
            };
        }
    } catch (e) {}

    try {
        window.addEventListener("pageshow", function () {
            restoreAuth(lastSnapshot);
            refreshSnapshot();
        });

        window.addEventListener("load", function () {
            restoreAuth(lastSnapshot);
            refreshSnapshot();
        });
    } catch (e) {}

    try {
        console.log("[NOVA_MOBILE_NEW_CHAT_AUTH_PRESERVER_20260702] active");
    } catch (e) {}
})();
'''

patched = []

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    if marker in text:
        print(f"already installed in {path}")
        continue

    text = text.rstrip() + "\n" + patch + "\n"
    path.write_text(text, encoding="utf-8")
    patched.append(str(path))

if not patched:
    raise SystemExit("no target mobile JS file patched")

print("patched new chat auth preserver:")
for item in patched:
    print("-", item)
