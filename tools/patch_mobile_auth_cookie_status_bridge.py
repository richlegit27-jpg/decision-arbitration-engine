from pathlib import Path

path = Path("static/js/nova-mobile-app.js")
text = path.read_text(encoding="utf-8")

marker = "NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702"

if marker in text:
    print("mobile auth cookie status bridge already installed")
    raise SystemExit(0)

patch = r'''

/* ============================================================
 * NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702
 * Mobile auth stabilizer:
 * - makes /api calls include cookies
 * - stores auth state from /api/auth/login/register/status
 * - protects auth localStorage/sessionStorage keys from broad clears
 * Does not touch backend auth, sessions, or account storage.
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var AUTH_KEYS = [
        "nova_auth_user",
        "nova_auth_authenticated",
        "nova_user_id",
        "nova_username",
        "nova_email",
        "user_id",
        "username",
        "auth_user",
        "authUser",
        "authenticated"
    ];

    function clean(value) {
        try {
            return String(value || "").trim();
        } catch (e) {
            return "";
        }
    }

    function safeSet(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (e) {}

        try {
            sessionStorage.setItem(key, value);
        } catch (e) {}
    }

    function safeGetLocal(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            return null;
        }
    }

    function persistAuthFromPayload(payload) {
        try {
            payload = payload || {};

            var user = payload.user || payload.current_user || null;
            var authenticated = payload.authenticated === true || !!user;

            if (!authenticated || !user) {
                return false;
            }

            var userId = clean(user.id || user.user_id || "");
            var username = clean(user.username || user.name || "");
            var email = clean(user.email || "");

            safeSet("nova_auth_authenticated", "true");
            safeSet("authenticated", "true");
            safeSet("nova_auth_user", JSON.stringify(user));

            if (userId) {
                safeSet("nova_user_id", userId);
                safeSet("user_id", userId);
            }

            if (username) {
                safeSet("nova_username", username);
                safeSet("username", username);
            }

            if (email) {
                safeSet("nova_email", email);
            }

            try {
                window.NOVA_AUTH_USER = user;
                window.NOVA_AUTHENTICATED = true;
                window.novaAuthUser = user;
                window.novaAuthenticated = true;
            } catch (e) {}

            try {
                window.dispatchEvent(new CustomEvent("nova:auth-ready", {
                    detail: {
                        authenticated: true,
                        user: user
                    }
                }));
            } catch (e) {}

            return true;
        } catch (e) {
            return false;
        }
    }

    function markLoggedOut() {
        try {
            window.NOVA_AUTHENTICATED = false;
            window.novaAuthenticated = false;
        } catch (e) {}

        safeSet("nova_auth_authenticated", "false");
        safeSet("authenticated", "false");
    }

    function protectStorage(storageName) {
        try {
            var storage = window[storageName];

            if (!storage || storage.__novaAuthProtected20260702) {
                return;
            }

            var originalClear = storage.clear;
            var originalRemoveItem = storage.removeItem;

            storage.clear = function () {
                var saved = {};

                AUTH_KEYS.forEach(function (key) {
                    try {
                        saved[key] = storage.getItem(key);
                    } catch (e) {}
                });

                var result = originalClear.apply(storage, arguments);

                Object.keys(saved).forEach(function (key) {
                    try {
                        if (saved[key] !== null && saved[key] !== undefined) {
                            storage.setItem(key, saved[key]);
                        }
                    } catch (e) {}
                });

                return result;
            };

            storage.removeItem = function (key) {
                key = clean(key);

                if (AUTH_KEYS.indexOf(key) !== -1) {
                    return undefined;
                }

                return originalRemoveItem.apply(storage, arguments);
            };

            storage.__novaAuthProtected20260702 = true;
        } catch (e) {}
    }

    protectStorage("localStorage");
    protectStorage("sessionStorage");

    function shouldIncludeCredentials(url) {
        url = clean(url);

        return (
            url.indexOf("/api/") !== -1 ||
            url.indexOf(location.origin + "/api/") === 0
        );
    }

    function maybeCaptureAuth(url, response) {
        try {
            url = clean(url);

            if (
                url.indexOf("/api/auth/status") === -1 &&
                url.indexOf("/api/auth/login") === -1 &&
                url.indexOf("/api/auth/register") === -1 &&
                url.indexOf("/api/login") === -1 &&
                url.indexOf("/api/register") === -1
            ) {
                return;
            }

            if (!response || !response.clone) {
                return;
            }

            response.clone().json().then(function (payload) {
                if (!persistAuthFromPayload(payload)) {
                    if (url.indexOf("/api/auth/status") !== -1 && payload && payload.authenticated === false) {
                        markLoggedOut();
                    }
                }
            }).catch(function () {});
        } catch (e) {}
    }

    try {
        var originalFetch = window.fetch;

        if (typeof originalFetch === "function" && !originalFetch.__novaAuthCookieBridge20260702) {
            var wrappedFetch = function (input, init) {
                var url = "";

                try {
                    url = typeof input === "string" ? input : clean(input && input.url);
                } catch (e) {
                    url = "";
                }

                init = init || {};

                if (shouldIncludeCredentials(url)) {
                    init = Object.assign({}, init, {
                        credentials: "include",
                        cache: init.cache || "no-store"
                    });
                }

                return originalFetch(input, init).then(function (response) {
                    maybeCaptureAuth(url, response);
                    return response;
                });
            };

            wrappedFetch.__novaAuthCookieBridge20260702 = true;
            window.fetch = wrappedFetch;
        }
    } catch (e) {}

    function refreshAuthStatus() {
        try {
            return fetch("/api/auth/status", {
                method: "GET",
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "application/json"
                }
            }).then(function (res) {
                if (!res || !res.ok) {
                    throw new Error("auth status failed " + (res && res.status));
                }

                return res.json();
            }).then(function (payload) {
                if (!persistAuthFromPayload(payload)) {
                    if (payload && payload.authenticated === false) {
                        markLoggedOut();
                    }
                }

                try {
                    console.log("[NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702] status", payload);
                } catch (e) {}

                return payload;
            }).catch(function (err) {
                try {
                    console.warn("[NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702] status failed", err);
                } catch (e) {}

                return null;
            });
        } catch (e) {
            return Promise.resolve(null);
        }
    }

    window.NovaMobileRefreshAuthStatus = refreshAuthStatus;

    setTimeout(refreshAuthStatus, 250);
    setTimeout(refreshAuthStatus, 1500);

    try {
        console.log("[NOVA_MOBILE_AUTH_COOKIE_STATUS_BRIDGE_20260702] active");
    } catch (e) {}
})();
'''

path.write_text(text.rstrip() + "\n" + patch + "\n", encoding="utf-8")
print("patched mobile auth cookie status bridge")
