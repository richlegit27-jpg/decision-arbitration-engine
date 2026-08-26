
(function () {
    "use strict";

    if (window.__NOVA_VISIBLE_SUMMARY_BOX_FINAL_20260621__) return;
    window.__NOVA_VISIBLE_SUMMARY_BOX_FINAL_20260621__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function clean(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function esc(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function ensureSummaryBox() {
        let box = $("novaVisibleSummaryBox");
        if (box) return box;

        const header = document.querySelector(".chat-top");
        const meta = $("meta");

        box = document.createElement("div");
        box.id = "novaVisibleSummaryBox";
        box.className = "nova-visible-summary-box";
        box.innerHTML = "<strong>Session summary</strong><p>No summary yet.</p>";

        if (header && header.parentNode) {
            header.parentNode.insertBefore(box, header.nextSibling);
        } else if (meta && meta.parentNode) {
            meta.parentNode.appendChild(box);
        } else {
            document.body.prepend(box);
        }

        return box;
    }

    function getChatTextRows() {
        const chat =
            $("chat") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("[data-messages]");

        if (!chat) return [];

        return Array.from(chat.querySelectorAll(".msg, .message"))
            .map(function (row) {
                if (row.classList.contains("nova-summary-final-card")) return "";
                if (row.classList.contains("nova-summary-card")) return "";

                const role = clean(row.querySelector(".role")?.textContent || "");
                const bubble = clean(row.querySelector(".bubble")?.textContent || row.textContent || "");

                if (!bubble) return "";
                if (/^Nova Desktop is ready/i.test(bubble)) return "";
                if (/^Nova is ready/i.test(bubble)) return "";

                return clean((role ? role + ": " : "") + bubble);
            })
            .filter(Boolean);
    }

    function short(value, limit) {
        const text = clean(value);
        if (text.length <= limit) return text;
        return text.slice(0, limit - 1).trim() + "â€¦";
    }

    function buildSummary() {
        const rows = getChatTextRows();

        if (!rows.length) {
            return "No conversation to summarize yet.";
        }

        const latest = rows.slice(-4);
        const latestUser = rows.filter(function (row) {
            return /^user:/i.test(row);
        }).slice(-1)[0] || rows[rows.length - 1];

        return [
            "This session has " + rows.length + " visible messages.",
            "Recent focus: " + latest.map(function (row) {
                return short(row.replace(/^(user|assistant):\s*/i, ""), 70);
            }).join(" / ") + ".",
            "Latest ask: â€œ" + short(latestUser.replace(/^user:\s*/i, ""), 120) + "â€."
        ].join(" ");
    }

    function showSummary() {
        const box = ensureSummaryBox();
        const meta = $("meta");
        const status = $("status");

        if (status) status.textContent = "Building summary...";

        const summary = buildSummary();

        box.innerHTML = "<strong>Session summary</strong><p>" + esc(summary) + "</p>";
        box.style.setProperty("display", "block", "important");

        if (meta) {
            meta.textContent = summary === "No conversation to summarize yet."
                ? "No summary yet."
                : "Summary: " + short(summary, 140);
        }

        if (status) status.textContent = "Summary ready";

        return summary;
    }

    function bindSummaryButton() {
        const oldBtn = $("summarizeBtn");
        if (!oldBtn || oldBtn.dataset.novaVisibleSummaryBound === "true") return;

        const btn = oldBtn.cloneNode(true);
        btn.disabled = false;
        btn.dataset.novaVisibleSummaryBound = "true";

        oldBtn.parentNode.replaceChild(btn, oldBtn);

        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }

            showSummary();
        }, true);
    }

    function injectStyle() {
        if ($("novaVisibleSummaryBoxStyle")) return;

        const style = document.createElement("style");
        style.id = "novaVisibleSummaryBoxStyle";
        style.textContent = `
            #novaVisibleSummaryBox {
                display: none !important;
                margin: 10px 0 12px !important;
                padding: 12px 14px !important;
                border-radius: 16px !important;
                border: 1px solid rgba(168, 85, 247, 0.30) !important;
                background: rgba(168, 85, 247, 0.10) !important;
                color: #f5f3ff !important;
                box-sizing: border-box !important;
            }

            #novaVisibleSummaryBox strong {
                display: block !important;
                margin-bottom: 6px !important;
                font-size: 13px !important;
            }

            #novaVisibleSummaryBox p {
                margin: 0 !important;
                font-size: 13px !important;
                line-height: 1.45 !important;
                opacity: 0.9 !important;
            }
        `;
        document.head.appendChild(style);
    }

    function boot() {
        injectStyle();
        ensureSummaryBox();
        bindSummaryButton();
    }

    boot();
    setTimeout(boot, 200);
    setTimeout(boot, 800);
    setTimeout(boot, 1600);

    window.NovaDesktopLocalSummary = showSummary;

    console.log("[Nova Visible Summary Box] ready");
})();
