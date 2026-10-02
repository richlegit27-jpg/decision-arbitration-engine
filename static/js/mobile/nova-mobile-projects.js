(function () {
  "use strict";

  if (window.__NOVA_MOBILE_PROJECTS_WORKSPACE_V1__) return;
  window.__NOVA_MOBILE_PROJECTS_WORKSPACE_V1__ = true;

  const $ = (id) => document.getElementById(id);
  const state = { projectId: "", busy: false, interruptBusy: false, listRequest: null };
  const terminal = new Set(["completed", "complete", "done", "success"]);
  const failed = new Set(["failed", "failure", "error", "errored", "blocked"]);
  const active = new Set(["running", "in_progress", "in progress", "executing", "planning"]);
  const waiting = new Set(["waiting_approval", "awaiting_approval", "approval_required", "needs_approval"]);

  async function api(url, options = {}) {
    const { allowDomainFailure = false, ...fetchOptions } = options;
    const response = await fetch(url, {
      credentials: "same-origin",
      ...fetchOptions,
      headers: { Accept: "application/json", ...(fetchOptions.body ? { "Content-Type": "application/json" } : {}), ...(fetchOptions.headers || {}) },
    });
    let data;
    try { data = await response.json(); } catch (_) { throw new Error("Nova returned an unreadable response."); }
    if (!response.ok || (!allowDomainFailure && data?.ok === false)) throw new Error(data?.error || data?.message || `Request failed (${response.status}).`);
    return data;
  }

  function setPanel(panel, open) {
    panel.classList.toggle("hidden", !open);
    panel.setAttribute("aria-hidden", String(!open));
    if (panel === $("nova-mobile-projects-panel")) $("nova-mobile-projects-toggle")?.setAttribute("aria-expanded", String(open));
  }

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function setMessage(message, isError = false) {
    const target = $("nova-mobile-project-message");
    target.textContent = message;
    target.dataset.state = isError ? "error" : "normal";
    $("nova-mobile-project-retry").hidden = !isError;
  }

  async function loadProjects() {
    if (state.listRequest) return state.listRequest;
    const list = $("novaMobileProjectList");
    list.replaceChildren();
    setMessage("Loading your projects…");
    state.listRequest = (async () => {
      try {
        const data = await api("/api/projects");
        const projects = Array.isArray(data.projects) ? data.projects : (Array.isArray(data.items) ? data.items : []);
        if (!projects.length) {
          setMessage("No projects yet. Describe a goal above to create your first one.");
          return;
        }
        setMessage(`${projects.length} saved project${projects.length === 1 ? "" : "s"}`);
        for (const project of projects) {
          if (!project || !project.id) continue;
          const button = make("button", "nova-mobile-project-card");
          button.type = "button";
          button.dataset.projectId = project.id;
          const title = make("strong", "nova-mobile-project-card-title", project.name || project.title || "Untitled project");
          const description = make("span", "nova-mobile-project-card-description", project.description || "Open this project to review its saved plan and status.");
          const meta = make("span", "nova-mobile-project-card-meta");
          const status = make("span", "nova-mobile-project-card-status", project.status || "Not started");
          const updated = project.updated_at ? new Date(project.updated_at).toLocaleDateString() : "Saved project";
          meta.append(status, make("span", "", updated));
          button.append(title, description, meta);
          button.addEventListener("click", () => openProject(project.id));
          list.appendChild(button);
        }
      } catch (error) {
        setMessage(`Projects could not be loaded: ${error.message}`, true);
      } finally {
        state.listRequest = null;
      }
    })();
    return state.listRequest;
  }

  function taskStatus(task) {
    return String(task?.status || task?.state || task?.completion_status || "pending").trim().toLowerCase().replace(/[ -]+/g, "_");
  }

  function renderTasks(tasks) {
    const list = $("nova-mobile-project-task-list");
    list.replaceChildren();
    const safeTasks = Array.isArray(tasks) ? tasks : [];
    const completeCount = safeTasks.filter((task) => terminal.has(taskStatus(task))).length;
    $("nova-mobile-project-progress").textContent = safeTasks.length ? `${completeCount} of ${safeTasks.length} complete` : "No tasks saved";
    if (!safeTasks.length) {
      list.appendChild(make("p", "nova-mobile-project-empty", "This project has no saved tasks yet."));
      return;
    }
    for (const task of safeTasks) {
      const row = make("article", "nova-mobile-project-task");
      row.dataset.status = taskStatus(task);
      row.append(make("span", "nova-mobile-project-task-mark", terminal.has(taskStatus(task)) ? "✓" : failed.has(taskStatus(task)) ? "!" : "•"));
      const body = make("div", "nova-mobile-project-task-body");
      body.append(make("strong", "", task.title || task.name || task.description || "Project task"));
      const details = task.error || task.result || task.output || task.status || "Pending";
      body.append(make("small", "", details));
      const dependencies = Array.isArray(task.dependencies) ? task.dependencies : [];
      if (dependencies.length) body.append(make("small", "", `Depends on: ${dependencies.join(", ")}`));
      const nested = task.steps || task.substeps || task.execution_steps || [];
      if (Array.isArray(nested) && nested.length) {
        const substeps = make("div", "nova-mobile-project-substeps");
        for (const step of nested) {
          const stepStatus = String(step.status || step.state || "pending").replace(/_/g, " ");
          const detail = step.error || step.result || step.output || stepStatus;
          const substep = make("div", "nova-mobile-project-substep");
          substep.append(make("span", "", step.title || step.name || "Step"), make("small", "", detail));
          substeps.appendChild(substep);
        }
        body.appendChild(substeps);
      }
      row.appendChild(body);
      list.appendChild(row);
    }
  }

  function renderPhases(phases) {
    const list = $("nova-mobile-project-phase-list");
    list.replaceChildren();
    const items = Array.isArray(phases) ? phases : [];
    if (!items.length) {
      list.appendChild(make("p", "nova-mobile-project-empty", "No project phases are saved."));
      return;
    }
    for (const [index, phase] of items.entries()) {
      const row = make("article", "nova-mobile-project-phase");
      row.append(make("span", "nova-mobile-project-task-mark", String(index + 1).padStart(2, "0")));
      const body = make("div", "nova-mobile-project-task-body");
      body.append(make("strong", "", phase.title || phase.name || `Phase ${index + 1}`));
      body.append(make("small", "", phase.description || phase.goal || phase.status || "Planned phase"));
      row.appendChild(body);
      list.appendChild(row);
    }
  }

  function renderFiles(files) {
    const list = $("nova-mobile-project-files-list");
    list.replaceChildren();
    const items = Array.isArray(files) ? files : [];
    if (!items.length) {
      list.appendChild(make("p", "nova-mobile-project-empty", "No project files are attached yet."));
      return;
    }
    for (const file of items) {
      const name = file.name || file.filename || file.original_filename || file.title || "Project file";
      const row = make("div", "nova-mobile-project-file");
      row.appendChild(make("span", "nova-mobile-project-file-icon", "↗"));
      if (file.id) {
        const link = make("a", "nova-mobile-project-file-link", name);
        link.href = `/api/projects/${encodeURIComponent(state.projectId)}/files/${encodeURIComponent(file.id)}/download`;
        link.target = "_blank";
        link.rel = "noopener";
        row.appendChild(link);
      } else {
        row.appendChild(make("span", "", name));
      }
      list.appendChild(row);
    }
  }

  function pendingApproval(execution, tasks) {
    const executionStatus = String(execution?.status || execution?.state || "").toLowerCase();
    if (waiting.has(executionStatus)) return true;
    if (execution?.waiting === true && /approv/i.test(String(execution?.waiting_reason || execution?.current_action || ""))) return true;
    return (Array.isArray(tasks) ? tasks : []).some((task) => {
      const steps = task?.steps || task?.substeps || task?.execution_steps || [];
      return Array.isArray(steps) && steps.some((step) => {
        const status = String(step?.status || step?.approval_status || "").toLowerCase();
        return waiting.has(status) || ((step?.approval_required === true || step?.requires_approval === true) && status !== "approved");
      });
    });
  }

  function updateControls(execution, tasks) {
    const status = String(execution?.status || execution?.state || "pending").trim().toLowerCase().replace(/[ -]+/g, "_");
    const incomplete = (Array.isArray(tasks) ? tasks : []).some((task) => !terminal.has(taskStatus(task)));
    const approval = pendingApproval(execution, tasks);
    const controls = {
      "nova-mobile-project-run": incomplete && !active.has(status) && !approval && ["", "pending", "idle", "not_started", "failed", "blocked"].includes(status),
      "nova-mobile-project-continue": incomplete && !active.has(status) && !approval && ["paused", "stopped", "failed", "blocked"].includes(status),
      "nova-mobile-project-pause": active.has(status),
      "nova-mobile-project-approve": approval,
      "nova-mobile-project-reset": status === "completed" || status === "complete" || status === "done" || status === "success" || status === "failed" || status === "blocked" || status === "paused" || status === "stopped",
    };
    for (const [id, visible] of Object.entries(controls)) $(id).hidden = !visible;
    const humanStatus = status.replace(/_/g, " ") || "pending";
    const currentStep = execution?.current_step || execution?.current_task || execution?.current_task_title || "";
    const detail = execution?.error || execution?.last_error || "";
    $("nova-mobile-project-execution-status").textContent = `${humanStatus[0].toUpperCase()}${humanStatus.slice(1)}${currentStep ? ` · ${currentStep}` : ""}${detail ? ` · ${detail}` : ""}`;
  }

  async function openProject(projectId) {
    state.projectId = String(projectId || "");
    if (!state.projectId) return;
    const listPanel = $("nova-mobile-projects-panel");
    const detailPanel = $("nova-mobile-project-workspace");
    setPanel(listPanel, false);
    setPanel(detailPanel, true);
    $("nova-mobile-project-title").textContent = "Loading project…";
    $("nova-mobile-project-description").textContent = "";
    $("nova-mobile-project-status").textContent = "Loading";
    $("nova-mobile-project-execution-status").textContent = "Loading project status…";
    try {
      const [projectData, executionData] = await Promise.all([
        api(`/api/projects/${encodeURIComponent(state.projectId)}`),
        api(`/api/projects/${encodeURIComponent(state.projectId)}/execution`),
      ]);
      const project = projectData.project || {};
      const tasks = Array.isArray(executionData.tasks) ? executionData.tasks : (Array.isArray(project.tasks) ? project.tasks : []);
      const execution = executionData.execution || {};
      $("nova-mobile-project-title").textContent = project.name || project.title || "Project";
      $("nova-mobile-project-description").textContent = project.description || project.goal || "";
      $("nova-mobile-project-status").textContent = project.status || execution.status || "Not started";
      renderTasks(tasks);
      try {
        const phaseData = await api(`/api/projects/${encodeURIComponent(state.projectId)}/phases`);
        renderPhases(phaseData.phases);
      } catch (_) {
        renderPhases(project.phases);
      }
      try {
        const filesData = await api(`/api/projects/${encodeURIComponent(state.projectId)}/files`);
        renderFiles(Array.isArray(filesData.files) ? filesData.files : project.files);
      } catch (_) {
        renderFiles(project.files);
      }
      updateControls(execution, tasks);
    } catch (error) {
      $("nova-mobile-project-execution-status").textContent = `Project could not be opened: ${error.message}`;
      $("nova-mobile-project-task-list").replaceChildren(make("p", "nova-mobile-project-error", "Try refreshing this project. Your saved project data has not been changed."));
      Object.keys({ run: 1, continue: 1, pause: 1, approve: 1, reset: 1 }).forEach((name) => { $("nova-mobile-project-" + name).hidden = true; });
    }
  }

  async function execute(action) {
    const interruptAction = action === "pause";
    if (!state.projectId || (state.busy && !interruptAction) || (interruptAction && state.interruptBusy)) return;
    if (interruptAction) state.interruptBusy = true;
    else state.busy = true;
    const buttons = ["run", "continue", "pause", "approve", "reset"].map((name) => $("nova-mobile-project-" + name));
    buttons.forEach((button) => {
      button.disabled = button.id !== "nova-mobile-project-pause" || state.interruptBusy;
    });
    if (action === "run_all" || action === "continue") {
      $("nova-mobile-project-pause").hidden = false;
    }
    $("nova-mobile-project-execution-status").textContent = `${action === "run_all" ? "Starting" : action === "continue" ? "Resuming" : action === "approve" ? "Approving" : action === "pause" ? "Pausing" : "Resetting"} project…`;
    try {
      const result = await api(`/api/projects/${encodeURIComponent(state.projectId)}/execution/control`, {
        method: "POST",
        body: JSON.stringify({ action }),
        allowDomainFailure: true,
      });
      await openProject(state.projectId);
      const resultStatus = String(result.status || result.execution_status || "").trim().toLowerCase();
      if (result.ok === false && !["paused", "stopped", "cancelled", "canceled", "waiting", "waiting_approval", "busy"].includes(resultStatus)) {
        $("nova-mobile-project-execution-status").textContent = `Action failed: ${result.message || result.error || "The project action was not accepted."}`;
      }
    } catch (error) {
      try {
        await openProject(state.projectId);
      } catch (_) {
        // Keep the original execution error visible below.
      }
      $("nova-mobile-project-execution-status").textContent = `Action failed: ${error.message}`;
    } finally {
      if (interruptAction) state.interruptBusy = false;
      else state.busy = false;
      buttons.forEach((button) => {
        button.disabled = (state.busy && button.id !== "nova-mobile-project-pause") || (button.id === "nova-mobile-project-pause" && state.interruptBusy);
      });
    }
  }

  async function createProject(event) {
    event.preventDefault();
    if (state.busy) return;
    const goal = $("nova-mobile-project-goal").value.trim();
    if (!goal) return;
    state.busy = true;
    const button = $("nova-mobile-project-create-button");
    button.disabled = true;
    setMessage("Creating your project and preparing its plan…");
    try {
      const data = await api("/api/projects/new", { method: "POST", body: JSON.stringify({ name: goal.length > 80 ? `${goal.slice(0, 77)}…` : goal, description: goal, session_id: window.__ACTIVE_SESSION_ID__ || localStorage.getItem("nova_active_session_id") || "" }) });
      if (!data.project?.id) throw new Error("The project service did not return a saved project.");
      $("nova-mobile-project-goal").value = "";
      setMessage("Project saved. Open it below to review its plan and status.");
      await loadProjects();
      await openProject(data.project.id);
    } catch (error) {
      setMessage(`Project could not be created: ${error.message}`, true);
    } finally {
      state.busy = false;
      button.disabled = false;
    }
  }

  function openList() {
    ["nova-mobile-sessions-panel", "nova-mobile-tools-panel", "nova-mobile-memory-panel", "nova-mobile-execution-panel"].forEach((id) => {
      const panel = $(id);
      if (panel) panel.classList.add("hidden");
    });
    setPanel($("nova-mobile-project-workspace"), false);
    setPanel($("nova-mobile-projects-panel"), true);
    loadProjects();
  }

  $("nova-mobile-projects-toggle").addEventListener("click", () => {
    const listOpen = !$("nova-mobile-projects-panel").classList.contains("hidden");
    const detailOpen = !$("nova-mobile-project-workspace").classList.contains("hidden");
    if (listOpen || detailOpen) {
      setPanel($("nova-mobile-projects-panel"), false);
      setPanel($("nova-mobile-project-workspace"), false);
    } else {
      openList();
    }
  });
  $("nova-mobile-sessions-toggle").addEventListener("click", () => {
    setPanel($("nova-mobile-projects-panel"), false);
    setPanel($("nova-mobile-project-workspace"), false);
  }, { capture: true });
  $("nova-mobile-projects-close").addEventListener("click", () => setPanel($("nova-mobile-projects-panel"), false));
  $("nova-mobile-project-back").addEventListener("click", openList);
  $("nova-mobile-project-retry").addEventListener("click", loadProjects);
  $("nova-mobile-project-create-form").addEventListener("submit", createProject);
  $("nova-mobile-project-refresh").addEventListener("click", () => state.projectId && openProject(state.projectId));
  $("nova-mobile-project-run").addEventListener("click", () => execute("run_all"));
  $("nova-mobile-project-continue").addEventListener("click", () => execute("continue"));
  $("nova-mobile-project-pause").addEventListener("click", () => execute("pause"));
  $("nova-mobile-project-approve").addEventListener("click", () => execute("approve"));
  $("nova-mobile-project-reset").addEventListener("click", () => execute("reset"));
})();
