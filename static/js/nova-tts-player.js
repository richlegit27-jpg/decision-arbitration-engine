(function () {
  "use strict";

  let currentAudio = null;
  let busy = false;

  function getLastAssistantText() {
    const assistantMessages = Array.from(
      document.querySelectorAll(".nova-message-assistant .nova-message-text")
    );

    const last = assistantMessages[assistantMessages.length - 1];

    if (!last) {
      return "";
    }

    return String(last.innerText || last.textContent || "").trim();
  }

  function getTtsButton() {
    return document.querySelector('[data-action="tts-toggle"]');
  }

  function setButtonState(state) {
    const button = getTtsButton();

    if (!button) {
      return;
    }

    button.classList.remove("is-playing", "is-busy");

    if (state === "busy") {
      button.textContent = "⏳";
      button.title = "Generating voice...";
      button.classList.add("is-busy");
      return;
    }

    if (state === "playing") {
      button.textContent = "⏹️";
      button.title = "Stop voice";
      button.classList.add("is-playing");
      return;
    }

    button.textContent = "🔊";
    button.title = "Play voice reply";
  }

  async function createSpeech(text) {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        voice: "alloy",
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "TTS failed.");
    }

    return data.audio_url;
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }

    busy = false;
    setButtonState("idle");
  }

  async function playLastAssistantMessage(event) {
    const button = event.target.closest('[data-action="tts-toggle"]');

    if (!button) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }

    if (currentAudio) {
      stopAudio();
      return;
    }

    if (busy) {
      return;
    }

    const text = getLastAssistantText();

    if (!text) {
      console.warn("[NovaTTS] No assistant text found.");
      return;
    }

    try {
      busy = true;
      setButtonState("busy");

      const audioUrl = await createSpeech(text);

      currentAudio = new Audio(audioUrl);

      currentAudio.onended = function () {
        currentAudio = null;
        busy = false;
        setButtonState("idle");
      };

      currentAudio.onerror = function () {
        currentAudio = null;
        busy = false;
        setButtonState("idle");
        console.error("[NovaTTS] Audio playback failed.");
      };

      setButtonState("playing");
      await currentAudio.play();

      console.log("[NovaTTS] playing", audioUrl);
    } catch (error) {
      console.error("[NovaTTS] failed", error);
      busy = false;
      currentAudio = null;
      setButtonState("idle");
    }
  }

  function wireTtsButton() {
    const button = getTtsButton();

    if (!button) {
      console.warn("[NovaTTS] TTS button not found");
      return;
    }

    button.setAttribute("data-nova-tts-bound", "true");
    button.style.pointerEvents = "auto";
    button.style.cursor = "pointer";

    document.addEventListener("click", playLastAssistantMessage, true);

    setButtonState("idle");

    console.log("[NovaTTS] button wired", button);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireTtsButton);
  } else {
    wireTtsButton();
  }

  window.NovaTTS = {
    playLast: function () {
      return playLastAssistantMessage({
        target: getTtsButton(),
        preventDefault: function () {},
        stopPropagation: function () {},
        stopImmediatePropagation: function () {},
      });
    },
    stop: stopAudio,
  };
})();