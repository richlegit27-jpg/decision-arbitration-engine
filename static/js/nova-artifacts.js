<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Nova Ultimate 2026</title>
  <link rel="stylesheet" href="/static/css/nova-main.css?v=api-origin-lock-2026-04-02-001">
</head>
<body data-active-session-id="">
  <script>
    (function () {
      "use strict";

      function trimSlash(value) {
        return String(value || "").replace(/\/+$/, "");
      }

      function inferApiBase() {
        var explicit =
          window.NOVA_API_BASE ||
          document.documentElement.getAttribute("data-api-base") ||
          document.body.getAttribute("data-api-base") ||
          "";

        if (explicit) return trimSlash(explicit);

        return trimSlash(window.location.origin);
      }

      window.NOVA_API_BASE = inferApiBase();
      document.documentElement.setAttribute("data-api-base", window.NOVA_API_BASE);
    })();
  </script>

  <div id="novaAppShell" class="nova-app-shell">
    <aside id="novaSidebar" class="nova-sidebar">
      <div class="nova-sidebar-top">
        <div class="nova-brand">Nova Ultimate 2026</div>
        <button id="sidebarToggle" class="nova-icon-btn" type="button" aria-label="Toggle sidebar">☰</button>
      </div>

      <div class="nova-sidebar-actions">
        <button id="newSessionBtn" class="nova-btn" type="button">New</button>
        <button id="refreshSessionsBtn" class="nova-btn nova-btn-secondary" type="button">Refresh</button>
      </div>

      <div id="sessionsList" class="nova-sessions-list"></div>
    </aside>

    <main class="nova-main">
      <header class="nova-topbar">
        <div class="nova-topbar-left">
          <button id="memoryPanelToggle" class="nova-btn nova-btn-secondary" type="button">Memory</button>
          <button id="artifactsPanelToggle" class="nova-btn nova-btn-secondary" type="button">Artifacts</button>
          <button id="webPanelToggle" class="nova-btn nova-btn-secondary" type="button">Web</button>
        </div>

        <div class="nova-topbar-right">
          <button id="closeRightRailBtn" class="nova-btn nova-btn-secondary" type="button">Close</button>
        </div>
      </header>

      <section id="messagesWrap" class="nova-messages-wrap">
        <div id="novaEmptyState" class="nova-empty-state">
          <div class="nova-empty-title">Nova is ready.</div>
          <div class="nova-empty-copy">Type a message, upload a file, or use commands like /image and /web.</div>
        </div>
        <div id="messages" class="nova-messages"></div>
      </section>

      <footer class="nova-composer">
        <div id="stagedFiles" class="nova-staged-files"></div>

        <div class="nova-composer-row">
          <textarea
            id="chatInput"
            class="nova-input"
            placeholder="Type a message or /web https://example.com"
            rows="3"
          ></textarea>
        </div>

        <div class="nova-composer-actions">
          <input id="fileInput" type="file" multiple hidden>
          <button id="uploadBtn" class="nova-btn nova-btn-secondary" type="button">Upload</button>
          <button id="sendBtn" class="nova-btn" type="button">Send</button>
        </div>
      </footer>
    </main>

    <aside id="rightRail" class="nova-right-rail is-collapsed" aria-hidden="true">
      <section id="memoryPanel" class="nova-right-panel" hidden aria-hidden="true">
        <div class="nova-panel-head">
          <h2>Memory</h2>
        </div>
        <div class="nova-panel-scroll">
          <div id="memoryStatus" class="nova-panel-status">Memory panel ready.</div>
          <div id="memoryList"></div>
        </div>
      </section>

      <section id="artifactsPanel" class="nova-right-panel" hidden aria-hidden="true">
        <div class="nova-panel-head">
          <h2>Artifacts</h2>
        </div>

        <div class="nova-panel-scroll">
          <div class="nova-artifact-toolbar">
            <input id="artifactSearchInput" class="nova-input" type="text" placeholder="Search artifacts">
            <div id="artifactStatus" class="nova-panel-status">Artifacts ready.</div>
          </div>

          <div id="artifactList" class="nova-artifact-list"></div>
          <div id="artifactViewer" class="nova-artifact-viewer"></div>
        </div>
      </section>

      <section id="webPanel" class="nova-right-panel" hidden aria-hidden="true">
        <div class="nova-panel-head">
          <h2>Web</h2>
        </div>
        <div class="nova-panel-scroll">
          <div id="webStatus" class="nova-panel-status">Web panel ready.</div>
          <div id="webResults"></div>
        </div>
      </section>
    </aside>
  </div>

  <script src="/static/js/nova-artifacts.js?v=api-origin-lock-2026-04-02-001"></script>
  <script src="/static/js/nova-composer-bundle.js?v=api-origin-lock-2026-04-02-001"></script>
</body>
</html>