
(function () {
  "use strict";

  if (window.__NOVA_CORE_INSTALLED__) return;
  window.__NOVA_CORE_INSTALLED__ = true;

  function $(id) {
    return document.getElementById(id);
  }

  function hide(el) {
    el.style.position = "fixed";
    el.style.left = "-99999px";
    el.style.top = "-99999px";
    el.style.width = "1px";
    el.style.height = "1px";
    el.style.opacity = "0";
    el.style.pointerEvents = "none";
    el.setAttribute("aria-hidden", "true");
    return el;
  }

  function installButtonAlias(aliasId, realId, fallbackFnName) {
    if ($(aliasId)) return;

    var alias = hide(document.createElement("button"));
    alias.id = aliasId;
    alias.type = "button";

    alias.addEventListener("click", function () {
      var real = $(realId);

      if (real && typeof real.click === "function") {
        real.click();
        return;
      }

      if (fallbackFnName && typeof window[fallbackFnName] === "function") {
        window[fallbackFnName]();
      }
    });

    document.body.appendChild(alias);
  }

  function installInputAlias(aliasId, realId) {
    if ($(aliasId)) return;

    var alias = hide(document.createElement("textarea"));
    alias.id = aliasId;

    Object.defineProperty(alias, "value", {
      get: function () {
        var real = $(realId);
        return real ? real.value : "";
      },
      set: function (value) {
        var real = $(realId);
        if (!real) return;

        real.value = value;
        real.dispatchEvent(new Event("input", { bubbles: true }));
        real.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });

    alias.focus = function () {
      var real = $(realId);
      if (real && typeof real.focus === "function") real.focus();
    };

    document.body.appendChild(alias);
  }

  function installCompatAliases() {
    installButtonAlias("desktopSessionsButton", "openSessionsBtn", "NovaDesktopOpenSessionsRescue");
    installButtonAlias("desktopMemoryButton", "openMemoryBtn", "NovaDesktopOpenMemoryRescue");
    installInputAlias("desktopChatInput", "input");
    installButtonAlias("desktopSendButton", "sendBtn", null);

    window.NovaOpenDesktopSessions = window.NovaOpenDesktopSessions || function () {
      var button = $("openSessionsBtn");
      if (button) return button.click();

      if (typeof window.NovaDesktopOpenSessionsRescue === "function") {
        return window.NovaDesktopOpenSessionsRescue();
      }
    };

// NOVA_LEGACY_MEMORY_BUTTON_ALIAS_DISABLED

    window.NovaDesktopCompatAliasesReady = true;
  }

  const ALIASES = {
    desktopSessionsButton: "openSessionsBtn",
    desktopMemoryButton: "openMemoryBtn",
    desktopChatInput: "input",
    desktopSendButton: "sendBtn"
  };

  function resolve(id) {
    return document.getElementById(id) || document.getElementById(ALIASES[id]);
  }

  function bindOnce(el, key, event, handler) {
    if (!el) return;

    var boundKey = "__novaBound_" + key;

    if (el[boundKey]) return;
    el[boundKey] = true;

    el.addEventListener(event, handler, true);
  }

  function initButtons() {
    const sendBtn = resolve("desktopSendButton");
    const input = resolve("desktopChatInput");
    const memoryBtn = resolve("desktopMemoryButton");

    bindOnce(sendBtn, "sendClickAction", "click", function (event) {
      event.preventDefault();

      console.log("[NOVA] send clicked");

      if (typeof handleSendClick === "function") {
        handleSendClick();
      }
    });

    bindOnce(input, "sendEnterAction", "keydown", function (event) {
      if (event.key !== "Enter" || event.shiftKey) {
        return;
      }

      event.preventDefault();

      if (typeof handleSendClick === "function") {
        handleSendClick();
      }
    });

    bindOnce(memoryBtn, "memoryClickLog", "click", function () {
      console.log("[NOVA] memory clicked");
    });
  }
  function initObserver() {
    if (window.__NOVA_OBSERVER__) return;

    const observer = new MutationObserver(function () {
      initButtons();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    window.__NOVA_OBSERVER__ = observer;
  }

  function boot() {
    if (window.__NOVA_BOOT_DONE__) return;
    window.__NOVA_BOOT_DONE__ = true;

    installCompatAliases();
    initButtons();
    initObserver();

    console.log("[NOVA CORE] initialized once");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

})();
