async function sendText(textOverride) {
  console.log("📎 sendText TRIGGERED");

  const liveInput =
    document.getElementById("input") ||
    document.querySelector("textarea");

  const capturedText =
    window.__novaLastInputBeforeSend || "";

  const rawText = String(
    textOverride ||
    capturedText ||
    liveInput?.value ||
    ""
  ).trim();

  window.__novaLastInputBeforeSend = "";

  const attachments =
    pendingDesktopAttachments.slice();

  const text =
    clarifyAttachmentPrompt(
      rawText,
      attachments
    );

  console.log("📎 SEND SNAPSHOT", {
    rawText,
    text,
    attachments
  });

  if (!text && !attachments.length) {
    return;
  }

  input.value = "";
  input.style.height = "auto";

  setStatus("loading...");

  novaChatAbortController =
    new AbortController();

  sendBtn.disabled = false;
  sendBtn.textContent = "Stop";
  sendBtn.dataset.mode = "stop";


  try {

    const response = await fetch(
      "/api/chat",
      {
        signal:
          novaChatAbortController.signal,

        method: "POST",

        headers: {
          "Content-Type": "application/json",
          "x-api-key": API_KEY
        },

        body:
          JSON.stringify(
            buildDesktopChatPayload(
              text,
              attachments
            )
          )
      }
    );


    if (!response.ok) {
      throw new Error(
        await response.text()
      );
    }


    const raw =
      await response.text();

    const data =
      JSON.parse(raw);


    const freshSessionId =
      data.session_id ||
      data.active_session_id ||
      data.session?.id ||
      data.assistant_message?.session_id;


    if (freshSessionId) {

      const newSessionId =
        String(freshSessionId);

      setSessionId(newSessionId);


      if (window.NovaChatState?.state) {
        window.NovaChatState.state.activeChatId =
          newSessionId;
      }


      console.log(
        "[NOVA sessions] adopted backend session",
        newSessionId
      );
    }


    const assistantText =
      data?.assistant_message?.text ||
      data?.response ||
      data?.message ||
      "";


    const appState =
      window.NovaChatState?.state;


    console.log(
      "[NOVA REAL STATE CHECK]",
      {
        appState,
        messages: appState?.messages
      }
    );


    if (
      appState &&
      Array.isArray(appState.messages)
    ) {

      appState.messages.push({

        id:
          "user-" + Date.now(),

        role:
          "user",

        content:
          text,

        text:
          text,

        created_at:
          new Date().toISOString()
      });


      appState.messages.push({

        id:
          "assistant-" + Date.now(),

        role:
          "assistant",

        content:
          assistantText,

        text:
          assistantText,

        created_at:
          new Date().toISOString()
      });


      console.log(
        "[NOVA STATE AFTER PUSH]",
        appState.messages
      );


    } else {

      console.warn(
        "[NOVA] No NovaChatState message state found"
      );

    }


    if (
      window.NovaChatMessages?.renderMessages
    ) {

      window.NovaChatMessages.renderMessages();

    }


    setStatus("done");

    clearDesktopAttachments();


  } catch (e) {

    console.warn(
      "sendText error:",
      e
    );

    setStatus("error");


  } finally {

    novaChatAbortController = null;

    sendBtn.disabled = false;

    sendBtn.textContent =
      "Send";

    sendBtn.dataset.mode =
      "send";

    setStatus("ready");
  }
}


window.sendText = sendText;

console.log(
  "[NOVA] sendText exported",
  typeof window.sendText
);