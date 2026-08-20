
(function () {
  "use strict";

  if (window.__NOVA_CODE_BLOCK_HEADER_POLISH_20260620__) return;
  window.__NOVA_CODE_BLOCK_HEADER_POLISH_20260620__ = true;

  function prettyLang(raw) {
    raw = String(raw || "").trim();

    if (!raw) return "CODE";

    raw = raw
      .replace(/^language-/i, "")
      .replace(/^lang-/i, "")
      .replace(/^hljs/i, "")
      .trim();

    const map = {
      js: "JavaScript",
      javascript: "JavaScript",
      py: "Python",
      python: "Python",
      html: "HTML",
      css: "CSS",
      json: "JSON",
      bash: "Bash",
      shell: "Shell",
      powershell: "PowerShell",
      ps1: "PowerShell"
    };

    return map[raw.toLowerCase()] || raw || "CODE";
  }

  function getLang(code) {
    const className = String(code.className || "");
    const match = className.match(/(?:language-|lang-)([a-zA-Z0-9_-]+)/);

    if (match && match[1]) {
      return prettyLang(match[1]);
    }

    return "CODE";
  }

  function ensureCopyButton(pre, code) {
    let btn = pre.querySelector(".nova-code-copy");

    if (btn) return btn;

    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nova-code-copy";
    btn.textContent = "Copy";

    btn.addEventListener("click", async function () {
      try {
        await navigator.clipboard.writeText(code.textContent || "");
        btn.textContent = "Copied";

        setTimeout(function () {
          btn.textContent = "Copy";
        }, 900);
      } catch (e) {
        btn.textContent = "Failed";

        setTimeout(function () {
          btn.textContent = "Copy";
        }, 900);
      }
    });

    return btn;
  }

  function polishPre(pre) {
    if (!pre || pre.dataset.novaCodeHeaderPolished === "1") return;

    const code = pre.querySelector("code");
    if (!code) return;

    const bar = document.createElement("div");
    bar.className = "nova-codebar";

    const lang = document.createElement("span");
    lang.className = "nova-code-lang";
    lang.textContent = getLang(code);

    const copy = ensureCopyButton(pre, code);

    bar.appendChild(lang);
    bar.appendChild(copy);

    pre.insertBefore(bar, pre.firstChild);
    pre.dataset.novaCodeHeaderPolished = "1";
  }

  function polishAll() {
    document.querySelectorAll("pre").forEach(polishPre);
  }

  polishAll();

  const observer = new MutationObserver(function () {
    polishAll();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  console.log("[Nova Code Block Header Polish] ready");
})();
