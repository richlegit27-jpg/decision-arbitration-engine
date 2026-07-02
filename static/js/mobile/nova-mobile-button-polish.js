// NOVA_MOBILE_BUTTON_POLISH_20260702
// Mobile-only button polish.
// No chat rendering changes. No width observers. No message duplication paths.

(function () {
    if (window.__NOVA_MOBILE_BUTTON_POLISH_20260702__) {
        return;
    }
    window.__NOVA_MOBILE_BUTTON_POLISH_20260702__ = true;

    let requestTimer = null;
    let micTimer = null;

    function textOf(el) {
        return String(
            el?.innerText ||
            el?.textContent ||
            el?.getAttribute?.("aria-label") ||
            el?.getAttribute?.("title") ||
            ""
        ).trim().toLowerCase();
    }

    function allButtonsAndLinks() {
        return [...document.querySelectorAll("button, a, [role='button'], input[type='button'], input[type='submit']")];
    }

    function matchesAny(el, selectors) {
        return selectors.some(sel => {
            try {
                return el.matches(sel);
            } catch {
                return false;
            }
        });
    }

    function findControl(kind) {
        const controls = allButtonsAndLinks();

        const selectors = {
            send: [
                "#mobileSendButton",
                "#mobileSendBtn",
                "#sendButton",
                "#sendBtn",
                ".mobile-send-button",
                ".send-button",
                "[data-action='send']",
                "[aria-label*='send' i]",
                "[title*='send' i]"
            ],
            stop: [
                "#mobileStopButton",
                "#mobileStopBtn",
                "#stopButton",
                "#stopBtn",
                ".mobile-stop-button",
                ".stop-button",
                "[data-action='stop']",
                "[aria-label*='stop' i]",
                "[title*='stop' i]"
            ],
            mic: [
                "#mobileVoiceButton",
                "#mobileMicButton",
                "#micButton",
                "#voiceButton",
                ".mobile-voice-button",
                ".mobile-mic-button",
                ".voice-button",
                ".mic-button",
                "[data-action='voice']",
                "[data-action='mic']",
                "[aria-label*='mic' i]",
                "[aria-label*='voice' i]",
                "[title*='mic' i]",
                "[title*='voice' i]"
            ],
            account: [
                "#mobileAccountButton",
                "#mobileAccountBtn",
                "#accountButton",
                "#accountBtn",
                "#profileButton",
                "#profileBtn",
                ".mobile-account-button",
                ".mobile-profile-button",
                ".account-button",
                ".profile-button",
                "[data-action='account']",
                "[data-action='profile']",
                "[aria-label*='account' i]",
                "[aria-label*='profile' i]",
                "[title*='account' i]",
                "[title*='profile' i]"
            ]
        }[kind] || [];

        let found = controls.find(el => matchesAny(el, selectors));
        if (found) {
            return found;
        }

        const textRegex = {
            send: /\b(send|➤|↑)\b/i,
            stop: /\b(stop|cancel|■)\b/i,
            mic: /\b(mic|voice|speak|record)\b/i,
            account: /\b(account|profile|me|user)\b/i
        }[kind];

        if (!textRegex) {
            return null;
        }

        return controls.find(el => textRegex.test(textOf(el))) || null;
    }

    function markControls() {
        document.body.classList.add("nova-mobile-button-polish-ready");

        const send = findControl("send");
        const stop = findControl("stop");
        const mic = findControl("mic");
        const account = findControl("account");

        if (send) {
            send.classList.add("nova-mobile-send-polished");
            send.setAttribute("aria-label", send.getAttribute("aria-label") || "Send message");
        }

        if (stop) {
            stop.classList.add("nova-mobile-stop-polished");
            stop.setAttribute("aria-label", stop.getAttribute("aria-label") || "Stop response");
        }

        if (mic) {
            mic.classList.add("nova-mobile-mic-polished");
            mic.setAttribute("aria-label", mic.getAttribute("aria-label") || "Voice input");
        }

        if (account) {
            account.classList.add("nova-mobile-account-polished");
            account.setAttribute("aria-label", account.getAttribute("aria-label") || "Account");
            account.style.pointerEvents = "auto";
        }
    }

    function setRequestActive(active) {
        document.body.classList.toggle("nova-mobile-request-active", Boolean(active));

        if (requestTimer) {
            clearTimeout(requestTimer);
            requestTimer = null;
        }

        if (active) {
            requestTimer = setTimeout(() => {
                document.body.classList.remove("nova-mobile-request-active");
            }, 30000);
        }
    }

    function setMicActive(active) {
        const mic = findControl("mic");
        document.body.classList.toggle("nova-mobile-mic-active", Boolean(active));
        if (mic) {
            mic.classList.toggle("nova-mobile-mic-active", Boolean(active));
            mic.setAttribute("aria-pressed", active ? "true" : "false");
        }

        if (micTimer) {
            clearTimeout(micTimer);
            micTimer = null;
        }

        if (active) {
            micTimer = setTimeout(() => {
                setMicActive(false);
            }, 15000);
        }
    }

    function isInsideControl(target, kind) {
        const control = findControl(kind);
        return Boolean(control && target && control.contains(target));
    }

    function start() {
        markControls();

        // One extra pass after Nova mobile boot finishes. No interval, no observer.
        setTimeout(markControls, 500);
        setTimeout(markControls, 1500);

        document.addEventListener("click", event => {
            const target = event.target;

            if (isInsideControl(target, "send")) {
                setRequestActive(true);
                return;
            }

            if (isInsideControl(target, "stop")) {
                setRequestActive(false);
                return;
            }

            if (isInsideControl(target, "mic")) {
                setMicActive(!document.body.classList.contains("nova-mobile-mic-active"));
                return;
            }

            if (isInsideControl(target, "account")) {
                const account = findControl("account");

                // If it is already a real link, let it work naturally.
                if (account && account.closest("a[href]")) {
                    return;
                }

                // Fallback because Richard's account button was visible but not clickable.
                const possible = ["/account", "/profile", "/dashboard"];
                const current = window.location.pathname;
                if (!possible.includes(current)) {
                    window.location.href = "/account";
                }
            }
        }, true);

        document.addEventListener("keydown", event => {
            if (event.key === "Enter" && !event.shiftKey) {
                const active = document.activeElement;
                const tag = active ? active.tagName.toLowerCase() : "";
                if (tag === "textarea" || tag === "input" || active?.isContentEditable) {
                    setRequestActive(true);
                }
            }
        }, true);

        window.addEventListener("nova:response-finished", () => setRequestActive(false));
        window.addEventListener("nova:stream-finished", () => setRequestActive(false));
        window.addEventListener("nova:voice-stop", () => setMicActive(false));

        console.log("[NOVA_MOBILE_BUTTON_POLISH_20260702] active");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
