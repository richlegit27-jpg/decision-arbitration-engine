(function () {
  "use strict";

  if (window.NovaComposerArtifacts) return;

  function log() {
    try {
      console.log("[NovaComposerArtifacts]", ...arguments);
    } catch (_) {}
  }

  function bootModule() {
    const core = window.NovaComposerCore;
    if (!core) return false;

    const state = core.state;
    const els = core.els;

    function getArtifacts() {
      return Array.isArray(state.artifacts) ? state.artifacts.slice() : [];
    }

    function getArtifactId(item) {
      return String(item?.id || item?.artifact_id || "");
    }

    function getArtifactKind(item) {
      return String(item?.viewer?.kind || item?.kind || "artifact");
    }

    function getArtifactTitle(item) {
      return String(
        item?.viewer?.title ||
        item?.title ||
        item?.name ||
        "Untitled Artifact"
      );
    }

    function getArtifactPreview(item) {
      return String(
        item?.viewer?.body ||
        item?.preview ||
        item?.summary ||
        item?.content ||
        item?.notes ||
        ""
      ).trim();
    }

    function getArtifactSessionId(item) {
      return String(item?.session_id || item?.sessionId || "");
    }

    function getArtifactUpdatedAt(item) {
      return String(item?.updated_at || item?.created_at || "");
    }

    function getViewer(item) {
      const viewer = item?.viewer && typeof item.viewer === "object" ? item.viewer : {};
      return {
        kind: String(viewer.kind || item?.kind || "artifact"),
        title: String(viewer.title || item?.title || "Untitled Artifact"),
        body: String(
          viewer.body ||
          item?.content ||
          item?.summary ||
          item?.notes ||
          item?.preview ||
          ""
        ),
        source_url: String(viewer.source_url || item?.source_url || item?.url || ""),
        image_url: String(viewer.image_url || item?.image_url || ""),
        video_url: String(viewer.video_url || item?.video_url || ""),
        audio_url: String(viewer.audio_url || item?.audio_url || ""),
        analysis_text: String(viewer.analysis_text || item?.analysis_text || ""),
        bullets: Array.isArray(viewer.bullets) ? viewer.bullets.slice() : [],
      };
    }

    function ensureViewerShell() {
      if (!els.artifactList) return null;

      let shell = els.artifactList.querySelector(".nova-artifact-viewer-shell");
      if (shell) return shell;

      shell = document.createElement("div");
      shell.className = "nova-artifact-viewer-shell";

      const listWrap = document.createElement("div");
      listWrap.className = "nova-artifact-list-wrap";
      listWrap.setAttribute("data-artifact-list-wrap", "");

      const viewerWrap = document.createElement("div");
      viewerWrap.className = "nova-artifact-viewer-wrap";
      viewerWrap.setAttribute("data-artifact-viewer-wrap", "");

      shell.appendChild(listWrap);
      shell.appendChild(viewerWrap);

      els.artifactList.innerHTML = "";
      els.artifactList.appendChild(shell);

      return shell;
    }

    function getListWrap() {
      const shell = ensureViewerShell();
      return shell ? shell.querySelector("[data-artifact-list-wrap]") : null;
    }

    function getViewerWrap() {
      const shell = ensureViewerShell();
      return shell ? shell.querySelector("[data-artifact-viewer-wrap]") : null;
    }

    function emitArtifactOpened(artifact) {
      try {
        document.dispatchEvent(
          new CustomEvent("nova:artifact-opened", {
            detail: {
              artifactId: getArtifactId(artifact),
              sessionId: getArtifactSessionId(artifact),
              artifact,
            },
          })
        );
      } catch (_) {}
    }

    function emitArtifactOpenSession(sessionId) {
      try {
        document.dispatchEvent(
          new CustomEvent("nova:artifact-open-session", {
            detail: {
              sessionId: String(sessionId || ""),
            },
          })
        );
      } catch (_) {}
    }

    function buildEmptyState() {
      const wrap = document.createElement("div");
      wrap.className = "nova-list-empty";
      wrap.textContent = "No artifacts yet.";
      return wrap;
    }

    function buildArtifactCard(item) {
      const artifactId = getArtifactId(item);
      const active = artifactId && artifactId === String(state.activeArtifactId || "");

      const card = document.createElement("button");
      card.type = "button";
      card.className = "nova-artifact-card";
      if (active) card.classList.add("is-active");
      card.setAttribute("data-artifact-id", artifactId);

      const top = document.createElement("div");
      top.className = "nova-artifact-card-top";

      const title = document.createElement("div");
      title.className = "nova-artifact-card-title";
      title.textContent = getArtifactTitle(item);

      const badge = document.createElement("span");
      badge.className = "nova-artifact-kind-badge";
      badge.textContent = getArtifactKind(item);

      top.appendChild(title);
      top.appendChild(badge);

      const preview = document.createElement("div");
      preview.className = "nova-artifact-card-preview";
      preview.textContent = getArtifactPreview(item) || "Open to inspect artifact details.";

      const bottom = document.createElement("div");
      bottom.className = "nova-artifact-card-bottom";

      const meta = document.createElement("div");
      meta.className = "nova-artifact-card-meta";
      meta.textContent = getArtifactUpdatedAt(item) || "Saved";

      const openSessionBtn = document.createElement("button");
      openSessionBtn.type = "button";
      openSessionBtn.className = "nova-artifact-open-session-btn";
      openSessionBtn.textContent = "Open Session";
      openSessionBtn.onclick = function (event) {
        event.preventDefault();
        event.stopPropagation();
        const sessionId = getArtifactSessionId(item);
        if (sessionId) {
          emitArtifactOpenSession(sessionId);
        }
      };

      bottom.appendChild(meta);
      bottom.appendChild(openSessionBtn);

      card.appendChild(top);
      card.appendChild(preview);
      card.appendChild(bottom);

      card.onclick = function () {
        openArtifact(artifactId);
      };

      return card;
    }

    function renderArtifactList() {
      const listWrap = getListWrap();
      if (!listWrap) return;

      listWrap.innerHTML = "";

      const items = getArtifacts();
      if (!items.length) {
        listWrap.appendChild(buildEmptyState());
        return;
      }

      const frag = document.createDocumentFragment();
      items.forEach((item) => {
        frag.appendChild(buildArtifactCard(item));
      });

      listWrap.appendChild(frag);
    }

    function buildViewerHeader(item, viewer) {
      const header = document.createElement("div");
      header.className = "nova-artifact-viewer-header";

      const left = document.createElement("div");
      left.className = "nova-artifact-viewer-header-left";

      const title = document.createElement("div");
      title.className = "nova-artifact-viewer-title";
      title.textContent = viewer.title || getArtifactTitle(item);

      const subtitle = document.createElement("div");
      subtitle.className = "nova-artifact-viewer-subtitle";
      subtitle.textContent = `${viewer.kind || getArtifactKind(item)}${getArtifactUpdatedAt(item) ? " · " + getArtifactUpdatedAt(item) : ""}`;

      left.appendChild(title);
      left.appendChild(subtitle);

      const right = document.createElement("div");
      right.className = "nova-artifact-viewer-header-right";

      const openSessionBtn = document.createElement("button");
      openSessionBtn.type = "button";
      openSessionBtn.className = "nova-secondary-btn";
      openSessionBtn.textContent = "Open Session";
      openSessionBtn.onclick = function () {
        const sessionId = getArtifactSessionId(item);
        if (sessionId) {
          emitArtifactOpenSession(sessionId);
        }
      };

      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "nova-secondary-btn";
      closeBtn.textContent = "Close";
      closeBtn.onclick = function () {
        closeArtifactViewer();
      };

      right.appendChild(openSessionBtn);
      right.appendChild(closeBtn);

      header.appendChild(left);
      header.appendChild(right);

      return header;
    }

    function buildViewerMedia(viewer) {
      const frag = document.createDocumentFragment();

      if (viewer.image_url) {
        const imageWrap = document.createElement("div");
        imageWrap.className = "nova-artifact-media-block";

        const img = document.createElement("img");
        img.className = "nova-artifact-image";
        img.src = viewer.image_url;
        img.alt = viewer.title || "Artifact image";

        imageWrap.appendChild(img);
        frag.appendChild(imageWrap);
      }

      if (viewer.video_url) {
        const videoWrap = document.createElement("div");
        videoWrap.className = "nova-artifact-media-block";

        const video = document.createElement("video");
        video.className = "nova-artifact-video";
        video.src = viewer.video_url;
        video.controls = true;
        if (viewer.image_url) {
          video.poster = viewer.image_url;
        }

        videoWrap.appendChild(video);
        frag.appendChild(videoWrap);
      }

      if (viewer.audio_url) {
        const audioWrap = document.createElement("div");
        audioWrap.className = "nova-artifact-media-block";

        const audio = document.createElement("audio");
        audio.className = "nova-artifact-audio";
        audio.src = viewer.audio_url;
        audio.controls = true;

        audioWrap.appendChild(audio);
        frag.appendChild(audioWrap);
      }

      return frag;
    }

    function buildViewerBody(viewer) {
      const wrap = document.createElement("div");
      wrap.className = "nova-artifact-viewer-body";

      if (viewer.body) {
        const text = document.createElement("pre");
        text.className = "nova-artifact-viewer-text";
        text.textContent = viewer.body;
        wrap.appendChild(text);
      }

      if (viewer.analysis_text) {
        const analysis = document.createElement("pre");
        analysis.className = "nova-artifact-viewer-text is-analysis";
        analysis.textContent = viewer.analysis_text;
        wrap.appendChild(analysis);
      }

      if (Array.isArray(viewer.bullets) && viewer.bullets.length) {
        const list = document.createElement("ul");
        list.className = "nova-artifact-bullets";

        viewer.bullets.forEach((bullet) => {
          const li = document.createElement("li");
          li.textContent = String(bullet || "");
          list.appendChild(li);
        });

        wrap.appendChild(list);
      }

      if (viewer.source_url) {
        const sourceRow = document.createElement("div");
        sourceRow.className = "nova-artifact-source-row";

        const link = document.createElement("a");
        link.className = "nova-artifact-source-link";
        link.href = viewer.source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Open Source";

        sourceRow.appendChild(link);
        wrap.appendChild(sourceRow);
      }

      return wrap;
    }

    function buildViewer(item) {
      const viewer = getViewer(item);

      const panel = document.createElement("div");
      panel.className = "nova-artifact-viewer";

      panel.appendChild(buildViewerHeader(item, viewer));
      panel.appendChild(buildViewerMedia(viewer));
      panel.appendChild(buildViewerBody(viewer));

      return panel;
    }

    function renderArtifactViewer() {
      const viewerWrap = getViewerWrap();
      if (!viewerWrap) return;

      viewerWrap.innerHTML = "";

      const artifactId = String(state.activeArtifactId || "");
      if (!artifactId) {
        const empty = document.createElement("div");
        empty.className = "nova-artifact-viewer-empty";

        const title = document.createElement("div");
        title.className = "nova-artifact-viewer-empty-title";
        title.textContent = "Artifact Viewer";

        const body = document.createElement("div");
        body.className = "nova-artifact-viewer-empty-body";
        body.textContent = "Pick an artifact to inspect its full details here.";

        empty.appendChild(title);
        empty.appendChild(body);
        viewerWrap.appendChild(empty);
        return;
      }

      const item = getArtifacts().find((entry) => getArtifactId(entry) === artifactId);
      if (!item) {
        state.activeArtifactId = "";
        renderArtifactList();
        renderArtifactViewer();
        return;
      }

      viewerWrap.appendChild(buildViewer(item));
    }

    function openArtifact(artifactId) {
      const id = String(artifactId || "").trim();
      if (!id) return;

      state.activeArtifactId = id;
      renderArtifactList();
      renderArtifactViewer();

      const item = getArtifacts().find((entry) => getArtifactId(entry) === id);
      if (item) {
        emitArtifactOpened(item);
      }
    }

    function closeArtifactViewer() {
      state.activeArtifactId = "";
      renderArtifactList();
      renderArtifactViewer();
    }

    function render() {
      const items = getArtifacts();
      const currentId = String(state.activeArtifactId || "");
      if (currentId && !items.some((entry) => getArtifactId(entry) === currentId)) {
        state.activeArtifactId = "";
      }

      renderArtifactList();
      renderArtifactViewer();
    }

    function bindEvents() {
      document.addEventListener("nova:render-artifacts", function () {
        render();
      });

      document.addEventListener("nova:artifact-close", function () {
        closeArtifactViewer();
      });
    }

    function boot() {
      bindEvents();
      render();

      window.NovaComposerArtifacts = {
        render,
        openArtifact,
        closeArtifactViewer,
      };

      log("boot complete");
      return true;
    }

    return boot();
  }

  if (!bootModule()) {
    document.addEventListener("DOMContentLoaded", function () {
      bootModule();
    });
  }
})();