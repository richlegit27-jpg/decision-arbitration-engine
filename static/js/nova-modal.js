(() => {
"use strict";

if (window.NovaModal) {
  console.warn("Nova modal already loaded.");
  return;
}

let activeOverlay = null;

function closeActive(result = null) {
  if (!activeOverlay) {
    return;
  }

  const overlay = activeOverlay;
  activeOverlay = null;

  if (overlay.__escHandler) {
    document.removeEventListener("keydown", overlay.__escHandler);
  }

  if (typeof overlay.__resolver === "function") {
    overlay.__resolver(result);
  }

  overlay.remove();
}

function makeButton(label, primary = false, danger = false) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = label;
  btn.style.minHeight = "42px";
  btn.style.padding = "10px 16px";
  btn.style.borderRadius = "12px";
  btn.style.cursor = "pointer";
  btn.style.font = "inherit";
  btn.style.transition = "transform .15s ease, opacity .15s ease, background .15s ease, border-color .15s ease";

  if (primary) {
    btn.style.background = danger
      ? "linear-gradient(135deg,#ef4444,#dc2626)"
      : "linear-gradient(135deg,#76a9ff,#8b5cf6)";
    btn.style.color = "#ffffff";
    btn.style.border = "none";
  } else {
    btn.style.background = "rgba(255,255,255,0.06)";
    btn.style.color = "#eef4ff";
    btn.style.border = "1px solid rgba(255,255,255,0.10)";
  }

  btn.addEventListener("mouseenter", () => {
    btn.style.transform = "translateY(-1px)";
  });

  btn.addEventListener("mouseleave", () => {
    btn.style.transform = "translateY(0)";
  });

  return btn;
}

function buildModalShell() {
  if (activeOverlay) {
    closeActive(null);
  }

  const overlay = document.createElement("div");
  overlay.style.position = "fixed";
  overlay.style.inset = "0";
  overlay.style.display = "flex";
  overlay.style.alignItems = "center";
  overlay.style.justifyContent = "center";
  overlay.style.padding = "20px";
  overlay.style.background = "rgba(2,6,23,0.72)";
  overlay.style.backdropFilter = "blur(8px)";
  overlay.style.zIndex = "10000";

  const box = document.createElement("div");
  box.style.width = "100%";
  box.style.maxWidth = "460px";
  box.style.background = "rgba(17,24,39,0.96)";
  box.style.color = "#eef4ff";
  box.style.border = "1px solid rgba(255,255,255,0.08)";
  box.style.borderRadius = "18px";
  box.style.boxShadow = "0 18px 50px rgba(0,0,0,0.35)";
  box.style.padding = "20px";
  box.style.display = "grid";
  box.style.gap = "16px";

  const title = document.createElement("div");
  title.style.fontSize = "18px";
  title.style.fontWeight = "700";

  const text = document.createElement("div");
  text.style.color = "#9fb0d0";
  text.style.lineHeight = "1.55";

  const input = document.createElement("input");
  input.type = "text";
  input.style.display = "none";
  input.style.width = "100%";
  input.style.minHeight = "44px";
  input.style.padding = "10px 12px";
  input.style.borderRadius = "12px";
  input.style.border = "1px solid rgba(255,255,255,0.10)";
  input.style.background = "rgba(255,255,255,0.06)";
  input.style.color = "#eef4ff";
  input.style.outline = "none";

  const buttons = document.createElement("div");
  buttons.style.display = "flex";
  buttons.style.justifyContent = "flex-end";
  buttons.style.gap = "10px";
  buttons.style.flexWrap = "wrap";

  box.appendChild(title);
  box.appendChild(text);
  box.appendChild(input);
  box.appendChild(buttons);
  overlay.appendChild(box);

  return { overlay, box, title, text, input, buttons };
}

function confirm(options = {}) {
  const config =
    typeof options === "string"
      ? { message: options }
      : (options && typeof options === "object" ? options : {});

  return new Promise((resolve) => {
    const { overlay, title, text, buttons } = buildModalShell();
    activeOverlay = overlay;
    overlay.__resolver = resolve;

    title.textContent = config.title || "Confirm action";
    text.textContent = config.message || "Are you sure?";

    const cancelBtn = makeButton(config.cancelText || "Cancel", false, false);
    const confirmBtn = makeButton(config.confirmText || "Confirm", true, false);

    cancelBtn.addEventListener("click", () => {
      if (typeof config.onCancel === "function") {
        config.onCancel();
      }
      closeActive(false);
    });

    confirmBtn.addEventListener("click", () => {
      if (typeof config.onConfirm === "function") {
        config.onConfirm();
      }
      closeActive(true);
    });

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        if (typeof config.onCancel === "function") {
          config.onCancel();
        }
        closeActive(false);
      }
    });

    const escHandler = (event) => {
      if (event.key === "Escape") {
        if (typeof config.onCancel === "function") {
          config.onCancel();
        }
        closeActive(false);
      }
    };

    overlay.__escHandler = escHandler;
    document.addEventListener("keydown", escHandler);

    buttons.appendChild(cancelBtn);
    buttons.appendChild(confirmBtn);
    document.body.appendChild(overlay);

    confirmBtn.focus();
  });
}

function prompt(options = {}) {
  const config =
    options && typeof options === "object"
      ? options
      : {};

  return new Promise((resolve) => {
    const { overlay, title, text, input, buttons } = buildModalShell();
    activeOverlay = overlay;
    overlay.__resolver = resolve;

    title.textContent = config.title || "Enter a value";
    text.textContent = config.message || "";
    input.style.display = "";
    input.value = config.value || "";

    const cancelBtn = makeButton(config.cancelText || "Cancel", false, false);
    const confirmBtn = makeButton(config.confirmText || "Save", true, false);

    function doCancel() {
      if (typeof config.onCancel === "function") {
        config.onCancel();
      }
      closeActive(null);
    }

    function doConfirm() {
      const value = String(input.value ?? "");
      if (typeof config.onConfirm === "function") {
        config.onConfirm(value);
      }
      closeActive(value);
    }

    cancelBtn.addEventListener("click", doCancel);
    confirmBtn.addEventListener("click", doConfirm);

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        doConfirm();
      } else if (event.key === "Escape") {
        event.preventDefault();
        doCancel();
      }
    });

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        doCancel();
      }
    });

    const escHandler = (event) => {
      if (event.key === "Escape") {
        doCancel();
      }
    };

    overlay.__escHandler = escHandler;
    document.addEventListener("keydown", escHandler);

    buttons.appendChild(cancelBtn);
    buttons.appendChild(confirmBtn);
    document.body.appendChild(overlay);

    input.focus();
    input.select();
  });
}

window.NovaModal = {
  confirm,
  prompt,
  close: closeActive
};
})();