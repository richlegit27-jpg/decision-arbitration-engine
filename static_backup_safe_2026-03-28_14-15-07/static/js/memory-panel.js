(() => {
"use strict";

const memoryPanel = document.getElementById("memoryPanel");
const btnOpenMemory = document.getElementById("btnOpenMemory");
const btnCloseMemory = document.getElementById("closeMemoryPanelBtn");
const btnDeleteAll = document.getElementById("deleteAllMemoryBtn");

let memoryItems = [];

function renderMemory() {
    if(!memoryPanel) return;
    const list = memoryPanel.querySelector(".memory-list");
    if(!list) return;
    list.innerHTML = "";
    if(memoryItems.length === 0){
        list.innerHTML = `<div class="empty-state-card">No memory saved</div>`;
        return;
    }
    memoryItems.forEach(item=>{
        const div = document.createElement("div");
        div.className = "memory-item";
        div.textContent = item;
        list.appendChild(div);
    });
}

function openPanel(){ memoryPanel.classList.add("open"); }
function closePanel(){ memoryPanel.classList.remove("open"); }
function deleteAllMemory(){ memoryItems=[]; renderMemory(); }

btnOpenMemory?.addEventListener("click", openPanel);
btnCloseMemory?.addEventListener("click", closePanel);
btnDeleteAll?.addEventListener("click", deleteAllMemory);

renderMemory();
})();