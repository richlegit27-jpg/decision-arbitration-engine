;(()=>{ try{
  /* NOVA_BOOTSTRAP_PING_V1 */
  window.__NOVA_BOOTSTRAP_PING_V1__ = (window.__NOVA_BOOTSTRAP_PING_V1__||0)+1;
  console.warn("[NOVA] BOOTSTRAP PING V1", window.__NOVA_BOOTSTRAP_PING_V1__, "href=", location.href);
}catch(e){} })();
;(()=>{ try{
  /* ---------- NOVA_BOOT_SEND_SHIM_V1 ---------- */
  if(window.__NOVA_BOOT_SEND_SHIM_V1_RAN__) return;
  window.__NOVA_BOOT_SEND_SHIM_V1_RAN__ = true;

  function qs(sel){ try{return document.querySelector(sel)}catch(e){return null} }

  function doSend(){
    const real = qs("#sendReal") || qs('button[type="submit"]');
    if(real){ try{ real.click(); }catch(e){} return true; }
    return false;
  }

  function bind(){
    const uiBtn = qs("#sendBtn") || qs("#novaBtn") || qs("#btnSend");
    const input = qs("#novaIn") || qs("textarea");

    if(uiBtn && !uiBtn.__novaBootSendBound){
      uiBtn.__novaBootSendBound = true;
      uiBtn.addEventListener("click", (e)=>{
        try{ e.preventDefault(); e.stopPropagation(); }catch(_){}
        const ok = doSend();
        try{ console.warn("[NOVA] BOOT_SEND click -> real:", ok); }catch(_){}
      }, true);
      try{ console.warn("[NOVA] BOOT_SEND bound click"); }catch(_){}
    }

    if(input && !input.__novaBootSendKeyBound){
      input.__novaBootSendKeyBound = true;
      input.addEventListener("keydown", (e)=>{
        const isEnter = (e.key === "Enter");
        const mod = (e.ctrlKey || e.metaKey);
        if(isEnter && mod){
          try{ e.preventDefault(); e.stopPropagation(); }catch(_){}
          const ok = doSend();
          try{ console.warn("[NOVA] BOOT_SEND ctrl/cmd+enter -> real:", ok); }catch(_){}
        }
      }, true);
      try{ console.warn("[NOVA] BOOT_SEND bound keydown"); }catch(_){}
    }
  }

  bind();
  setTimeout(bind, 200);
  setTimeout(bind, 800);
  setTimeout(bind, 1500);

  /* ---------- /NOVA_BOOT_SEND_SHIM_V1 ---------- */
}catch(e){ try{ console.warn("[NOVA] BOOT_SEND shim failed", e); }catch(_){}} })();
;(()=>{ try{
  
}catch(e){} })();
;(()=>{ try{
  /* ---------- NOVA_FORCE_20_DETERMINISTIC_V1 ---------- */
  // Always load 20.app.js exactly once, deterministically, with cache-bust.
  const existing = document.getElementById("nova20");
  if(existing){
    try{ console.warn("[NOVA] nova20 already present:", existing.src); }catch(e){}
    return;
  }

  const s = document.createElement("script");
  try{ s.id = "nova_js_" + String(src||"").split("?")[0].replace(/[^a-z0-9]+/ig,"_"); }catch(e){}
  s.id = "nova20";
  s.async = false;
  s.defer = false;
  s.type = "text/javascript";
  s.src = "/static/js/20.app.js?v=APP_20260218_114419_" + Date.now();
  /* --- NOVA_ADDJS_ID_DEDUPE_V2 --- */
  try{
    const path = String(s.src||"").split("?")[0];
    const exists = Array.from(document.scripts||[])
      .some(x => String(x.src||"").split("?")[0] === path);
    if(exists){
      try{ console.warn("[NOVA] addJs ID dedupe skip:", path); }catch(e){}
      return;
    }
  }catch(e){}
  /* --- /NOVA_ADDJS_ID_DEDUPE_V2 --- */

  s.onload = function(){
    try{ console.warn("[NOVA] injected 20.app.js OK:", s.src); }catch(e){}
    try{
      const m = document.createElement("div");
      m.id = "novaBoot20Loaded";
      m.textContent = "BOOTSTRAP: 20.app.js LOADED";
      m.style.cssText = "position:fixed;right:8px;bottom:8px;z-index:999999;padding:6px 10px;border-radius:10px;border:1px solid #333;background:#111;color:#0f0;font:12px/1.2 monospace;opacity:.85";
      (document.body || document.documentElement).appendChild(m);
    }catch(e){}
  };

  s.onerror = function(ev){
    try{ console.error("[NOVA] injected 20.app.js FAILED:", s.src, ev); }catch(e){}
    try{ window.__NOVA_20_SCRIPT_ERROR__ = "load_failed"; }catch(e){}
  };

    try{ if(s.id && document.getElementById(s.id)){ console.warn("[NOVA] addJs id skip:", s.id); return; } }catch(e){}
(document.head || document.documentElement || document.body).appendChild(s);
  try{ console.warn("[NOVA] injecting 20.app.js:", s.src); }catch(e){}
  /* ---------- /NOVA_FORCE_20_DETERMINISTIC_V1 ---------- */
}catch(e){ try{ console.warn("[NOVA] FORCE_20_DETERMINISTIC failed", e); }catch(_){} } })();
;(()=>{ try{
  if(!window.__NOVA_BOOT_STAMP__){
    window.__NOVA_BOOT_STAMP__ = "APP_20260218_114047_" + Date.now();
  }
}catch(e){} })();/* ---------- NOVA_TRAP_SEND_V1 ---------- */
try{
  if(!window.__NOVA_SEND_TRAP__){
    window.__NOVA_SEND_TRAP__ = true;
    let _v = window.__NOVA_SEND;

    Object.defineProperty(window, "__NOVA_SEND", {
      configurable: true,
      get(){ return _v; },
      set(v){
        try{
          console.warn("[NOVA] __NOVA_SEND SET ->", v, "type:", typeof v);
          console.warn((new Error("NOVA_SEND_SET_TRACE")).stack);
        }catch(e){}
        _v = v;
      }
    });

    console.log("[NOVA] __NOVA_SEND trap armed (bootstrap). initial type =", typeof _v);
  }
} catch(e){
  console.warn("[NOVA] __NOVA_SEND trap failed", e);
}
/* ---------- /NOVA_TRAP_SEND_V1 ---------- */
console.log("[NOVA] BOOT TOP", new Date().toISOString());
/* --- NOVA_BOOTSTRAP_API8793_V1 --- */
try{ window.__NOVA_API_BASE__ = "http://127.0.0.1:8793"; }catch(e){}
try{
  // Force global URL builder for all /api/*
  window.__novaUrl = function(u){
    try{
      if(typeof u !== "string") return u;
      if(/^https?:\/\//i.test(u)) return u;
      if(u.startsWith("/api/")){
        const base = String(window.__NOVA_API_BASE__ || "").replace(/\/+$/,"");
        return base ? (base + u) : u;
      }
    }catch(e){}
    return u;
  };
}catch(e){}
try{
  // Patch fetch to route /api/* through window.__novaUrl
  const _f = window.fetch;
  window.fetch = function(input, init){
    try{
      const fn = window.__novaUrl;
      if(typeof fn === "function"){
        if(typeof input === "string"){
          input = fn(input);
        } else if(input && typeof input.url === "string"){
          input = new Request(fn(input.url), input);
        }
      }
    }catch(e){}
    return _f(input, init);
  };
}catch(e){}
/* --- /NOVA_BOOTSTRAP_API8793_V1 --- */
/* NOVA_BOOTSTRAP v2 (clean, Request-safe) */
(function(){
  if (window.__NOVA_BOOTSTRAP_V2__) return;
  window.__NOVA_BOOTSTRAP_V2__ = true;

  function getKey(){
    try { return String(localStorage.getItem("NOVA_API_KEY") || "").trim(); }
    catch(e){ return ""; }
  }

  function toObj(h){
    try{
      if(!h) return {};
      if (typeof Headers !== "undefined" && h instanceof Headers){
        var o={}; h.forEach(function(v,k){ o[k]=v; }); return o;
      }
      if (typeof h === "object") return Object.assign({}, h);
    }catch(e){}
    return {};
  }

  window.__novaAuthDebug = function(){
    var k = getKey();
    return { key_len: k.length, key_tail: k ? k.slice(-6) : "", origin: location.origin };
  };

  window.__novaSetKey = function(){
    var k = prompt("Paste NOVA_API_KEY");
    if(!k) return false;
    try { localStorage.setItem("NOVA_API_KEY", String(k).replace(/[\r\n\t]/g,"").trim()); } catch(e) {}
    return true;
  };

  // compatibility helpers
  window.apiHeaders = function apiHeaders(extra){
    var k = getKey();
    var h = extra ? Object.assign({}, extra) : {};
    if (k) h["x-api-key"] = k;
    return h;
  };
  window.__novaApiHeaders = window.apiHeaders;

  var _fetch = window.fetch;
  window.fetch = function(input, init){
    try{
      var k = getKey();
      if(!k) return _fetch(input, init);

      var url = "";
      if (typeof input === "string") url = input;
      else if (input && typeof input.url === "string") url = input.url;

      if (String(url).includes("/api/")){
        init = init || {};
        var hdr = toObj(init.headers);

        if (typeof Request !== "undefined" && input instanceof Request){
          var rh = toObj(input.headers);
          hdr = Object.assign({}, rh, hdr);
        }

        hdr["x-api-key"] = k;
        init.headers = hdr;

        if (typeof Request !== "undefined" && input instanceof Request){
          input = new Request(input, init);
          return _fetch(input);
        }
      }
    } catch(e) {}
    return _fetch(input, init);
  };
})();

/* NOVA_CURSOR_FIX_V1 */
(function(){
  function fix(){
    try{
      document.documentElement.style.cursor = "default";
      document.body && (document.body.style.cursor = "default");
    }catch(e){}
  }
  try{
    document.addEventListener("DOMContentLoaded", function(){
      fix();
      setTimeout(fix, 250);
      setTimeout(fix, 1500);
    }, { once:true });
  }catch(e){}
})();

/* NOVA_FATAL_TRAP_V1 */
(function(){
  function show(msg){
    try{
      console.error("[NOVA FATAL]", msg);
      var pre = document.getElementById("novaFatal");
      if(!pre){
        pre = document.createElement("pre");
        pre.id = "novaFatal";
        pre.style.position="fixed";
        pre.style.left="10px";
        pre.style.right="10px";
        pre.style.bottom="10px";
        pre.style.maxHeight="40vh";
        pre.style.overflow="auto";
        pre.style.padding="10px";
        pre.style.background="#111";
        pre.style.color="#eee";
        pre.style.border="1px solid #444";
        pre.style.zIndex="999999";
        pre.textContent="Nova frontend error:\n";
        document.addEventListener("DOMContentLoaded", function(){
          document.body && document.body.appendChild(pre);
        }, {once:true});
      }
      pre.textContent += String(msg) + "\n";
    }catch(e){}
  }

  window.addEventListener("error", function(ev){
    try{
      show((ev && ev.message ? ev.message : "Unknown error") + (ev && ev.filename ? (" @ " + ev.filename + ":" + ev.lineno) : ""));
    }catch(e){}
  }, true);

  window.addEventListener("unhandledrejection", function(ev){
    try{ show("Unhandled promise rejection: " + (ev && ev.reason ? ev.reason : ev)); }catch(e){}
  });
})();

/* NOVA_CURSOR_FIX_V2 */
(function(){
  function fix(){
    try{
      document.documentElement.style.cursor = "default";
      if(document.body) document.body.style.cursor = "default";
    }catch(e){}
  }
  try{
    setInterval(fix, 500);
    document.addEventListener("DOMContentLoaded", function(){ fix(); }, {once:true});
  }catch(e){}
})();

console.log("[NOVA] BOOT PRE-FORCE", new Date().toISOString());

/* NOVA_UI_CLEAN_LOADER v1 */
(() => {
  try {
    const CSS_HREF = "/static/css/99.patch.css?v=UICLEAN2_20260218_101244";
    const JS_SRC   = "/static/js/99.ui_patch_v4.js?v=V4FORCE_20260218_123102";

    function addCss(){
      if (document.querySelector('link[data-nova-clean="1"]')) return;
      const l = document.createElement("link");
      l.rel = "stylesheet";
      l.href = CSS_HREF;
      l.setAttribute("data-nova-clean","1");
      (document.head || document.documentElement).appendChild(l);
    }

    function addJs(){
      if (window.__NOVA_UI_PATCH_LOADER_DONE) return;
      window.__NOVA_UI_PATCH_LOADER_DONE = true;
      const s = document.createElement("script");
  try{ s.id = "nova_js_" + String(src||"").split("?")[0].replace(/[^a-z0-9]+/ig,"_"); }catch(e){}
      s.src = JS_SRC;
  /* --- NOVA_ADDJS_ID_DEDUPE_V2 --- */
  try{
    const path = String(s.src||"").split("?")[0];
    const exists = Array.from(document.scripts||[])
      .some(x => String(x.src||"").split("?")[0] === path);
    if(exists){
      try{ console.warn("[NOVA] addJs ID dedupe skip:", path); }catch(e){}
      return;
    }
  }catch(e){}
  /* --- /NOVA_ADDJS_ID_DEDUPE_V2 --- */
  /* --- NOVA_ADDJS_DEDUPE_V1 --- */
  try{
    const u = String(s.src||"");
    const path = u.replace(location.origin,"");
    const exists = Array.from(document.scripts||[])
      .some(x => String(x.src||"").endsWith(path));
    if(exists){
      try{ console.warn("[NOVA] addJs dedupe skip:", path); }catch(e){}
      return;
    }
  }catch(e){}
  /* --- /NOVA_ADDJS_DEDUPE_V1 --- */

      s.defer = true;
      s.setAttribute("data-nova-clean","1");
        try{ if(s.id && document.getElementById(s.id)){ console.warn("[NOVA] addJs id skip:", s.id); return; } }catch(e){}
(document.head || document.documentElement || document.body).appendChild(s);
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => { addCss(); addJs(); }, { once:true });
    } else {
      addCss(); addJs();
    }
  } catch (e) {}
})();

