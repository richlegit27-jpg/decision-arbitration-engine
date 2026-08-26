
(function(){
  "use strict";

  var map = {
    desktopSessionsButton: "openSessionsBtn",
    desktopMemoryButton: "openMemoryBtn",
    desktopChatInput: "input",
    desktopSendButton: "sendBtn"
  };

  for (const alias in map) {
    if (!document.getElementById(alias)) {
      const real = document.getElementById(map[alias]);
      if (real) {
        const dummy = document.createElement("div");
        dummy.id = alias;
        dummy.style.display = "none";
        // Attach a pointer to real element for easy access
        dummy._real = real;
        real.parentNode.insertBefore(dummy, real.nextSibling);
      }
    }
  }

})();
