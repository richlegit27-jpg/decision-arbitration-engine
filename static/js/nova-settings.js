(() => {
  "use strict";
  const API = "/api/settings";
  const body = document.body;
  const status = document.getElementById("settingsStatus");
  let preferences = { theme: "dark", enter_to_send: true };

  function applyTheme(theme) {
    const light = theme === "light" || (theme === "system" && matchMedia("(prefers-color-scheme: light)").matches);
    body.classList.toggle("theme-light", light);
    body.classList.toggle("theme-dark", !light);
    body.dataset.novaThemePreference = theme;
    localStorage.setItem("nova_theme_mode", theme);
  }

  function applyEnterPreference() {
    document.documentElement.dataset.novaEnterToSend = preferences.enter_to_send ? "true" : "false";
  }

  async function load() {
    try {
      const response = await fetch(API, { credentials: "same-origin" });
      if (!response.ok) return;
      const data = await response.json();
      if (!data.ok || !data.preferences) return;
      preferences = data.preferences;
      applyTheme(preferences.theme);
      applyEnterPreference();
      const theme = document.getElementById("theme");
      const enter = document.getElementById("enterToSend");
      if (theme) theme.value = preferences.theme;
      if (enter) enter.checked = preferences.enter_to_send;
    } catch (_) {}
  }

  async function save(key, value) {
    if (status) status.textContent = "Saving…";
    try {
      const response = await fetch(API, {
        method: "PATCH", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value })
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || "Save failed");
      preferences = data.preferences;
      applyTheme(preferences.theme);
      applyEnterPreference();
      if (status) status.textContent = "Saved to your account.";
    } catch (error) {
      if (status) status.textContent = error.message || "Could not save this preference.";
      await load();
    }
  }

  document.getElementById("theme")?.addEventListener("change", (event) => save("theme", event.target.value));
  document.getElementById("enterToSend")?.addEventListener("change", (event) => save("enter_to_send", event.target.checked));

  // Capture before the legacy composer listeners so Enter can be reserved for
  // a newline without allowing a second handler to submit the message.
  document.addEventListener("keydown", (event) => {
    if (document.documentElement.dataset.novaEnterToSend !== "false" || event.key !== "Enter" || event.shiftKey) return;
    const target = event.target;
    if (!target || !(target.matches("textarea") || target.id === "composerInput" || target.id === "chatInput")) return;
    event.stopImmediatePropagation();
  }, true);

  matchMedia("(prefers-color-scheme: light)").addEventListener?.("change", () => {
    if (preferences.theme === "system") applyTheme("system");
  });
  load();
})();
