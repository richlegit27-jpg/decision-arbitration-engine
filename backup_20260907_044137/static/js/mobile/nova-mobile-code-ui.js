(function () {
    "use strict";

    function hasCodeText(text) {
        if (text && text.trim()) return true;

        showToast("No code to copy.");
        vibrate(20);

        return false;
    }

    function notifyCodeCopied() {
        showToast("Code copied.");
        vibrate(10);
    }

    function updateExpandButton(button, expanded) {
        if (!button) return;

        button.textContent =
            expanded ? "Collapse" : "Expand";
    }

    function shouldCollapseCode(pre) {
        return !!(
            pre &&
            pre.innerText &&
            pre.innerText.length > 1200
        );
    }

    function notifyCodeToggle(isCollapsed) {
        showToast(
            isCollapsed
                ? "Code collapsed."
                : "Code expanded."
        );
    }

    function enhanceCodeBlocks(wrapper) {
        if (!wrapper) return;

        wrapper.querySelectorAll("pre").forEach(function (pre) {
            if (pre.dataset.enhanced === "1") return;

            pre.dataset.enhanced = "1";

            if (shouldCollapseCode(pre)) {
                pre.classList.add("mobile-code-collapsed");
            }

            const copyBtn = document.createElement("button");

            copyBtn.type = "button";
            copyBtn.textContent = "Copy";
            copyBtn.className = "mobile-code-copy-btn";

            copyBtn.addEventListener("click", function () {
                const codeText =
                    pre.innerText ||
                    pre.textContent ||
                    "";

                if (!hasCodeText(codeText)) return;

                copyText(codeText);
                notifyCodeCopied();

                flashButtonState(
                    copyBtn,
                    "Copied",
                    "Copy"
                );
            });

            pre.appendChild(copyBtn);

            if (shouldCollapseCode(pre)) {
                const expandBtn =
                    document.createElement("button");

                expandBtn.type = "button";

                expandBtn.className =
                    "mobile-code-expand-btn";

                expandBtn.textContent = "Expand";

                expandBtn.addEventListener("click", function () {
                    pre.classList.toggle("mobile-code-collapsed");

                    updateExpandButton(
                        expandBtn,
                        !pre.classList.contains(
                            "mobile-code-collapsed"
                        )
                    );

                    notifyCodeToggle(
                        pre.classList.contains(
                            "mobile-code-collapsed"
                        )
                    );

                    vibrate(8);
                });

                pre.appendChild(expandBtn);
            }
        });
    }

    window.NovaMobileCodeUI = {
        enhanceCodeBlocks
    };

})();

