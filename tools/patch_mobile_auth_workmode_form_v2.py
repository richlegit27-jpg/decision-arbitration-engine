from pathlib import Path

path = Path("static/js/nova-mobile-app.js")
text = path.read_text(encoding="utf-8")

marker = "NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702"

if marker in text:
    print("mobile auth workmode form v2 already installed")
    raise SystemExit(0)

patch = r'''

/* ============================================================
 * NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702
 * Replaces the rough fallback auth panel with a proper form:
 * - fixes Chrome password-form warning
 * - shows real backend errors
 * - supports create account and login
 * - verifies /api/auth/status after success
 * - exposes debug helpers for live mobile testing
 * ============================================================ */
(function () {
    var MARKER = "__NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var PANEL_ID = "nova-auth-workmode-panel";
    var STATUS_ID = "nova-auth-workmode-status";
    var USERNAME_ID = "nova-auth-workmode-username";
    var EMAIL_ID = "nova-auth-workmode-email";
    var PASSWORD_ID = "nova-auth-workmode-password";
    var FORM_ID = "nova-auth-workmode-form-v2";

    function clean(value) {
        try {
            return String(value || "").trim();
        } catch (e) {
            return "";
        }
    }

    function authFetch(path, options) {
        options = options || {};
        options.credentials = "include";
        options.cache = options.cache || "no-store";
        options.headers = Object.assign({
            "Accept": "application/json"
        }, options.headers || {});

        return fetch(path, options).then(function (res) {
            return res.text().then(function (text) {
                var payload = {};

                try {
                    payload = text ? JSON.parse(text) : {};
                } catch (e) {
                    payload = {
                        raw: text
                    };
                }

                if (!res.ok || payload.ok === false) {
                    var message = (
                        payload.error ||
                        payload.message ||
                        payload.raw ||
                        ("HTTP " + res.status)
                    );

                    var err = new Error(message);
                    err.status = res.status;
                    err.payload = payload;
                    throw err;
                }

                return payload;
            });
        });
    }

    function setStoredUser(payload) {
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

    function clearStoredUserStateOnly() {
        try {
            localStorage.setItem("nova_auth_authenticated", "false");
            sessionStorage.setItem("nova_auth_authenticated", "false");

            window.NOVA_AUTHENTICATED = false;
            window.novaAuthenticated = false;
        } catch (e) {}
    }

    function getPanel() {
        return document.getElementById(PANEL_ID);
    }

    function getStatusNode() {
        return document.getElementById(STATUS_ID);
    }

    function setStatus(message, kind) {
        try {
            var node = getStatusNode();

            if (!node) {
                return;
            }

            node.textContent = message || "";
            node.setAttribute("data-kind", kind || "info");

            if (kind === "error") {
                node.style.color = "#ffb4b4";
            } else if (kind === "success") {
                node.style.color = "#b7ffcc";
            } else {
                node.style.color = "rgba(255,255,255,0.86)";
            }
        } catch (e) {}
    }

    function showPanel() {
        try {
            ensurePanel();
            var panel = getPanel();

            if (panel) {
                panel.style.display = "block";
            }
        } catch (e) {}
    }

    function hidePanel() {
        try {
            var panel = getPanel();

            if (panel) {
                panel.style.display = "none";
            }
        } catch (e) {}
    }

    function buttonStyle(primary) {
        return [
            "min-height:44px",
            "border:0",
            "border-radius:14px",
            "font-weight:800",
            "font-size:15px",
            "padding:10px 12px",
            "background:" + (primary ? "white" : "rgba(255,255,255,.13)"),
            "color:" + (primary ? "#111" : "white"),
            "box-shadow:" + (primary ? "0 4px 18px rgba(255,255,255,.14)" : "none")
        ].join(";");
    }

    function inputStyle() {
        return [
            "box-sizing:border-box",
            "width:100%",
            "margin:0 0 8px 0",
            "padding:10px 14px",
            "border-radius:14px",
            "border:1px solid rgba(255,255,255,.26)",
            "background:#111",
            "color:white",
            "min-height:44px",
            "font-size:16px",
            "outline:none"
        ].join(";");
    }

    function ensurePanel() {
        if (!document.body) {
            return null;
        }

        var panel = getPanel();

        if (!panel) {
            panel = document.createElement("div");
            panel.id = PANEL_ID;
            panel.setAttribute("data-nova-auth-workmode", "true");
            document.body.appendChild(panel);
        }

        panel.style.position = "fixed";
        panel.style.left = "10px";
        panel.style.right = "10px";
        panel.style.top = "10px";
        panel.style.zIndex = "999999";
        panel.style.padding = "12px";
        panel.style.borderRadius = "18px";
        panel.style.background = "rgba(20, 20, 28, 0.97)";
        panel.style.border = "1px solid rgba(255,255,255,0.22)";
        panel.style.boxShadow = "0 10px 36px rgba(0,0,0,0.42)";
        panel.style.color = "white";
        panel.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
        panel.style.fontSize = "14px";

        panel.innerHTML = [
            '<form id="' + FORM_ID + '" autocomplete="on">',
            '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">',
            '<div>',
            '<div style="font-weight:900;font-size:16px;">Nova account</div>',
            '<div style="font-size:12px;opacity:.75;">Create an account or log in to save chats and restore sessions.</div>',
            '</div>',
            '<button type="button" id="nova-auth-workmode-close-v2" style="' + buttonStyle(false) + ';width:44px;">×</button>',
            '</div>',
            '<div id="' + STATUS_ID + '" style="font-size:13px;margin:8px 0 10px 0;color:rgba(255,255,255,.86);">Checking auth...</div>',
            '<label style="display:block;font-size:12px;opacity:.78;margin:0 0 4px 2px;">Username</label>',
            '<input id="' + USERNAME_ID + '" name="username" placeholder="choose a username" autocomplete="username" autocapitalize="none" spellcheck="false" style="' + inputStyle() + '">',
            '<label style="display:block;font-size:12px;opacity:.78;margin:0 0 4px 2px;">Email optional</label>',
            '<input id="' + EMAIL_ID + '" name="email" placeholder="email optional" autocomplete="email" autocapitalize="none" spellcheck="false" style="' + inputStyle() + '">',
            '<label style="display:block;font-size:12px;opacity:.78;margin:0 0 4px 2px;">Password</label>',
            '<input id="' + PASSWORD_ID + '" name="password" placeholder="password" type="password" autocomplete="current-password" style="' + inputStyle() + '">',
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px;">',
            '<button type="submit" id="nova-auth-workmode-login-v2" style="' + buttonStyle(true) + ';">Login</button>',
            '<button type="button" id="nova-auth-workmode-register-v2" style="' + buttonStyle(false) + ';">Create account</button>',
            '</div>',
            '<button type="button" id="nova-auth-workmode-status-v2" style="' + buttonStyle(false) + ';width:100%;margin-top:8px;">Check login status</button>',
            '</form>'
        ].join("");

        var form = document.getElementById(FORM_ID);
        var closeButton = document.getElementById("nova-auth-workmode-close-v2");
        var registerButton = document.getElementById("nova-auth-workmode-register-v2");
        var statusButton = document.getElementById("nova-auth-workmode-status-v2");

        if (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                login();
            });
        }

        if (closeButton) {
            closeButton.addEventListener("click", function () {
                hidePanel();
            });
        }

        if (registerButton) {
            registerButton.addEventListener("click", function () {
                register();
            });
        }

        if (statusButton) {
            statusButton.addEventListener("click", function () {
                refreshStatus(true);
            });
        }

        return panel;
    }

    function getCreds() {
        var usernameNode = document.getElementById(USERNAME_ID);
        var emailNode = document.getElementById(EMAIL_ID);
        var passwordNode = document.getElementById(PASSWORD_ID);

        var username = clean(usernameNode && usernameNode.value);
        var email = clean(emailNode && emailNode.value);
        var password = clean(passwordNode && passwordNode.value);

        if (!email && username && username.indexOf("@") !== -1) {
            email = username;
        }

        if (!email && username) {
            email = username.replace(/[^a-z0-9_.-]/gi, "_").toLowerCase() + "@example.com";
        }

        return {
            username: username,
            email: email,
            password: password
        };
    }

    function validateCreds(creds, isRegister) {
        if (!creds.username) {
            return "Enter a username.";
        }

        if (!creds.password) {
            return "Enter a password.";
        }

        if (creds.password.length < 6) {
            return "Password needs at least 6 characters.";
        }

        if (isRegister && !creds.email) {
            return "Enter an email, or use a simple username so Nova can create a placeholder email.";
        }

        return "";
    }

    function afterAuthPayload(payload, successMessage) {
        if (!setStoredUser(payload)) {
            setStatus("Auth returned no user. Try again.", "error");
            showPanel();
            return payload;
        }

        setStatus(successMessage || "Logged in.", "success");

        return refreshStatus(false).then(function (statusPayload) {
            if (statusPayload && statusPayload.authenticated) {
                hidePanel();
            }

            return statusPayload || payload;
        });
    }

    function login() {
        ensurePanel();

        var creds = getCreds();
        var validation = validateCreds(creds, false);

        if (validation) {
            setStatus(validation, "error");
            showPanel();
            return Promise.resolve(null);
        }

        setStatus("Logging in...", "info");

        return authFetch("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: creds.username,
                password: creds.password
            })
        }).then(function (payload) {
            return afterAuthPayload(payload, "Logged in.");
        }).catch(function (err) {
            var message = clean(err && err.message) || "Login failed.";
            setStatus(message, "error");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702] login failed", err);
            } catch (e) {}

            return null;
        });
    }

    function register() {
        ensurePanel();

        var creds = getCreds();
        var validation = validateCreds(creds, true);

        if (validation) {
            setStatus(validation, "error");
            showPanel();
            return Promise.resolve(null);
        }

        setStatus("Creating account...", "info");

        return authFetch("/api/auth/register", {
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
            return afterAuthPayload(payload, "Account created.");
        }).catch(function (err) {
            var message = clean(err && err.message) || "Create account failed.";
            setStatus(message, "error");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702] register failed", err);
            } catch (e) {}

            return null;
        });
    }

    function refreshStatus(forceShow) {
        ensurePanel();

        return authFetch("/api/auth/status", {
            method: "GET"
        }).then(function (payload) {
            if (setStoredUser(payload)) {
                var user = payload.user || {};
                setStatus("Logged in as " + clean(user.username || user.email), "success");
                hidePanel();
            } else {
                clearStoredUserStateOnly();
                setStatus("Not logged in. Create an account or log in.", "info");

                if (forceShow || !payload.authenticated) {
                    showPanel();
                }
            }

            try {
                console.log("[NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702] status", payload);
            } catch (e) {}

            return payload;
        }).catch(function (err) {
            setStatus("Could not check login status.", "error");
            showPanel();

            try {
                console.warn("[NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702] status failed", err);
            } catch (e) {}

            return null;
        });
    }

    function boot() {
        ensurePanel();
        refreshStatus(false);
        setTimeout(function () {
            refreshStatus(false);
        }, 700);
        setTimeout(function () {
            refreshStatus(false);
        }, 1800);
    }

    window.NovaMobileAuthWorkmodeStatus = refreshStatus;
    window.NovaMobileAuthWorkmodeLogin = login;
    window.NovaMobileAuthWorkmodeRegister = register;
    window.NovaMobileAuthWorkmodeEnsurePanel = ensurePanel;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    try {
        console.log("[NOVA_MOBILE_AUTH_WORKMODE_FORM_V2_20260702] active");
    } catch (e) {}
})();
'''

path.write_text(text.rstrip() + "\n" + patch + "\n", encoding="utf-8")
print("patched mobile auth workmode form v2")
