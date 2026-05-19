(function () {
  "use strict";

  let currentAudio = null;
  let busy = false;
  let wired = false;

  const NOVA_TTS_VOICE_KEY = "nova_tts_voice";
  const NOVA_TTS_AUTOSPEAK_KEY = "nova_tts_autospeak";

const NOVA_HANDS_FREE_KEY = "nova_hands_free";

function getHandsFreeEnabled() {
  return localStorage.getItem(NOVA_HANDS_FREE_KEY) === "true";
}

function setHandsFreeEnabled(enabled) {
  localStorage.setItem(NOVA_HANDS_FREE_KEY, enabled ? "true" : "false");
}

  function getAutoSpeakEnabled() {
    return localStorage.getItem(NOVA_TTS_AUTOSPEAK_KEY) === "true";
  }

  function setAutoSpeakEnabled(enabled) {
    localStorage.setItem(NOVA_TTS_AUTOSPEAK_KEY, enabled ? "true" : "false");
  }

  function getSelectedVoice() {
    return localStorage.getItem(NOVA_TTS_VOICE_KEY) || "alloy";
  }

  function setSelectedVoice(voice) {
    localStorage.setItem(NOVA_TTS_VOICE_KEY, voice || "alloy");
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

  function getGlobalTtsButton() {
    return document.querySelector('[data-action="tts-toggle"]');
  }

  function injectStyles() {
    if (document.querySelector("#nova-tts-player-style")) {
      return;
    }

    const style = document.createElement("style");
    style.id = "nova-tts-player-style";
    style.textContent = `
      .nova-voice-control-shell {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-left: 8px;
        padding: 4px 6px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(15,23,42,0.62);
        backdrop-filter: blur(14px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
        vertical-align: middle;
      }

      #nova-tts-voice-picker {
        min-width: 86px;
        height: 28px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(17,24,39,0.92);
        color: white;
        padding: 0 9px;
        font-size: 12px;
        outline: none;
        cursor: pointer;
      }

      #nova-tts-voice-picker:hover {
        border-color: rgba(255,255,255,0.28);
      }

#nova-hands-free-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(17,24,39,0.78);
  color: rgba(255,255,255,0.88);
  font-size: 12px;
  cursor: pointer;
  user-select: none;
}

#nova-hands-free-toggle:hover {
  border-color: rgba(255,255,255,0.28);
  color: white;
}

#nova-hands-free-toggle input {
  accent-color: #60a5fa;
  cursor: pointer;
}

#nova-speaking-status-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.56);
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 12px;
  white-space: nowrap;
}

#nova-speaking-status-label:empty {
  display: none;
}

      #nova-tts-autospeak-toggle:hover {
        border-color: rgba(255,255,255,0.28);
        color: white;
      }

      #nova-tts-autospeak-toggle input {
        accent-color: #60a5fa;
        cursor: pointer;
      }

      .nova-inline-tts-button {
        margin-left: 8px;
        padding: 5px 9px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.16);
        background: rgba(17,24,39,0.78);
        color: white;
        font-size: 13px;
        line-height: 1;
        cursor: pointer;
        vertical-align: middle;
        opacity: 0.86;
        transition:
          opacity 140ms ease,
          transform 140ms ease,
          border-color 140ms ease,
          background 140ms ease;
      }

      .nova-inline-tts-button:hover {
        opacity: 1;
        transform: translateY(-1px);
        border-color: rgba(255,255,255,0.3);
      }

      .nova-inline-tts-button.is-playing,
      [data-action="tts-toggle"].is-playing {
        background: rgba(220,38,38,0.88);
      }

      .nova-inline-tts-button.is-busy,
      [data-action="tts-toggle"].is-busy {
        opacity: 0.65;
        cursor: wait;
      }
    `;

    document.head.appendChild(style);
  }

  function ensureControlShell() {
    const globalButton = getGlobalTtsButton();

    if (!globalButton || !globalButton.parentElement) {
      return null;
    }

    let shell = document.querySelector(".nova-voice-control-shell");

    if (!shell) {
      shell = document.createElement("span");
      shell.className = "nova-voice-control-shell";

      globalButton.parentElement.insertBefore(shell, globalButton.nextSibling);
    }

    return shell;
  }

function setSpeakingStatus(text) {
  let label = document.querySelector("#nova-speaking-status-label");

  if (!label) {
    label = document.createElement("span");
    label.id = "nova-speaking-status-label";
    label.textContent = "";

    const shell = document.querySelector(".nova-voice-control-shell");
    const globalButton = getGlobalTtsButton();

    if (shell) {
      shell.appendChild(label);
    } else if (globalButton && globalButton.parentElement) {
      globalButton.parentElement.appendChild(label);
    }
  }

  label.textContent = text || "";
}

  function setButtonState(button, state) {
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
  button.title = "Speaking… click to stop";
  button.setAttribute("aria-label", "Speaking. Click to stop.");
  button.classList.add("is-playing");
  setSpeakingStatus("Speaking… click 🔊/⏹️ to stop");
  return;
}

    button.textContent = "🔊";
    button.title = "Play voice";
    button.setAttribute("aria-label", "Play voice");
    setSpeakingStatus("");
  }

  function resetAllButtons() {
    const buttons = document.querySelectorAll(
      '[data-action="tts-toggle"], .nova-inline-tts-button'
    );

    buttons.forEach(function (button) {
      setButtonState(button, "idle");
    });
  }

  async function createSpeech(text) {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        voice: getSelectedVoice(),
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
    resetAllButtons();
  }

  async function playText(text, button) {
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
      resetAllButtons();
      setButtonState(button, "busy");

      const audioUrl = await createSpeech(text);

      currentAudio = new Audio(audioUrl);

      currentAudio.onended = function () {
        currentAudio = null;
        busy = false;
        resetAllButtons();

        if (getHandsFreeEnabled() && window.NovaMicRecorder) {
          console.log("[NovaTTS] hands-free ready for next voice turn");

          if (typeof window.NovaMicRecorder.showHandsFreeReady === "function") {
            window.NovaMicRecorder.showHandsFreeReady();
          }
        }
      };

      currentAudio.onerror = function () {
        currentAudio = null;
        busy = false;
        resetAllButtons();
        console.error("[NovaTTS] Audio playback failed.");
      };

      setButtonState(button, "playing");
      await currentAudio.play();

      console.log("[NovaTTS] playing", audioUrl);
    } catch (error) {
      console.error("[NovaTTS] failed", error);
      busy = false;
      currentAudio = null;
      resetAllButtons();
    }
  }

  function addInlineButtons() {
    injectStyles();

    const assistantMessages = findAssistantMessages();

    assistantMessages.forEach(function (message) {
      if (message.querySelector(".nova-inline-tts-button")) {
        return;
      }

      const button = document.createElement("button");
      button.type = "button";
      button.className = "nova-inline-tts-button";
      button.setAttribute("data-action", "tts-message");
      button.textContent = "🔊";
      button.title = "Play this reply";

      const target =
        message.querySelector(".nova-message-role") ||
        message.querySelector(".nova-message-text") ||
        message;

      target.appendChild(button);
    });
  }

  async function handleTtsClick(event) {
    const inlineButton = event.target.closest(".nova-inline-tts-button");
    const globalButton = event.target.closest('[data-action="tts-toggle"]');

    if (!inlineButton && !globalButton) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }

    if (inlineButton) {
      const message = inlineButton.closest(
        ".nova-message-assistant, [data-role='assistant'], [data-message-role='assistant']"
      );

      const text = getMessageTextFromElement(message);
      await playText(text, inlineButton);
      return;
    }

    const lastMessage = getLastAssistantMessage();
    const text = getMessageTextFromElement(lastMessage);
    await playText(text, globalButton);
  }

  function observeMessages() {
    const target =
      document.querySelector("[data-chat-thread]") ||
      document.querySelector(".nova-thread") ||
      document.querySelector("#chat-thread") ||
      document.body;

    let lastAutoSpokenText = "";

    const observer = new MutationObserver(function () {
      addInlineButtons();

      if (!getAutoSpeakEnabled()) {
        return;
      }

      const lastMessage = getLastAssistantMessage();
      const text = getMessageTextFromElement(lastMessage);

      if (!text || text === lastAutoSpokenText) {
        return;
      }

      lastAutoSpokenText = text;

      setTimeout(function () {
        playText(text, getGlobalTtsButton());
      }, 300);
    });

    observer.observe(target, {
      childList: true,
      subtree: true,
    });
  }

  function ensureVoicePicker() {
    if (document.querySelector("#nova-tts-voice-picker")) {
      return;
    }

    const shell = ensureControlShell();

    if (!shell) {
      return;
    }

    const picker = document.createElement("select");
    picker.id = "nova-tts-voice-picker";
    picker.title = "TTS voice";
    picker.value = getSelectedVoice();

    const voices = [
      "alloy",
      "ash",
      "ballad",
      "coral",
      "echo",
      "fable",
      "nova",
      "onyx",
      "sage",
      "shimmer",
      "verse",
    ];

    voices.forEach(function (voice) {
      const option = document.createElement("option");
      option.value = voice;
      option.textContent = voice;
      picker.appendChild(option);
    });

    picker.onchange = function () {
      setSelectedVoice(picker.value);
      console.log("[NovaTTS] voice selected", picker.value);
    };

    shell.appendChild(picker);
  }

  function ensureAutoSpeakToggle() {
    if (document.querySelector("#nova-tts-autospeak-toggle")) {
      return;
    }

    const shell = ensureControlShell();

    if (!shell) {
      return;
    }

    const label = document.createElement("label");
    label.id = "nova-tts-autospeak-toggle";
    label.title = "Auto-speak assistant replies";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = getAutoSpeakEnabled();

    checkbox.onchange = function () {
      setAutoSpeakEnabled(checkbox.checked);
      console.log("[NovaTTS] auto-speak", checkbox.checked);
    };

    label.appendChild(checkbox);
    label.appendChild(document.createTextNode("auto"));

    shell.appendChild(label);
  }

