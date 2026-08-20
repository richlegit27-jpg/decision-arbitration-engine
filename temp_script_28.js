
(function () {
  "use strict";

  if (window.__NOVA_TEXT_COLOR_POLISH_20260620__) return;
  window.__NOVA_TEXT_COLOR_POLISH_20260620__ = true;

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function token(type, text) {
    return '<span class="nova-token-' + type + '">' + escapeHtml(text) + '</span>';
  }

  function colorize(code) {
    const keywords = new Set([
      "function", "const", "let", "var", "return", "if", "else", "for", "while",
      "async", "await", "try", "catch", "class", "new", "this", "true", "false",
      "null", "undefined", "import", "from", "export", "def", "print", "pass",
      "in", "and", "or", "not"
    ]);

    const pattern =
      /(\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->|\/\/[^\n]*|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`|<\/?[a-zA-Z][^>\n]*>|\b\d+(?:\.\d+)?\b|\b[a-zA-Z_$][\w$]*\b)/g;

    let output = "";
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(code)) !== null) {
      const raw = match[0];
      const index = match.index;

      output += escapeHtml(code.slice(lastIndex, index));

      if (
        raw.startsWith("//") ||
        raw.startsWith("/*") ||
        raw.startsWith("<!--")
      ) {
        output += token("comment", raw);
      } else if (
        raw.startsWith('"') ||
        raw.startsWith("'") ||
        raw.startsWith("`")
      ) {
        output += token("string", raw);
      } else if (raw.startsWith("<")) {
        output += token("tag", raw);
      } else if (/^\d/.test(raw)) {
        output += token("number", raw);
      } else if (keywords.has(raw)) {
        output += token("keyword", raw);
      } else {
        const after = code.slice(index + raw.length);
        if (/^\s*\(/.test(after)) {
          output += token("function", raw);
        } else {
          output += escapeHtml(raw);
        }
      }

      lastIndex = index + raw.length;
    }

    output += escapeHtml(code.slice(lastIndex));
    return output;
  }

  function addCopyButton(pre, code) {
    if (pre.querySelector(".nova-code-copy")) return;

    const btn = document.createElement("button");
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

    pre.appendChild(btn);
  }

  function polishCodeBlocks(root) {
    const scope = root || document;

    scope.querySelectorAll("pre code").forEach(function (code) {
      const pre = code.closest("pre");
      if (!pre) return;

      addCopyButton(pre, code);

      if (code.dataset.novaColorized === "1") return;

      const raw = code.textContent || "";
      code.innerHTML = colorize(raw);
      code.dataset.novaColorized = "1";
    });
  }

  function polishAll() {
    polishCodeBlocks(document);
  }

  polishAll();

  const observer = new MutationObserver(function () {
    polishAll();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  console.log("[Nova Text Color Polish] ready");
})();
