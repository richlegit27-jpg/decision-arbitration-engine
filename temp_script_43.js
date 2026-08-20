
(function () {
    "use strict";

    if (window.__NOVA_CODE_BLOCK_POLISH_FINAL_20260622__) return;
    window.__NOVA_CODE_BLOCK_POLISH_FINAL_20260622__ = true;

    function detectLanguage(pre) {
        const code = pre.querySelector("code");
        const className = code ? String(code.className || "") : "";
        const match = className.match(/language-([a-z0-9_-]+)/i);

        if (match && match[1]) {
            return match[1].replace(/_/g, "-");
        }

        const text = code ? String(code.textContent || "") : String(pre.textContent || "");

        if (/^\s*(cd |git |python |powershell|Remove-Item|Set-Content|Select-String)/mi.test(text)) return "powershell";
        if (/^\s*(function|const|let|var|document\.|window\.)/mi.test(text)) return "javascript";
        if (/^\s*(from |import |def |class |path = Path)/mi.test(text)) return "python";
        if (/^\s*(<script|<style|<div|<!doctype|<html)/mi.test(text)) return "html";
        if (/^\s*[\.\#a-z0-9_-]+\s*\{/mi.test(text)) return "css";

        return "code";
    }

    async function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }

        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        ta.style.top = "-9999px";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();

        try {
            document.execCommand("copy");
            return true;
        } finally {
            ta.remove();
        }
    }

    function enhanceCodeBlocks(root) {
        const scope = root || document;
        const blocks = scope.querySelectorAll ? scope.querySelectorAll("#chat pre") : [];

        blocks.forEach(function (pre) {
            if (!pre || pre.dataset.novaCodeEnhanced === "1") return;

            pre.dataset.novaCodeEnhanced = "1";

            const toolbar = document.createElement("div");
            toolbar.className = "nova-code-toolbar";

            const label = document.createElement("div");
            label.className = "nova-code-language";
            label.textContent = detectLanguage(pre);

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "nova-code-copy-btn";
            btn.textContent = "Copy";

            btn.addEventListener("click", async function (event) {
                event.preventDefault();
                event.stopPropagation();

                const code = pre.querySelector("code");
                const text = code ? code.textContent : pre.textContent.replace(btn.textContent, "").trim();

                try {
                    await copyText(text || "");
                    btn.textContent = "Copied";
                    setTimeout(function () {
                        btn.textContent = "Copy";
                    }, 900);
                } catch (_) {
                    btn.textContent = "Failed";
                    setTimeout(function () {
                        btn.textContent = "Copy";
                    }, 1200);
                }
            });

            toolbar.appendChild(label);
            toolbar.appendChild(btn);
            pre.insertBefore(toolbar, pre.firstChild);
        });
    }

    window.NovaEnhanceCodeBlocks = enhanceCodeBlocks;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            enhanceCodeBlocks(document);
        });
    } else {
        enhanceCodeBlocks(document);
    }

    setTimeout(function () { enhanceCodeBlocks(document); }, 300);
    setTimeout(function () { enhanceCodeBlocks(document); }, 1000);

    try {
        const chat = document.getElementById("chat");

        if (chat) {
            const observer = new MutationObserver(function () {
                enhanceCodeBlocks(chat);
            });

            observer.observe(chat, {
                childList: true,
                subtree: true
            });
        }
    } catch (_) {}

    console.log("[Nova Code Block Polish] ready");
})();