function ensureHandsFreeToggle() {
  if (document.querySelector("#nova-hands-free-toggle")) {
    return;
  }

  const shell = ensureControlShell();

  if (!shell) {
    return;
  }

  const label = document.createElement("label");
  label.id = "nova-hands-free-toggle";
  label.title = "Hands-free voice mode";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = getHandsFreeEnabled();

  checkbox.onchange = function () {
    setHandsFreeEnabled(checkbox.checked);
    console.log("[NovaTTS] hands-free", checkbox.checked);
  };

  label.appendChild(checkbox);
  label.appendChild(document.createTextNode("hands-free"));

  shell.appendChild(label);
}

  function wireTts() {
    injectStyles();
    addInlineButtons();
    ensureVoicePicker();
    ensureAutoSpeakToggle();
    ensureHandsFreeToggle();

    const globalButton = getGlobalTtsButton();

    if (globalButton) {
      globalButton.setAttribute("data-nova-tts-bound", "true");
      globalButton.style.pointerEvents = "auto";
      globalButton.style.cursor = "pointer";
      setButtonState(globalButton, "idle");
    }

    if (!wired) {
      document.addEventListener("click", handleTtsClick, true);
      observeMessages();
      wired = true;
    }

    setTimeout(addInlineButtons, 500);
    setTimeout(addInlineButtons, 1500);
    setTimeout(addInlineButtons, 3000);

    console.log("[NovaTTS] wired");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireTts);
  } else {
    wireTts();
  }

  window.NovaTTS = {
    playLast: function () {
      const lastMessage = getLastAssistantMessage();
      return playText(getMessageTextFromElement(lastMessage), getGlobalTtsButton());
    },
    playText: function (text) {
      return playText(text, getGlobalTtsButton());
    },
    stop: stopAudio,
    wire: wireTts,
    addButtons: addInlineButtons,
  };
})();