/* NOVA_MOBILE_AUTH_GUARD_20260610 */
(function () {
    "use strict";

    const AUTH_STATUS_URL = "/api/auth/status";
    const AUTH_LOGOUT_URL = "/api/auth/logout";
    const LOGIN_URL = "/login";

    function setBodyAuthState(authenticated, username) {
        document.body.dataset.novaAuthenticated = authenticated ? "true" : "false";
        document.body.dataset.novaUsername = username || "";
        window.NovaAuthState = {
            authenticated: Boolean(authenticated),
            username: username || ""
        };
    }

    function ensureStyles() {
        if (document.getElementById("nova-mobile-auth-style")) return;

        const style = document.createElement("style");
        style.id = "nova-mobile-auth-style";
        style.textContent = `
            .nova-mobile-auth-chip {
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 2147483000;
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 8px;
                border: 1px solid rgba(255,255,255,.12);
                border-radius: 999px;
                background: rgba(12,12,18,.72);
                backdrop-filter: blur(10px);
                color: rgba(255,255,255,.88);
                font: 12px/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                box-shadow: 0 8px 24px rgba(0,0,0,.25);
            }

            .nova-mobile-auth-chip button {
                border: 0;
                border-radius: 999px;
                padding: 4px 7px;
                background: rgba(255,255,255,.12);
                color: rgba(255,255,255,.92);
                font: inherit;
                cursor: pointer;
            }

            .nova-mobile-auth-chip button:active {
                transform: scale(.98);
            }

            body[data-nova-authenticated="false"] .nova-mobile-auth-chip {
                display: none;
            }
        `;
        document.head.appendChild(style);
    }

    function renderChip(username) {
        ensureStyles();

        let chip = document.getElementById("nova-mobile-auth-chip");
        if (!chip) {
            chip = document.createElement("div");
            chip.id = "nova-mobile-auth-chip";
            chip.className = "nova-mobile-auth-chip";
            chip.innerHTML = `
                <span id="nova-mobile-auth-name"></span>
                <button id="nova-mobile-auth-logout" type="button">Logout</button>
            `;
            document.body.appendChild(chip);
        }

        const name = document.getElementById("nova-mobile-auth-name");
        const logout = document.getElementById("nova-mobile-auth-logout");

        if (name) {
            name.textContent = username ? `@${username}` : "Signed in";
        }

        if (logout && !logout.dataset.bound) {
            logout.dataset.bound = "true";
            logout.addEventListener("click", async function () {
                logout.disabled = true;
                logout.textContent = "Logging out...";

                try {
                    await fetch(AUTH_LOGOUT_URL, {
                        method: "POST",
                        credentials: "include"
                    });
                } catch (error) {
                    console.warn("[Nova Mobile Auth] logout failed", error);
                }

                window.location.href = LOGIN_URL;
            });
        }
    }

    async function refreshMobileAuth() {
        try {
            const response = await fetch(AUTH_STATUS_URL, {
                method: "GET",
                credentials: "include",
                headers: {
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                setBodyAuthState(false, "");
                window.location.href = LOGIN_URL;
                return;
            }

            const data = await response.json();
            const authenticated = Boolean(data && data.authenticated);
            const user = data && data.user ? data.user : {};
            const username = String(user.username || data.username || "");

            setBodyAuthState(authenticated, username);

            if (!authenticated) {
                window.location.href = LOGIN_URL;
                return;
            }

            renderChip(username);
            console.log("[Nova Mobile Auth] authenticated", username || "user");
        } catch (error) {
            console.warn("[Nova Mobile Auth] status failed", error);
            setBodyAuthState(false, "");
            window.location.href = LOGIN_URL;
        }
    }

    window.NovaRefreshMobileAuth = refreshMobileAuth;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", refreshMobileAuth);
    } else {
        refreshMobileAuth();
    }
})();


