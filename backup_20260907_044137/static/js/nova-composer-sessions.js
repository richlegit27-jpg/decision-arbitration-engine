(function () {
  "use strict";

  if (window.NovaComposerSessions) return;

  function log() {
    try {
      console.log("[NovaComposerSessions]", ...arguments);
    } catch (_) {}
  }

  function bootModule() {
    const core = window.NovaComposerCore;
    if (!core) return false;

    const api = core.api;
    const state = core.state;
    const els = core.els;

    function getSessionId(session) {
      return String(session?.id || session?.session_id || "");
    }

    function getSessionTitle(session) {
      return String(session?.title || session?.name || "New Chat");
    }

    function getSessionPreview(session) {
      return String(
        session?.last_message_preview ||
        session?.preview ||
        (session?.message_count ? `${session.message_count} messages` : "No messages yet")
      );
    }

    function isPinned(session) {
      return !!session?.pinned;
    }

    function setBusy(flag) {
      state.sessionRailBusy = !!flag;
      if (els.sessionList) {
        els.sessionList.classList.toggle("is-busy", !!flag);
      }
    }

    function emitSessionChanged(payload) {
      try {
        document.dispatchEvent(
          new CustomEvent("nova:session-changed", {
            detail: payload || {},
          })
        );
      } catch (_) {}
    }

    function emitRailRendered() {
      try {
        document.dispatchEvent(
          new CustomEvent("nova:session-rail-rendered", {
            detail: {
              activeSessionId: state.activeSessionId || "",
              count: Array.isArray(state.sessions) ? state.sessions.length : 0,
            },
          })
        );
      } catch (_) {}
    }

    async function refreshFromBackend(preferredSessionId) {
      const payload = await api.get("/api/state");
      if (typeof core.applyState === "function") {
        core.applyState(payload);
      } else {
        state.lastState = payload || {};
        state.sessions = Array.isArray(payload?.sessions) ? payload.sessions.slice() : [];
        state.messages = Array.isArray(payload?.messages) ? payload.messages.slice() : [];
        state.artifacts = Array.isArray(payload?.artifacts) ? payload.artifacts.slice() : [];
        state.memory = Array.isArray(payload?.memory) ? payload.memory.slice() : [];
        state.web = Array.isArray(payload?.web) ? payload.web.slice() : [];
        state.activeSessionId =
          String(
            preferredSessionId ||
            payload?.active_session_id ||
            payload?.session_id ||
            state.activeSessionId ||
            ""
          );
      }

      if (preferredSessionId) {
        state.activeSessionId = String(preferredSessionId);
      }

      if (typeof core.renderAll === "function") {
        core.renderAll();
      } else {
        renderSessionRail();
      }

      emitSessionChanged({
        sessionId: state.activeSessionId || "",
        source: "refresh",
        payload,
      });

      return payload;
    }

    async function openSession(sessionId) {
      const id = String(sessionId || "").trim();
      if (!id || state.sessionRailBusy) return;

      setBusy(true);
      try {
        const payload = await api.post("/api/sessions/open", { session_id: id });
        if (typeof core.applyState === "function") {
          core.applyState(payload);
        } else {
          state.activeSessionId = id;
          state.lastState = payload || {};
          state.sessions = Array.isArray(payload?.sessions) ? payload.sessions.slice() : state.sessions;
          state.messages = Array.isArray(payload?.messages) ? payload.messages.slice() : [];
          state.artifacts = Array.isArray(payload?.artifacts) ? payload.artifacts.slice() : [];
          state.memory = Array.isArray(payload?.memory) ? payload.memory.slice() : [];
          state.web = Array.isArray(payload?.web) ? payload.web.slice() : [];
        }

        state.activeSessionId =
          String(payload?.active_session_id || payload?.session_id || id);

        if (typeof core.renderAll === "function") {
          core.renderAll();
        } else {
          renderSessionRail();
        }

        emitSessionChanged({
          sessionId: state.activeSessionId,
          source: "open",
          payload,
        });
      } catch (error) {
        console.error("[NovaComposerSessions] openSession failed", error);
        alert(error?.message || "Failed to open session.");
      } finally {
        setBusy(false);
      }
    }

    async function createSession() {
      if (state.sessionRailBusy) return;

      setBusy(true);
      try {
        const payload = await api.post("/api/sessions/new", {});
        if (typeof core.applyState === "function") {
          core.applyState(payload);
        } else {
          state.lastState = payload || {};
          state.sessions = Array.isArray(payload?.sessions) ? payload.sessions.slice() : state.sessions;
          state.messages = Array.isArray(payload?.messages) ? payload.messages.slice() : [];
          state.artifacts = Array.isArray(payload?.artifacts) ? payload.artifacts.slice() : [];
          state.memory = Array.isArray(payload?.memory) ? payload.memory.slice() : [];
          state.web = Array.isArray(payload?.web) ? payload.web.slice() : [];
          state.activeSessionId = String(
            payload?.active_session_id || payload?.session_id || state.activeSessionId || ""
          );
        }

        if (typeof core.renderAll === "function") {
          core.renderAll();
        } else {
          renderSessionRail();
        }

        emitSessionChanged({
          sessionId: state.activeSessionId || "",
          source: "new",
          payload,
        });
      } catch (error) {
        console.error("[NovaComposerSessions] createSession failed", error);
        alert(error?.message || "Failed to create session.");
      } finally {
        setBusy(false);
      }
    }

    async function renameSession(sessionId) {
      const id = String(sessionId || "").trim();
      if (!id || state.sessionRailBusy) return;

      const target = (state.sessions || []).find((s) => getSessionId(s) === id);
      const currentTitle = getSessionTitle(target);
      const nextTitle = window.prompt("Rename session", currentTitle);

      if (nextTitle == null) return;
      const cleanTitle = String(nextTitle).trim();
      if (!cleanTitle || cleanTitle === currentTitle) return;

      setBusy(true);
      try {
        await api.post("/api/sessions/rename", {
          session_id: id,
          title: cleanTitle,
        });
        await refreshFromBackend(id);
      } catch (error) {
        console.error("[NovaComposerSessions] renameSession failed", error);
        alert(error?.message || "Failed to rename session.");
      } finally {
        setBusy(false);
      }
    }

    async function togglePinSession(sessionId) {
      const id = String(sessionId || "").trim();
      if (!id || state.sessionRailBusy) return;

      setBusy(true);
      try {
        await api.post("/api/sessions/pin", { session_id: id });
        await refreshFromBackend(id);
      } catch (error) {
        console.error("[NovaComposerSessions] togglePinSession failed", error);
        alert(error?.message || "Failed to update pin.");
      } finally {
        setBusy(false);
      }
    }

    async function deleteSession(sessionId) {
      const id = String(sessionId || "").trim();
      if (!id || state.sessionRailBusy) return;

      const ok = window.confirm("Delete this session?");
      if (!ok) return;

      setBusy(true);
      try {
        await api.post("/api/sessions/delete", { session_id: id });
        await refreshFromBackend("");
      } catch (error) {
        console.error("[NovaComposerSessions] deleteSession failed", error);
        alert(error?.message || "Failed to delete session.");
      } finally {
        setBusy(false);
      }
    }

    function buildSessionCard(session) {
      const id = getSessionId(session);
      const active = id && id === String(state.activeSessionId || "");
      const card = document.createElement("button");
      card.type = "button";
      card.className = "nova-session-card";
      if (active) card.classList.add("is-active");
      if (isPinned(session)) card.classList.add("is-pinned");
      card.setAttribute("data-session-id", id);

      const glow = document.createElement("div");
      glow.className = "nova-session-card-glow";

      const main = document.createElement("div");
      main.className = "nova-session-card-main";

      const top = document.createElement("div");
      top.className = "nova-session-card-top";

      const title = document.createElement("div");
      title.className = "nova-session-card-title";
      title.textContent = getSessionTitle(session);

      const badges = document.createElement("div");
      badges.className = "nova-session-card-badges";

      if (isPinned(session)) {
        const pinned = document.createElement("span");
        pinned.className = "nova-session-mini-badge";
        pinned.textContent = "Pinned";
        badges.appendChild(pinned);
      }

      const count = document.createElement("span");
      count.className = "nova-session-mini-badge";
      count.textContent = `${Number(session?.message_count || 0)} msgs`;
      badges.appendChild(count);

      top.appendChild(title);
      top.appendChild(badges);

      const preview = document.createElement("div");
      preview.className = "nova-session-card-preview";
      preview.textContent = getSessionPreview(session);

      const bottom = document.createElement("div");
      bottom.className = "nova-session-card-bottom";

      const updated = document.createElement("div");
      updated.className = "nova-session-card-updated";
      updated.textContent = session?.updated_at ? `Updated ${session.updated_at}` : "Ready";

      const actions = document.createElement("div");
      actions.className = "nova-session-card-actions";

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "nova-session-action-btn";
      pinBtn.setAttribute("title", isPinned(session) ? "Unpin session" : "Pin session");
      pinBtn.textContent = "â˜…";
      pinBtn.onclick = async function (event) {
        event.preventDefault();
        event.stopPropagation();
        await togglePinSession(id);
      };

      const renameBtn = document.createElement("button");
      renameBtn.type = "button";
      renameBtn.className = "nova-session-action-btn";
      renameBtn.setAttribute("title", "Rename session");
      renameBtn.textContent = "âœŽ";
      renameBtn.onclick = async function (event) {
        event.preventDefault();
        event.stopPropagation();
        await renameSession(id);
      };

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "nova-session-action-btn is-danger";
      deleteBtn.setAttribute("title", "Delete session");
      deleteBtn.textContent = "Ã—";
      deleteBtn.onclick = async function (event) {
        event.preventDefault();
        event.stopPropagation();
        await deleteSession(id);
      };

      actions.appendChild(pinBtn);
      actions.appendChild(renameBtn);
      actions.appendChild(deleteBtn);

      bottom.appendChild(updated);
      bottom.appendChild(actions);

      main.appendChild(top);
      main.appendChild(preview);
      main.appendChild(bottom);

      card.appendChild(glow);
      card.appendChild(main);

      card.onclick = async function () {
        await openSession(id);
      };

      return card;
    }

    function renderEmptyState() {
      if (!els.sessionList) return;
      els.sessionList.innerHTML = "";

      const empty = document.createElement("div");
      empty.className = "nova-session-empty";

      const title = document.createElement("div");
      title.className = "nova-session-empty-title";
      title.textContent = "No sessions yet";

      const body = document.createElement("div");
      body.className = "nova-session-empty-body";
      body.textContent = "Start a new chat and your session rail will populate here.";

      const action = document.createElement("button");
      action.type = "button";
      action.className = "nova-primary-btn nova-session-empty-btn";
      action.textContent = "Start New Chat";
      action.onclick = createSession;

      empty.appendChild(title);
      empty.appendChild(body);
      empty.appendChild(action);

      els.sessionList.appendChild(empty);
    }

    function sortSessions(list) {
      return (Array.isArray(list) ? list.slice() : []).sort((a, b) => {
        const aPinned = isPinned(a) ? 1 : 0;
        const bPinned = isPinned(b) ? 1 : 0;
        if (aPinned !== bPinned) return bPinned - aPinned;

        const aUpdated = String(a?.updated_at || "");
        const bUpdated = String(b?.updated_at || "");
        return bUpdated.localeCompare(aUpdated);
      });
    }

    function renderSessionRail() {
      if (!els.sessionList) return;
      els.sessionList.innerHTML = "";

      const sessions = sortSessions(state.sessions);
      if (!sessions.length) {
        renderEmptyState();
        emitRailRendered();
        return;
      }

      const frag = document.createDocumentFragment();
      sessions.forEach((session) => {
        frag.appendChild(buildSessionCard(session));
      });

      els.sessionList.appendChild(frag);
      emitRailRendered();
    }

    function bindGlobalActions() {
      document.addEventListener("click", async function (event) {
        const target = event.target.closest("[data-action]");
        if (!target) return;

        const action = target.getAttribute("data-action");
        if (action === "new-chat") {
          event.preventDefault();
          await createSession();
        }
      });

      document.addEventListener("nova:refresh-session-rail", function () {
        renderSessionRail();
      });

      document.addEventListener("nova:artifact-open-session", async function (event) {
        const sessionId = String(event?.detail?.sessionId || "");
        if (!sessionId) return;
        await openSession(sessionId);
      });
    }

    function boot() {
      bindGlobalActions();
      renderSessionRail();

      window.NovaComposerSessions = {
        render: renderSessionRail,
        openSession,
        createSession,
        renameSession,
        togglePinSession,
        deleteSession,
        refreshFromBackend,
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

