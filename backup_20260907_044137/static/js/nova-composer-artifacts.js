(function () {
  "use strict";

  if (window.NovaComposerArtifacts) return;

  function boot() {
    const core = window.NovaComposerCore;
    if (!core) return;

    const state = core.state;
    const els = core.els;

    function render() {
      if (!els.artifactList) return;

      els.artifactList.innerHTML = "";

      const items = Array.isArray(state.artifacts) ? state.artifacts : [];

      if (!items.length) {
        els.artifactList.innerHTML = "<div>No artifacts yet</div>";
        return;
      }

      items.forEach(function (a) {
        const el = document.createElement("div");
        el.textContent = a.title || "artifact";
        els.artifactList.appendChild(el);
      });
    }

    document.addEventListener("nova:render-artifacts", render);

    window.NovaComposerArtifacts = {
      render
    };

    render();
    console.log("[Artifacts] stable boot");
  }

  document.addEventListener("DOMContentLoaded", boot);
})();

