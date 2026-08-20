
(function () {
  "use strict";

  // NOVA_DESKTOP_COMPACT_RECENT_SCROLL_CHAT_20260610

  function findDesktopChatTarget() {
    var candidates = Array.from(document.querySelectorAll("h1, h2, h3, main, .desktop-chat, .chat-panel, .chat-column, .chat-container"));

    var heading = candidates.find(function (el) {
      return String(el.textContent || "").trim().toLowerCase().includes("desktop chat");
    });

    return heading || document.querySelector("main") || document.body;
  }

  function scrollToDesktopChatSoon() {
    setTimeout(function () {
      var target = findDesktopChatTarget();
      if (target && target.scrollIntoView) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 250);
  }


})();
