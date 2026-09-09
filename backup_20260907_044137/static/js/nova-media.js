(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.media = Nova.media || {};

  const state = Nova.state;

  // Ensure media state exists
  state.mediaItems = Array.isArray(state.mediaItems) ? state.mediaItems : [];
  state.mediaLoaded = !!state.mediaLoaded;

  const API = {
    upload: "/api/media/upload",
    list: "/api/media",
    delete: (id) => `/api/media/delete/${encodeURIComponent(id)}`,
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
  // Render media list with previews
  // ------------------------------
  async function loadMedia() {
    try {
      const res = await fetch(API.list);
      const items = await res.json();
      state.mediaItems = items;

      const container = document.getElementById("novaMediaList");
      container.innerHTML = "";

      items.forEach((item) => {
        const div = document.createElement("div");
        div.className = "media-card";

        // Card click except action buttons
        div.addEventListener("click", (e) => {
          if (!e.target.classList.contains("media-action")) {
            console.log("Media selected:", item);
          }
        });

        // Preview
        const preview = document.createElement("div");
        preview.className = "media-preview";

        if (item.type.startsWith("image/")) {
          const img = document.createElement("img");
          img.src = item.url;
          img.alt = item.title || "Image";
          img.style.maxHeight = "100px";
          img.style.borderRadius = "0.3rem";
          preview.appendChild(img);
        } else if (item.type.startsWith("video/")) {
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
        deleteBtn.className = "media-action";
        deleteBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          await fetch(API.delete(item.id), { method: "POST" });
          loadMedia();
        });

        div.appendChild(deleteBtn);
        container.appendChild(div);
      });
    } catch (err) {
      console.error("[nova-media] failed to load media", err);
    }
  }

  // ------------------------------
  // Upload handler
  // ------------------------------
  function initUpload() {
    const input = document.getElementById("novaMediaInput");
    if (!input) return;

    input.addEventListener("change", async () => {
      const file = input.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        await fetch(API.upload, { method: "POST", body: formData });
        loadMedia();
      } catch (err) {
        console.error("[nova-media] upload failed", err);
      } finally {
        input.value = "";
      }
    });
  }

  // ------------------------------
  // Bootstrap function
  // ------------------------------
  function bootstrap() {
    installPanelToggles();
    initUpload();
    loadMedia();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();

