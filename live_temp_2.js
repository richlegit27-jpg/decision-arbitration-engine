
(function () {
  "use strict";

  // =========================
  // SOURCE CARDS
  // =========================
  function novaDesktopRescueSourceCards_20260611(msg) {
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
      wrap.className = "nova-source-cards";
      wrap.style.marginTop = "10px";
      wrap.style.display = "grid";
      wrap.style.gap = "8px";

      sources.slice(0, 8).forEach(function (src, index) {
        src = src || {};

        var url = String(src.url || src.link || src.href || "").trim();
        var title = String(src.title || src.name || ("Source " + (index + 1)));
        var snippet = String(src.snippet || src.text || "");

        var card = document.createElement(url ? "a" : "div");
        card.className = "nova-source-card";
        card.style.display = "block";
        card.style.padding = "10px";
        card.style.border = "1px solid rgba(255,255,255,.14)";
        card.style.borderRadius = "10px";

        if (url) {
          card.href = url;
          card.target = "_blank";
        }

        var t = document.createElement("div");
        t.textContent = title;
        t.style.fontWeight = "700";

        card.appendChild(t);

        if (snippet) {
          var s = document.createElement("div");
          s.textContent = snippet;
          s.style.opacity = ".75";
          s.style.fontSize = "12px";
          card.appendChild(s);
        }

        wrap.appendChild(card);
      });

      return wrap;
    } catch (e) {
      return null;
    }
  }

  // =========================
  // MESSAGE RENDERER (SINGLE VERSION ONLY)
  // =========================

function dedupeNovaMessages(messages) {
    const seen = new Set();

    return (Array.isArray(messages) ? messages : []).filter(function (message) {
        const id =
            message?.id ||
            message?.message_id ||
            message?.created_at + ":" + message?.role + ":" + message?.text;

        if (!id) return true;

        const key = String(id);

        if (seen.has(key)) return false;

        seen.add(key);
        return true;
    });
}

function renderDesktopChatMessagesRescue(messages) {

    if (window.__NOVA_RESCUE_RENDER_LOCK__) return false;

    window.__NOVA_RESCUE_RENDER_LOCK__ = true;

    setTimeout(() => {
        window.__NOVA_RESCUE_RENDER_LOCK__ = false;
    }, 150);

    var box = getDesktopMessagesContainerRescue();

    if (!box) return false;

    messages = dedupeNovaMessages(messages);

    box.innerHTML = "";

    if (!messages || !messages.length) {

        var session =
            window.NovaCurrentSessionManager &&
            window.NovaCurrentSessionManager.currentSession;

        if (
            session &&
            session.meta &&
            session.meta.onboarding &&
            typeof window.renderDesktopOnboarding === "function"
        ) {
            window.renderDesktopOnboarding(session);
            return true;
        }

        box.innerHTML = `
            <div class="message assistant">
<strong>Welcome to Nova.</strong><br><br>
Your AI workspace for serious projects.<br><br>
I help you keep context, plan decisions, analyze files, and move work forward without starting over every conversation.
            </div>
        `;

        return true;
    }

    messages.forEach(function (msg, index) {

        var role = String(msg.role || "assistant");

        var text =
            msg.content ||
            msg.text ||
            msg.message ||
            "";

        text = String(text || "");

        if (
            !String(text || "").trim() &&
            !msg.image_url &&
            !msg.image
        ) {
            return;
        }

        var row = document.createElement("div");

        row.className =
            "message " +
            (
                role.includes("user")
                    ? "user"
                    : "assistant"
            );

        row.setAttribute(
            "data-message-id",
            msg.id ||
            msg.message_id ||
            "rescue_" + index
        );

        const bubble =
            document.createElement("div");

        bubble.className = "bubble";

        if (
            typeof renderMessageWithCodeBlocks === "function" &&
            role.indexOf("user") === -1
        ) {
            renderMessageWithCodeBlocks(
                bubble,
                String(text)
            );
        } else {
            bubble.textContent =
                String(text);
        }

        row.appendChild(bubble);

        if (!role.includes("user")) {

            var existingCards =
                row.querySelector(
                    ".nova-source-cards"
                );

            if (!existingCards) {

                var cards =
                    novaDesktopRescueSourceCards_20260611(msg);

                if (cards) {
                    row.appendChild(cards);
                }
            }
        }

        box.appendChild(row);
    });

    return true;
}

  // =========================
  // EXPORTS (ONLY ONCE)
  // =========================
  window.renderDesktopChatMessagesRescue = renderDesktopChatMessagesRescue;
  window.novaDesktopRescueSourceCards_20260611 = novaDesktopRescueSourceCards_20260611;

})();
