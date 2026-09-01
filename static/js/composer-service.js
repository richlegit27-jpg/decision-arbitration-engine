(function () {
  "use strict";

  /*
   * NOVA COMPOSER SERVICE
   *
   * IMPORTANT:
   * composer-actions.js is the SINGLE owner of:
   *   - Send button
   *   - Enter-to-send
   *   - stop button
   *   - sendCurrentMessage()
   *
   * This module intentionally does NOT:
   *   - bind Send
   *   - bind Enter
   *   - call sendCurrentMessage()
   *   - initialize a second composer controller
   *
   * It exists only as a compatibility/service layer.
   */

  console.log(
    "[NovaComposerService] compatibility service loaded"
  );

  function createComposerService(options = {}) {
    const state = options.state || {};
    const streamService =
      options.streamService ||
      window.NovaStreamService ||
      null;

    const inputController =
      options.inputController ||
      window.NovaComposerInput ||
      null;

    function getInputValue() {
      try {
        if (
          inputController &&
          typeof inputController.getInputValue === "function"
        ) {
          return String(
            inputController.getInputValue() || ""
          );
        }
      } catch (error) {
        console.warn(
          "[NovaComposerService] getInputValue failed:",
          error
        );
      }

      const input =
        document.getElementById("input") ||
        document.getElementById("composerInput");

      return String(input?.value || "");
    }

    function getTrimmedInputValue() {
      return getInputValue().trim();
    }

    function getPendingFiles() {
      if (
        Array.isArray(state.pendingFiles)
      ) {
        return state.pendingFiles;
      }

      if (
        Array.isArray(state.pendingAttachments)
      ) {
        return state.pendingAttachments;
      }

      return [];
    }

    function updateComposerState() {
      try {
        if (
          typeof window.NovaComposerActions
            ?.updateComposerState === "function"
        ) {
          return window.NovaComposerActions.updateComposerState();
        }
      } catch (error) {
        console.warn(
          "[NovaComposerService] updateComposerState failed:",
          error
        );
      }

      return null;
    }

    function stopGenerating() {
      try {
        if (
          typeof window.NovaComposerActions
            ?.stopGenerating === "function"
        ) {
          return window.NovaComposerActions.stopGenerating();
        }
      } catch (error) {
        console.warn(
          "[NovaComposerService] stopGenerating failed:",
          error
        );
      }

      try {
        if (
          typeof streamService?.stop === "function"
        ) {
          return streamService.stop();
        }

        if (
          typeof streamService?.abortActiveStream ===
            "function"
        ) {
          return streamService.abortActiveStream();
        }
      } catch (error) {
        console.warn(
          "[NovaComposerService] stream stop failed:",
          error
        );
      }

      return null;
    }

    /*
     * Compatibility wrapper.
     *
     * There is intentionally NO local send implementation.
     * Any caller using this legacy API is forwarded to the
     * single authoritative composer-actions implementation.
     */
    async function sendCurrentMessage(payload = {}) {
      if (
        typeof window.NovaComposerActions
          ?.sendCurrentMessage === "function"
      ) {
        return window.NovaComposerActions.sendCurrentMessage(
          payload
        );
      }

      console.error(
        "[NovaComposerService] authoritative send unavailable"
      );

      return null;
    }

    /*
     * Compatibility init.
     *
     * Deliberately does nothing.
     *
     * composer-actions.js owns all event binding.
     */
    function init() {
      console.log(
        "[NovaComposerService] compatibility init - no event bindings"
      );

      return true;
    }

    /*
     * Deliberately empty.
     *
     * Kept for compatibility with any code that expects
     * bindEvents() to exist.
     */
    function bindEvents() {
      return true;
    }

    const service = {
      init,
      bindEvents,
      getInputValue,
      getTrimmedInputValue,
      getPendingFiles,
      updateComposerState,
      stopGenerating,
      sendCurrentMessage,
      send: sendCurrentMessage
    };

    return service;
  }

  const service =
    createComposerService({
      state:
        window.Nova?.state ||
        window.NovaState?.state ||
        {}
    });

  window.NovaComposerService =
    service;

  /*
   * IMPORTANT:
   * Do NOT call init() here.
   *
   * Calling init() in this compatibility module could
   * accidentally reintroduce a second composer lifecycle.
   */

  console.log(
    "[NovaComposerService] compatibility layer ready",
    {
      hasSend:
        typeof service.sendCurrentMessage ===
        "function",

      hasInit:
        typeof service.init ===
        "function",

      eventBinding:
        "NONE - composer-actions.js owns composer events"
    }
  );
})();