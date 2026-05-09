(() => {
  "use strict";

  if (window.__novaPolishLoaded) {
    console.warn("Nova polish already loaded.");
    return;
  }
  window.__novaPolishLoaded = true;

  const els = {
    chatMessages: document.getElementById("chatMessages"),
    messageInput: document.getElementById("messageInput"),
    sendBtn: document.getElementById("sendBtn"),
    stopBtn: document.getElementById("stopBtn"),
    chatSubtitle: document.getElementById("chatSubtitle"),
    modelStatus: document.getElementById("modelStatus")
  };

  let typingBubble = null;
  let lastKnownAssistantCount = 0;
  let scrollLock = false;

  function getMessageNodes() {
    if (!els.chatMessages) return [];
    return Array.from(
      els.chatMessages.querySelectorAll(".message, .chat-message, .msg")
    );
  }

  function getAssistantMessages() {
    return getMessageNodes().filter((node) => node.classList.contains("assistant"));
  }

  function getUserMessages() {
    return getMessageNodes().filter((node) => node.classList.contains("user"));
  }

  function getMessageText(node) {
    if (!node) return "";
    const content =
      node.querySelector(".chat-message-content") ||
      node.querySelector(".message-content") ||
      node.querySelector("[data-role='message-content']");
    return (content?.innerText || node.innerText || "").trim();
  }

  function updateEmptyState() {
    if (!els.chatMessages) return;
    const hasMessages = getMessageNodes().length > 0;
    els.chatMessages.classList.toggle("has-messages", hasMessages);
  }

  function autoGrowTextarea() {
    if (!els.messageInput) return;
    els.messageInput.style.height = "auto";
    const next = Math.min(Math.max(els.messageInput.scrollHeight, 50), 180);
    els.messageInput.style.height = `${next}px`;
  }

  function setSubtitle(text) {
    if (els.chatSubtitle) {
      els.chatSubtitle.textContent = text;
    }
  }

  function setModelStatus(text) {
    if (els.modelStatus) {
      els.modelStatus.textContent = text;
    }
  }

  function userIsNearBottom() {
    if (!els.chatMessages) return true;
    const threshold = 140;
    const distanceFromBottom =
      els.chatMessages.scrollHeight -
      els.chatMessages.scrollTop -
      els.chatMessages.clientHeight;
    return distanceFromBottom <= threshold;
  }

  function scrollToBottom(force = false) {
    if (!els.chatMessages) return;
    if (!force && scrollLock) return;

    window.requestAnimationFrame(() => {
      if (!els.chatMessages) return;
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    });
  }

  function createTypingBubble() {
    const bubble = document.createElement("div");
    bubble.className = "nova-typing";
    bubble.id = "novaTypingBubble";
    bubble.innerHTML = `
      <div class="nova-typing-label">Nova</div>
      <div class="nova-typing-dots" aria-label="Nova is typing">
        <span></span><span></span><span></span>
      </div>
    `;
    return bubble;
  }

  function ensureTypingBubble() {
    if (!els.chatMessages) return;
    if (typingBubble && document.body.contains(typingBubble)) {
      scrollToBottom(true);
      return;
    }

    typingBubble = createTypingBubble();
    els.chatMessages.appendChild(typingBubble);
    scrollToBottom(true);
  }

  function removeTypingBubble() {
    if (typingBubble && typingBubble.parentNode) {
      typingBubble.parentNode.removeChild(typingBubble);
    }
    typingBubble = null;
  }

  function setSendingState(on) {
    document.body.classList.toggle("is-sending", !!on);

    if (on) {
      scrollLock = false;
      ensureTypingBubble();
      setSubtitle("Thinking...");
      setModelStatus("Generating...");
      scrollToBottom(true);
      return;
    }

    removeTypingBubble();
    setSubtitle("Ready");
    setModelStatus("Model ready");
    scrollToBottom(true);
  }

  function addActionRowToMessage(node) {
    if (!node || !node.classList.contains("assistant")) return;
    if (node.querySelector(".nova-polish-actions")) return;

    const actionRow = document.createElement("div");
    actionRow.className = "nova-polish-actions";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "nova-polish-btn";
    copyBtn.textContent = "Copy";

    copyBtn.addEventListener("click", async () => {
      const text = getMessageText(node);
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = "Copied";
        copyBtn.classList.add("is-done");
        window.setTimeout(() => {
          copyBtn.textContent = "Copy";
          copyBtn.classList.remove("is-done");
        }, 1200);
      } catch (error) {
        console.warn("Copy failed:", error);
        copyBtn.textContent = "Copy failed";
        window.setTimeout(() => {
          copyBtn.textContent = "Copy";
        }, 1200);
      }
    });

    const regenBtn = document.createElement("button");
    regenBtn.type = "button";
    regenBtn.className = "nova-polish-btn";
    regenBtn.textContent = "Regenerate";

    regenBtn.addEventListener("click", () => {
      const userMessages = getUserMessages();
      const lastUser = userMessages[userMessages.length - 1];
      const lastUserText = getMessageText(lastUser);

      if (!lastUserText || !els.messageInput || !els.sendBtn) {
        return;
      }

      els.messageInput.value = lastUserText;
      autoGrowTextarea();
      els.messageInput.focus();
      setSendingState(true);

      window.setTimeout(() => {
        els.sendBtn.click();
      }, 30);
    });

    actionRow.appendChild(copyBtn);
    actionRow.appendChild(regenBtn);
    node.appendChild(actionRow);
  }

  function enhanceMessages() {
    const messages = getMessageNodes();
    messages.forEach((node) => {
      addActionRowToMessage(node);
    });
    updateEmptyState();
  }

  function monitorMessageFlow() {
    if (!els.chatMessages) return;

    const observer = new MutationObserver(() => {
      const assistantCount = getAssistantMessages().length;
      const allMessages = getMessageNodes();
      const shouldStick = userIsNearBottom() || document.body.classList.contains("is-sending");

      if (allMessages.length > 0) {
        updateEmptyState();
      }

      if (assistantCount > lastKnownAssistantCount) {
        setSendingState(false);
      }

      lastKnownAssistantCount = assistantCount;
      enhanceMessages();

      if (shouldStick) {
        scrollLock = false;
        scrollToBottom(true);
      }
    });

    observer.observe(els.chatMessages, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  function wireComposer() {
    if (els.messageInput) {
      els.messageInput.addEventListener("input", autoGrowTextarea);
      autoGrowTextarea();
    }

    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", () => {
        const value = (els.messageInput?.value || "").trim();
        if (!value) return;
        scrollLock = false;
        setSendingState(true);
        scrollToBottom(true);
      });
    }

    if (els.stopBtn) {
      els.stopBtn.addEventListener("click", () => {
        setSendingState(false);
      });
    }
  }

  function wireScrollTracking() {
    if (!els.chatMessages) return;

    els.chatMessages.addEventListener("scroll", () => {
      scrollLock = !userIsNearBottom();
    });
  }

  function init() {
    lastKnownAssistantCount = getAssistantMessages().length;
    wireComposer();
    wireScrollTracking();
    enhanceMessages();
    monitorMessageFlow();
    updateEmptyState();
    scrollToBottom(true);
    console.log("Nova polish loaded.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();