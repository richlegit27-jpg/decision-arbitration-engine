[1mdiff --git a/static/js/nova-mobile-app.js b/static/js/nova-mobile-app.js[m
[1mindex d6643af..2dd5b7c 100644[m
[1m--- a/static/js/nova-mobile-app.js[m
[1m+++ b/static/js/nova-mobile-app.js[m
[36m@@ -1,4 +1,4 @@[m
[31m-ï»¿(() => {[m
[32m+[m[32m(() => {[m
     "use strict";[m
 [m
 console.log("[NOVA FILE STARTED]");[m
[36m@@ -159,7 +159,7 @@[m [mfunction renderAttachmentPreview() {[m
         img.style.objectFit = "cover";[m
 [m
         const remove = document.createElement("button");[m
[31m-        remove.textContent = "Ã—";[m
[32m+[m[32m        remove.textContent = "×";[m
         remove.style.position = "absolute";[m
         remove.style.top = "4px";[m
         remove.style.right = "4px";[m
[36m@@ -263,7 +263,7 @@[m [mfunction wireDragDrop() {[m
 }[m
 [m
 async function uploadFile(file) {[m
[31m-console.log("ðŸ”¥ uploadFile() CALLED");[m
[32m+[m[32mconsole.log("?? uploadFile() CALLED");[m
     const form = new FormData();[m
     form.append("file", file);[m
 [m
[36m@@ -393,7 +393,7 @@[m [mwindow.runModules = function () {[m
     console.log("[Nova Modules] lifecycle complete");[m
 };[m
 [m
[31m-console.log("ðŸ”¥ REACHED WIRE SECTION");[m
[32m+[m[32mconsole.log("?? REACHED WIRE SECTION");[m
 [m
 function wire() {[m
 window.__WIRED__ = window.__WIRED__ || false;[m
[36m@@ -435,7 +435,7 @@[m [msend.addEventListener("click", (e) => {[m
         };[m
     }[m
 [m
[31m-// âœ… SESSION TOGGLE[m
[32m+[m[32m// ? SESSION TOGGLE[m
 const sessionsToggle = $("nova-mobile-sessions-toggle");[m
 [m
 if (sessionsToggle) {[m
[36m@@ -482,7 +482,7 @@[m [masync function loadSessionsPanel() {[m
     }[m
 }[m
 window.boot = function () {[m
[31m-    console.log("ðŸ”¥ REACHED BOOT SECTION");[m
[32m+[m[32m    console.log("?? REACHED BOOT SECTION");[m
     wire();[m
     ensureSessionId?.();[m
     window.runModules?.();[m
[36m@@ -1522,7 +1522,7 @@[m [mimportant("pointer-events", "auto");[m
 [m
 const close = document.createElement("button");[m
 close.type = "button";[m
[31m-close.textContent = "Ã—";[m
[32m+[m[32mclose.textContent = "×";[m
 [m
 close.style.setProperty("margin-left", "auto", "important");[m
 close.style.setProperty("width", "32px", "important");[m
[36m@@ -4913,7 +4913,7 @@[m [mif ([m
 [m
         actionRows.forEach((row) => row.remove());[m
 [m
[31m-        el.appendChild(makeActionRow(el));[m
[32m+[m[32m        // NOVA_DISABLE_DUPLICATE_FINAL_MESSAGE_ACTIONS_20260724[m
         el.dataset.novaFinalActionsOwner = "1";[m
     }[m
 [m
[36m@@ -5553,7 +5553,7 @@[m [mfunction closePanel(panel) {[m
         return ([m
             raw.includes("close") ||[m
             raw.includes("dismiss") ||[m
[31m-            label === "Ã—" ||[m
[32m+[m[32m            label === "×" ||[m
             label === "x" ||[m
             label === "close" ||[m
             label === "done"[m
[36m@@ -6339,7 +6339,7 @@[m [mfunction closePanel(panel) {[m
 [m
         return ([m
             text === "thinking..." ||[m
[31m-            text === "thinkingâ€¦" ||[m
[32m+[m[32m            text === "thinking…" ||[m
             text.includes("thinking") ||[m
             text.includes("generating") ||[m
             text.includes("loading")[m
[36m@@ -6599,7 +6599,7 @@[m [mfunction closePanel(panel) {[m
 [m
         return ([m
             text === "thinking..." ||[m
[31m-            text === "thinkingâ€¦" ||[m
[32m+[m[32m            text === "thinking…" ||[m
             text.includes("thinking") ||[m
             text.includes("generating") ||[m
             text.includes("loading")[m
[36m@@ -8140,7 +8140,7 @@[m [mfunction closePanel(panel) {[m
             '<div style="display:flex;gap:8px;">',[m
             '<button id="nova-auth-workmode-login" style="flex:1;padding:9px;border-radius:9px;border:0;font-weight:700;">Login</button>',[m
             '<button id="nova-auth-workmode-register" style="flex:1;padding:9px;border-radius:9px;border:0;font-weight:700;">Register</button>',[m
[31m-            '<button id="nova-auth-workmode-close" style="width:44px;padding:9px;border-radius:9px;border:0;">Ã—</button>',[m
[32m+[m[32m            '<button id="nova-auth-workmode-close" style="width:44px;padding:9px;border-radius:9px;border:0;">×</button>',[m
             '</div>'[m
         ].join("");[m
 [m
[36m@@ -8541,7 +8541,7 @@[m [mfunction closePanel(panel) {[m
             '<div style="font-weight:900;font-size:16px;">Nova account</div>',[m
             '<div style="font-size:12px;opacity:.75;">Create an account or log in to save chats and restore sessions.</div>',[m
             '</div>',[m
[31m-            '<button type="button" id="nova-auth-workmode-close-v2" style="' + buttonStyle(false) + ';width:44px;">Ã—</button>',[m
[32m+[m[32m            '<button type="button" id="nova-auth-workmode-close-v2" style="' + buttonStyle(false) + ';width:44px;">×</button>',[m
             '</div>',[m
             '<div id="' + STATUS_ID + '" style="font-size:13px;margin:8px 0 10px 0;color:rgba(255,255,255,.86);">Checking auth...</div>',[m
             '<label style="display:block;font-size:12px;opacity:.78;margin:0 0 4px 2px;">Username</label>',[m
