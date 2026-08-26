
(function () {
  "use strict";

  if (window.__NOVA_REGEN_BUTTON_REPAIR_V2_20260620__) return;
  window.__NOVA_REGEN_BUTTON_REPAIR_V2_20260620__ = true;

  function cleanMessageText(value) {
    return String(value || "")
      .replace(/\bCopy\b/g, "")
      .replace(/\bRegen\b/g, "")
      .replace(/^user\s*/i, "")
      .replace(/^assistant\s*/i, "")
      .trim();
  }

  function isRegenButton(btn) {
    const raw = String(btn && btn.textContent || "").trim().toLowerCase();
    return raw === "regen" || raw === "regenerate";
  }

  function isUserNode(node) {
    if (!node) return false;

    const role = String(node.getAttribute && node.getAttribute("data-role") || "").toLowerCase();
    const cls = String(node.className || "").toLowerCase();

    return (
      role === "user" ||
      cls.includes("user-bubble") ||
      cls.includes("user-message") ||
      cls.includes("message user") ||
      cls.includes("msg user") ||
      cls.includes("desktop-message user")
    );
  }

  function findPreviousUserText(fromButton) {
    let node =
      fromButton.closest(".message.assistant") ||
      fromButton.closest(".msg.assistant") ||
      fromButton.closest(".desktop-message.assistant") ||
      fromButton.closest("[data-role='assistant']") ||
      fromButton.closest(".assistant-bubble") ||
      fromButton.closest(".assistant-message");

    while (node && node.previousElementSibling) {
      node = node.previousElementSibling;

      if (isUserNode(node)) {
        return cleanMessageText(node.innerText || node.textContent || "");
      }

      const nested = node.querySelector &&
        node.querySelector(".user-bubble, .user-message, .message.user, .msg.user, .desktop-message.user, [data-role='user']");

      if (nested) {
        return cleanMessageText(nested.innerText || nested.textContent || "");
      }
    }

    const users = Array.from(document.querySelectorAll(
      ".user-bubble, .user-message, .message.user, .msg.user, .desktop-message.user, [data-role='user']"
    ));

    if (!users.length) return "";

    return cleanMessageText(users[users.length - 1].innerText || users[users.length - 1].textContent || "");
  }

  function runRegen(text) {
    const input = document.getElementById("input") || document.querySelector("textarea");
    const sendBtn = document.getElementById("sendBtn");

    if (!text) {
      console.warn("[Nova Regen V2] no previous user text found");
      return;
    }

    console.log("[Nova Regen V2] regenerating:", text);

    if (input) {
      input.value = text;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (typeof window.handleSendClick === "function") {
      window.handleSendClick(text);
      return;
    }

    if (typeof window.sendText === "function") {
      window.sendText(text);
      return;
    }

    if (sendBtn && typeof sendBtn.click === "function") {
      sendBtn.click();
      return;
    }

    console.warn("[Nova Regen V2] no send function or send button found");
  }

  document.addEventListener("click", function (event) {
    const btn = event.target.closest("button");
    if (!btn || !isRegenButton(btn)) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    runRegen(findPreviousUserText(btn));
  }, true);

  console.log("[Nova Regen Button Repair V2] ready");
})();
