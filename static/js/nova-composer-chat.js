(function () {
  "use strict";

  if (window.NovaComposerChat) return;

  function bootModule() {
    const core = window.NovaComposerCore;
    if (!core) return false;

    const state = core.state;
    const els = core.els;

    function log() {
      try {
        console.log("[NovaComposerChat]", ...arguments);
      } catch (_) {}
    }

    function autosizeInput() {
      if (!els.chatInput) return;
      els.chatInput.style.height = "0px";
      els.chatInput.style.height = Math.min(Math.max(42, els.chatInput.scrollHeight), 220) + "px";
    }

    function getChatThread() {
      return els.chatThread || els.chat || document.querySelector("[data-chat-thread]");
    }

    function scrollToBottom() {
      const thread = getChatThread();
      if (!thread) return;
      thread.scrollTop = thread.scrollHeight;
    }

    function createMessageNode(role, text) {
      const thread = getChatThread();
      if (!thread) return null;

      const wrap = document.createElement("div");
      wrap.className = "nova-message nova-message-" + role;

      const body = document.createElement("div");
      body.className = "nova-message-body";
      body.textContent = text || "";

      wrap.appendChild(body);
      thread.appendChild(wrap);
      scrollToBottom();

      return { wrap, body };
    }

    function setSending(flag) {
      state.sending = !!flag;

      if (typeof core.renderTopbar === "function") {
        core.renderTopbar();
      }

      const sendBtn =
        els.sendBtn ||
        document.querySelector('[data-action="send"]');

      if (sendBtn) {
        sendBtn.disabled = !!flag;
      }

      if (els.chatInput) {
        els.chatInput.disabled = !!flag;
      }
    }

    async function streamMessage(text) {
      const userNode = createMessageNode("user", text);
      const assistantNode = createMessageNode("assistant", "");
      if (assistantNode && assistantNode.wrap) {
        assistantNode.wrap.classList.add("is-streaming");
      }

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream"
        },
        body: JSON.stringify({
          message: text,
          session_id: state.activeSessionId || state.sessionId || "",
          attachments: Array.isArray(state.pendingUploads) ? state.pendingUploads : []
        })
      });

      if (!response.ok || !response.body) {
        throw new Error("Streaming request failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalPayload = null;

      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;

        buffer += decoder.decode(chunk.value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const line = part
            .split("\n")
            .find((entry) => entry.startsWith("data:"));

          if (!line) continue;

          const raw = line.slice(5).trim();
          if (!raw) continue;

          let eventData = null;
          try {
            eventData = JSON.parse(raw);
          } catch (err) {
            console.error("[NovaComposerChat] stream parse failed", err, raw);
            continue;
          }

          if (eventData.delta && assistantNode && assistantNode.body) {
            assistantNode.body.textContent += eventData.delta;
            scrollToBottom();
          }

          if (eventData.route_meta) {
            state.lastResponse = Object.assign({}, state.lastResponse || {}, {
              route_meta: eventData.route_meta
            });
            if (typeof core.renderTopbar === "function") {
              core.renderTopbar();
            }
          }

          if (eventData.done) {
            finalPayload = eventData;
          }

          if (eventData.error) {
            throw new Error(eventData.error);
          }
        }
      }

      if (assistantNode && assistantNode.wrap) {
        assistantNode.wrap.classList.remove("is-streaming");
      }

      if (finalPayload && typeof core.applyState === "function") {
        core.applyState(finalPayload);
      }

      if (typeof core.renderAll === "function") {
        core.renderAll();
      } else {
        scrollToBottom();
      }
    }

    async function sendMessage() {
      if (!els.chatInput || state.sending) return;

      const text = String(els.chatInput.value || "").trim();
      if (!text && !(Array.isArray(state.pendingUploads) && state.pendingUploads.length)) {
        return;
      }

      setSending(true);

      try {
        els.chatInput.value = "";
        autosizeInput();

        await streamMessage(text);

        state.pendingUploads = [];
        if (typeof core.renderAll === "function") {
          core.renderAll();
        }
      } catch (error) {
        console.error("[NovaComposerChat] sendMessage failed", error);
        alert(error && error.message ? error.message : "Send failed.");
      } finally {
        setSending(false);
        autosizeInput();
      }
    }

    function bind() {
      document.addEventListener("click", async function (event) {
        const trigger = event.target.closest('[data-action="send"]');
        if (!trigger) return;
        event.preventDefault();
        await sendMessage();
      });

      if (els.chatInput) {
        els.chatInput.addEventListener("input", autosizeInput);
        els.chatInput.addEventListener("keydown", async function (event) {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            await sendMessage();
          }
        });
      }
    }

    function boot() {
      bind();
      autosizeInput();

      window.NovaComposerChat = {
        sendMessage,
        autosizeInput,
      };

      log("streaming enabled");
      return true;
    }

    return boot();
  }

  if (!bootModule()) {
    document.addEventListener("DOMContentLoaded", function () {
      bootModule();
    });
  }
})();