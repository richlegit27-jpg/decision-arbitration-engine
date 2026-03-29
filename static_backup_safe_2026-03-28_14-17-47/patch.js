(() => {
  const getKey = () => (localStorage.getItem("NOVA_API_KEY") || "").trim();

  // ---- fetch patch ----
  const patchFetch = () => {
    const origFetch = window.fetch && window.fetch.bind(window);
    if (!origFetch) return;

    window.fetch = async (input, init = {}) => {
      try {
        const url = (typeof input === "string") ? input : (input && input.url) ? input.url : "";
        const isApi = url.startsWith("/api/") || url.includes("/api/");
        if (isApi) {
          const key = getKey();
          if (key) {
            init.headers = new Headers(init.headers || {});
            if (!init.headers.has("X-API-Key")) init.headers.set("X-API-Key", key);
            if (!init.headers.has("Authorization")) init.headers.set("Authorization", `Bearer ${key}`);
          }
        }
      } catch(e){}
      return origFetch(input, init);
    };
  };

  // ---- XHR patch ----
  const patchXHR = () => {
    const XHR = window.XMLHttpRequest;
    if (!XHR || XHR.__nova_patched) return;
    XHR.__nova_patched = true;

    const origOpen = XHR.prototype.open;
    const origSend = XHR.prototype.send;
    XHR.prototype.open = function(method, url, ...rest){
      this.__nova_url = url;
      return origOpen.call(this, method, url, ...rest);
    };
    XHR.prototype.send = function(body){
      try {
        const url = this.__nova_url || "";
        const isApi = (typeof url === "string") && (url.startsWith("/api/") || url.includes("/api/"));
        if (isApi) {
          const key = getKey();
          if (key) {
            try { this.setRequestHeader("X-API-Key", key); } catch(e){}
            try { this.setRequestHeader("Authorization", `Bearer ${key}`); } catch(e){}
          }
        }
      } catch(e){}
      return origSend.call(this, body);
    };
  };

  patchFetch();
  patchXHR();

  // Reinforce a few times in case app.js overwrites
  let n = 0;
  const t = setInterval(() => {
    patchFetch();
    patchXHR();
    n++;
    if (n >= 40) clearInterval(t);
  }, 250);

  console.log("[nova-ui] patch: auth injector active (fetch + XHR)");
})();
