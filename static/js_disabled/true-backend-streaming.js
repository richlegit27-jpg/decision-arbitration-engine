/* notepad C:\Users\Owner\nova\static\js\true-backend-streaming.js */

(() => {
"use strict";

/*
Legacy file kept only so old script tags do not break.
Real backend streaming is now handled by:
- /static/js/app-fixed.js
- /static/js/composer.js
- /api/chats/{chat_id}/messages/stream

Do not add streaming logic here.
*/

if (window.__novaTrueBackendStreamingLoaded) {
  console.warn("Nova true-backend-streaming legacy stub already loaded.");
  return;
}

window.__novaTrueBackendStreamingLoaded = true;

console.info("Nova legacy true-backend-streaming stub loaded. Real streaming is handled by composer.js.");
})();