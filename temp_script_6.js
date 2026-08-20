
(function () {
  "use strict";

  console.log("[Nova Desktop Button Animation Safe] ready");

  /* NOVA_DESKTOP_AUTH_WIDGET_20260611 */
    "use strict";

    function ensureAuthWidget() {
        var existing = document.getElementById("nova-desktop-auth-widget");
        if (existing) return existing;

        var widget = document.createElement("div");
        widget.id = "nova-desktop-auth-widget";
        widget.className = "nova-auth-widget";
        widget.innerHTML = '<span class="nova-auth-user">Checking account...</span>';
        document.body.appendChild(widget);
        return widget;
    }

    function userLabel(user) {
        if (!user) return "Guest";
        return user.username || user.email || user.id || "Signed in";
    }

    function renderAuthWidget(data) {
        var widget = ensureAuthWidget();
        var authenticated = !!(data && data.authenticated);
        var user = data && data.user;

        window.NovaAuth = {
            authenticated: authenticated,
            user: user || null,
            checked_at: new Date().toISOString()
        };

        if (authenticated) {
            widget.innerHTML = [
                '<span class="nova-auth-user">Account: ',
                escapeHtml(userLabel(user)),
                '</span>',
                '<button type="button" id="nova-desktop-logout-btn">Logout</button>'
            ].join("");

            var logout = document.getElementById("nova-desktop-logout-btn");
            if (logout) {
                logout.addEventListener("click", async function () {
                    logout.disabled = true;
                    logout.textContent = "Logging out...";
                    try {
                        await fetch("/api/auth/logout", {
                            method: "POST",
                            headers: { "Accept": "application/json" },
                            credentials: "same-origin"
                        });
                    } catch (error) {
                        console.warn("[Nova Auth] logout failed", error);
                    }
                    window.NovaAuth = {
                        authenticated: false,
                        user: null,
                        checked_at: new Date().toISOString()
                    };
                    refreshAuthStatus();
                });
            }
        } else {
            widget.innerHTML = [
                '<span class="nova-auth-user">Guest</span>',
                '<a href="/login">Login</a>',
                '<a href="/register">Register</a>'
            ].join("");
        }
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async function refreshAuthStatus() {
        try {
            var response = await fetch("/api/auth/status", {
                headers: { "Accept": "application/json" },
                credentials: "same-origin",
                cache: "no-store"
            });

const raw = await response.text();

let data = {};
try {
  data = JSON.parse(raw);
} catch (error) {
  console.warn("[Nova Auth] Non-JSON response:", raw);
}

renderAuthWidget(data || {});

        } catch (error) {
            console.warn("[Nova Auth] status failed", error);
            renderAuthWidget({ authenticated: false, user: null });
        }
    }

    window.NovaRefreshAuthStatus = refreshAuthStatus;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", refreshAuthStatus);
    } else {
        refreshAuthStatus();
    }

    setInterval(refreshAuthStatus, 60000);
})();
(function () {
  "use strict";

  function getDesktopMessageBox() {
    var existing =
      document.getElementById("chat") ||
      document.getElementById("messages") ||
      document.getElementById("chatMessages") ||
      document.getElementById("desktopMessages") ||
      document.querySelector(".messages") ||
      document.querySelector(".chat-messages") ||
      document.querySelector("[data-messages]");

    if (existing) return existing;

    var host =
      document.querySelector("main") ||
      document.querySelector(".chat") ||
      document.querySelector(".chat-panel") ||
      document.querySelector(".desktop-chat") ||
      document.body;

    var box = document.createElement("div");
    box.id = "chat";
    box.className = "messages chat-messages desktop-rescue-messages";
    box.setAttribute("data-messages", "true");

    box.style.minHeight = "320px";
    box.style.maxHeight = "60vh";
    box.style.overflowY = "auto";
    box.style.padding = "16px";
    box.style.margin = "12px 0";
    box.style.borderRadius = "18px";
    box.style.background = "rgba(255,255,255,.04)";

    host.appendChild(box);
    return box;
  }

  function makeSourceCards(msg) {
    try {
      var meta = msg && typeof msg === "object" && msg.meta && typeof msg.meta === "object"
        ? msg.meta
        : {};

      var sources = Array.isArray(meta.sources) ? meta.sources : [];

      if (!sources.length && Array.isArray(msg && msg.sources)) {
        sources = msg.sources;
      }

      if (!sources.length) return null;

      var wrap = document.createElement("div");
      wrap.className = "nova-source-cards nova-desktop-global-source-cards";
      wrap.style.marginTop = "10px";
      wrap.style.display = "grid";
      wrap.style.gap = "8px";

      sources.slice(0, 8).forEach(function (src, index) {
        src = src || {};

        var url = String(src.url || src.link || src.href || src.file_url || "").trim();
        var title = String(src.title || src.name || src.label || src.source || ("Source " + (index + 1))).trim();
        var snippet = String(src.snippet || src.text || src.description || src.summary || "").trim();

        var card = document.createElement(url ? "a" : "div");
        card.className = "nova-source-card nova-desktop-global-source-card";
        card.style.display = "block";
        card.style.padding = "10px 12px";
        card.style.border = "1px solid rgba(255,255,255,.14)";
        card.style.borderRadius = "12px";
        card.style.background = "rgba(255,255,255,.06)";
        card.style.color = "inherit";
        card.style.textDecoration = "none";

        if (url) {
          card.href = url;
          card.target = "_blank";
          card.rel = "noopener noreferrer";
        }

        var titleEl = document.createElement("div");
        titleEl.className = "nova-source-title";
        titleEl.textContent = title;
        titleEl.style.fontWeight = "700";
        titleEl.style.fontSize = "13px";
        card.appendChild(titleEl);

        if (snippet) {
          var snippetEl = document.createElement("div");
          snippetEl.className = "nova-source-snippet";
          snippetEl.textContent = snippet;
          snippetEl.style.marginTop = "4px";
          snippetEl.style.opacity = ".78";
          snippetEl.style.fontSize = "12px";
          snippetEl.style.lineHeight = "1.35";
          card.appendChild(snippetEl);
        }

        wrap.appendChild(card);
      });

      return wrap;
    } catch (err) {
      console.warn("[Nova Desktop Global Source Cards] render failed", err);
      return null;
    }
  }

})();
