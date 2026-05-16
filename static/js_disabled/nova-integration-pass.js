/* notepad C:\Users\Owner\nova\static\js\nova-integration-pass.js */

(() => {
"use strict";

/*
Legacy file kept only so old script tags do not break.
Real Nova integration is now handled by:
- /static/js/markdown-engine.js
- /static/js/app-fixed.js
- /static/js/composer.js
- /static/js/memory-panel.js

Do not add hydration, streaming, or message rendering logic here.
*/

if (window.__novaIntegrationPassLoaded) {
  console.warn("Nova integration-pass legacy stub already loaded.");
  return;
}

window.__novaIntegrationPassLoaded = true;

console.info("Nova legacy integration-pass stub loaded. Real integration is handled by the main UI files.");
})();