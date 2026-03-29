(() => {
"use strict";

if (window.NovaToast) return;

const stack = document.getElementById("novaToastStack") || createStack();

function createStack() {
  const div = document.createElement("div");
  div.id = "novaToastStack";
  div.style.position = "fixed";
  div.style.bottom = "20px";
  div.style.right = "20px";
  div.style.display = "flex";
  div.style.flexDirection = "column";
  div.style.gap = "10px";
  div.style.zIndex = "9999";
  document.body.appendChild(div);
  return div;
}

function show(message, type="info") {
  const toast = document.createElement("div");

  toast.textContent = message;

  toast.style.padding = "10px 14px";
  toast.style.borderRadius = "10px";
  toast.style.fontSize = "14px";
  toast.style.background = "#1e293b";
  toast.style.color = "white";
  toast.style.boxShadow = "0 4px 16px rgba(0,0,0,.35)";
  toast.style.opacity = "0";
  toast.style.transform = "translateY(8px)";
  toast.style.transition = "all .2s ease";

  if (type === "error") toast.style.background = "#7f1d1d";
  if (type === "success") toast.style.background = "#14532d";

  stack.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(6px)";
    setTimeout(() => toast.remove(), 200);
  }, 3200);
}

window.NovaToast = {
  show,
  success: (m)=>show(m,"success"),
  error: (m)=>show(m,"error")
};

})();