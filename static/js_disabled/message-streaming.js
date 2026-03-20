/* notepad C:\Users\Owner\nova\static\js\message-streaming.js */

(() => {
"use strict";

/*
Legacy file kept only so old script tags do not break.
Real streaming is now handled by:
- /static/js/app-fixed.js
- /static/js/composer.js
- backend SSE route

Do not add UI logic here.
*/

if (window.__novaMessageStreamingLoaded) {
  console.warn("Nova message-streaming legacy stub already loaded.");
  return;
}

window.__novaMessageStreamingLoaded = true;

console.info("Nova legacy message-streaming stub loaded. Real streaming is handled by composer.js.");
})();