/* NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_DISABLED_NOOP_20260705 */
(function disableNovaMobileAttachButtonAuthority() {
    "use strict";

    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_DISABLED_NOOP_20260705__ = true;

    /*
      This file is intentionally disabled.

      Reason:
      The normal + menu upload path works.
      This override was hijacking the + button and causing first-click/double-click issues.
      If this file is still loaded by an old hidden loader, it must do nothing.
    */

    try {
        delete window.NovaMobileAttachButtonAuthorityV1;
    } catch (_) {
        window.NovaMobileAttachButtonAuthorityV1 = undefined;
    }

    try {
        console.log("[Nova Attach Button Authority] disabled no-op loaded");
    } catch (_) {}
})();
