(function(){
"use strict";

// Sidebar
const sidebarBtn=document.getElementById("sidebarToggle");
sidebarBtn?.addEventListener("click",()=>document.getElementById("novaSidebar").classList.toggle("collapsed"));

// Assets
const state={assetsItems:[]};
async function loadAssets(){
  const artifacts=await fetch("/api/artifacts").then(r=>r.json());
  const media=await fetch("/api/media").then(r=>r.json());
  state.assetsItems=[...artifacts,...media];
  const container=document.getElementById("novaAssetsList");
  container.innerHTML="";
  state.assetsItems.forEach(item=>{
    const div=document.createElement("div");
    div.className="asset-card";
    div.innerHTML=`
      <div class="asset-preview">
        ${item.type.startsWith("image/")?`<img src="${item.url}">`:''}
        ${item.type.startsWith("video/")?`<video src="${item.url}" controls></video>`:''}
        ${item.type==="application/pdf"?`<iframe src="${item.url}#page=1"></iframe>`:''}
      </div>
      <button class="asset-action pin">${item.pinned?"📌":"📍"}</button>
      <button class="asset-action delete">Delete</button>
    `;
    container.appendChild(div);
    div.querySelector(".pin").addEventListener("click",async e=>{e.stopPropagation();await fetch(`/api/artifacts/toggle-pin/${item.id}`,{method:"POST"});loadAssets();});
    div.querySelector(".delete").addEventListener("click",async e=>{e.stopPropagation();const url=artifacts.includes(item)?`/api/artifacts/delete/${item.id}`:`/api/media/delete/${item.id}`;await fetch(url,{method:"POST"});loadAssets();});
    div.querySelector(".asset-preview").addEventListener("click",()=>openLightbox(item));
  });
}

function openLightbox(item){
  const preview=document.getElementById("novaLightboxPreview"); preview.innerHTML="";
  if(item.type.startsWith("image/")) preview.innerHTML=`<img src="${item.url}">`;
  else if(item.type.startsWith("video/")) preview.innerHTML=`<video src="${item.url}" controls style="max-height:90vh"></video>`;
  else if(item.type==="application/pdf") preview.innerHTML=`<iframe src="${item.url}#page=1" style="width:90vw;height:90vh;"></iframe>`;
  document.getElementById("novaLightbox").style.display="flex";
}
document.getElementById("novaLightboxClose")?.addEventListener("click",()=>document.getElementById("novaLightbox").style.display="none");

// Chat
const chatInput=document.getElementById("novaChatInput");
const chatBtn=document.getElementById("novaSendBtn");
const chatMessages=document.getElementById("novaMessages");
chatBtn?.addEventListener("click",sendMessage);
chatInput?.addEventListener("keypress",e=>{if(e.key==='Enter')sendMessage();});
async function sendMessage(){const content=chatInput.value.trim();if(!content)return;appendMessage("user",content);chatInput.value="";const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({content})});const data=await res.json();appendMessage("assistant",data.reply||"…");}
function appendMessage(role,text){const div=document.createElement("div");div.className=`chat-message ${role}`;div.textContent=text;chatMessages.appendChild(div);chatMessages.scrollTop=chatMessages.scrollHeight;}

// Memory
const memoryInput=document.getElementById("novaMemoryInput");
const memoryBtn=document.getElementById("novaMemoryAdd");
const memoryList=document.getElementById("novaMemoryList");
memoryBtn?.addEventListener("click",async ()=>{const val=memoryInput.value.trim();if(!val)return;memoryInput.value="";await fetch("/api/memory/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({value:val})});const li=document.createElement("li");li.textContent=val;memoryList.appendChild(li);});

// Bootstrap
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",loadAssets);
else loadAssets();
})();