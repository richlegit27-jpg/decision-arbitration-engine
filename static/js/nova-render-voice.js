(() => {
  "use strict";

  if (window.__novaRenderVoiceLoaded) return;
  window.__novaRenderVoiceLoaded = true;

  const Nova = (window.Nova = window.Nova || {});
  Nova.voice = Nova.voice || {};

  const state = {
    recognition: null,
    supported: false,
    listening: false,
    denied: false,
    button: null,
    input: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function getVoiceButton() {
    return (
      byId("novaVoiceBtn") ||
      byId("voiceBtn") ||
      qs('[data-action="voice"]') ||
      qs(".nova-voice-btn")
    );
  }

  function getComposerInput() {
    return (
      byId("novaComposerInput") ||
      byId("novaInput") ||
      byId("composerInput") ||
      qs("textarea")
    );
  }

  function setButtonState(mode, label) {
    const btn = state.button || getVoiceButton();
    if (!btn) return;

    btn.classList.remove(
      "is-listening",
      "is-idle",
      "is-unsupported",
      "is-denied",
      "is-busy"
    );

    if (mode) {
      btn.classList.add(mode);
    }

    if (label) {
      btn.setAttribute("aria-label", label);
      btn.title = label;
    }

    btn.disabled = mode === "is-unsupported";
  }

  function insertTextAtCursor(text) {
    const input = state.input || getComposerInput();
    if (!input) return;

    const current = input.value || "";
    const start = Number.isInteger(input.selectionStart) ? input.selectionStart : current.length;
    const end = Number.isInteger(input.selectionEnd) ? input.selectionEnd : current.length;

    const before = current.slice(0, start);
    const after = current.slice(end);

    const joiner =
      before && !before.endsWith(" ") && text && !String(text).startsWith(" ")
        ? " "
        : "";

    input.value = `${before}${joiner}${text}${after}`;
    input.focus();

    const pos = (before + joiner + text).length;
    try {
      input.setSelectionRange(pos, pos);
    } catch {}

    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function stopListening() {
    if (state.recognition && state.listening) {
      try {
        state.recognition.stop();
      } catch {}
    }

    state.listening = false;

    if (state.supported) {
      setButtonState("is-idle", "Start voice input");
    }
  }

  function startListening() {
    if (!state.supported || !state.recognition) return;
    if (state.listening) return;

    state.input = getComposerInput();

    try {
      state.recognition.start();
      state.listening = true;
      setButtonState("is-listening", "Listening… click to stop");
    } catch (err) {
      console.error("Voice start failed:", err);
      state.listening = false;
      setButtonState("is-idle", "Start voice input");
    }
  }

  function toggleListening() {
    if (!state.supported) return;

    if (state.denied) {
      setButtonState("is-denied", "Microphone permission denied");
      return;
    }

    if (state.listening) {
      stopListening();
      return;
    }

    startListening();
  }

  function handleResult(event) {
    const results = Array.from(event.results || []);
    const transcript = results
      .map((result) => {
        const alt = result && result[0];
        return alt && alt.transcript ? alt.transcript : "";
      })
      .join(" ")
      .trim();

    if (!transcript) return;

    insertTextAtCursor(transcript);
  }

  function buildRecognition() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      state.supported = false;
      setButtonState("is-unsupported", "Voice input not supported in this browser");
      return;
    }

    state.supported = true;

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      state.listening = true;
      setButtonState("is-listening", "Listening… click to stop");
    };

    recognition.onresult = (event) => {
      handleResult(event);
    };

    recognition.onerror = (event) => {
      const error = String(event?.error || "").toLowerCase();
      console.error("Voice recognition error:", error || event);

      state.listening = false;

      if (
        error === "not-allowed" ||
        error === "service-not-allowed" ||
        error === "permission-denied"
      ) {
        state.denied = true;
        setButtonState("is-denied", "Microphone permission denied");
        return;
      }

      if (error === "no-speech") {
        setButtonState("is-idle", "No speech detected");
        return;
      }

      if (error === "audio-capture") {
        setButtonState("is-denied", "No microphone detected");
        return;
      }

      setButtonState("is-idle", "Start voice input");
    };

    recognition.onend = () => {
      state.listening = false;

      if (state.denied) {
        setButtonState("is-denied", "Microphone permission denied");
      } else {
        setButtonState("is-idle", "Start voice input");
      }
    };

    state.recognition = recognition;
    setButtonState("is-idle", "Start voice input");
  }

  function bindUI() {
    state.button = getVoiceButton();
    state.input = getComposerInput();

    if (!state.button) return;

    if (state.button.dataset.voiceBound === "1") return;
    state.button.dataset.voiceBound = "1";

    state.button.addEventListener("click", (e) => {
      e.preventDefault();
      toggleListening();
    });
  }

  function bootstrap() {
    bindUI();
    buildRecognition();
  }

  Nova.voice.start = startListening;
  Nova.voice.stop = stopListening;
  Nova.voice.toggle = toggleListening;
  Nova.voice.state = state;

  document.addEventListener("DOMContentLoaded", bootstrap);
})();