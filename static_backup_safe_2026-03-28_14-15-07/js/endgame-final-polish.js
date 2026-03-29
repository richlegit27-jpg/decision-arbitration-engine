(() => {
"use strict";

// --- Memory card animation ---
// Already handled by CSS; ensure new cards get 'memory-card' class
const renderMemoryCard = (item) => {
  const li = document.createElement("div");
  li.className = "memory-card";
  li.textContent = item.text;
  return li;
};

window.renderMemory = (memoryItems) => {
  const memoryList = document.getElementById("memoryList");
  memoryList.innerHTML = "";
  memoryItems.forEach(item => memoryList.appendChild(renderMemoryCard(item)));
};

// --- Chat input improvements ---
const chatInput = document.getElementById("chatInput");
chatInput.addEventListener("keydown", (e) => {
  if(e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("composer").requestSubmit();
  }
});

// --- Voice recording live indicator ---
const voiceBtn = document.getElementById("voiceBtn");
voiceBtn.addEventListener("click", () => {
  if(voiceBtn.dataset.recording === "true") {
    voiceBtn.dataset.recording = "false";
    voiceBtn.classList.remove("recording");
  } else {
    voiceBtn.dataset.recording = "true";
    voiceBtn.classList.add("recording");
  }
});

// --- Attachment previews for images/audio ---
const attachInput = document.getElementById("attachInput");
const dropZone = document.getElementById("dropZone");

function showFilePreview(file){
  const thumb = document.createElement("div");
  thumb.className = "file-thumb";
  thumb.textContent = file.name;

  // Preview images or audio
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

  // Remove file on click
  thumb.addEventListener("click", ()=>{
    thumb.remove();
    const dt = new DataTransfer();
    Array.from(attachInput.files)
      .filter(f => f.name !== file.name)
      .forEach(f => dt.items.add(f));
    attachInput.files = dt.files;
  });
}

attachInput.addEventListener("change", ()=>{
  dropZone.querySelectorAll(".file-thumb").forEach(t=>t.remove());
  Array.from(attachInput.files).forEach(f=>showFilePreview(f));
});
})();