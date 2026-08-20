
(function () {
  "use strict";

  function addDesktopSessionsButton() {
    if (document.getElementById("openSessionsBtn")) return;

    var newButton = document.getElementById("newSessionBtn");
    var memoryButton = document.getElementById("openMemoryBtn");
    var host =
      (newButton && newButton.parentElement) ||
      (memoryButton && memoryButton.parentElement) ||
      document.querySelector("aside") ||
      document.querySelector(".sidebar") ||
      document.body;

    var button = document.createElement("button");
    button.id = "openSessionsBtn";
    button.type = "button";
    button.className = newButton ? newButton.className : "primary-side-button";
    button.textContent = "Sessions";

    button.onclick = function (event) {
      event.preventDefault();
      event.stopPropagation();

      console.log("[NOVA sessions] refreshing sessions after send")

      if (typeof window.NovaDesktopOpenSessionsRescue === "function") {
        window.NovaDesktopOpenSessionsRescue().catch(console.error);
      } else if (typeof window.loadDesktopSessions === "function") {
        window.loadDesktopSessions();
        console.log("[Nova Desktop Sessions Button] loaded sessions directly");
      }
    };

    if (newButton && newButton.nextSibling) {
      newButton.parentElement.insertBefore(button, newButton.nextSibling);
    } else if (newButton) {
      newButton.parentElement.appendChild(button);
    } else {
      host.insertBefore(button, host.firstChild);
    }
  }

  function bindExactDesktopButtons() {
    var memoryButton = document.getElementById("openMemoryBtn");
    var newButton = document.getElementById("newSessionBtn");

    addDesktopSessionsButton();

    if (memoryButton && memoryButton.dataset.novaExactMemoryBound !== "true") {
      memoryButton.dataset.novaExactMemoryBound = "true";

      memoryButton.onclick = function (event) {
        event.preventDefault();
        event.stopPropagation();

        console.log("[Nova Desktop Exact Bind] memory clicked");

// NOVA_LEGACY_MEMORY_RESCUE_DISABLED
      };
    }

    if (newButton) {
      newButton.onclick = function (event) {
        event.preventDefault();
        event.stopPropagation();

        console.log("[NOVA clean sessions] new session clicked");

        newSession();
      };
    }
  }

  bindExactDesktopButtons();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindExactDesktopButtons);
  } else {
    setTimeout(bindExactDesktopButtons, 0);
  }

  window.NovaDesktopAddSessionsButton = addDesktopSessionsButton;
  console.log("[Nova Desktop Sessions Button] ready");
})();
