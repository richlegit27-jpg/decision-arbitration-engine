(() => {
"use strict";

const chatWindow = document.getElementById("chatWindow");
const composerInput = document.getElementById("composerInput");
const sendBtn = document.getElementById("sendBtn");
const stopBtn = document.getElementById("stopBtn");
const voiceBtn = document.getElementById("voiceBtn");
const attachBtn = document.getElementById("attachBtn");
const fileInput = document.getElementById("fileInput");
const workspace = document.querySelector(".workspace");
const sidebar = document.querySelector(".sidebar");

let streamController = null;

// ------------------- UTIL -------------------
function appendMessage(content, type="user"){
  const msg = document.createElement("div");
  msg.className = `chat-message ${type}`;
  msg.innerText = content;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ------------------- SEND -------------------
async function sendMessage(content){
  if(!content) return;
  appendMessage(content, "user");
  composerInput.value = "";
  stopBtn.disabled = false;

  try {
    streamController = new AbortController();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({message: content}),
      signal: streamController.signal
    });
    if(!res.ok) throw new Error("Send failed");
    const data = await res.json();
    appendMessage(data.reply || "[No reply]", "ai");
  } catch(err){
    appendMessage("[Error] " + err.message, "system");
  } finally {
    stopBtn.disabled = true;
    streamController = null;
  }
}

// ------------------- STOP -------------------
function stopMessage(){
  if(streamController){
    streamController.abort();
    streamController = null;
    stopBtn.disabled = true;
    appendMessage("[Stopped]", "system");
  }
}

// ------------------- VOICE -------------------
async function startVoice(){
  if(!navigator.mediaDevices?.getUserMedia){
    alert("Voice input not supported");
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  const recorder = new MediaRecorder(stream);
  let chunks = [];

  recorder.ondataavailable = e => chunks.push(e.data);
  recorder.onstop = async () => {
    const blob = new Blob(chunks, {type:'audio/webm'});
    const form = new FormData();
    form.append("file", blob, "voice.webm");
    const res = await fetch("/api/voice", {method:"POST", body: form});
    const json = await res.json();
    composerInput.value = json.transcript || "";
  };

  recorder.start();
  setTimeout(()=>recorder.stop(),5000);
}

// ------------------- ATTACH -------------------
attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", async e => {
  const file = e.target.files[0];
  if(!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", {method:"POST", body: form});
  const json = await res.json();
  appendMessage(`[File uploaded] ${file.name}`, "system");
});

// ------------------- BACKGROUND TOGGLE -------------------
const colors = ["#0b0f14","#1a1f2b","#101820","#2b1a1f"];
let bgIndex = 0;
const bgToggleBtn = document.getElementById("bgToggleBtn");
bgToggleBtn.addEventListener("click", () => {
  bgIndex = (bgIndex + 1) % colors.length;
  workspace.style.background = colors[bgIndex];
  sidebar.style.background = colors[bgIndex];
});

// ------------------- EVENT LISTENERS -------------------
sendBtn.addEventListener("click", () => sendMessage(composerInput.value));
stopBtn.addEventListener("click", stopMessage);
voiceBtn.addEventListener("click", startVoice);
composerInput.addEventListener("keydown", e => {
  if(e.key === "Enter" && !e.shiftKey){
    e.preventDefault();
    sendMessage(composerInput.value);
  }
});
})();