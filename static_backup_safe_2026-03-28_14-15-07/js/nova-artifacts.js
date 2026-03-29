(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.artifacts = Nova.artifacts || {};

  const state = Nova.state;

  // Ensure artifacts state exists
  state.artifacts = Array.isArray(state.artifacts) ? state.artifacts : [];
  state.artifactDetail = state.artifactDetail || null;
  state.artifactQuery = typeof state.artifactQuery === "string" ? state.artifactQuery : "";
  state.artifactSessionFilter = !!state.artifactSessionFilter;
  state.artifactsLoaded = !!state.artifactsLoaded;

  const API = {
    list: "/api/artifacts",
    get: (id) => `/api/artifacts/${encodeURIComponent(id)}`,
    create: "/api/artifacts/create",
    update: "/api/artifacts/update",
    delete: "/api/artifacts/delete",
    togglePin: "/api/artifacts/toggle-pin",
  };

  // ------------------------------
  // Sidebar toggle wiring
  // ------------------------------
  function installPanelToggles() {
    const sidebarBtn = document.getElementById("sidebarToggle");
    if (!sidebarBtn) return;

    sidebarBtn.addEventListener("click", () => {
      const sidebar = document.getElementById("novaSidebar");
      sidebar.classList.toggle("collapsed");
    });
  }

  // ------------------------------
  // Render artifact list with previews
  // ------------------------------
  async function loadArtifacts() {
    try {
      const res = await fetch(API.list);
      const items = await res.json();
      state.artifacts = items;

      const container = document.getElementById("novaArtifactsList");
      container.innerHTML = "";

      items.forEach((item) => {
        const div = document.createElement("div");
        div.className = "artifact-card";

        // Card click except action buttons
        div.addEventListener("click", (e) => {
          if (!e.target.classList.contains("artifact-action")) {
            console.log("Artifact selected:", item);
          }
        });

        // Preview
        const preview = document.createElement("div");
        preview.className = "artifact-preview";

        if (item.type && item.type.startsWith("image/")) {
          const img = document.createElement("img");
          img.src = item.url;
          img.alt = item.title || "Image";
          img.style.maxHeight = "100px";
          img.style.borderRadius = "0.3rem";
          preview.appendChild(img);
        } else if (item.type && item.type.startsWith("video/")) {
          const video = document.createElement("video");
          video.src = item.url;
          video.controls = true;
          video.style.maxHeight = "100px";
          preview.appendChild(video);
        } else if (item.type === "application/pdf") {
          const pdf = document.createElement("iframe");
          pdf.src = item.url;
          pdf.style.width = "100%";
          pdf.style.height = "120px";
          preview.appendChild(pdf);
        } else {
          preview.textContent = item.title || "File";
        }

        div.appendChild(preview);

        // Delete button
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Delete";
        deleteBtn.className = "artifact-action";
        deleteBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          await fetch(API.delete(item.id), { method: "POST" });
          loadArtifacts();
        });

        div.appendChild(deleteBtn);
        container.appendChild(div);
      });
    } catch (err) {
      console.error("[nova-artifacts] failed to load artifacts", err);
    }
  }

  // ------------------------------
  // Bootstrap function
  // ------------------------------
  function bootstrap() {
    installPanelToggles();
    loadArtifacts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();