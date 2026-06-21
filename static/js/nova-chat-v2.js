(function () {
  "use strict";

  const LS_SID = "nova.session_id";
  let sending = false;

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text) {
    const el = $("status");
    if (el) {
      el.textContent = "status: " + text;
    }
  }

  function esc(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getSessionId() {
    const input = $("sid");
    const fromInput = input ? input.value : "";

    return (
      String(fromInput || "").trim() ||
      localStorage.getItem(LS_SID) ||
      localStorage.getItem("nova_active_session_id") ||
      localStorage.getItem("nova_session_id") ||
      window.__NOVA_ACTIVE_SESSION_ID ||
      ""
    );
  }

  function setSessionId(id) {
    const sid = String(id || "").trim();
    if (!sid) return;

    const input = $("sid");
    if (input) input.value = sid;

    localStorage.setItem(LS_SID, sid);
    localStorage.setItem("nova_active_session_id", sid);
    localStorage.setItem("nova_session_id", sid);

    window.__NOVA_ACTIVE_SESSION_ID = sid;
  }

  function getUserText() {
    const input = $("input") || $("desktopChatInput");
    return input ? String(input.value || "").trim() : "";
  }

  function clearUserText() {
    const input = $("input") || $("desktopChatInput");
    if (input) input.value = "";
  }

  function getChatBox() {
    return $("chat") || $("desktopChatBox") || $("messages");
  }

  function scrollChat() {
    const box = getChatBox();
    if (box) {
      box.scrollTop = box.scrollHeight;
    }
  }

  function appendMessage(role, text) {
    const box = getChatBox();
    if (!box) return null;

    const node = document.createElement("div");
    node.className = "msg " + esc(role);

    const roleNode = document.createElement("div");
    roleNode.className = "role";
    roleNode.textContent = role;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text || "";

    node.appendChild(roleNode);
    node.appendChild(bubble);

    box.appendChild(node);
    scrollChat();

    return node;
  }

  function setAssistantText(node, text) {
    if (!node) return;

    const bubble = node.querySelector(".bubble");
    if (bubble) {
      const value = String(text || "");

      if (
        value.includes("<img") ||
        value.includes("nova-image-result")
      ) {
        bubble.innerHTML = value;
      } else {
        bubble.textContent = value;
      }
    } else {
      node.textContent = text || "";
    }

    scrollChat();
  }

  function setAssistantImage(node, imageUrl, labelText) {
    if (!node || !imageUrl) return false;

    const bubble = node.querySelector(".bubble");
    if (!bubble) return false;

    bubble.innerHTML = "";

    const wrap = document.createElement("div");
    wrap.className = "nova-image-result";

    const img = document.createElement("img");
    img.src = imageUrl;
    img.alt = labelText || "Generated image";
    img.loading = "lazy";
    img.style.maxWidth = "100%";
    img.style.borderRadius = "14px";
    img.style.display = "block";

    wrap.appendChild(img);
    bubble.appendChild(wrap);

    scrollChat();
    return true;
  }

  function extractAssistantText(data) {
    return (
      data?.assistant_message?.text ||
      data?.assistant_message?.content ||
      data?.text ||
      data?.response ||
      data?.message ||
      ""
    );
  }

  function extractImageUrl(data) {
    return (
      data?.image_url ||
      data?.assistant_message?.image_url ||
      data?.assistant_message?.meta?.image_url ||
      data?.artifact?.image_url ||
      data?.saved_artifact?.image_url ||
      ""
    );
  }

  function extractSessionId(data) {
    return (
      data?.active_session_id ||
      data?.session_id ||
      data?.session?.id ||
      data?.assistant_message?.session_id ||
      ""
    );
  }

  async function sendText(promptOverride) {
    if (sending) {
      console.warn("[NOVA Chat V2] blocked duplicate send");
      return;
    }

    const text = String(promptOverride || getUserText() || "").trim();
    if (!text) return;

    sending = true;

    const sendBtn = $("sendBtn") || $("desktopSendButton");
    if (sendBtn) sendBtn.disabled = true;

    appendMessage("user", text);
    clearUserText();

    const assistantNode = appendMessage("assistant", "Nova is thinking...");

    try {
      setStatus("sending");

      const payload = {
        message: text,
        text: text,
        user_text: text,
        session_id: getSessionId()
      };

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "testkey123"
        },
        body: JSON.stringify(payload)
      });

      const raw = await res.text();

      let data = null;
      try {
        data = JSON.parse(raw);
      } catch (error) {
        console.warn("[NOVA Chat V2] non-json response", raw);
      }

      if (!res.ok) {
        throw new Error("Chat request failed: " + res.status);
      }

      if (!data) {
        throw new Error("Empty chat response");
      }

      const sid = extractSessionId(data);
      if (sid && sid !== "[object HTMLInputElement]") {
        setSessionId(sid);
      }

      const imageUrl = extractImageUrl(data);

      if (imageUrl) {
        setAssistantImage(
          assistantNode,
          imageUrl,
          extractAssistantText(data) || "Generated image"
        );
      } else {
        setAssistantText(
          assistantNode,
          extractAssistantText(data) || "No response text returned."
        );
      }

      if (typeof window.NovaLoadSessionsV2 === "function") {
        window.NovaLoadSessionsV2();
      }

      if (typeof window.NovaLoadMemoryV2 === "function") {
        window.NovaLoadMemoryV2();
      }

      if (typeof window.NovaLoadArtifactsV2 === "function") {
        window.NovaLoadArtifactsV2();
      }

      setStatus("done");

    } catch (error) {
      console.warn("[NOVA Chat V2] failed", error);
      setAssistantText(assistantNode, "Error generating response.");
      setStatus("error");

    } finally {
      sending = false;

      if (sendBtn) sendBtn.disabled = false;

      setStatus("ready");
    }
  }

  function bindChat() {
    const input = $("input") || $("desktopChatInput");
    const sendBtn = $("sendBtn") || $("desktopSendButton");

    if (sendBtn) {
      sendBtn.onclick = function () {
        sendText();
      };
    }

    if (input) {
      input.addEventListener("keydown", function (event) {
        if (event.key !== "Enter") return;
        if (event.shiftKey) return;

        event.preventDefault();
        sendText();
      });
    }
  }

  function boot() {
    bindChat();
    setStatus("ready");
    console.log("[NOVA Chat V2] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.NovaSendTextV2 = sendText;
  window.sendText = sendText;
})();

