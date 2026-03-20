/* --- NOVA_CHAT_WIRE v1: /api/chat + /api/chat --- */
function __novaUpstream(){
  try{
    const u = (localStorage.getItem("NOVA_UPSTREAM") || "").trim().toLowerCase();
    return (u === "openai" || u === "ollama") ? u : "";
  }catch(e){ return ""; }
}
function __novaModel(){
  try{ return (localStorage.getItem("NOVA_MODEL") || "").trim(); }catch(e){ return ""; }
}
function __novaChatPayload(text){
  const model = __novaModel();
  const upstream = __novaUpstream();
  const payload = {
    messages: [{ role: "user", content: String(text ?? "") }]
  };
  if(upstream) payload.upstream = upstream;
  if(model) payload.model = model;
  return payload;
}
/* --- /NOVA_CHAT_WIRE v1 --- */
window.__novaGetKey = function(){
    try{
      const k = (window.NOVA_API_KEY || localStorage.getItem("NOVA_API_KEY") || "").trim();
      if(k) { try{ (() => { const __v = (k); const __k = (""+(__v ?? "")).trim(); if(!__k || __k==="undefined" || __k==="null"){ console.log("BLOCK NOVA_API_KEY write:", __v); return; } localStorage.setItem("NOVA_API_KEY", __k); console.log("STORED NOVA_API_KEY len=", __k.length); })(); }catch(e){} }
      return k;
    }catch(e){
      return (window.NOVA_API_KEY || "").trim();
    }
  };



