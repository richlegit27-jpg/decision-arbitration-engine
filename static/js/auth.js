/* notepad C:\Users\Owner\nova\static\js\auth.js */

(() => {
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const el = {
    loginForm: document.getElementById("loginForm"),
    registerForm: document.getElementById("registerForm"),
    logoutBtn: document.getElementById("logoutBtn"),
    authStatusText: document.getElementById("authStatusText"),
    authUsernameText: document.getElementById("authUsernameText"),
    loginUsername: document.getElementById("loginUsername"),
    loginPassword: document.getElementById("loginPassword"),
    registerUsername: document.getElementById("registerUsername"),
    registerPassword: document.getElementById("registerPassword"),
    changePasswordForm: document.getElementById("changePasswordForm"),
    currentPassword: document.getElementById("currentPassword"),
    newPassword: document.getElementById("newPassword"),
    authMessage: document.getElementById("authMessage"),
  };

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function setMessage(text, type = "info") {
    if (!el.authMessage) return;
    el.authMessage.className = `message ${type}`;
    el.authMessage.innerHTML = escapeHtml(text);
  }

  function clearMessage() {
    if (!el.authMessage) return;
    el.authMessage.className = "message";
    el.authMessage.innerHTML = "";
  }

  async function apiFetch(url, options = {}) {
    const isFormData = options.body instanceof FormData;

    const headers = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    };

    const response = await fetch(url, {
      credentials: "include",
      ...options,
      headers,
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";

    try {
      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();
        data = text ? { message: text } : null;
      }
    } catch (_) {
      data = null;
    }

    if (!response.ok) {
      const message =
        (data && (data.error || data.detail || data.message)) ||
        `Request failed: ${response.status}`;
      const error = new Error(message);
      error.status = response.status;
      error.payload = data;
      throw error;
    }

    return data;
  }

  function renderAuthState(data) {
    const authenticated = Boolean(data && data.authenticated);
    const username = authenticated ? String(data.username || "") : "";

    document.body.dataset.authenticated = authenticated ? "true" : "false";

    if (el.authStatusText) {
      el.authStatusText.textContent = authenticated ? "Logged in" : "Logged out";
    }

    if (el.authUsernameText) {
      el.authUsernameText.textContent = authenticated ? username : "Guest";
    }

    if (el.logoutBtn) {
      el.logoutBtn.disabled = !authenticated;
    }

    const userChip = document.getElementById("userMenuToggleBtn");
    if (userChip) {
      const nameNode = userChip.querySelector(".user-name");
      if (nameNode) {
        nameNode.textContent = authenticated ? username : "Guest";
      }
    }

    const menuUsername = document.querySelector(".user-menu-username");
    if (menuUsername) {
      menuUsername.textContent = authenticated ? username : "Guest";
    }
  }

  async function refreshAuthStatus() {
    try {
      const data = await apiFetch("/api/auth/status", {
        method: "GET",
      });

      const username =
        data && typeof data.username === "string"
          ? data.username
          : data && data.user && typeof data.user.username === "string"
            ? data.user.username
            : "";

      renderAuthState({
        authenticated: Boolean(data && data.authenticated),
        username,
      });

      return data;
    } catch (_) {
      renderAuthState({
        authenticated: false,
        username: "",
      });
      return null;
    }
  }

  async function login(username, password) {
    clearMessage();

    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
      }),
    });

    await refreshAuthStatus();
    setMessage("Login successful.", "success");
    return data;
  }

  async function register(username, password) {
    clearMessage();

    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
      }),
    });

    await refreshAuthStatus();
    setMessage("Registration successful.", "success");
    return data;
  }

  async function logout() {
    clearMessage();

    await apiFetch("/api/auth/logout", {
      method: "POST",
    });

    renderAuthState({
      authenticated: false,
      username: "",
    });

    setMessage("Logged out.", "success");
  }

  async function changePassword(currentPassword, newPassword) {
    clearMessage();

    const data = await apiFetch("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    setMessage(data.message || "Password changed successfully.", "success");
    return data;
  }

  if (el.loginForm) {
    el.loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const username = el.loginUsername ? el.loginUsername.value.trim() : "";
      const password = el.loginPassword ? el.loginPassword.value : "";

      if (!username || !password) {
        setMessage("Username and password are required.", "error");
        return;
      }

      try {
        const data = await login(username, password);
        if (el.loginPassword) el.loginPassword.value = "";
        window.location.href = data.redirect_to || "/app";
      } catch (error) {
        setMessage(error.message, "error");
      }
    });
  }

  if (el.registerForm) {
    el.registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const username = el.registerUsername ? el.registerUsername.value.trim() : "";
      const password = el.registerPassword ? el.registerPassword.value : "";

      if (!username || !password) {
        setMessage("Username and password are required.", "error");
        return;
      }

      try {
        const data = await register(username, password);
        if (el.registerPassword) el.registerPassword.value = "";
        window.location.href = data.redirect_to || "/app";
      } catch (error) {
        setMessage(error.message, "error");
      }
    });
  }

  if (el.logoutBtn) {
    el.logoutBtn.addEventListener("click", async () => {
      try {
        await logout();
        window.location.href = "/login";
      } catch (error) {
        setMessage(error.message, "error");
      }
    });
  }

  if (el.changePasswordForm) {
    el.changePasswordForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const currentPassword = el.currentPassword ? el.currentPassword.value : "";
      const newPassword = el.newPassword ? el.newPassword.value : "";

      if (!currentPassword || !newPassword) {
        setMessage("Current password and new password are required.", "error");
        return;
      }

      try {
        await changePassword(currentPassword, newPassword);

        if (el.currentPassword) el.currentPassword.value = "";
        if (el.newPassword) el.newPassword.value = "";
      } catch (error) {
        setMessage(error.message, "error");
      }
    });
  }

  refreshAuthStatus();

  window.NovaAuth = {
    refreshAuthStatus,
    login,
    register,
    logout,
    changePassword,
  };
});
})();