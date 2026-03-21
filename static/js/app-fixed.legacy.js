(() => {
"use strict";

if (window.__novaAppFixedCleanupLoaded) {
  console.warn("Legacy app-fixed cleanup already loaded.");
  return;
}
window.__novaAppFixedCleanupLoaded = true;

console.warn(
  "Legacy app-fixed.js is no longer used. Nova now loads from app-state.js, app-api.js, app-render.js, controls.js, and sidebar.js."
);

// Safety shim only.
// This file intentionally does nothing so old script references do not break the page.
window.NovaApp = window.NovaApp || {};
})();