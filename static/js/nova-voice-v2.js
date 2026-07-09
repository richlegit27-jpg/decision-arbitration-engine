(function () {
  "use strict";

  let recognition = null;
  let listening = false;
  let lastAssistantText = "";

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) {
      el.textContent = "status: " + text;
    }
  }

  function getInput() {
    return $("input") || $("desktopChatInput");
  }

  function getVoiceButton() {
    return $("voiceBtn") || $("desktopVoiceButton") || $("micBtn");
  }

  function getTtsButton() {
    return $("ttsBtn") || $("desktopTtsButton") || $("speakBtn");
  }

  function getLatestAssistantText() {
    const bubbles = document.querySelectorAll(".msg.assistant .bubble");
    if (!bubbles.length) return lastAssistantText;

    const latest = bubbles[bubbles.length - 1];
    return String(latest.textContent || "").trim();
  }

  function appendToInput(text) {
    const input = getInput();
    if (!input) return;

    const existing = String(input.value || "").trim();
    const incoming = String(text || "").trim();

    input.value = existing
      ? existing + " " + incoming
      : incoming;

    input.focus();
  }

  function setupRecognition() {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("[NOVA Voice V2] speech recognition not supported");
      return null;
    }

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = "en-US";

    rec.onstart = function () {
      listening = true;
      setStatus("listening");
      const btn = getVoiceButton();
      if (btn) btn.classList.add("active");
    };

    rec.onend = function () {
      listening = false;
      setStatus("ready");
      const btn = getVoiceButton();
      if (btn) btn.classList.remove("active");
    };

    rec.onerror = function (event) {
      console.warn("[NOVA Voice V2] recognition error", event);
      listening = false;
      setStatus("voice failed");
    };

    rec.onresult = function (event) {
      const result =
        event.results &&
        event.results[0] &&
        event.results[0][0];

      const text = result ? result.transcript : "";
      appendToInput(text);
      setStatus("voice captured");
    };

    return rec;
  }

  function toggleVoice() {
    if (!recognition) {
      recognition = setupRecognition();
    }

    if (!recognition) {
      setStatus("voice unsupported");
      return;
    }

    if (listening) {
      recognition.stop();
      return;
    }

    recognition.start();
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  function speakLatest() {
    if (!("speechSynthesis" in window)) {
      setStatus("tts unsupported");
      return;
    }

    const text = getLatestAssistantText();
    if (!text) {
      setStatus("nothing to speak");
      return;
    }

    stopSpeaking();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onstart = function () {
      setStatus("speaking");
    };

    utterance.onend = function () {
      setStatus("ready");
    };

    utterance.onerror = function (event) {
      console.warn("[NOVA Voice V2] tts error", event);
      setStatus("tts failed");
    };

    window.speechSynthesis.speak(utterance);
  }

  function bindVoice() {
    const voiceBtn = getVoiceButton();
    const ttsBtn = getTtsButton();

    if (voiceBtn) {
      voiceBtn.onclick = function (event) {
        event.preventDefault();
        toggleVoice();
      };
    }

    if (ttsBtn) {
      ttsBtn.onclick = function (event) {
        event.preventDefault();

        if (
          window.speechSynthesis &&
          window.speechSynthesis.speaking
        ) {
          stopSpeaking();
          setStatus("speech stopped");
          return;
        }

        speakLatest();
      };
    }
  }

  function boot() {
    bindVoice();
    console.log("[NOVA Voice V2] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaSpeakLatestV2 = speakLatest;
  window.NovaStopSpeakingV2 = stopSpeaking;
  window.NovaToggleVoiceV2 = toggleVoice;
})();

