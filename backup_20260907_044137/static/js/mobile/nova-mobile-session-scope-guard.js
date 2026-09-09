(function () {
    "use strict";

    const originalSetItem = Storage.prototype.setItem;

    Storage.prototype.setItem = function (key, value) {
        try {
            return originalSetItem.call(this, key, value);
        } catch (e) {
            console.warn("[SessionGuard] error:", e);
        }
    };

    console.log("[SessionGuard] CLEAN BOOT OK");
})();