/* NOVA_UI_CLEAN_LOADER2 v1 (immediate + retry) */
(() => {
  try {
    const CSS_HREF = "/static/css/99.patch.css?v=UICLEAN2_20260218_101244";
    const JS_SRC   = "/static/js/99.ui_patch_v4.js?v=V4FORCE_20260218_123102";

    function addCss(){
      if (document.querySelector('link[data-nova-clean="1"]')) return true;
      const l = document.createElement("link");
      l.rel = "stylesheet";
      l.href = CSS_HREF;
      l.setAttribute("data-nova-clean","1");
      (document.head || document.documentElement).appendChild(l);
      return true;
    }

    function addJs(){
      if (window.__NOVA_UI_PATCH_LOADER_DONE2) return true;
      window.__NOVA_UI_PATCH_LOADER_DONE2 = true;
      const s = document.createElement("script");
  try{ s.id = "nova_js_" + String(src||"").split("?")[0].replace(/[^a-z0-9]+/ig,"_"); }catch(e){}
      s.src = JS_SRC;
  /* --- NOVA_ADDJS_ID_DEDUPE_V2 --- */
  try{
    const path = String(s.src||"").split("?")[0];
    const exists = Array.from(document.scripts||[])
      .some(x => String(x.src||"").split("?")[0] === path);
    if(exists){
      try{ console.warn("[NOVA] addJs ID dedupe skip:", path); }catch(e){}
      return;
    }
  }catch(e){}
  /* --- /NOVA_ADDJS_ID_DEDUPE_V2 --- */
  /* --- NOVA_ADDJS_DEDUPE_V1 --- */
  try{
    const u = String(s.src||"");
    const path = u.replace(location.origin,"");
    const exists = Array.from(document.scripts||[])
      .some(x => String(x.src||"").endsWith(path));
    if(exists){
      try{ console.warn("[NOVA] addJs dedupe skip:", path); }catch(e){}
      return;
    }
  }catch(e){}
  /* --- /NOVA_ADDJS_DEDUPE_V1 --- */

      s.defer = true;
      s.setAttribute("data-nova-clean","1");
        try{ if(s.id && document.getElementById(s.id)){ console.warn("[NOVA] addJs id skip:", s.id); return; } }catch(e){}
(document.head || document.documentElement || document.body).appendChild(s);
      return true;
    }

    // do it now + retry a few times (UI mounts late sometimes)
    addCss(); addJs();
    setTimeout(() => { try{ addCss(); addJs(); }catch(e){} }, 50);
    setTimeout(() => { try{ addCss(); addJs(); }catch(e){} }, 250);
    setTimeout(() => { try{ addCss(); addJs(); }catch(e){} }, 900);
  } catch (e) {}
})();























