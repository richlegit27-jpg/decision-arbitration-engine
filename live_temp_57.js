
(function () {
    "use strict";

    if (window.__NOVA_CODE_BLOCK_STACK_FIX_20260622__) return;
    window.__NOVA_CODE_BLOCK_STACK_FIX_20260622__ = true;

    function detectLang(codeText, className) {
        const cls = String(className || "");
        const match = cls.match(/language-([a-z0-9_-]+)/i);

        if (match && match[1]) {
            return match[1];
        }

        const t = String(codeText || "").trim();

        if (/^(Get-|Set-|New-|Remove-|Start-|Stop-|Test-|Invoke-|\$)/m.test(t)) {
            return "powershell";
        }

        if (/^(def |import |from |print\()/m.test(t)) {
            return "python";
        }

        if (/^(const |let |var |function |\(\)\s*=>)/m.test(t)) {
            return "javascript";
        }

        if (/^(cd |dir |ls |git |python |npm |pip )/m.test(t)) {
            return "shell";
        }

        return "code";
    }

    function stripToolbarText(raw) {
        let text = String(raw || "");

        text = text.replace(/^\s*Copy\s+/i, "");
        text = text.replace(/^\s*(PowerShell|Python|JavaScript|Bash|Shell|Code)\s*Copy\s*/i, "");
        text = text.replace(/^\s*(POWERSHELL|PYTHON|JAVASCRIPT|BASH|SHELL|CODE)\s*\n/i, "");

        return text.trimEnd();
    }

    function rebuildPre(pre) {
        if (!pre || pre.nodeType !== 1) return;

        const oldCode = pre.querySelector("code");
        if (!oldCode) return;

        const rawText = stripToolbarText(oldCode.textContent || "");
        const oldClass = oldCode.className || "";
        const lang = detectLang(rawText, oldClass);

        pre.innerHTML = "";
        pre.dataset.novaCodeStackFixed = "1";

        const bar = document.createElement("div");
        bar.className = "nova-codebar-stackfix";

        const label = document.createElement("div");
        label.className = "nova-codebar-stackfix-lang";
        label.textContent = lang;

        const copy = document.createElement("button");
        copy.type = "button";
        copy.className = "nova-codebar-stackfix-copy";
        copy.textContent = "Copy";

        const code = document.createElement("code");
        code.className = oldClass || ("language-" + lang);
        code.textContent = rawText;

        copy.addEventListener("click", async function (event) {
            event.preventDefault();
            event.stopPropagation();

            try {
                await navigator.clipboard.writeText(code.textContent || "");
                copy.textContent = "Copied";
                setTimeout(() => copy.textContent = "Copy", 900);
            } catch (_) {
                copy.textContent = "Copy failed";
                setTimeout(() => copy.textContent = "Copy", 1200);
            }
        });

        bar.appendChild(label);
        bar.appendChild(copy);
        pre.appendChild(bar);
        pre.appendChild(code);
    }

    function cleanNearbyToolbarJunk(pre) {
        let prev = pre.previousSibling;

        while (prev) {
            const text = String(prev.textContent || prev.nodeValue || "").trim();

            if (!text) {
                const remove = prev;
                prev = prev.previousSibling;
                remove.remove();
                continue;
            }

            if (/^(Copy|PowerShellCopy|PythonCopy|JavaScriptCopy|BashCopy|ShellCopy|CodeCopy)$/i.test(text)) {
                const remove = prev;
                prev = prev.previousSibling;
                remove.remove();
                continue;
            }

            break;
        }
    }

    function fixAllCodeBlocks(root) {
        const scope = root && root.nodeType === 1 ? root : document;

        const blocks = [];

        if (scope.matches && scope.matches("pre")) {
            blocks.push(scope);
        }

        scope.querySelectorAll?.("pre").forEach(pre => blocks.push(pre));

        blocks.forEach(pre => {
            cleanNearbyToolbarJunk(pre);
            rebuildPre(pre);
        });
    }

    fixAllCodeBlocks(document);

    const observer = new MutationObserver(mutations => {
        let shouldFix = false;

        for (const mutation of mutations) {
            mutation.addedNodes.forEach(node => {
                if (node && node.nodeType === 1) {
                    if (
                        node.matches?.("pre") ||
                        node.querySelector?.("pre")
                    ) {
                        shouldFix = true;
                    }
                }
            });
        }

        if (shouldFix) {
            requestAnimationFrame(() => fixAllCodeBlocks(document));
        }
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    console.log("[Nova] code block stack fix ready");
})();
