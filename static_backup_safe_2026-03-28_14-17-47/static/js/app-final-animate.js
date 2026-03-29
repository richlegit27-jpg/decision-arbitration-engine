(() => {
"use strict";

// Memory panel slide toggle
const memoryPanel = document.getElementById("memoryPanel");
const btnOpenMemory = document.getElementById("btnOpenMemory");
const btnCloseMemory = document.getElementById("closeMemoryPanelBtn");

btnOpenMemory.addEventListener("click", () => {
  memoryPanel.classList.add("active");
});

btnCloseMemory.addEventListener("click", () => {
  memoryPanel.classList.remove("active");
});

// Animate file thumbnails when attached
const attachInput = document.getElementById("attachInput");
const dropZone = document.getElementById("dropZone");

function addFileThumbnail(file){
  const thumb = document.createElement("div");
  thumb.className = "file-thumb";
  thumb.textContent = file.name;
  dropZone.appendChild(thumb);

  // Remove file on click
  thumb.addEventListener("click", () => {
    thumb.remove();
    const dt = new DataTransfer();
    Array.from(attachInput.files)
      .filter(f => f.name !== file.name)
      .forEach(f => dt.items.add(f));
    attachInput.files = dt.files;
  });
}

attachInput.addEventListener("change", () => {
  dropZone.querySelectorAll(".file-thumb").forEach(t => t.remove());
  Array.from(attachInput.files).forEach(f => addFileThumbnail(f));
});
})();