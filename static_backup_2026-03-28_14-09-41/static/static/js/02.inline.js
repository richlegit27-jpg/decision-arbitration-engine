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
/* NOVA_PREPEND_AUTH_CLEAN */
(() => {
  const clean = (k) => {
    k = (k ?? "").toString().trim();
    if(!k) return "";
    if(k === "undefined" || k === "null") return "";
    return k;
  };

  const getKey = () => {
    try { return clean(localStorage.getItem("NOVA_API_KEY")); } catch {}
    try { return clean(window.state && window.state.apiKey); } catch {}
    return "";
  };

  const origFetch = window.fetch && window.fetch.bind(window);
  if(!origFetch) return;

  window.fetch = async (input, init) => {
    const url = (typeof input === "string") ? input : (input && input.url) ? input.url : "";
    if(url.startsWith("/api/") || url.includes("/api/")){
      const k = getKey();
      init = init || {};
      const h = (init.headers instanceof Headers) ? init.headers : new Headers(init.headers || {});
      if(k){
        if(!h.get("Authorization")) h.set("Authorization", "Bearer " + k);
        if(!h.get("x-api-key"))     h.set("x-api-key", k);
      }
      init.headers = h;
    }
    return origFetch(input, init);
  };

  console.log("NOVA_PREPEND_AUTH_CLEAN active");
})();
/* NOVA_STOP_KEY_PROMPT_LOOP */
(() => {
  try {
    // 1) Guard against writing bad values ("undefined"/empty) to NOVA_API_KEY
    const __origSet = Storage.prototype.setItem;
    Storage.prototype.setItem = function(k, v){
      if (k === "NOVA_API_KEY") {
        const s = ("" + (v ?? "")).trim();
        if (!s || s === "undefined") {
          console.log("BLOCK setItem NOVA_API_KEY bad value:", v);
          return;
        }
        return __origSet.call(this, k, s);
      }
      return __origSet.call(this, k, v);
    };

    // 2) Block accidental clears unless explicitly allowed
    const __origRemove = Storage.prototype.removeItem;
    Storage.prototype.removeItem = function(k){
      if (k === "NOVA_API_KEY" && !window.__NOVA_ALLOW_KEY_CLEAR) {
        console.log("BLOCK removeItem NOVA_API_KEY (set window.__NOVA_ALLOW_KEY_CLEAR=true to allow)");
        return;
      }
      return __origRemove.call(this, k);
    };

    // 3) Intercept key prompt loops:
    //    - If key exists, auto-return it
    //    - If key missing, allow ONE prompt max, then stop spamming
    const __origPrompt = window.prompt ? window.prompt.bind(window) : null;
    if (__origPrompt) {
      window.prompt = function(msg, defVal){
        const m = (msg || "").toLowerCase();
        const looksLikeKeyPrompt = m.includes("api key") || m.includes("nova");
        if (looksLikeKeyPrompt) {
          const existing = (localStorage.getItem("NOVA_API_KEY") || "").trim();
          if (existing && existing !== "undefined") {
            console.log("PROMPT intercepted: using stored key len=", existing.length);
            return existing;
          }
          if (window.__novaPromptedOnce) {
            console.log("PROMPT blocked (already prompted once).");
            return defVal || "";
          }
          window.__novaPromptedOnce = true;
        }
        return __origPrompt(msg, defVal);
      };
    }

    // 4) If storage was poisoned earlier, wipe it once
    try {
      if (localStorage.getItem("NOVA_API_KEY") === "undefined") {
        localStorage.removeItem("NOVA_API_KEY"); // will be blocked unless allow flag; so allow briefly
      }
    } catch(e){}
  } catch(e) {
    console.log("NOVA_STOP_KEY_PROMPT_LOOP failed:", e && e.message);
  }
})();
/* NOVA_EARLY_FETCH_AUTH */
(() => {
  try {
    const origFetch = window.fetch && window.fetch.bind(window);
    if (!origFetch) return;

    const earlyKey = () => {
      try { return (localStorage.getItem("NOVA_API_KEY") || "").trim(); } catch(e){ return ""; }
    };

    window.fetch = async (input, init) => {
      init = init || {};
      const url = (typeof input === "string") ? input : (input && input.url) ? input.url : "";

      // Only attach to session endpoints (boot)
      if (url.startsWith("/api/")) {
        const k = earlyKey();
        init.headers = init.headers || {};
        if (k && !init.headers["x-api-key"]) init.headers["Authorization"] = ("Bearer " + k);
        if (!init.cache) init.cache = "no-store";
      }
      return origFetch(input, init);
    };
    console.log("NOVA_EARLY_FETCH_AUTH installed, keylen=", earlyKey().length);
  } catch(e) {
    console.log("NOVA_EARLY_FETCH_AUTH failed:", e && e.message);
  }
})();
function __novaEarlyHeaders(){ try{ const k=(localStorage.getItem("NOVA_API_KEY")||"").trim(); return k?{"x-api-key":k}:{ }; }catch(e){ return {}; } }
(function(){
    const origFetch = window.fetch;
    window.fetch = function(input, init){
      init = init || {};
      const h = new Headers(init.headers || {});
      try {
        const k = (window.__novaGetKey ? window.__novaGetKey() : (window.NOVA_API_KEY || '')).trim();
        if (k) { h.set("x-api-key", k); h.set("X-API-Key", k); }
      } catch(e) {}
      init.headers = h;
      init.cache = init.cache || "no-store";
      return origFetch(input, init);
    };
  })();









