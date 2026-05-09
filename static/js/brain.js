(() => {
"use strict";

if (window.__novaBrainLoaded) {
  return;
}
window.__novaBrainLoaded = true;

const STATES = new Set(["idle", "thinking", "streaming", "success", "error", "reasoning"]);

function injectBrainStyles() {
  if (document.getElementById("nova-brain-styles")) return;

  const style = document.createElement("style");
  style.id = "nova-brain-styles";
  style.textContent = `
    .topbar-brain{
      position:relative;
      width:42px;
      height:42px;
      flex:0 0 42px;
      border-radius:14px;
      display:grid;
      place-items:center;
      border:1px solid var(--line, rgba(255,255,255,0.08));
      background:
        radial-gradient(circle at 30% 30%, rgba(121,168,255,0.22), transparent 45%),
        linear-gradient(135deg, rgba(121,168,255,0.12), rgba(155,125,255,0.10));
      box-shadow:
        0 10px 24px rgba(121,168,255,0.18),
        inset 0 1px 0 rgba(255,255,255,0.10);
      overflow:hidden;
      transition:
        transform 180ms ease,
        box-shadow 180ms ease,
        border-color 180ms ease,
        filter 180ms ease,
        background 180ms ease;
      color: var(--text, #e6ebff);
    }

    .topbar-brain::before{
      content:"";
      position:absolute;
      inset:-20%;
      background:
        conic-gradient(
          from 0deg,
          rgba(121,168,255,0) 0deg,
          rgba(121,168,255,0.35) 90deg,
          rgba(155,125,255,0.18) 180deg,
          rgba(121,168,255,0) 270deg,
          rgba(121,168,255,0.35) 360deg
        );
      filter:blur(10px);
      opacity:.9;
      animation:novaBrainAuraSpin 7s linear infinite;
      transition:opacity 180ms ease;
    }

    .topbar-brain::after{
      content:"";
      position:absolute;
      inset:0;
      border-radius:inherit;
      pointer-events:none;
      background:linear-gradient(180deg, rgba(255,255,255,0.14), transparent 40%);
    }

    .topbar-brain-svg{
      position:relative;
      z-index:1;
      width:22px;
      height:22px;
      color:currentColor;
      animation:novaBrainFloat 2.6s ease-in-out infinite;
      transition:filter 180ms ease, transform 180ms ease;
    }

    body.nova-brain-thinking .topbar-brain{
      border-color:rgba(121,168,255,0.34);
      box-shadow:
        0 14px 30px rgba(121,168,255,0.26),
        0 0 28px rgba(121,168,255,0.18),
        inset 0 1px 0 rgba(255,255,255,0.14);
      filter:saturate(1.08);
      animation:novaBrainPulse 1.15s ease-in-out infinite;
    }

    body.nova-brain-thinking .topbar-brain::before{
      animation-duration:3.2s;
      opacity:1;
    }

    body.nova-brain-thinking .topbar-brain-svg{
      animation:
        novaBrainFloat 1.2s ease-in-out infinite,
        novaBrainGlowBlue 1.5s ease-in-out infinite;
    }

    body.nova-brain-streaming .topbar-brain{
      border-color:rgba(121,168,255,0.44);
      box-shadow:
        0 16px 34px rgba(121,168,255,0.30),
        0 0 34px rgba(121,168,255,0.22),
        inset 0 1px 0 rgba(255,255,255,0.16);
      filter:saturate(1.12);
      animation:novaBrainPulse 0.9s ease-in-out infinite;
    }

    body.nova-brain-streaming .topbar-brain::before{
      animation-duration:2.2s;
      opacity:1;
    }

    body.nova-brain-streaming .topbar-brain-svg{
      animation:
        novaBrainFloat 0.95s ease-in-out infinite,
        novaBrainGlowBlue 1.1s ease-in-out infinite;
    }

    body.nova-brain-success .topbar-brain{
      border-color:rgba(111,227,160,0.42);
      background:
        radial-gradient(circle at 30% 30%, rgba(111,227,160,0.20), transparent 45%),
        linear-gradient(135deg, rgba(111,227,160,0.10), rgba(121,168,255,0.08));
      box-shadow:
        0 14px 30px rgba(111,227,160,0.22),
        0 0 28px rgba(111,227,160,0.16),
        inset 0 1px 0 rgba(255,255,255,0.14);
    }

    body.nova-brain-success .topbar-brain::before{
      background:
        conic-gradient(
          from 0deg,
          rgba(111,227,160,0) 0deg,
          rgba(111,227,160,0.34) 90deg,
          rgba(121,168,255,0.14) 180deg,
          rgba(111,227,160,0) 270deg,
          rgba(111,227,160,0.34) 360deg
        );
      opacity:1;
      animation-duration:2.6s;
    }

    body.nova-brain-success .topbar-brain-svg{
      animation:
        novaBrainFloat 1.3s ease-in-out 2,
        novaBrainGlowGreen 1.2s ease-in-out 2;
    }

    body.nova-brain-error .topbar-brain{
      border-color:rgba(255,115,115,0.42);
      background:
        radial-gradient(circle at 30% 30%, rgba(255,115,115,0.20), transparent 45%),
        linear-gradient(135deg, rgba(255,115,115,0.12), rgba(155,125,255,0.08));
      box-shadow:
        0 14px 30px rgba(255,115,115,0.22),
        0 0 28px rgba(255,115,115,0.16),
        inset 0 1px 0 rgba(255,255,255,0.14);
      animation:novaBrainErrorPulse 0.45s ease-in-out 3;
    }

    body.nova-brain-error .topbar-brain::before{
      background:
        conic-gradient(
          from 0deg,
          rgba(255,115,115,0) 0deg,
          rgba(255,115,115,0.34) 90deg,
          rgba(155,125,255,0.14) 180deg,
          rgba(255,115,115,0) 270deg,
          rgba(255,115,115,0.34) 360deg
        );
      opacity:1;
      animation-duration:1.9s;
    }

    body.nova-brain-error .topbar-brain-svg{
      animation:
        novaBrainFloat 0.8s ease-in-out 3,
        novaBrainGlowRed 0.8s ease-in-out 3;
    }

    body.nova-brain-reasoning .topbar-brain{
      border-color:rgba(155,125,255,0.40);
      background:
        radial-gradient(circle at 30% 30%, rgba(155,125,255,0.18), transparent 45%),
        linear-gradient(135deg, rgba(155,125,255,0.12), rgba(121,168,255,0.08));
      box-shadow:
        0 14px 30px rgba(155,125,255,0.22),
        0 0 30px rgba(155,125,255,0.16),
        inset 0 1px 0 rgba(255,255,255,0.14);
      animation:novaBrainPulse 1.3s ease-in-out infinite;
    }

    body.nova-brain-reasoning .topbar-brain::before{
      opacity:1;
      animation-duration:2.4s;
    }

    body.nova-brain-reasoning .topbar-brain-svg{
      animation:
        novaBrainFloat 1.0s ease-in-out infinite,
        novaBrainGlowPurple 1.4s ease-in-out infinite;
    }

    @keyframes novaBrainFloat{
      0%, 100%{ transform:translateY(0) scale(1); }
      50%{ transform:translateY(-2px) scale(1.04); }
    }

    @keyframes novaBrainGlowBlue{
      0%, 100%{ filter:drop-shadow(0 0 0 rgba(121,168,255,0)); }
      50%{ filter:drop-shadow(0 0 8px rgba(121,168,255,0.42)); }
    }

    @keyframes novaBrainGlowGreen{
      0%, 100%{ filter:drop-shadow(0 0 0 rgba(111,227,160,0)); }
      50%{ filter:drop-shadow(0 0 8px rgba(111,227,160,0.42)); }
    }

    @keyframes novaBrainGlowRed{
      0%, 100%{ filter:drop-shadow(0 0 0 rgba(255,115,115,0)); }
      50%{ filter:drop-shadow(0 0 8px rgba(255,115,115,0.42)); }
    }

    @keyframes novaBrainGlowPurple{
      0%, 100%{ filter:drop-shadow(0 0 0 rgba(155,125,255,0)); }
      50%{ filter:drop-shadow(0 0 8px rgba(155,125,255,0.42)); }
    }

    @keyframes novaBrainAuraSpin{
      from{ transform:rotate(0deg); }
      to{ transform:rotate(360deg); }
    }

    @keyframes novaBrainPulse{
      0%, 100%{ transform:scale(1); }
      50%{ transform:scale(1.035); }
    }

    @keyframes novaBrainErrorPulse{
      0%, 100%{ transform:translateX(0); }
      25%{ transform:translateX(-1px); }
      75%{ transform:translateX(1px); }
    }
  `;
  document.head.appendChild(style);
}

function ensureBrainMarkup() {
  const left = document.querySelector(".top-bar-left");
  if (!left) return;

  if (document.querySelector(".topbar-brain")) return;

  const titleWrap = left.querySelector(".topbar-title-wrap");
  if (!titleWrap) return;

  const brain = document.createElement("div");
  brain.className = "topbar-brain";
  brain.setAttribute("aria-hidden", "true");
  brain.innerHTML = `
    <svg
      class="topbar-brain-svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M9 4a3 3 0 0 0-3 3v1a2 2 0 0 0 0 4v1a3 3 0 0 0 3 3h1"></path>
      <path d="M15 4a3 3 0 0 1 3 3v1a2 2 0 0 1 0 4v1a3 3 0 0 1-3 3h-1"></path>
      <path d="M12 6v12"></path>
    </svg>
  `;

  left.insertBefore(brain, titleWrap);
}

function clearBodyStateClasses() {
  document.body.classList.remove(
    "nova-brain-idle",
    "nova-brain-thinking",
    "nova-brain-streaming",
    "nova-brain-success",
    "nova-brain-error",
    "nova-brain-reasoning"
  );
}

function setState(state) {
  const next = STATES.has(state) ? state : "idle";
  clearBodyStateClasses();
  document.body.classList.add(`nova-brain-${next}`);
}

function initBridge() {
  window.NovaBrain = {
    setState,
    idle() { setState("idle"); },
    thinking() { setState("thinking"); },
    streaming() { setState("streaming"); },
    success() { setState("success"); window.setTimeout(() => setState("idle"), 1200); },
    error() { setState("error"); window.setTimeout(() => setState("idle"), 1600); },
    reasoning() { setState("reasoning"); }
  };
}

function initBrain() {
  injectBrainStyles();
  ensureBrainMarkup();
  initBridge();
  setState("idle");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initBrain, { once: true });
} else {
  initBrain();
}
})();