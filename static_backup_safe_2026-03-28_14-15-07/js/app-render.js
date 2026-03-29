(() => {
"use strict";
if(window.__novaRenderLoaded) return;
window.__novaRenderLoaded=true;

const app = window.NovaApp || (window.NovaApp = {});
app.state = app.state || {};

function byId(id){ return document.getElementById(id); }

function renderMessage(msg, role){
    const chat = byId("chatMessages");
    const div = document.createElement("div");
    div.className = "message "+role+" fade-in";
    div.textContent = msg;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}
app.renderMessage = renderMessage;
})();