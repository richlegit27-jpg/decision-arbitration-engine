(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.assets = Nova.assets || {};

  const state = Nova.state;
  state.assetsItems = [];

  const API = {
    artifacts: "/api/artifacts",
    media: "/api/media",
    deleteArtifact: (id) => `/api/artifacts/delete/${encodeURIComponent(id)}`,
    deleteMedia: (id) => `/api/media/delete/${encodeURIComponent(id)}`,
    upload: "/api/media/upload",
    togglePin: (id) => `/api/artifacts/toggle-pin/${encodeURIComponent(id)}`,
  };

  function installPanelToggles() {
    const sidebarBtn = document.getElementById("sidebarToggle");
    if (!sidebarBtn) return;
    sidebarBtn.addEventListener("click", () => {
      const sidebar = document.getElementById("novaSidebar");
      sidebar.classList.toggle("collapsed");
    });
  }

  async function loadAssets() {
    try {
      const [artifactsRes, mediaRes] = await Promise.all([
        fetch(API.artifacts),
        fetch(API.media),
      ]);
      const artifacts = await artifactsRes.json();
      const media = await mediaRes.json();

      state.assetsItems = [...artifacts, ...media];

      // Sort pinned assets first
      state.assetsItems.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

      const container = document.getElementById("novaAssetsList");
      container.innerHTML = "";

      if (!state.assetsItems.length) {
        const placeholder = document.createElement("div");
        placeholder.className = "asset-card placeholder";
        placeholder.textContent = "No assets yet. Drop files here!";
        container.appendChild(placeholder);
        return;
      }

      state.assetsItems.forEach((item) => {
        const div = document.createElement("div");
        div.className = "asset-card";
        div.setAttribute("draggable", "true");

        div.addEventListener("click", (e) => {
          if (!e.target.classList.contains("asset-action")) {
            openLightbox(item);
          }
        });

        const preview = document.createElement("div");
        preview.className = "asset-preview";

        // Image / Video / PDF thumbnails
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
          const pdfThumb = document.createElement("iframe");
          pdfThumb.src = item.url + "#page=1";
          pdfThumb.style.width = "100%";
          pdfThumb.style.height = "120px";
          preview.appendChild(pdfThumb);
        } else {
          preview.textContent = item.title || "File";
        }

        div.appendChild(preview);

        // Pin button
        const pinBtn = document.createElement("button");
        pinBtn.textContent = item.pinned ? "ðŸ“Œ" : "ðŸ“";
        pinBtn.className = "asset-action";
        pinBtn.title = "Toggle Pin";
        pinBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          await fetch(API.togglePin(item.id), { method: "POST" });
          loadAssets();
        });
        div.appendChild(pinBtn);

        // Delete button
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Delete";
        deleteBtn.className = "asset-action";
        deleteBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (artifacts.includes(item)) {
            await fetch(API.deleteArtifact(item.id), { method: "POST" });
          } else {
            await fetch(API.deleteMedia(item.id), { method: "POST" });
          }
          loadAssets();
        });
        div.appendChild(deleteBtn);

        container.appendChild(div);
      });
    } catch (err) {
      console.error("[nova-assets] failed to load assets", err);
    }
  }

  function initUpload() {
    const input = document.getElementById("novaMediaInput");
    const container = document.getElementById("novaAssetsList");
    if (!input || !container) return;

    const showToast = (msg) => {
      const toast = document.createElement("div");
      toast.className = "nova-toast";
      toast.textContent = msg;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 2500);
    };

    const uploadFile = async (file) => {
      const formData = new FormData();
      formData.append("file", file);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", API.upload, true);

      // Progress bar
      const progress = document.createElement("progress");
      progress.max = 100;
      progress.value = 0;
      container.appendChild(progress);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          progress.value = (e.loaded / e.total) * 100;
        }
      };

      xhr.onload = async () => {
        progress.remove();
        if (xhr.status === 200) {
          showToast(`Uploaded: ${file.name}`);
          await loadAssets();
        } else {
          showToast(`Upload failed: ${file.name}`);
        }
      };

      xhr.onerror = () => {
        progress.remove();
        showToast(`Upload error: ${file.name}`);
      };

      xhr.send(formData);
    };

    input.addEventListener("change", async () => {
      const files = Array.from(input.files);
      if (!files.length) return;
      await Promise.all(files.map(file => uploadFile(file)));
      input.value = "";
    });

    container.addEventListener("dragover", (e) => {
      e.preventDefault();
      container.style.background = "rgba(110,168,255,0.1)";
    });

    container.addEventListener("dragleave", (e) => {
      e.preventDefault();
      container.style.background = "transparent";
    });

    container.addEventListener("drop", async (e) => {
      e.preventDefault();
      container.style.background = "transparent";
      const files = Array.from(e.dataTransfer.files);
      if (!files.length) return;
      await Promise.all(files.map(file => uploadFile(file)));
    });
  }

  // ------------------------------
  // Lightbox with PDF full preview
  // ------------------------------
  function openLightbox(item) {
    const lightbox = document.getElementById("novaLightbox");
    const preview = document.getElementById("novaLightboxPreview");
    preview.innerHTML = "";

    if (item.type && item.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = item.url;
      preview.appendChild(img);
    } else if (item.type && item.type.startsWith("video/")) {
      const video = document.createElement("video");
      video.src = item.url;
      video.controls = true;
      video.style.maxHeight = "90vh";
      preview.appendChild(video);
    } else if (item.type === "application/pdf") {
      const pdf = document.createElement("iframe");
      pdf.src = item.url + "#page=1";
      pdf.style.width = "90vw";
      pdf.style.height = "90vh";
      preview.appendChild(pdf);
    } else {
      preview.textContent = item.title || "File";
    }

    lightbox.style.display = "flex";
  }

  document.getElementById("novaLightboxClose").addEventListener("click", () => {
    document.getElementById("novaLightbox").style.display = "none";
  });

  document.getElementById("novaLightbox").addEventListener("click", (e) => {
    if (e.target.id === "novaLightbox") {
      document.getElementById("novaLightbox").style.display = "none";
    }
  });

  function bootstrap() {
    installPanelToggles();
    initUpload();
    loadAssets();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();

