// C:\Users\Owner\nova\static\js\chat\input.js

(() => {
  const app = window.NovaApp;
  const state = app.state;
  const ui = app.ui;

  const input = document.querySelector("#messageInput");
  const btnSend = document.querySelector("#btnSend");

  const inputMod = {
    handlers: {
      onSend: null,
      onStop: null
    },

    bind(handlers) {
      this.handlers = { ...this.handlers, ...(handlers || {}) };

      if (btnSend) {
        btnSend.onclick = () => {
          if (typeof this.handlers.onSend === "function") {
            this.handlers.onSend();
          }
        };
      }

      if (input) {
        input.addEventListener("input", () => ui.autoResizeInput());

        input.addEventListener("keydown", (e) => {
          if (e.key === "Escape") {
            if (state.isStreaming && typeof this.handlers.onStop === "function") {
              e.preventDefault();
              this.handlers.onStop();
            }
            return;
          }

          if (e.key === "ArrowUp" && !e.shiftKey) {
            const atStart = input.selectionStart === 0 && input.selectionEnd === 0;
            const empty = input.value.length === 0;

            if ((empty || atStart) && state.promptHistory.length > 0) {
              e.preventDefault();

              if (state.promptHistoryIndex === -1) {
                state.draftBeforeHistory = input.value;
                state.promptHistoryIndex = state.promptHistory.length - 1;
              } else if (state.promptHistoryIndex > 0) {
                state.promptHistoryIndex -= 1;
              }

              input.value = state.promptHistory[state.promptHistoryIndex] || "";
              ui.autoResizeInput();

              requestAnimationFrame(() => {
                input.selectionStart = input.selectionEnd = input.value.length;
              });
            }
            return;
          }

          if (e.key === "ArrowDown" && !e.shiftKey && state.promptHistory.length > 0 && state.promptHistoryIndex !== -1) {
            e.preventDefault();

            if (state.promptHistoryIndex < state.promptHistory.length - 1) {
              state.promptHistoryIndex += 1;
              input.value = state.promptHistory[state.promptHistoryIndex] || "";
            } else {
              state.promptHistoryIndex = -1;
              input.value = state.draftBeforeHistory || "";
            }

            ui.autoResizeInput();

            requestAnimationFrame(() => {
              input.selectionStart = input.selectionEnd = input.value.length;
            });
            return;
          }

          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (typeof this.handlers.onSend === "function") {
              this.handlers.onSend();
            }
          }
        });
      }
    }
  };

  window.NovaApp = window.NovaApp || {};
  window.NovaApp.input = inputMod;
})();