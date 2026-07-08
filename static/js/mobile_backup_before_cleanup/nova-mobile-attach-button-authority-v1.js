(function () {
    "use strict";

    /*
      NOVA ATTACH BUTTON AUTHORITY DISABLED

      2026-07-05 decision:
      The + button must NOT open the native file picker directly.

      Correct attachment path:
      + button -> attachment menu
      Upload button inside menu -> file picker
      file input change -> upload-change authority
      send authority -> /api/chat payload

      This file is intentionally a no-op to prevent old cached/script references
      from reintroducing double-click / first-click attachment bugs.
    */

    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_DISABLED_20260705__ = true;

    console.log("[Nova Attach Button Authority] disabled - + button is menu-only");
})();
