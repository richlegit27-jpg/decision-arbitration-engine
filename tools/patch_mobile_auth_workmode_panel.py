from pathlib import Path

path = Path("static/js/nova-mobile-app.js")
text = path.read_text(encoding="utf-8")

marker = "NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702"

if marker in text:
    print("mobile auth workmode panel already installed")
    raise SystemExit(0)

patch = r'''

/* ============================================================
 * NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702
 * Plain mobile auth panel:
 * - Shows a simple login/register panel when browser is logged out
 * - Uses credentials: include for auth API calls
 * - Hides itself when /api/auth/status is authenticated true
 * - Does not depend on existing pretty UI/auth widgets
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var PANEL_ID = "nova-auth-workmode-panel";
    var STATUS_ID = "nova-auth-workmode-status";

    function clean(value) {
        try {
            return String(value || "").trim();
        } catch (e) {
            return "";
        }
    }

    function api(path, options) {
        options = options || {};
        options.credentials = "include";
        options.cache = options.cache || "no-store";
        options.headers = Object.assign({
            "Accept": "application/json"
        }, options.headers || {});

        return fetch(path, options).then(function (res) {
            return res.text().then(function (text) {
                var payload = null;

                try {
                    payload = text ? JSON.parse(text) : null;
                } catch (e) {
                    payload = { raw: text };
                }

                if (!res.ok) {
                    var err = new Error("HTTP " + res.status);
                    err.status = res.status;
                    err.payload = payload;
                    throw err;
                }

                return payload;
            });
        });
    }

    function persistUser(payload) {
        try {
            payload = payload || {};
            var user = payload.user || null;

            if (!payload.authenticated || !user) {
                return false;
            }

            localStorage.setItem("nova_auth_authenticated", "true");
            localStorage.setItem("nova_auth_user", JSON.stringify(user));
            localStorage.setItem("nova_user_id", clean(user.id));
            localStorage.setItem("nova_username", clean(user.username));
            localStorage.setItem("nova_email", clean(user.email));

            sessionStorage.setItem("nova_auth_authenticated", "true");
            sessionStorage.setItem("nova_auth_user", JSON.stringify(user));

            window.NOVA_AUTHENTICATED = true;
            window.NOVA_AUTH_USER = user;
            window.novaAuthenticated = true;
            window.novaAuthUser = user;

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
            localStorage.setItem("nova_auth_authenticated", "false");
            sessionStorage.setItem("nova_auth_authenticated", "false");
            window.NOVA_AUTHENTICATED = false;
            window.novaAuthenticated = false;
        } catch (e) {}
    }

    function setStatus(message) {
        try {
            var node = document.getElementById(STATUS_ID);
            if (node) {
                node.textContent = message;
            }
        } catch (e) {}
    }

    function showPanel() {
        try {
            ensurePanel();
            var panel = document.getElementById(PANEL_ID);
            if (panel) {
                panel.style.display = "block";
            }
        } catch (e) {}
    }

    function hidePanel() {
        try {
            var panel = document.getElementById(PANEL_ID);
            if (panel) {
                panel.style.display = "none";
            }
        } catch (e) {}
    }

    function ensurePanel() {
        if (!document.body) {
            return null;
        }

        var existing = document.getElementById(PANEL_ID);
        if (existing) {
            return existing;
        }

        var panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.setAttribute("data-nova-auth-workmode", "true");

        panel.style.position = "fixed";
        panel.style.left = "10px";
        panel.style.right = "10px";
        panel.style.top = "10px";
        panel.style.zIndex = "999999";
        panel.style.padding = "10px";
        panel.style.borderRadius = "12px";
        panel.style.background = "rgba(20, 20, 28, 0.96)";
        panel.style.border = "1px solid rgba(255,255,255,0.22)";
        panel.style.boxShadow = "0 8px 32px rgba(0,0,0,0.35)";
        panel.style.color = "white";
        panel.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
        panel.style.fontSize = "14px";
        panel.style.display = "none";

        panel.innerHTML = [
            '<div style="font-weight:700;margin-bottom:6px;">Nova login</div>',
            '<div id="' + STATUS_ID + '" style="font-size:12px;opacity:.85;margin-bottom:8px;">Checking auth...</div>',
            '<input id="nova-auth-workmode-username" placeholder="username or email" autocomplete="username" style="box-sizing:border-box;width:100%;margin-bottom:6px;padding:9px;border-radius:9px;border:1px solid rgba(255,255,255,.25);background:#111;color:white;">',
            '<input id="nova-auth-workmode-password" placeholder="password" type="password" autocomplete="current-password" style="box-sizing:border-box;width:100%;margin-bottom:8px;padding:9px;border-radius:9px;border:1px solid rgba(255,255,255,.25);background:#111;color:white;">',
            '<div style="display:flex;gap:8px;">',
            '<button id="nova-auth-workmode-login" style="flex:1;padding:9px;border-radius:9px;border:0;font-weight:700;">Login</button>',
            '<button id="nova-auth-workmode-register" style="flex:1;padding:9px;border-radius:9px;border:0;font-weight:700;">Register</button>',
            '<button id="nova-auth-workmode-close" style="width:44px;padding:9px;border-radius:9px;border:0;">×</button>',
            '</div>'
        ].join("");

        document.body.appendChild(panel);

        document.getElementById("nova-auth-workmode-close").addEventListener("click", function () {
            hidePanel();
        });

        document.getElementById("nova-auth-workmode-login").addEventListener("click", function () {
            workmodeLogin();
        });

        document.getElementById("nova-auth-workmode-register").addEventListener("click", function () {
            workmodeRegister();
        });

        return panel;
    }

    function getCreds() {
        var username = clean((document.getElementById("nova-auth-workmode-username") || {}).value);
        var password = clean((document.getElementById("nova-auth-workmode-password") || {}).value);

        return {
            username: username,
            email: username && username.indexOf("@") !== -1 ? username : username + "@example.com",
            password: password
        };
    }

    function refreshStatus() {
        return api("/api/auth/status", {
            method: "GET"
        }).then(function (payload) {
            if (persistUser(payload)) {
                setStatus("Logged in as " + clean(payload.user.username || payload.user.email));
                hidePanel();
            } else {
                markLoggedOut();
                setStatus("Not logged in.");
                showPanel();
            }

            try {
                console.log("[NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702] status", payload);
            } catch (e) {}

            return payload;
        }).catch(function (err) {
            setStatus("Auth check failed.");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702] status failed", err);
            } catch (e) {}

            return null;
        });
    }

    function workmodeLogin() {
        var creds = getCreds();

        if (!creds.username || !creds.password) {
            setStatus("Enter username and password.");
            return;
        }

        setStatus("Logging in...");

        return api("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: creds.username,
                password: creds.password
            })
        }).then(function (payload) {
            if (persistUser(payload)) {
                setStatus("Logged in.");
                return refreshStatus();
            }

            setStatus("Login returned no user.");
            showPanel();
            return payload;
        }).catch(function (err) {
            setStatus("Login failed.");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702] login failed", err);
            } catch (e) {}

            return null;
        });
    }

    function workmodeRegister() {
        var creds = getCreds();

        if (!creds.username || !creds.password) {
            setStatus("Enter username and password.");
            return;
        }

        setStatus("Registering...");

        return api("/api/auth/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: creds.username,
                email: creds.email,
                password: creds.password
            })
        }).then(function (payload) {
            if (persistUser(payload)) {
                setStatus("Registered and logged in.");
                return refreshStatus();
            }

            setStatus("Register returned no user.");
            showPanel();
            return payload;
        }).catch(function (err) {
            setStatus("Register failed. Try login if account exists.");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702] register failed", err);
            } catch (e) {}

            return null;
        });
    }

    window.NovaMobileAuthWorkmodeStatus = refreshStatus;
    window.NovaMobileAuthWorkmodeLogin = workmodeLogin;
    window.NovaMobileAuthWorkmodeRegister = workmodeRegister;

    function boot() {
        ensurePanel();
        refreshStatus();
        setTimeout(refreshStatus, 1000);
        setTimeout(refreshStatus, 2500);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    try {
        console.log("[NOVA_MOBILE_AUTH_WORKMODE_PANEL_20260702] active");
    } catch (e) {}
})();
'''

path.write_text(text.rstrip() + "\n" + patch + "\n", encoding="utf-8")
print("patched mobile auth workmode panel")
