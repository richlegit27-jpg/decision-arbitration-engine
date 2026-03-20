(() => {
"use strict";

// --- Memory panel enhancements ---
const memoryPanel = document.getElementById("memoryPanel");
const memoryList = document.getElementById("memoryList");
const deleteAllBtn = document.getElementById("deleteAllMemoryBtn");
const btnOpenMemory = document.getElementById("btnOpenMemory");
const btnCloseMemory = document.getElementById("closeMemoryPanelBtn");

btnOpenMemory.addEventListener("click", () => {
  memoryPanel.classList.add("active");
});

btnCloseMemory.addEventListener("click", () => {
  memoryPanel.classList.remove("active");
});

deleteAllBtn.addEventListener("click", async () => {
  const res = await fetch("/api/memory/delete_all", { method: "POST" });
  const data = await res.json();
  memoryList.innerHTML = "";
  data.memory_items.forEach(item => {
    const li = document.createElement("div");
    li.className = "memory-card";
    li.textContent = item.text;
    memoryList.appendChild(li);
    li.scrollIntoView({ behavior: "smooth" });
  });
});

window.renderMemory = (memoryItems) => {
  memoryList.innerHTML = "";
  memoryItems.forEach(item => {
    const li = document.createElement("div");
    li.className = "memory-card";
    li.textContent = item.text;
    memoryList.appendChild(li);
    li.scrollIntoView({ behavior: "smooth" });
  });
};

// --- Chat input enhancements ---
const chatForm = document.getElementById("composer");
const chatInput = document.getElementById("chatInput");
const messageContainer = document.getElementById("messageContainer");

chatInput.addEventListener("keydown", (e) => {
  if(e.key === "Enter" && !e.shiftKey){
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

// --- Voice recording UI ---
const voiceBtn = document.getElementById("voiceBtn");
let mediaRecorder, recordingChunks = [];

voiceBtn.addEventListener("click", async () => {
  if(voiceBtn.dataset.recording === "true"){
    mediaRecorder.stop();
    voiceBtn.dataset.recording = "false";
    voiceBtn.classList.remove("recording");
  } else {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    recordingChunks = [];
    mediaRecorder.ondataavailable = e => recordingChunks.push(e.data);
    mediaRecorder.onstop = () => {
      const blob = new Blob(recordingChunks, { type: 'audio/webm' });
      const file = new File([blob], `voice_${Date.now()}.webm`, { type: blob.type });
      const dt = new DataTransfer();
      dt.items.add(file);
      Array.from(document.getElementById("attachInput").files).forEach(f => dt.items.add(f));
      document.getElementById("attachInput").files = dt.files;
      showFilePreview(file);
    };
    mediaRecorder.start();
    voiceBtn.dataset.recording = "true";
    voiceBtn.classList.add("recording");
  }
});

// --- Attachment previews ---
const attachInput = document.getElementById("attachInput");
const dropZone = document.getElementById("dropZone");

function showFilePreview(file){
  const thumb = document.createElement("div");
  thumb.className = "file-thumb";
  thumb.textContent = file.name;

  if(file.type.startsWith("image/")){
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    thumb.appendChild(img);
  } else if(file.type.startsWith("audio/")){
    const audio = document.createElement("audio");
    audio.src = URL.createObjectURL(file);
    audio.controls = true;
    thumb.appendChild(audio);
  }

  dropZone.appendChild(thumb);

  thumb.addEventListener("click", () => {
    thumb.remove();
    const dt = new DataTransfer();
    Array.from(attachInput.files).filter(f => f.name !== file.name).forEach(f => dt.items.add(f));
    attachInput.files = dt.files;
  });
}

attachInput.addEventListener("change", () => {
  dropZone.querySelectorAll(".file-thumb").forEach(t => t.remove());
  Array.from(attachInput.files).forEach(f => showFilePreview(f));
});

// --- Chat message slide/fade-in ---
window.renderMessages = async (messages) => {
  messageContainer.innerHTML = "";
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
    messageContainer.appendChild(div);
    setTimeout(() => div.style.opacity = 1, 50);
    messageContainer.scrollTop = messageContainer.scrollHeight;
    await new Promise(r => setTimeout(r, 120));
  }
};
})();