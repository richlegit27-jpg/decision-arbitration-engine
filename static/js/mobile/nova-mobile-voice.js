(function () {
    "use strict";

    // NOVA_MOBILE_SAFE_VOICE_TOAST_20260608
    function safeToast(message) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        if (typeof window.NovaToast === "function") {
            window.NovaToast(message);
            return;
        }

        try {
            console.log("[Nova Mobile Voice]", message);
        } catch (error) {}
    }

    function getRecognitionConstructor() {
        return (
            window.SpeechRecognition ||
            window.webkitSpeechRecognition ||
            null
        );
    }

    async function startVoiceInput() {
        const Recognition = getRecognitionConstructor();

        if (!Recognition) {
            safeToast("Voice input is not supported in this browser.");
            return;
        }

        const input =
            window.inputEl ||
            document.getElementById("nova-mobile-input");

        if (!input) {
            safeToast("Input box not found.");
            return;
        }

        const recognition = new Recognition();

        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = function (event) {
            const transcript =
                event.results &&
                event.results[0] &&
                event.results[0][0]
                    ? event.results[0][0].transcript
                    : "";

            if (!transcript.trim()) return;

            input.value = transcript.trim();
            input.focus();

            if (
                window.NovaMobileCore &&
                typeof window.NovaMobileCore.autoGrowInput === "function"
            ) {
                window.NovaMobileCore.autoGrowInput();
            }

            safeToast("Voice captured.");
        };

        recognition.onerror = function () {
            safeToast("Voice input failed.");
        };

        recognition.onend = function () {
            if (window.voiceBtn) {
                window.voiceBtn.classList.remove("recording");
            }
        };

        recognition.start();
        safeToast("Listening...");
    }

    window.NovaMobileVoice = {
        startVoiceInput
    };

// The loaded mobile app owns the visible Voice button. Keep this helper
// available to legacy tool callers without binding a second button handler.

    console.log("[Nova Mobile] voice module ready");
})();


