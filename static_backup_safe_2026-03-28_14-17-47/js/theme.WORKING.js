(() => {
"use strict";

if (window.__novaThemeLoaded) {
  console.warn("Nova theme already loaded.");
  return;
}
window.__novaThemeLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

const STORAGE_KEY = "nova_theme";
const DEFAULT_THEME = "dark";
const THEMES = new Set(["dark", "light"]);

function byId(id) {
  return document.getElementById(id);
}

function normalizeTheme(value) {
  const theme = String(value || "").trim().toLowerCase();
  return THEMES.has(theme) ? theme : "";
}

function getSavedTheme() {
  try {
    return normalizeTheme(localStorage.getItem(STORAGE_KEY));
  } catch (error) {
    console.warn("[Nova theme] Could not read theme from localStorage.", error);
    return "";
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch (error) {
    console.warn("[Nova theme] Could not save theme to localStorage.", error);
  }
}

function ensureState() {
  app.state = app.state || {};
  app.state.theme =
    app.state.theme && typeof app.state.theme === "object"
      ? app.state.theme
      : {};
  return app.state;
}

function getStateThemeMode() {
  const raw =
    app?.state?.theme?.mode ??
    app?.state?.theme;

  return normalizeTheme(raw);
}

function getDomTheme() {
  const root = document.documentElement;
  const body = document.body;

  const candidates = [
    root?.getAttribute("data-theme"),
    body?.getAttribute("data-theme"),
    root?.dataset?.theme,
    body?.dataset?.theme,
    window.__novaInlineTheme
  ];

  for (const value of candidates) {
    const theme = normalizeTheme(value);
    if (theme) {
      return theme;
    }
  }

  if (root?.classList?.contains("theme-light") || body?.classList?.contains("theme-light")) {
    return "light";
  }

  if (root?.classList?.contains("theme-dark") || body?.classList?.contains("theme-dark")) {
    return "dark";
  }

  return "";
}

function getThemeToggleButton() {
  return (
    byId("themeToggleBtn")
    || byId("btnThemeToggle")
    || byId("themeBtn")
  );
}

function setThemeLabel(theme) {
  const btn = getThemeToggleButton();
  if (!btn) return;

  const nextMode = theme === "dark" ? "light" : "dark";
  const label = nextMode === "light" ? "Light mode" : "Dark mode";

  btn.textContent = label;
  btn.setAttribute("aria-label", `Switch to ${nextMode} mode`);
  btn.setAttribute("title", `Switch to ${nextMode} mode`);
}

function syncThemeState(theme) {
  const state = ensureState();
  state.theme.mode = theme;
  saveTheme(theme);
  setThemeLabel(theme);
}

function writeThemeToDom(theme, options = {}) {
  const { log = true } = options;
  const finalTheme = normalizeTheme(theme) || DEFAULT_THEME;
  const root = document.documentElement;
  const body = document.body;

  if (!root) return;

  root.setAttribute("data-theme", finalTheme);
  root.dataset.theme = finalTheme;
  root.classList.remove("theme-dark", "theme-light");
  root.classList.add(`theme-${finalTheme}`);

  if (body) {
    body.setAttribute("data-theme", finalTheme);
    body.dataset.theme = finalTheme;
    body.classList.remove("theme-dark", "theme-light");
    body.classList.add(`theme-${finalTheme}`);
  }

  window.__novaInlineTheme = finalTheme;

  if (log) {
    console.log("[Nova theme] applied:", finalTheme);
  }
}

function applyTheme(theme) {
  const finalTheme = normalizeTheme(theme) || DEFAULT_THEME;
  writeThemeToDom(finalTheme, { log: true });
  syncThemeState(finalTheme);
}

function resolveInitialTheme() {
  const domTheme = getDomTheme();
  if (domTheme) return domTheme;

  const stateTheme = getStateThemeMode();
  if (stateTheme) return stateTheme;

  const savedTheme = getSavedTheme();
  if (savedTheme) return savedTheme;

  return DEFAULT_THEME;
}

function toggleTheme() {
  const current = getDomTheme() || resolveInitialTheme();
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next);
}

function bindThemeButton() {
  const btn = getThemeToggleButton();
  if (!btn) {
    return;
  }

  if (btn.dataset.boundTheme === "true") {
    return;
  }

  btn.dataset.boundTheme = "true";
  btn.addEventListener("click", (event) => {
    event.preventDefault();
    toggleTheme();
  });
}

function init() {
  bindThemeButton();

  const domTheme = getDomTheme();
  if (domTheme) {
    syncThemeState(domTheme);
    setThemeLabel(domTheme);
    console.log("[Nova theme] applied:", domTheme);
    return;
  }

  const initialTheme = resolveInitialTheme();
  writeThemeToDom(initialTheme, { log: true });
  syncThemeState(initialTheme);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
  init();
}

app.theme = {
  init,
  applyTheme,
  toggleTheme
};
})();