
(function () {
  "use strict";

  if (window.__NOVA_RESCUE_CONTAINER_SHIM_20260620__) return;
  window.__NOVA_RESCUE_CONTAINER_SHIM_20260620__ = true;

  window.getDesktopMessagesContainerRescue =
    window.getDesktopMessagesContainerRescue ||
    function () {
      return (
        document.getElementById("messages") ||
        document.getElementById("chat") ||
        document.querySelector("#messages") ||
        document.querySelector(".messages") ||
        document.querySelector(".chat-messages") ||
        document.querySelector(".desktop-messages") ||
        document.querySelector(".chat-log") ||
        document.querySelector(".chat-container")
      );
    };

  console.log("[Nova Rescue Container Shim] ready");
})();
