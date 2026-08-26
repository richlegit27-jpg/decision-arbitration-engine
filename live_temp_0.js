

(function () {

  "use strict";
  var marker = "NOVA_DESKTOP_VISUAL_POLISH_LOCK_20260611";

    if (window[marker]) {
        return;
    }
    window[marker] = true;

    function isDesktop() {
        return window.matchMedia && window.matchMedia("(min-width: 769px)").matches;
    }

    function scrollMainChatToBottom() {
        if (!isDesktop()) {
            return;
        }

        var candidates = [
            document.getElementById("chatMessages"),
            document.getElementById("desktopChatMessages"),
            document.getElementById("messages"),
            document.querySelector(".chat-messages"),
            document.querySelector(".messages"),
            document.querySelector(".chat-scroll"),
            document.querySelector(".conversation"),
            document.querySelector(".nova-chat")
        ].filter(Boolean);

        candidates.forEach(function (el) {
            try {
                var distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
                if (distanceFromBottom < 240) {
                    el.scrollTop = el.scrollHeight;
                }
            } catch (err) {}
        });
    }

    function normalizeAttachmentTitles() {
        if (!isDesktop()) {
            return;
        }

        var nodes = document.querySelectorAll(
            ".attachment, .attachment-chip, .attachment-preview, .nova-attachment, [data-attachment], .file-chip, .file-preview"
        );

        nodes.forEach(function (node) {
            if (!node || node.getAttribute("data-nova-title-polished") === "true") {
                return;
            }

            var text = (node.textContent || "").trim().replace(/\s+/g, " ");
            if (text) {
                node.title = text;
            }

            node.setAttribute("data-nova-title-polished", "true");
        });
    }

    function polishDesktop() {
        if (!isDesktop()) {
            return;
        }

        normalizeAttachmentTitles();
        scrollMainChatToBottom();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", polishDesktop);


    } else {
        polishDesktop();
    }

var observer = new MutationObserver(function () {
    polishDesktop();
});

observer.observe(document.documentElement, {
    childList: true,
    subtree: true
});

    window.addEventListener("resize", polishDesktop);
})();
