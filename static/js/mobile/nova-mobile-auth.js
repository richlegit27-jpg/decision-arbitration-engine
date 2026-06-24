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


    // NOVA_MOBILE_AUTH_BLANK_SLATE_20260623
    function clearWorkspaceSessionState(reason) {
        const keys = [
            "nova_mobile_active_session_id",
            "nova_active_session_id",
            "active_session_id",
            "session_id",
            "nova_session_id",
            "novaMobileSessionId",
            "NovaMobileActiveSessionId",
            "NOVA_ACTIVE_SESSION_ID",
            "nova_pending_session_id",
            "nova_pending_new_session_id",
            "nova_mobile_pending_attachments",
            "nova_desktop_pending_attachments",
            "nova_mobile_session_cache",
            "nova_session_restore_cache"
        ];

        keys.forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (_) {}

            try {
                sessionStorage.removeItem(key);
            } catch (_) {}
        });

        window.NOVA_ACTIVE_SESSION_ID = "";
        window.NovaActiveSessionId = "";
        window.NovaMobileActiveSessionId = "";
        window.novaMobileActiveSessionId = "";
        window.NovaCurrentSessionId = "";
        window.currentSessionId = "";
        window.activeSessionId = "";
        window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = true;
        window.NOVA_PENDING_NEW_SESSION_ID = "";

        console.log("[Nova Mobile Auth Blank Slate] cleared workspace session state", reason || "");
    }

    function normalizeUsername(value) {
        return String(value || "").trim().toLowerCase();
    }

    function applyAuthWorkspaceBoundary(authenticated, username) {
        const currentUser = normalizeUsername(username);
        const previousUser = normalizeUsername(localStorage.getItem("nova_last_auth_username") || "");

        if (!authenticated || !currentUser) {
            clearWorkspaceSessionState("not authenticated");
            localStorage.removeItem("nova_last_auth_username");
            return;
        }

        if (previousUser && previousUser !== currentUser) {
            clearWorkspaceSessionState("user changed from " + previousUser + " to " + currentUser);
        }

        if (!previousUser) {
            clearWorkspaceSessionState("fresh authenticated workspace for " + currentUser);
        }

        localStorage.setItem("nova_last_auth_username", currentUser);
        document.body.dataset.novaWorkspaceUser = currentUser;
        window.NovaWorkspaceUser = currentUser;
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

                clearWorkspaceSessionState("logout");
                localStorage.removeItem("nova_last_auth_username");
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
            applyAuthWorkspaceBoundary(authenticated, username);

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


// NOVA_MOBILE_REAL_ACCOUNT_BUTTON_OUTSIDE_COMPOSER_20260624
(function () {
    const MARK = "NOVA_MOBILE_REAL_ACCOUNT_BUTTON_OUTSIDE_COMPOSER_20260624";

    function ensureStyle() {
        if (document.getElementById("nova-mobile-real-account-outside-style")) return;

        const style = document.createElement("style");
        style.id = "nova-mobile-real-account-outside-style";
        style.textContent = `
            #nova-mobile-bottom-login.nova-mobile-real-account-outside {
                position: fixed !important;
                left: 50% !important;
                right: auto !important;
                bottom: var(--nova-mobile-real-account-bottom, 132px) !important;
                transform: translateX(-50%) !important;
                z-index: 49999 !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: auto !important;
                max-width: calc(100vw - 24px) !important;
                min-width: 92px !important;
                min-height: 24px !important;
                height: 24px !important;
                padding: 3px 11px !important;
                margin: 0 !important;
                border-radius: 999px !important;
                border: 1px solid rgba(168, 85, 247, 0.55) !important;
                background: rgba(17, 12, 34, 0.96) !important;
                color: rgba(245, 243, 255, 0.94) !important;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.34) !important;
                font-size: 11px !important;
                font-weight: 700 !important;
                line-height: 1 !important;
                letter-spacing: 0.01em !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                pointer-events: auto !important;
            }

            #nova-mobile-composer #nova-mobile-bottom-login {
                display: none !important;
            }

            #nova-mobile-bottom-login.nova-mobile-real-account-outside {
                display: inline-flex !important;
            }

            #nova-mobile-static-account-strip,
            #nova-mobile-account-strip,
            #nova-mobile-floating-account-strip {
                display: none !important;
            }
        `;

        document.head.appendChild(style);
    }

    function composerRect() {
        const composer = document.getElementById("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer,.mobile-composer");

        if (!composer) return null;

        return composer.getBoundingClientRect();
    }

    function moveRealAccountButton() {
        ensureStyle();

        const button = document.getElementById("nova-mobile-bottom-login");

        if (!button) return false;

        const rect = composerRect();

        if (rect) {
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
            const bottom = Math.max(8, Math.ceil(viewportHeight - rect.top + 6));

            document.documentElement.style.setProperty(
                "--nova-mobile-real-account-bottom",
                bottom + "px"
            );
        } else {
            document.documentElement.style.setProperty(
                "--nova-mobile-real-account-bottom",
                "132px"
            );
        }

        if (button.parentElement !== document.body) {
            document.body.appendChild(button);
        }

        button.classList.add("nova-mobile-real-account-outside");

        if (!button.textContent.trim()) {
            button.textContent = "Account";
        }

        button.setAttribute("aria-label", "Account");

        document.querySelectorAll(
            "#nova-mobile-static-account-strip,#nova-mobile-account-strip,#nova-mobile-floating-account-strip"
        ).forEach(el => el.remove());

        return true;
    }

    window.NovaMobileMoveRealAccountButtonOutsideComposer = moveRealAccountButton;

    moveRealAccountButton();
    setTimeout(moveRealAccountButton, 250);
    setTimeout(moveRealAccountButton, 1000);
    setTimeout(moveRealAccountButton, 2500);

    window.addEventListener("resize", moveRealAccountButton, { passive: true });
    window.addEventListener("orientationchange", function () {
        setTimeout(moveRealAccountButton, 350);
    }, { passive: true });

    new MutationObserver(function () {
        clearTimeout(window.__novaRealAccountOutsideTimer);
        window.__novaRealAccountOutsideTimer = setTimeout(moveRealAccountButton, 150);
    }).observe(document.documentElement, {
        childList: true,
        subtree: true
    });
})();
// /NOVA_MOBILE_REAL_ACCOUNT_BUTTON_OUTSIDE_COMPOSER_20260624

