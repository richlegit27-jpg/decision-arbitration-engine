document.addEventListener("DOMContentLoaded", () => {
  const sidebarToggle = document.getElementById("sidebarToggle");
  const memoryPanelToggle = document.getElementById("memoryPanelToggle");
  const memoryPanel = document.getElementById("memoryPanel");
  const memoryCloseBtn = document.getElementById("memoryCloseBtn");
  const artifactsPanelToggle = document.getElementById("artifactsPanelToggle");
  const artifactsPanel = document.getElementById("novaArtifactsRoot");
  const artifactsCloseBtn = document.getElementById("artifactsCloseBtn");
  const themeToggle = document.getElementById("themeToggle");

  sidebarToggle?.addEventListener("click", () => document.body.classList.toggle("sidebar-collapsed"));
  memoryPanelToggle?.addEventListener("click", () => memoryPanel.classList.toggle("is-active"));
  memoryCloseBtn?.addEventListener("click", () => memoryPanel.classList.remove("is-active"));
  artifactsPanelToggle?.addEventListener("click", () => artifactsPanel.classList.toggle("is-active"));
  artifactsCloseBtn?.addEventListener("click", () => artifactsPanel.classList.remove("is-active"));
  themeToggle?.addEventListener("click", () => {
    const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
  });
});