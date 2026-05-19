(function () {
  "use strict";

  let currentAudio = null;
  let busy = false;
  let wired = false;

  function getTtsButton() {
    return document.querySelector('[data-action="tts-toggle"]');
  }

  function findAssistantMessages() {
    return Array.from(
      document.querySelectorAll(
        ".nova-message-assistant, [data-role='assistant'], [data-message-role='assistant']"
      )
    );
  }

  function getMessageTextFromElement(element) {
    if (!element) {
      return "";
    }

    const textElement =
      element.querySelector(".nova-message-text") ||
      element.querySelector("[data-message-text]") ||
      element;

    return String(textElement.innerText || textElement.textContent || "").trim();
  }

  function getLastAssistantMessage() {
    const assistantMessages = findAssistantMessages();
    return assistantMessages[assistantMessages.length - 1] || null;
  }

  function getTargetAssistantText(event) {
    const clickedMessage = event.target.closest(
      ".nova-message-assistant, [data-role='assistant'], [data-message-role='assistant']"
    );

    if (clickedMessage) {
      return getMessageTextFromElement(clickedMessage);
    }

    return getMessageTextFromElement(getLastAssistantMessage());
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

  async function playText(text) {
    if (!text) {
      console.warn("[NovaTTS] No assistant text found.");
      return;
    }

    if (currentAudio) {
      stopAudio();
      return;
    }

    if (busy) {
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

  async function handleTtsClick(event) {
    const button = event.target.closest('[data-action="tts-toggle"]');

    if (!button) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }

    const text = getTargetAssistantText(event);
    await playText(text);
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

    if (!wired) {
      document.addEventListener("click", handleTtsClick, true);
      wired = true;
    }

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
      return playText(getMessageTextFromElement(getLastAssistantMessage()));
    },
    playText: playText,
    stop: stopAudio,
    wire: wireTtsButton,
  };
})();