(() => {
  "use strict";

  if (window.__novaArtifactsAutoPersistLoaded) return;
  window.__novaArtifactsAutoPersistLoaded = true;

  console.log("ðŸš€ Nova Phase 4 Auto-Persist Artifacts Engaged");

  const Nova = (window.Nova = window.Nova || {});
  Nova.artifacts = Nova.artifacts || {};
  Nova.chatStream = Nova.chatStream || {};

  const state = Nova.state;

  function byId(id) { return document.getElementById(id); }
  function qsa(selector, root = document) { return Array.from((root || document).querySelectorAll(selector)); }
  function makeId(prefix="artifact") { return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,10)}`; }

  function normalizeArtifact(input) {
    if (!input) return null;
    const now = new Date().toISOString();
    return {
      id: input.id || input.artifact_id || makeId(),
      title: input.title || input.name || "Untitled Artifact",
      type: input.type || input.kind || "document",
      content: input.content || input.text || "",
      source_prompt: input.prompt || input.source_prompt || "",
      route_mode: input.route_mode || "manual",
      contract: input.contract || "direct",
      created_at: input.created_at || now,
      updated_at: input.updated_at || now,
      meta: input.meta || {},
    };
  }

  function getArtifactStore() {
    if (!state.artifacts || typeof state.artifacts !== "object") state.artifacts = {};
    return state.artifacts;
  }

  function mergeArtifacts(nextArtifacts) {
    const store = getArtifactStore();
    const arr = Array.isArray(nextArtifacts) ? nextArtifacts : [nextArtifacts];
    arr.forEach(a => {
      const normalized = normalizeArtifact(a);
      if (normalized?.id) store[normalized.id] = {...(store[normalized.id]||{}), ...normalized};
    });
    renderArtifacts();
    return store;
  }

  function getArtifactsArray() { return Object.values(getArtifactStore()).sort((a,b)=>String(b.updated_at||b.created_at).localeCompare(String(a.updated_at||a.created_at))); }

  function renderArtifacts() {
    const listEl = byId("novaArtifactsList");
    const countEl = byId("novaArtifactsCount");
    const emptyEl = byId("novaArtifactsEmpty");
    const artifacts = getArtifactsArray();
    if (countEl) countEl.textContent = artifacts.length;
    if (emptyEl) emptyEl.hidden = artifacts.length > 0;
    if (!listEl) return;
    listEl.innerHTML = artifacts.map(item=>{
      const preview = (item.content||"").slice(0,280);
      return `<article class="nova-artifact-card" data-artifact-id="${item.id}">
        <div class="nova-artifact-card-head"><h4>${item.title}</h4><div>${item.type}</div></div>
        <div class="nova-artifact-card-body"><pre>${preview}</pre></div>
        <div class="nova-artifact-card-actions">
          <button data-action="open-artifact" data-artifact-id="${item.id}">Open</button>
          <button data-action="copy-artifact" data-artifact-id="${item.id}">Copy</button>
        </div>
      </article>`;
    }).join("");
    bindArtifactButtons();
  }

  function bindArtifactButtons() {
    qsa("[data-action='open-artifact']").forEach(btn=>{
      if(btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click",()=>openArtifact(btn.dataset.artifactId));
    });
    qsa("[data-action='copy-artifact']").forEach(btn=>{
      if(btn.dataset.boundCopy) return;
      btn.dataset.boundCopy="1";
      btn.addEventListener("click",async ()=>{
        const artifact = getArtifactStore()[btn.dataset.artifactId];
        if(!artifact) return;
        try { await navigator.clipboard.writeText(artifact.content||""); } catch {}
      });
    });
    const closeBtn = byId("artifactViewerCloseBtn");
    if(closeBtn && !closeBtn.dataset.bound) {
      closeBtn.dataset.bound = "1";
      closeBtn.addEventListener("click",()=>byId("novaArtifactViewer").hidden=true);
    }
  }

  function openArtifact(id) {
    const artifact = getArtifactStore()[id];
    if(!artifact) return;
    const viewer = byId("novaArtifactViewer");
    if(!viewer) return;
    byId("novaArtifactViewerTitle").textContent = artifact.title;
    byId("novaArtifactViewerContent").textContent = artifact.content;
    byId("novaArtifactViewerType").textContent = artifact.type;
    byId("novaArtifactViewerTime").textContent = new Date(artifact.updated_at).toLocaleString();
    viewer.hidden = false;
  }

  function extractArtifactsFromMessage(msg) {
    const found = [];
    if(!msg) return found;
    if(Array.isArray(msg)) msg.forEach(m=>found.push(...extractArtifactsFromMessage(m)));
    else if(typeof msg==="object"){
      if(msg.artifacts) found.push(...msg.artifacts);
      if(msg.content||msg.text) found.push({title:"Chat Artifact", type:"document", content:msg.content||msg.text, meta:msg.meta||{}});
    }
    return found;
  }

  function persistMessageArtifacts(msg){
    const artifacts = extractArtifactsFromMessage(msg);
    if(!artifacts.length) return [];
    return mergeArtifacts(artifacts);
  }

  // Hook into chat-stream
  if(Nova.chatStream){
    const oldSend = Nova.chatStream.sendCurrentMessage;
    Nova.chatStream.sendCurrentMessage = async function(...args){
      const msg = await oldSend.apply(this,args);
      persistMessageArtifacts(msg);
      return msg;
    };
    const oldHandle = Nova.chatStream.handleStreamEvent;
    Nova.chatStream.handleStreamEvent = async function(eventName,payload){
      const result = await oldHandle.apply(this,[eventName,payload]);
      persistMessageArtifacts(payload);
      return result;
    };
  }

  // Global hook for direct chat messages
  window.addEventListener("nova:chat-response",e=>{
    persistMessageArtifacts(e.detail);
  });

  console.log("âœ… Nova Phase 4 Auto-Persist Artifacts Loaded");
})();

