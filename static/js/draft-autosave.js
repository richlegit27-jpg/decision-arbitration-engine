/* notepad C:\Users\Owner\nova\static\js\draft-autosave.js */

(() => {
"use strict";

document.addEventListener("DOMContentLoaded", () => {

  const input = document.getElementById("messageInput");

  if(!input) return;

  const KEY = "nova_draft_message";

  /* restore draft */

  const saved = localStorage.getItem(KEY);

  if(saved){
    input.value = saved;
  }

  /* save draft while typing */

  input.addEventListener("input", () => {
    localStorage.setItem(KEY, input.value);
  });

  /* clear draft when message sent */

  const sendBtn = document.getElementById("sendBtn");

  if(sendBtn){
    sendBtn.addEventListener("click", () => {
      localStorage.removeItem(KEY);
    });
  }

});
})();