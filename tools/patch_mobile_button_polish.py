from pathlib import Path

CSS = Path("static/css/nova-mobile.css")
JS = Path("static/js/mobile/nova-mobile-button-polish.js")
TEMPLATE = Path("templates/mobile.html")

CSS_MARKER = "NOVA_MOBILE_BUTTON_POLISH_20260702"
JS_MARKER = "NOVA_MOBILE_BUTTON_POLISH_20260702"

css_block = r'''

/* NOVA_MOBILE_BUTTON_POLISH_20260702
   Mobile-only button polish.
   Improves Send/Stop feedback, mic active state, and account button visibility/clickability.
   No chat rendering changes. No width observers. No desktop target.
*/
body.nova-mobile-button-polish-ready {
    --nova-polish-purple: #8b5cf6;
    --nova-polish-purple-2: #a855f7;
    --nova-polish-danger: #ef4444;
    --nova-polish-green: #22c55e;
    --nova-polish-dark: rgba(15, 23, 42, 0.96);
}

/* Shared polished mobile buttons */
.nova-mobile-send-polished,
.nova-mobile-stop-polished,
.nova-mobile-mic-polished,
.nova-mobile-account-polished {
    position: relative !important;
    isolation: isolate !important;
    min-width: 42px !important;
    min-height: 42px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    box-shadow: 0 8px 22px rgba(0,0,0,0.28) !important;
    transition:
        transform 140ms ease,
        opacity 140ms ease,
        box-shadow 140ms ease,
        background 140ms ease,
        border-color 140ms ease !important;
    -webkit-tap-highlight-color: transparent !important;
    pointer-events: auto !important;
    touch-action: manipulation !important;
}

.nova-mobile-send-polished:active,
.nova-mobile-stop-polished:active,
.nova-mobile-mic-polished:active,
.nova-mobile-account-polished:active {
    transform: scale(0.94) !important;
}

/* Send button: purple, clear, animated while request is active */
.nova-mobile-send-polished {
    background: linear-gradient(135deg, var(--nova-polish-purple), var(--nova-polish-purple-2)) !important;
    color: #fff !important;
    font-weight: 800 !important;
}

body.nova-mobile-request-active .nova-mobile-send-polished {
    color: transparent !important;
    opacity: 0.92 !important;
}

body.nova-mobile-request-active .nova-mobile-send-polished::after {
    content: "" !important;
    position: absolute !important;
    width: 18px !important;
    height: 18px !important;
    left: calc(50% - 9px) !important;
    top: calc(50% - 9px) !important;
    border-radius: 999px !important;
    border: 3px solid rgba(255,255,255,0.35) !important;
    border-top-color: #fff !important;
    animation: nova-mobile-button-spin-20260702 800ms linear infinite !important;
    z-index: 2 !important;
}

/* Stop button: red pulse when request is active */
.nova-mobile-stop-polished {
    background: rgba(239, 68, 68, 0.95) !important;
    color: #fff !important;
    font-weight: 900 !important;
}

body.nova-mobile-request-active .nova-mobile-stop-polished {
    box-shadow:
        0 0 0 4px rgba(239, 68, 68, 0.20),
        0 10px 26px rgba(239, 68, 68, 0.32) !important;
    animation: nova-mobile-stop-pulse-20260702 900ms ease-in-out infinite !important;
}

/* Mic: noticeable idle and obvious active/listening pulse */
.nova-mobile-mic-polished {
    background: rgba(30, 41, 59, 0.96) !important;
    color: #fff !important;
}

.nova-mobile-mic-polished.nova-mobile-mic-active,
body.nova-mobile-mic-active .nova-mobile-mic-polished,
.nova-mobile-mic-polished[aria-pressed="true"] {
    background: linear-gradient(135deg, var(--nova-polish-green), #14b8a6) !important;
    color: #04111f !important;
    border-color: rgba(255,255,255,0.45) !important;
    box-shadow:
        0 0 0 5px rgba(34,197,94,0.20),
        0 0 24px rgba(34,197,94,0.55),
        0 10px 28px rgba(0,0,0,0.32) !important;
    animation: nova-mobile-mic-pulse-20260702 850ms ease-in-out infinite !important;
}

.nova-mobile-mic-polished.nova-mobile-mic-active::after,
body.nova-mobile-mic-active .nova-mobile-mic-polished::after {
    content: "listening" !important;
    position: absolute !important;
    left: 50% !important;
    top: -24px !important;
    transform: translateX(-50%) !important;
    padding: 3px 8px !important;
    border-radius: 999px !important;
    background: rgba(4, 17, 31, 0.92) !important;
    color: #bbf7d0 !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: 0.02em !important;
    white-space: nowrap !important;
    pointer-events: none !important;
}

/* Account/profile top button: visible and clickable */
.nova-mobile-account-polished,
#mobileAccountButton,
#accountButton,
#accountBtn,
#profileButton,
#profileBtn,
.mobile-account-button,
.mobile-profile-button,
.account-button,
.profile-button,
button[aria-label*="account" i],
button[aria-label*="profile" i],
a[aria-label*="account" i],
a[aria-label*="profile" i] {
    position: relative !important;
    z-index: 9999 !important;
    pointer-events: auto !important;
    background: linear-gradient(135deg, #111827, var(--nova-polish-purple)) !important;
    color: #fff !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    box-shadow: 0 8px 24px rgba(139, 92, 246, 0.35) !important;
    opacity: 1 !important;
    visibility: visible !important;
}

.nova-mobile-account-polished::after {
    content: "" !important;
    position: absolute !important;
    inset: -5px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(168,85,247,0.35) !important;
    pointer-events: none !important;
}

@keyframes nova-mobile-button-spin-20260702 {
    to {
        transform: rotate(360deg);
    }
}

@keyframes nova-mobile-stop-pulse-20260702 {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.045);
    }
}

@keyframes nova-mobile-mic-pulse-20260702 {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.065);
    }
}
'''

js_code = r'''// NOVA_MOBILE_BUTTON_POLISH_20260702
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
'''

if not CSS.exists():
    raise SystemExit(f"missing CSS: {CSS}")

css_text = CSS.read_text(encoding="utf-8-sig", errors="ignore")
if CSS_MARKER not in css_text:
    CSS.write_text(css_text.rstrip() + "\n" + css_block + "\n", encoding="utf-8")
    print("patched", CSS)
else:
    print("CSS already patched")

JS.parent.mkdir(parents=True, exist_ok=True)
JS.write_text(js_code, encoding="utf-8")
print("wrote", JS)

if not TEMPLATE.exists():
    raise SystemExit(f"missing template: {TEMPLATE}")

template_text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")
script_tag = '<script src="{{ url_for(\'static\', filename=\'js/mobile/nova-mobile-button-polish.js\') }}?v=20260702"></script>'

if "nova-mobile-button-polish.js" not in template_text:
    lower = template_text.lower()
    idx = lower.rfind("</body>")
    if idx >= 0:
        template_text = template_text[:idx] + "    " + script_tag + "\n" + template_text[idx:]
    else:
        template_text = template_text.rstrip() + "\n" + script_tag + "\n"
    TEMPLATE.write_text(template_text, encoding="utf-8")
    print("wired", TEMPLATE)
else:
    print("template already wired")
