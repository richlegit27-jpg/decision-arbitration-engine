(() => {
const init = () => {
console.log("Nova AI Tools Suite Loaded");

    const panels = {
        memory: document.getElementById("memoryPanel"),
        chat: document.getElementById("chatMessages")
    };

    const backendPort = window.NOVA_BACKEND_PORT || 5001;
    const model = "gpt-4.1-mini";
    const currentSession = "default";

    // ---------------- Helper: AI Request ----------------
    async function aiRequest(prompt) {
        try {
            const res = await fetch(
                `http://127.0.0.1:${backendPort}/api/chat`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        content: prompt,
                        session_id: currentSession,
                        model
                    })
                }
            );

            if (!res.ok) {
                throw new Error(
                    `Chat API returned HTTP ${res.status}`
                );
            }

            const data = await res.json();

            if (Array.isArray(data) && data[1]?.content != null) {
                return data[1].content;
            }

            if (data && typeof data === "object") {
                return data.content ??
                    data.response ??
                    data.message ??
                    "AI returned no response text.";
            }

            return "AI returned an unexpected response format.";
        } catch (error) {
            console.error("[Nova AI Request]", error);
            return "Error: AI request failed";
        }
    }

    // ---------------- Context Menu for Memory ----------------
    if (panels.memory) {
        panels.memory.addEventListener("contextmenu", async event => {
            event.preventDefault();

            const target = event.target.closest("div");
            if (!target) return;

            const action = window.prompt(
                "AI Action: summarize/translate/explain/execute",
                "summarize"
            );

            if (!action) return;

            const result = await aiRequest(
                `${action}: ${target.textContent}`
            );

            window.alert(`AI Result:\n${result}`);

            if (["summarize", "translate", "explain"].includes(action)) {
                const resultElement = document.createElement("div");
                resultElement.style.cssText =
                    "margin-top:2px;color:#0ff;";
                resultElement.textContent =
                    `[AI ${action}]: ${result}`;
                target.appendChild(resultElement);
            }
        });
    }

    // ---------------- Keyboard Shortcut for Selected Text ----------------
    document.addEventListener("keydown", async event => {
        if (event.ctrlKey && event.key.toLowerCase() === "a") {
            const selection = window.getSelection()?.toString();

            if (selection) {
                event.preventDefault();

                const result = await aiRequest(
                    `summarize: ${selection}`
                );

                window.alert(`AI Summary:\n${result}`);
            }
        }
    });

    // ---------------- Persisted Token Usage ----------------

async function updateTokenUsage() {
    const widget = document.getElementById("tokenUsageDisplay");
    if (!widget) return;

    try {
        const response = await fetch("/api/usage", {
            cache: "no-store",
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error(`Usage API returned HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.ok === false) {
            throw new Error(data.error || "Usage API reported failure");
        }

        let inputTokens = 0;
        let outputTokens = 0;
        let totalTokens = 0;
        let calls = 0;

        // Use the totals returned by the active /api/usage endpoint.
        if (data.totals && typeof data.totals === "object") {
            inputTokens = Number(data.totals.input_tokens || 0);
            outputTokens = Number(data.totals.output_tokens || 0);
            totalTokens = Number(
                data.totals.total_tokens ?? (inputTokens + outputTokens)
            );
            calls = Number(data.totals.calls || 0);
        } else if (
            data.by_model &&
            typeof data.by_model === "object"
        ) {
            // Backward compatibility with the older response format.
            const modelUsage = Object.values(data.by_model);

            for (const usage of modelUsage) {
                const input = Number(usage.input_tokens || 0);
                const output = Number(usage.output_tokens || 0);

                inputTokens += input;
                outputTokens += output;
                totalTokens += Number(
                    usage.total_tokens ?? (input + output)
                );
                calls += Number(usage.calls || 0);
            }
        }

        widget.textContent =
            `Tokens used: ${totalTokens.toLocaleString()} ` +
            `(In: ${inputTokens.toLocaleString()} · ` +
            `Out: ${outputTokens.toLocaleString()})`;

        widget.title = `Recorded calls: ${calls.toLocaleString()}`;
    } catch (error) {
        console.error("[Nova Token Usage]", error);
        widget.textContent = "Token usage unavailable";
    }
}
    // ---------------- Remaining Credits and Optional Money Balance ----------------
    async function updateCreditBalance() {
        const balanceElement =
            document.getElementById("nova-credit-balance");

        if (!balanceElement) return;

        try {
            const response = await fetch("/api/billing/account", {
                cache: "no-store",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                throw new Error(
                    `Billing API returned HTTP ${response.status}`
                );
            }

            const data = await response.json();
            const account = data.account || {};

            if (
                data.ok === false ||
                account.credits == null ||
                !Number.isFinite(Number(account.credits))
            ) {
                throw new Error("Valid credit balance was not returned");
            }

            // Display remaining credits for the signed-in account.
            balanceElement.textContent =
                Number(account.credits).toLocaleString();

            // Only display money when the API explicitly supplies
            // a monetary balance. "balance" is deliberately excluded
            // because Nova may use that field for credits.
            const moneyElement =
                document.getElementById("nova-money-balance");

            if (!moneyElement) return;

            const plan = String(
                account.plan || data.plan || ""
            ).trim().toLowerCase();

            const isFreePlan = [
                "free",
                "free_tier",
                "free-tier"
            ].includes(plan);

            const monetaryBalance =
                account.balance_usd ??
                account.monetary_balance ??
                null;

            if (
                !isFreePlan &&
                monetaryBalance !== null &&
                monetaryBalance !== "" &&
                Number.isFinite(Number(monetaryBalance))
            ) {
                moneyElement.textContent =
                    new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: "USD"
                    }).format(Number(monetaryBalance));

                moneyElement.hidden = false;
            } else {
                moneyElement.textContent = "";
                moneyElement.hidden = true;
            }

        } catch (error) {
            console.error("[Nova Credits]", error);
            balanceElement.textContent = "Unavailable";

            const moneyElement =
                document.getElementById("nova-money-balance");

            if (moneyElement) {
                moneyElement.textContent = "";
                moneyElement.hidden = true;
            }
        }
    }

    // ---------------- Initial Refresh ----------------
    updateTokenUsage();
    updateCreditBalance();

    // ---------------- Periodic Refresh ----------------
    window.setInterval(() => {
        updateTokenUsage();
        updateCreditBalance();
    }, 30000);

    // ---------------- Refresh on Window Focus ----------------
    window.addEventListener("focus", () => {
        updateTokenUsage();
        updateCreditBalance();
    });

    // ---------------- Refresh After Usage Changes ----------------
    window.addEventListener("nova:usage-updated", () => {
        updateTokenUsage();
        updateCreditBalance();
    });
};

// Support scripts loaded before OR after DOMContentLoaded.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {
        once: true
    });
} else {
    init();
}

})();

