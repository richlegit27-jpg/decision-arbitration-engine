(() => {
"use strict";

if (window.NovaMarkdown) {
  console.warn("NovaMarkdown already loaded. Skipping duplicate init.");
  return;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

function isLikelyListLine(line) {
  return /^(\s*[-*]\s+|\s*\d+\.\s+)/.test(line);
}

function renderInline(text) {
  let safe = escapeHtml(text);

  safe = safe.replace(
    /`([^`]+)`/g,
    (_match, code) => `<code class="nova-inline-code">${escapeHtml(code)}</code>`
  );

  safe = safe.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_match, label, url) => {
      const safeLabel = escapeHtml(label);
      const safeUrl = escapeAttr(url);
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeLabel}</a>`;
    }
  );

  safe = safe.replace(
    /(^|[\s(])(https?:\/\/[^\s<]+)(?=$|[\s).,!?:;])/g,
    (_match, prefix, url) => {
      const safeUrl = escapeAttr(url);
      return `${prefix}<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`;
    }
  );

  safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  safe = safe.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
  safe = safe.replace(/(?<!_)_([^_\n]+)_(?!_)/g, "<em>$1</em>");

  return safe;
}

function renderParagraphBlock(block) {
  const trimmed = block.trim();
  if (!trimmed) return "";
  return `<p>${renderInline(trimmed).replace(/\n/g, "<br>")}</p>`;
}

function renderListBlock(block) {
  const lines = block.split("\n").filter(line => line.trim());
  if (!lines.length) return "";

  const isOrdered = /^\s*\d+\.\s+/.test(lines[0]);
  const tag = isOrdered ? "ol" : "ul";

  const items = lines.map(line => {
    const clean = line.replace(/^\s*([-*]|\d+\.)\s+/, "");
    return `<li>${renderInline(clean)}</li>`;
  }).join("");

  return `<${tag} class="nova-list">${items}</${tag}>`;
}

function renderHeading(line) {
  const match = /^(#{1,6})\s+(.*)$/.exec(line.trim());
  if (!match) return null;

  const level = Math.min(match[1].length, 6);
  const text = renderInline(match[2]);
  return `<h${level} class="nova-h${level}">${text}</h${level}>`;
}

function renderCodeBlocks(source) {
  const parts = [];
  const regex = /```([\w#+.-]*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(source)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: "text",
        value: source.slice(lastIndex, match.index)
      });
    }

    parts.push({
      type: "code",
      language: String(match[1] || "").trim(),
      value: String(match[2] || "").replace(/\n$/, "")
    });

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < source.length) {
    parts.push({
      type: "text",
      value: source.slice(lastIndex)
    });
  }

  return parts;
}

function renderTextSegment(segment) {
  const normalized = String(segment || "").replace(/\r\n/g, "\n");
  const rawBlocks = normalized.split(/\n{2,}/);
  const rendered = [];

  for (const rawBlock of rawBlocks) {
    const block = rawBlock.trim();
    if (!block) continue;

    const lines = block.split("\n");
    if (lines.length === 1) {
      const heading = renderHeading(lines[0]);
      if (heading) {
        rendered.push(heading);
        continue;
      }
    }

    if (lines.every(isLikelyListLine)) {
      rendered.push(renderListBlock(block));
      continue;
    }

    rendered.push(renderParagraphBlock(block));
  }

  return rendered.join("");
}

function render(source) {
  const text = String(source ?? "");
  const segments = renderCodeBlocks(text);

  return segments.map(segment => {
    if (segment.type === "code") {
      const safeLanguage = escapeHtml(segment.language || "");
      const safeCode = escapeHtml(segment.value || "");
      const copyPayload = escapeAttr(segment.value || "");

      return `
        <div class="nova-code-block">
          <div class="nova-code-toolbar">
            <span class="nova-code-language">${safeLanguage || "code"}</span>
            <button
              type="button"
              class="nova-copy-code-btn"
              data-copy-code="${copyPayload}"
              title="Copy code"
            >Copy</button>
          </div>
          <pre><code>${safeCode}</code></pre>
        </div>
      `;
    }

    return renderTextSegment(segment.value);
  }).join("");
}

function bindCopyButtons(root = document) {
  const buttons = root.querySelectorAll(".nova-copy-code-btn");

  for (const button of buttons) {
    if (button.dataset.copyBound === "1") continue;
    button.dataset.copyBound = "1";

    button.addEventListener("click", async () => {
      const code = button.getAttribute("data-copy-code") || "";
      try {
        await navigator.clipboard.writeText(code);
        const previous = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => {
          button.textContent = previous || "Copy";
        }, 1200);
      } catch (error) {
        console.error(error);
        button.textContent = "Failed";
        setTimeout(() => {
          button.textContent = "Copy";
        }, 1200);
      }
    });
  }
}

window.NovaMarkdown = {
  render,
  bindCopyButtons
};
})();