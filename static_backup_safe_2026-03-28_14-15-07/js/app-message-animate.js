(() => {
"use strict";

// Override renderMessage to animate incoming messages sequentially
const originalRenderMessages = window.renderMessages || function(messages){
  const container = document.getElementById("messageContainer");
  container.innerHTML = "";
  messages.forEach(msg => {
    const div = document.createElement("div");
    div.className = "chat-message " + msg.role;
    let attachmentsHtml = "";
    if(msg.attachments?.length){
      attachmentsHtml = msg.attachments.map(a => `<div><a href="${a.url}" target="_blank">${a.filename}</a></div>`).join("");
    }
    div.innerHTML = `<strong>${msg.role}:</strong> ${msg.content}${attachmentsHtml}`;
    container.appendChild(div);
    div.style.opacity = 0;
    setTimeout(() => div.style.opacity = 1, 50);
  });
  container.scrollTop = container.scrollHeight;
};

// New sequential render
window.renderMessages = async function(messages){
  const container = document.getElementById("messageContainer");
  container.innerHTML = "";
  for(let i=0;i<messages.length;i++){
    const msg = messages[i];
    const div = document.createElement("div");
    div.className = "chat-message " + msg.role;
    let attachmentsHtml = "";
    if(msg.attachments?.length){
      attachmentsHtml = msg.attachments.map(a => `<div><a href="${a.url}" target="_blank">${a.filename}</a></div>`).join("");
    }
    div.innerHTML = `<strong>${msg.role}:</strong> ${msg.content}${attachmentsHtml}`;
    div.style.opacity = 0;
    container.appendChild(div);
    // fade in
    setTimeout(() => div.style.opacity = 1, 50);
    container.scrollTop = container.scrollHeight;
    // delay next message for animation effect
    await new Promise(r => setTimeout(r, 120));
  }
};
})();