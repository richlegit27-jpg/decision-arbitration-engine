<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0, viewport-fit=cover"
  />
  <title>Nova</title>

  <link rel="stylesheet" href="/static/css/nova-main.css?v=phase35_artifactrail1" />
</head>
<body>
  <div class="nova-shell" id="novaAppShell">
    <aside class="nova-sidebar" id="novaSidebar">
      <div class="nova-sidebar-head">
        <div class="nova-brand">
          <div class="nova-brand-mark">N</div>
          <div class="nova-brand-copy">
            <div class="nova-brand-title">Nova</div>
            <div class="nova-brand-subtitle">Endgame</div>
          </div>
        </div>

        <button
          type="button"
          class="nova-icon-btn"
          id="sidebarToggle"
          aria-label="Toggle sidebar"
          title="Toggle sidebar"
        >
          ☰
        </button>
      </div>

      <div class="nova-sidebar-actions">
        <button type="button" class="nova-primary-btn" id="newChatBtn">
          + New Chat
        </button>
      </div>

      <div class="nova-sidebar-section">
        <div class="nova-sidebar-label">Sessions</div>
        <div class="nova-session-list" id="sessionList"></div>
      </div>
    </aside>

    <main class="nova-main" id="novaMain">
      <header class="nova-topbar">
        <div class="nova-topbar-left">
          <button
            type="button"
            class="nova-icon-btn nova-mobile-only"
            id="mobileSidebarToggle"
            aria-label="Open sidebar"
            title="Open sidebar"
          >
            ☰
          </button>

          <div class="nova-title-wrap">
            <div class="nova-page-title" id="sessionTitle">Ready</div>
            <div class="nova-page-subtitle">Locked and launch-ready</div>
          </div>
        </div>

        <div class="nova-topbar-actions">
          <button
            type="button"
            class="nova-ghost-btn"
            id="memoryPanelToggle"
            aria-label="Toggle memory"
            title="Toggle memory"
          >
            Memory
          </button>

          <button
            type="button"
            class="nova-ghost-btn"
            id="artifactsPanelToggle"
            aria-label="Toggle artifacts"
            title="Toggle artifacts"
          >
            Artifacts
          </button>

          <button
            type="button"
            class="nova-ghost-btn"
            id="themeToggle"
            aria-label="Toggle theme"
            title="Toggle theme"
          >
            Theme
          </button>
        </div>
      </header>

      <section class="nova-chat-shell">
        <div class="nova-chat-scroll" id="chatScroll">
          <div class="nova-empty-state" id="emptyState">
            <div class="nova-empty-card">
              <div class="nova-empty-title">Nova is ready</div>
              <div class="nova-empty-subtitle">
                Start a message. Save strong replies straight into artifacts.
              </div>
            </div>
          </div>

          <div class="nova-messages" id="messages"></div>
        </div>

        <div class="nova-composer-wrap">
          <div class="nova-attachments-bar" id="attachmentsBar" hidden></div>

          <div class="nova-composer">
            <button
              type="button"
              class="nova-composer-side-btn"
              id="attachBtn"
              aria-label="Attach"
              title="Attach"
            >
              ＋
            </button>

            <textarea
              id="composerInput"
              class="nova-composer-input"
              rows="1"
              placeholder="Message Nova..."
              autocomplete="off"
            ></textarea>

            <button
              type="button"
              class="nova-composer-side-btn"
              id="voiceBtn"
              aria-label="Voice"
              title="Voice"
            >
              🎤
            </button>

            <button
              type="button"
              class="nova-send-btn"
              id="sendBtn"
              aria-label="Send"
              title="Send"
            >
              Send
            </button>
          </div>
        </div>
      </section>
    </main>

    <aside class="nova-right-rail" id="novaRightRail">
      <section class="nova-panel" id="memoryPanel">
        <div class="nova-panel-head">
          <div>
            <div class="nova-panel-title">Memory</div>
            <div class="nova-panel-subtitle">Pinned context and recall</div>
          </div>

          <button
            type="button"
            class="nova-icon-btn"
            id="memoryCloseBtn"
            aria-label="Close memory"
            title="Close memory"
          >
            ✕
          </button>
        </div>

        <div class="nova-panel-body">
          <div class="nova-memory-placeholder">
            Memory panel ready.
          </div>
        </div>
      </section>

      <section class="nova-panel nova-artifacts-root" id="novaArtifactsRoot">
        <div class="nova-panel-head">
          <div>
            <div class="nova-panel-title">Artifacts</div>
            <div class="nova-panel-subtitle">
              <span id="novaArtifactsCount">0</span> saved
            </div>
          </div>

          <button
            type="button"
            class="nova-icon-btn"
            id="artifactsCloseBtn"
            aria-label="Close artifacts"
            title="Close artifacts"
          >
            ✕
          </button>
        </div>

        <div class="nova-artifacts-status" id="novaArtifactsStatus"></div>

        <div class="nova-panel-body nova-artifacts-body">
          <div class="nova-artifacts-empty" id="novaArtifactsEmpty">
            No artifacts yet. Save a reply from chat or let Nova generate one.
          </div>

          <div class="nova-artifacts-list" id="novaArtifactsList"></div>
        </div>
      </section>
    </aside>
  </div>

  <section class="nova-artifact-viewer" id="novaArtifactViewer" hidden data-open="false">
    <div class="nova-artifact-viewer-backdrop"></div>

    <div class="nova-artifact-viewer-card">
      <div class="nova-artifact-viewer-head">
        <div class="nova-artifact-viewer-title-wrap">
          <div class="nova-artifact-viewer-title" id="novaArtifactViewerTitle">
            Artifact
          </div>
          <div class="nova-artifact-viewer-meta">
            <span class="nova-artifact-viewer-badge" id="novaArtifactViewerType">document</span>
            <span class="nova-artifact-viewer-time" id="novaArtifactViewerTime"></span>
          </div>
        </div>

        <button
          type="button"
          class="nova-icon-btn"
          id="artifactViewerCloseBtn"
          aria-label="Close artifact viewer"
          title="Close artifact viewer"
        >
          ✕
        </button>
      </div>

      <div class="nova-artifact-viewer-body">
        <pre class="nova-artifact-viewer-content" id="novaArtifactViewerContent"></pre>
      </div>
    </div>
  </section>

  <script src="/static/js/nova-artifacts.js?v=phase35_artifactrail1"></script>
  <script src="/static/js/nova-render.js?v=phase35_artifactrail1"></script>
</body>
</html>