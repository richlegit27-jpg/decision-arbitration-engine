// C:\Users\Owner\nova\static\js\composer-reactive.js
(() => {
"use strict"

const chatStateApi = window.NovaChatState
if(!chatStateApi) throw new Error("NovaComposerReactive: NovaChatState is required")
const { state } = chatStateApi

const el = {
  composerForm: document.getElementById("composerForm"),
  composerInput: document.getElementById("composerInput"),
  sendBtn: document.getElementById("sendBtn"),
  attachBtn: document.getElementById("attachBtn"),
  imageBtn: document.getElementById("imageBtn"),
  voiceBtn: document.getElementById("voiceBtn"),
  pendingAttachments: document.getElementById("pendingAttachments"),
  memoryPanel: document.getElementById("memoryPanel"),
  messagesContainer: document.getElementById("messagesContainer"),
  thinkingStatus: document.getElementById("thinkingStatus"),
  voiceStatus: document.getElementById("voiceStatus"),
  imageModeHint: document.getElementById("imageModeHint"),
}

let eventsBound = false
let mediaRecorder = null
let mediaStream = null
let recordingChunks = []
let isRecording = false
const MAX_TEXTAREA_HEIGHT = 240

// --- Utilities ---
function makeId(prefix="msg"){ return window.crypto?.randomUUID ? `${prefix}_${window.crypto.randomUUID()}` : `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}` }
function nowIso(){ return new Date().toISOString() }
function escapeHtml(value){ return String(value||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;") }
function ensureMessages(){ if(!Array.isArray(state.messages)) state.messages=[]; return state.messages }
function ensurePendingAttachments(){ if(!Array.isArray(state.pendingAttachments)) state.pendingAttachments=[]; return state.pendingAttachments }
function ensureMemory(){ if(!Array.isArray(state.memoryItems)) state.memoryItems=[]; return state.memoryItems }
function autoResizeComposer(){ if(el.composerInput){ el.composerInput.style.height="auto"; el.composerInput.style.height=`${Math.min(el.composerInput.scrollHeight,MAX_TEXTAREA_HEIGHT)}px`} }

// --- Rendering ---
function renderPendingAttachments(){
  if(!el.pendingAttachments) return
  const items = ensurePendingAttachments()
  if(!items.length){ el.pendingAttachments.innerHTML=""; el.pendingAttachments.classList.add("hidden"); return }
  el.pendingAttachments.classList.remove("hidden")
  el.pendingAttachments.innerHTML = items.map(a=>`
    <div class="pending-attachment-chip" data-remove-pending-attachment="${escapeHtml(a.id)}">
      <span>${escapeHtml(a.name)}</span>
      <button type="button" data-remove-pending-attachment="${escapeHtml(a.id)}">×</button>
    </div>
  `).join("")
}

function renderMemoryPanel(){
  if(!el.memoryPanel) return
  const items = ensureMemory()
  if(!items.length){ el.memoryPanel.innerHTML=`<p class="empty-memory">No memory yet</p>`; return }
  el.memoryPanel.innerHTML = items.map(m=>{
    const attachments = (m.attachments||[]).map(a=>`<div class="memory-attachment">${escapeHtml(a.name)}</div>`).join("")
    return `<div class="memory-item">${escapeHtml(m.text||"[Attachment]")}${attachments}</div>`
  }).join("")
}

function renderMessageList(){
  if(!el.messagesContainer) return
  const items = ensureMessages()
  el.messagesContainer.innerHTML = items.map(msg=>{
    const attachments = (msg.attachments||[]).map(a=>`<div class="message-attachment">${escapeHtml(a.name)}</div>`).join("")
    return `<div class="message ${msg.role}">${escapeHtml(msg.content||"[Attachment]")}${attachments}</div>`
  }).join("")
}

// --- Messages ---
function pushMessage(msg){
  ensureMessages().push(msg)
  ensureMemory().push({ id: makeId("mem"), text: msg.content||"[Attachment]", attachments: msg.attachments||[] })
  renderMessageList()
  renderMemoryPanel()
  window.dispatchEvent(new CustomEvent("nova:messages-changed",{detail:state.messages}))
  window.dispatchEvent(new CustomEvent("nova:memory-changed",{detail:state.memoryItems}))
}

function appendUserMessage(text, attachments=[]){ const msg={id:makeId("user"),role:"user",content:text,created_at:nowIso(),attachments}; pushMessage(msg); return msg }
function appendAssistantMessage(text, attachments=[]){ const msg={id:makeId("assistant"),role:"assistant",content:text,created_at:nowIso(),attachments}; pushMessage(msg); return msg }

// --- Attachments ---
function clearPendingAttachments(){ state.pendingAttachments=[]; renderPendingAttachments(); window.dispatchEvent(new CustomEvent("nova:attachments-changed",{detail:[]})) }
function removePendingAttachment(id){ state.pendingAttachments = ensurePendingAttachments().filter(a=>a.id!==id); renderPendingAttachments(); window.dispatchEvent(new CustomEvent("nova:attachments-changed",{detail:state.pendingAttachments})) }
async function readFileAsDataUrl(file){ return await new Promise((res,rej)=>{ const r=new FileReader(); r.onload=()=>res(String(r.result||"")); r.onerror=()=>rej(new Error(`Failed to read ${file?.name||"file"}`)); r.readAsDataURL(file) }) }
async function addFilesToPending(files){ const next=[]; for(const f of Array.from(files||[])){ const url = await readFileAsDataUrl(f); next.push({id:makeId("att"),name:f.name,type:f.type,size:f.size,url,content:""}) } state.pendingAttachments = [...ensurePendingAttachments(),...next]; renderPendingAttachments(); window.dispatchEvent(new CustomEvent("nova:attachments-changed",{detail:state.pendingAttachments})) }

// --- Voice recording ---
function getSupportedMimeType(){ const types=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/mp4"]; for(const t of types) if(window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t; return "" }
async function startVoiceRecording(){ mediaStream=await navigator.mediaDevices.getUserMedia({audio:true}); recordingChunks=[]; const mime=getSupportedMimeType(); mediaRecorder=mime?new MediaRecorder(mediaStream,{mimeType:mime}):new MediaRecorder(mediaStream); mediaRecorder.ondataavailable=e=>{if(e.data&&e.data.size>0) recordingChunks.push(e.data)}; mediaRecorder.start(); isRecording=true; if(el.voiceBtn){el.voiceBtn.textContent="Stop";el.voiceBtn.classList.add("is-recording")} if(el.voiceStatus) el.voiceStatus.textContent="Recording…"}
async function stopVoiceRecording(commit=true){ if(!mediaRecorder) return; await new Promise(r=>mediaRecorder.addEventListener("stop",r,{once:true})); mediaStream?.getTracks().forEach(t=>t.stop()); mediaStream=null; mediaRecorder=null; isRecording=false; if(el.voiceBtn){el.voiceBtn.textContent="🎤"; el.voiceBtn.classList.remove("is-recording")} if(el.voiceStatus) el.voiceStatus.textContent=""; if(!commit){recordingChunks=[];return} if(!recordingChunks.length)return; const blob=new Blob(recordingChunks,{type:mediaRecorder?.mimeType||"audio/webm"}); recordingChunks=[]; const url=await new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(String(r.result||"")); r.onerror=()=>rej(new Error("Voice note failed")); r.readAsDataURL(blob)}); state.pendingAttachments.push({id:makeId("voice"),name:`voice-${Date.now()}.webm`,type:blob.type,size:blob.size,url,content:""}); renderPendingAttachments(); window.dispatchEvent(new CustomEvent("nova:attachments-changed",{detail:state.pendingAttachments}))}

// --- Send ---
async function sendMessage(){ const text=String(el.composerInput?.value||"").trim(); const attachments=[...ensurePendingAttachments()]; if(!text&&!attachments.length) return; appendUserMessage(text||"[Attachment]",attachments); clearPendingAttachments(); el.composerInput.value=""; autoResizeComposer(); setTimeout(()=>appendAssistantMessage("This is a local offline response"),500) }

// --- Event handlers ---
function handleSubmit(e){e.preventDefault();sendMessage()}
function handleComposerKeydown(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}}
function handlePendingAttachmentsClick(e){const t=e.target.closest("[data-remove-pending-attachment]");if(t)removePendingAttachment(t.getAttribute("data-remove-pending-attachment"))}
async function handleAttachClick(){const input=document.createElement("input");input.type="file";input.multiple=true;input.onchange=async()=>{await addFilesToPending(input.files)};input.click()}
function handleImageClick(){el.composerInput.value=`/image ${el.composerInput.value||""}`;el.composerInput.focus();if(el.imageModeHint){el.imageModeHint.textContent="Image mode ready";setTimeout(()=>{el.imageModeHint.textContent=""},1500)}}
async function handleVoiceClick(){if(isRecording){await stopVoiceRecording(true)}else{await startVoiceRecording()}}

// --- Bind ---
function bindEvents(){ if(eventsBound) return; el.composerForm?.addEventListener("submit",handleSubmit); el.composerInput?.addEventListener("input",autoResizeComposer); el.composerInput?.addEventListener("keydown",handleComposerKeydown); el.pendingAttachments?.addEventListener("click",handlePendingAttachmentsClick); el.attachBtn?.addEventListener("click",handleAttachClick); el.imageBtn?.addEventListener("click",handleImageClick); el.voiceBtn?.addEventListener("click",handleVoiceClick); eventsBound=true }

// --- Init ---
function init(){ ensureMessages(); ensurePendingAttachments(); ensureMemory(); bindEvents(); autoResizeComposer(); renderPendingAttachments(); renderMemoryPanel(); renderMessageList() }
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",init,{once:true})}else{init()}

window.NovaComposerReactive={sendMessage,addFilesToPending,clearPendingAttachments,renderPendingAttachments,renderMessageList,renderMemoryPanel}
})();