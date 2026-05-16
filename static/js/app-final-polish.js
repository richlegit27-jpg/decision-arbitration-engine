(() => {
"use strict";

// --------------------------
// Voice Recording UI
// --------------------------
const voiceBtn = document.getElementById("voiceBtn");
let mediaRecorder;
let recordingChunks = [];

voiceBtn.addEventListener("click", async () => {
  if(voiceBtn.dataset.recording === "true"){
    // Stop recording
    mediaRecorder.stop();
    voiceBtn.dataset.recording = "false";
    voiceBtn.textContent = "🎤 Record";
  } else {
    // Start recording
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    recordingChunks = [];

    mediaRecorder.ondataavailable = e => recordingChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(recordingChunks, { type: 'audio/webm' });
      const file = new File([blob], `voice_${Date.now()}.webm`, { type: blob.type });
      // append to attachInput
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      const attachInput = document.getElementById("attachInput");
      for(let i=0;i<attachInput.files.length;i++){
        dataTransfer.items.add(attachInput.files[i]);
      }
      attachInput.files = dataTransfer.files;

      // Optional: show thumbnail in dropZone
      showFileThumbnail(file);
    };

    mediaRecorder.start();
    voiceBtn.dataset.recording = "true";
    voiceBtn.textContent = "⏺ Recording...";
  }
});

// --------------------------
// Drag & Drop File Thumbnails
// --------------------------
const dropZone = document.getElementById("dropZone");
function showFileThumbnail(file){
  let thumb = document.createElement("div");
  thumb.className = "file-thumb";
  thumb.textContent = file.name;
  dropZone.appendChild(thumb);

  // Remove thumbnail on click
  thumb.addEventListener("click", () => {
    thumb.remove();
    const attachInput = document.getElementById("attachInput");
    const dt = new DataTransfer();
    Array.from(attachInput.files)
      .filter(f => f.name !== file.name)
      .forEach(f => dt.items.add(f));
    attachInput.files = dt.files;
  });
}

const attachInput = document.getElementById("attachInput");
attachInput.addEventListener("change", () => {
  // Clear old thumbnails
  dropZone.querySelectorAll(".file-thumb").forEach(t => t.remove());
  Array.from(attachInput.files).forEach(f => showFileThumbnail(f));
});

// Visual hover effect for drag over
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => dropZone.classList.remove("dragover"));
})();