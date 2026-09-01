(function () {
  "use strict";

  /*
   * ============================================================
   * NOVA CHAT STREAM
   * ============================================================
   *
   * TRANSPORT ONLY.
   *
   * composer-actions.js is the SINGLE OWNER of:
   *
   *   - Send button
   *   - Enter-to-send
   *   - sendCurrentMessage()
   *   - user messages
   *   - assistant messages
   *   - thinking state
   *   - composer state
   *   - session state
   *   - rendering
   *   - persistence
   *
   * This file MUST NOT:
   *
   *   - bind DOM events
   *   - create sessions
   *   - render messages
   *   - render sessions
   *   - modify message state
   *   - bootstrap the application
   *   - expose another sendCurrentMessage()
   *   - call sendCurrentMessage()
   *
   * It ONLY provides NovaStreamService.send().
   * ============================================================
   */

  console.log(
    "[NOVA CHAT STREAM] transport-only service loading"
  );


  const Nova =
    window.Nova =
      window.Nova || {};


  /*
   * ------------------------------------------------------------
   * Shared stream service
   * ------------------------------------------------------------
   */

  const streamService =
    window.NovaStreamService =
      window.NovaStreamService || {};


  /*
   * ------------------------------------------------------------
   * Safe helpers
   * ------------------------------------------------------------
   */

  function safeString(
    value,
    fallback = ""
  ) {
    return typeof value === "string"
      ? value
      : fallback;
  }


  /*
   * ------------------------------------------------------------
   * Response parser
   * ------------------------------------------------------------
   */

  async function readResponse(
    response
  ) {

    const text =
      await response.text();


    let data = {};


    if(text){

      try{

        data =
          JSON.parse(text);

      }catch(_error){

        data = {
          raw: text
        };

      }

    }


    if(!response.ok){

      const message =
        safeString(
          data?.message
        ) ||

        safeString(
          data?.error
        ) ||

        safeString(
          data?.detail
        ) ||

        safeString(
          text
        ) ||

        `POST failed (${response.status}) /api/chat`;


      throw new Error(message);

    }


    return data;

  }


  /*
   * ------------------------------------------------------------
   * SINGLE TRANSPORT SEND
   * ------------------------------------------------------------
   *
   * composer-actions.js owns the actual send lifecycle.
   *
   * This function ONLY:
   *
   *   1. receives the payload
   *   2. POSTs it to /api/chat
   *   3. returns the server response
   *
   * It does NOT touch UI/message/session state.
   * ------------------------------------------------------------
   */

  streamService.send =
    async function (
      payload = {}
    ){

      const novaState =
        window.NovaChatState?.state ||

        window.Nova?.state ||

        {};


      const message =
        safeString(
          payload.message,
          ""
        ) ||

        safeString(
          payload.content,
          ""
        );


      const sessionId =
        payload.chatId ||

        payload.sessionId ||

        novaState.activeChatId ||

        novaState.activeSessionId ||

        null;


      const model =
        payload.model ||

        novaState.selectedModel ||

        novaState.defaultModel ||

        "gpt-5.4";


      const attachments =
        Array.isArray(
          payload.attachments
        )

          ? payload.attachments

          : [];


      const requestBody = {

        session_id:
          sessionId,

        content:
          message,

        model:
          model,

        attachments:
          attachments

      };


      console.log(
        "[NOVA STREAM SERVICE SEND]",
        {
          session_id:
            requestBody.session_id,

          content_length:
            requestBody.content.length,

          model:
            requestBody.model,

          attachment_count:
            requestBody.attachments.length
        }
      );


      const response =
        await fetch(
          "/api/chat",
          {
            method:
              "POST",

            credentials:
              "same-origin",

            headers: {
              "Content-Type":
                "application/json",

              "Accept":
                "application/json"
            },

            body:
              JSON.stringify(
                requestBody
              )
          }
        );


      return await readResponse(
        response
      );

    };


  /*
   * ------------------------------------------------------------
   * Compatibility namespace
   * ------------------------------------------------------------
   *
   * These are aliases to the SAME transport function.
   *
   * They do not create another sender.
   * ------------------------------------------------------------
   */

  Nova.stream =
    Nova.stream || {};


  Nova.stream.send =
    streamService.send;


  Nova.chatStream =
    Nova.chatStream || {};


  Nova.chatStream.send =
    streamService.send;


  /*
   * ------------------------------------------------------------
   * Final diagnostics
   * ------------------------------------------------------------
   */

  console.log(
    "[NOVA CHAT STREAM] transport ready",
    {
      hasStreamService:
        !!window.NovaStreamService,

      hasSend:
        typeof window.NovaStreamService?.send ===
        "function",

      hasChatStreamSend:
        typeof window.Nova.chatStream?.send ===
        "function",

      hasNovaStreamSend:
        typeof window.Nova.stream?.send ===
        "function",

      hasCompetingSendCurrentMessage:
        typeof window.NovaStreamService?.sendCurrentMessage ===
        "function"
    }
  );

})();