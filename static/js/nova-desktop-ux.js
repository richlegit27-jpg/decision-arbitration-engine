(function () {
  "use strict";

  if (window.NovaDesktopUX) return;

  const executionButtons = {
    continue: "desktopContinueProject",
    approve: "desktopApproveProject",
    runAll: "desktopRunAll",
    pause: "desktopPause",
    next: "desktopNextProject",
    stop: "desktopStopProject",
    reset: "desktopResetProject",
  };

  function errorText(error) {
    if (typeof error === "string") return error;
    return String(error?.message || error?.error || "").trim();
  }

  function formatError(context, error, fallback) {
    const detail = errorText(error);
    const normalized = detail.toLowerCase();
    const status = Number(error?.status || error?.statusCode || normalized.match(/\b(401|403)\b/)?.[1] || 0);

    if (/failed to fetch|networkerror|network request failed|load failed/.test(normalized)) {
      return "Nova couldn't connect to the server. Check your connection and try again.";
    }
    if (status === 401 || /unauthorized|authentication expired|session expired/.test(normalized)) {
      return "Your session has expired. Sign in again, then retry.";
    }
    if (status === 403 || /forbidden|not authorized/.test(normalized)) {
      return "You don't have access to complete that action.";
    }
    if (/no target_file|target file|target_files|file operation has no target/.test(normalized)) {
      return "Nova can't continue this project because a planned task is missing required file information. Try updating the plan or regenerating the blocked task.";
    }
    if (/no remaining task is runnable|remaining work is blocked|execution is blocked|\bblocked\b/.test(normalized)) {
      return "Nova can't continue yet because the remaining project work is blocked. Review the blocked task and update the plan before continuing.";
    }
    if (/provider|model.*unavailable|model.*not available|rate limit|temporarily unavailable/.test(normalized)) {
      return "The selected model is unavailable right now. Try again shortly or choose another model.";
    }
    if (context === "session-load") return "Nova couldn't load this conversation. Check your connection and try again.";
    if (context === "session") return fallback || "Nova couldn't complete this conversation action. Please try again.";
    if (context === "project-load") return "Nova couldn't load this project. Select it again to retry.";
    if (context === "project-files") return "Nova couldn't load this project's files. Please try again.";
    if (context === "project-notes") return "Nova couldn't load this project's notes. Please try again.";
    if (context === "project") return fallback || "Nova couldn't complete this project action. Review the project and try again.";
    if (context === "upload") return "Nova couldn't upload that file. Check the file and connection, then try again.";
    if (context === "execution") return "Nova couldn't complete this project action. Review the project status and try again.";
    if (context === "artifact") return "Nova couldn't load Artifacts. Check your connection and try again.";
    if (context === "chat") return "Nova couldn't complete that message. Please try again.";
    return "Nova couldn't complete that action. Please try again.";
  }

  function statusLabel(status) {
    const key = String(status || "").toLowerCase().replace(/[ -]+/g, "_");
    const labels = {
      ready: "Ready",
      pending: "Ready",
      not_started: "Ready",
      open: "Ready",
      todo: "Ready",
      queued: "Ready",
      running: "Running",
      active: "Running",
      in_progress: "Running",
      paused: "Paused",
      stopped: "Paused",
      waiting_approval: "Needs approval",
      waiting_for_approval: "Needs approval",
      awaiting_approval: "Needs approval",
      pending_approval: "Needs approval",
      approval_pending: "Needs approval",
      approval_required: "Needs approval",
      needs_approval: "Needs approval",
      blocked: "Blocked",
      failed: "Blocked",
      error: "Blocked",
      complete: "Complete",
      completed: "Complete",
      done: "Complete",
      success: "Complete",
    };
    return labels[key] || "Needs attention";
  }

  function setButtonVisible(id, visible) {
    const button = document.getElementById(id);
    if (!button) return;
    button.hidden = !visible;
    button.setAttribute("aria-hidden", visible ? "false" : "true");
  }

  function taskSteps(task) {
    if (Array.isArray(task?.steps)) return task.steps;
    if (Array.isArray(task?.substeps)) return task.substeps;
    return Array.isArray(task?.execution_steps) ? task.execution_steps : [];
  }

  function renderExecution(input) {
    const state = input && typeof input === "object" ? input : {};
    const projectId = String(state.projectId || window.__NOVA_PROJECT_STATE?.activeProjectId || "").trim();
    const execution = state.execution && typeof state.execution === "object" ? state.execution : {};
    const tasks = Array.isArray(state.tasks) ? state.tasks : [];
    const label = document.getElementById("novaDesktopExecutionLabel");
    const body = document.querySelector("#nova-desktop-execution-native [data-execution-panel]");

    Object.values(executionButtons).forEach((id) => setButtonVisible(id, false));

    if (!projectId) {
      if (label) label.textContent = "Execution · No active project";
      if (body) body.textContent = "Start or select a project to use execution controls.";
      return;
    }

    const rawStatus = String(execution.status || state.status || "").toLowerCase();
    let status = statusLabel(rawStatus);
    const allComplete = tasks.length > 0 && tasks.every((task) => {
      const taskStatus = String(task?.status || "").toLowerCase();
      return ["complete", "completed", "done", "success"].includes(taskStatus);
    });
    const hasBlockedTask = tasks.some((task) => {
      const taskStatus = String(task?.status || "").toLowerCase();
      if (["blocked", "failed", "error"].includes(taskStatus)) return true;
      if (["complete", "completed", "done", "success"].includes(taskStatus)) return false;
      return taskSteps(task).some((step) => ["blocked", "failed", "error"].includes(String(step?.status || "").toLowerCase()));
    });
    const blockedTask = tasks.find((task) => {
      const taskStatus = String(task?.status || "").toLowerCase();
      if (["blocked", "failed", "error"].includes(taskStatus)) return true;
      if (["complete", "completed", "done", "success"].includes(taskStatus)) return false;
      return taskSteps(task).some((step) => ["blocked", "failed", "error"].includes(String(step?.status || "").toLowerCase()));
    });

    if (hasBlockedTask) status = "Blocked";
    if (allComplete && !rawStatus) status = "Complete";
    if (!rawStatus && tasks.length === 0) status = "Ready";

    if (label) label.textContent = `Execution · ${status}`;
    if (body) {
      if (status === "Blocked") {
        const blockedStep = taskSteps(blockedTask)
          .find((step) => ["blocked", "failed", "error"].includes(String(step?.status || "").toLowerCase()));
        body.textContent = formatError("execution", execution.error || execution.blocker || state.error || blockedTask?.blocker || blockedTask?.error || blockedTask?.last_error || blockedStep?.blocker || blockedStep?.error || "blocked");
      } else if (status === "Complete") {
        body.textContent = "All planned project work is complete.";
      } else if (status === "Needs approval") {
        body.textContent = "Review the pending work, then approve it to continue.";
      } else if (status === "Needs attention") {
        body.textContent = "Nova couldn't confirm this project's execution state. Refresh the project before continuing.";
      } else if (status === "Running") {
        body.textContent = "Nova is working on this project.";
      } else if (status === "Paused") {
        body.textContent = "Project work is paused and can be continued.";
      } else if (!tasks.length) {
        body.textContent = "Add project tasks before starting execution.";
      } else {
        body.textContent = "Planned project work is ready to continue.";
      }
    }

    const hasTasks = tasks.length > 0;
    if (status === "Ready" && hasTasks) {
      setButtonVisible(executionButtons.continue, true);
      setButtonVisible(executionButtons.runAll, true);
      setButtonVisible(executionButtons.next, true);
      setButtonVisible(executionButtons.reset, true);
    } else if (status === "Paused") {
      setButtonVisible(executionButtons.continue, true);
      setButtonVisible(executionButtons.next, true);
      setButtonVisible(executionButtons.reset, true);
    } else if (status === "Running") {
      setButtonVisible(executionButtons.pause, true);
      setButtonVisible(executionButtons.stop, true);
    } else if (status === "Needs approval") {
      setButtonVisible(executionButtons.approve, true);
      setButtonVisible(executionButtons.stop, true);
      setButtonVisible(executionButtons.reset, true);
    } else if (status === "Blocked") {
      setButtonVisible(executionButtons.reset, true);
    }
    setButtonVisible(executionButtons.reset, hasTasks && status !== "Running");
  }

  window.NovaDesktopUX = { formatError, renderExecution, statusLabel };
})();
