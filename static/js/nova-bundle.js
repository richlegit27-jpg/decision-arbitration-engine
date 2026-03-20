(() => {
"use strict";

/* --- CORE APP LOGIC --- */
const chatForm = document.getElementById("composer");
const chatInput = document.getElementById("chatInput");
const messageContainer = document.getElementById("messageContainer");
const attachInput = document.getElementById("attachInput");
const dropZone = document.getElementById("dropZone");
const memoryPanel = document.getElementById("memoryPanel");
const memoryList = document.getElementById("memoryList");
const btnNewChat = document.getElementById("btnNewChat");
const btnOpenMemory = document.getElementById("btnOpenMemory");
const btnCloseMemory = document.getElementById("closeMemoryPanelBtn");
const deleteAllBtn = document.getElementById("deleteAllMemoryBtn");
const voiceBtn = document.getElementById("voiceBtn");
window.currentChatId = "default";

// Helper: Render messages sequentially
window.renderMessages = async function(messages){
  messageContainer.innerHTML = "";
  for(let i=0;i<messages.length;i++){
    const msg = messages[i];
    const div = document.createElement("div");
    div.className = "chat-message " + msg.role;
    let attachmentsHtml = "";
    if(msg.attachments?.length){
      attachmentsHtml = msg.attachments.map(a=>`<div><a href="${a.url}" target="_blank">${a.filename}</a></div>`).join("");
    }
    div.innerHTML = `<strong>${msg.role}:</strong> ${msg.content}${attachmentsHtml}`;
    div.style.opacity=0;
    messageContainer.appendChild(div);
    setTimeout(()=>div.style.opacity=1,50);
    messageContainer.scrollTop=messageContainer.scrollHeight;
    await new Promise(r=>setTimeout(r,120));
  }
};

// Fetch chats & memory
async function fetchChats(){
  const res = await fetch("/api/chats");
  const data = await res.json();
  const chat = data.chats.find(c=>c.id===window.currentChatId);
  if(chat) window.renderMessages(chat.messages);
  if(window.renderMemory) window.renderMemory(data.memory_items);
}

// Send message
chatForm.addEventListener("submit",async e=>{
  e.preventDefault();
  const formData = new FormData();
  formData.append("message",chatInput.value);
  formData.append("chat_id",window.currentChatId);
  for(let i=0;i<attachInput.files.length;i++){formData.append("attachments",attachInput.files[i]);}
  const res=await fetch("/api/chat",{method:"POST",body:formData});
  const data=await res.json();
  chatInput.value="";
  attachInput.value="";
  window.renderMessages(data.chat.messages);
  if(window.renderMemory) window.renderMemory(data.memory_items);
});

// Drag & Drop files
dropZone.addEventListener("click",()=>attachInput.click());
dropZone.addEventListener("dragover",e=>e.preventDefault());
dropZone.addEventListener("drop",e=>{e.preventDefault();attachInput.files=e.dataTransfer.files;});

// Sidebar toggle
btnNewChat.addEventListener("click",()=>{
  window.currentChatId="chat_"+Date.now();
  messageContainer.innerHTML="";
  fetchChats();
});
btnOpenMemory.addEventListener("click",()=>memoryPanel.classList.add("active"));
btnCloseMemory.addEventListener("click",()=>memoryPanel.classList.remove("active"));

// Memory panel delete all
deleteAllBtn.addEventListener("click",async()=>{
  const res=await fetch("/api/memory/delete_all",{method:"POST"});
  const data=await res.json();
  memoryList.innerHTML="";
  data.memory_items.forEach(item=>{
    const li=document.createElement("div");
    li.textContent=item.text;
    li.className="memory-card";
    memoryList.appendChild(li);
  });
});

// Voice recording
let mediaRecorder,recordingChunks=[];
voiceBtn.addEventListener("click",async()=>{
  if(voiceBtn.dataset.recording==="true"){mediaRecorder.stop();voiceBtn.dataset.recording="false";voiceBtn.textContent="🎤 Record";}
  else{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    mediaRecorder=new MediaRecorder(stream);recordingChunks=[];
    mediaRecorder.ondataavailable=e=>recordingChunks.push(e.data);
    mediaRecorder.onstop=async()=>{
      const blob=new Blob(recordingChunks,{type:'audio/webm'});
      const file=new File([blob],`voice_${Date.now()}.webm`,{type:blob.type});
      const dt=new DataTransfer();
      dt.items.add(file);
      Array.from(attachInput.files).forEach(f=>dt.items.add(f));
      attachInput.files=dt.files;
      showFileThumbnail(file);
    };
    mediaRecorder.start();voiceBtn.dataset.recording="true";voiceBtn.textContent="⏺ Recording...";
  }
});

// File thumbnails
function showFileThumbnail(file){
  const thumb=document.createElement("div");
  thumb.className="file-thumb";
  thumb.textContent=file.name;
  dropZone.appendChild(thumb);
  thumb.addEventListener("click",()=>{
    thumb.remove();
    const dt=new DataTransfer();
    Array.from(attachInput.files).filter(f=>f.name!==file.name).forEach(f=>dt.items.add(f));
    attachInput.files=dt.files;
  });
}
attachInput.addEventListener("change",()=>{
  dropZone.querySelectorAll(".file-thumb").forEach(t=>t.remove());
  Array.from(attachInput.files).forEach(f=>showFileThumbnail(f));
});

// Global render memory
window.renderMemory=data=>{memoryList.innerHTML="";data.forEach(item=>{const li=document.createElement("div");li.textContent=item.text;li.className="memory-card";memoryList.appendChild(li);});};

// Initial fetch
fetchChats();
})();