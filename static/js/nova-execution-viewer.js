(function (global) {
  "use strict";

  var expandedSteps = {};

  function safeStr(value) {
    return value == null ? "" : String(value);
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function escapeHtml(value) {
    return safeStr(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function titleCase(value) {
    return safeStr(value)
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, function (m) {
        return m.toUpperCase();
      });
  }

  function clampNumber(value, min, max) {
    var n = Number(value);
    if (!Number.isFinite(n)) return min;
    if (n < min) return min;
    if (n > max) return max;
    return n;
  }

  function percentFromExecution(execution) {
    execution = execution || {};
    var steps = safeArray(execution.steps);
    var completed = Number(execution.progress);

    if (!Number.isFinite(completed)) {
      completed = steps.filter(function (s) {
        return s && s.done;
      }).length;
    }

    if (!steps.length) return 0;
    return clampNumber(Math.round((completed / steps.length) * 100), 0, 100);
  }

  function currentStepIndex(execution) {
    var steps = safeArray(execution.steps);
    var current =
      Number(execution.currentIndex);

    if (!Number.isFinite(current)) {
      current = Number(execution.current_index);
    }

    if (!Number.isFinite(current)) {
      current = Number(execution.current_step_index);
    }

    if (Number.isFinite(current) && current >= 0 && current < steps.length) {
      return current;
    }

    for (var i = 0; i < steps.length; i++) {
      if (!steps[i] || !steps[i].done) return i;
    }

    return steps.length ? steps.length - 1 : 0;
  }

  function normalizeExecutionFromArtifact(artifact) {
    artifact = artifact || {};
    var meta = artifact.meta || {};
    var viewer = artifact.viewer || {};

    var execution =
      artifact.execution ||
      meta.execution ||
      viewer.execution || {
        goal: artifact.title || "",
        steps: safeArray(meta.steps),
        progress: meta.progress || 0,
      };

    var stepResults = safeArray(execution.step_results);
    var summary =
      safeStr(execution.summary) ||
      (stepResults.length
        ? safeStr(stepResults[stepResults.length - 1] && stepResults[stepResults.length - 1].output)
        : "");

    var steps = safeArray(execution.steps).map(function (step, index) {
      step = step || {};

      var logs = [];
      var matchingResult = stepResults[index] || {};

      if (Array.isArray(step.logs)) {
        logs = step.logs.map(function (l) {
          return safeStr(l);
        });
      }

      if (!logs.length && Array.isArray(matchingResult.logs)) {
        logs = matchingResult.logs.map(function (l) {
          return safeStr(l);
        });
      }

      if (!logs.length && step.result) {
        logs = [safeStr(step.result)];
      }

      if (!logs.length && matchingResult.output) {
        logs = [safeStr(matchingResult.output)];
      }

      return {
        index: index,
        title: safeStr(step.title) || ("Step " + (index + 1)),
        done: Boolean(step.done || step.status === "done"),
        logs: logs,
        status: safeStr(step.status || ""),
      };
    });

    var currentIndex = currentStepIndex({
      steps: steps,
      currentIndex: execution.currentIndex,
      current_index: execution.current_index,
      current_step_index: execution.current_step_index,
    });

    return {
      goal: safeStr(execution.goal) || "Execution",
      status: safeStr(execution.status) || "running",
      steps: steps,
      currentIndex: currentIndex,
      progress: Number(execution.progress) || 0,
      progressPercent: percentFromExecution({ steps: steps, progress: execution.progress }),
      summary: summary,
      artifactId: safeStr(artifact.id || ""),
    };
  }

  function renderStatusBadge(status) {
    var clean = safeStr(status).toLowerCase() || "running";
    return '<span class="nova-execution-status nova-execution-status--' + clean + '">' + titleCase(clean) + "</span>";
  }

  function renderProgressBar(percent) {
    percent = clampNumber(percent, 0, 100);
    return (
      '<div class="nova-execution-progress">' +
        '<div class="nova-execution-progress__bar">' +
          '<div class="nova-execution-progress__fill" style="width:' + percent + '%;"></div>' +
        "</div>" +
        '<div class="nova-execution-progress__label">' + percent + "%</div>" +
      "</div>"
    );
  }

  function stepState(step, execution) {
    var steps = safeArray(execution.steps);
    var currentIndex = execution.currentIndex;
    var isDone = !!step.done;
    var isCurrent = step.index === currentIndex && execution.status !== "complete";

    if (execution.status === "complete") {
      return isDone || step.index <= currentIndex || step.index === steps.length - 1
        ? "done"
        : "todo";
    }

    if (execution.status === "error" && isCurrent) {
      return "current";
    }

    if (isDone || step.index < currentIndex) {
      return "done";
    }

    if (isCurrent) {
      return "current";
    }

    return "todo";
  }

  function renderStep(step, execution) {
    var stateClass = stepState(step, execution);
    var stepId = "step_" + step.index;
    var isExpanded = !!expandedSteps[stepId];

    var marker = "â€¢";
    if (stateClass === "done") marker = "âœ“";
    if (stateClass === "current") marker = "âžœ";

    var metaText = "Pending";
    if (stateClass === "done") metaText = "Completed";
    if (stateClass === "current") metaText = execution.status === "error" ? "Needs attention" : "Running...";

    return (
      '<div class="nova-execution-step nova-execution-step--' + stateClass + '" data-step-id="' + stepId + '" data-current="' + (stateClass === "current" ? "1" : "0") + '">' +
        '<div class="nova-execution-step__head">' +
          '<div class="nova-execution-step__marker">' + marker + "</div>" +
          '<div class="nova-execution-step__body">' +
            '<div class="nova-execution-step__title">' + escapeHtml(step.title) + "</div>" +
            '<div class="nova-execution-step__meta">' + escapeHtml(metaText) + "</div>" +
          "</div>" +
        "</div>" +
        (
          isExpanded && step.logs.length
            ? '<div class="nova-execution-step__logs">' +
                step.logs.map(function (log, i) {
                  return '<div class="nova-execution-step__log">[' + (i + 1) + '] ' + escapeHtml(log).replace(/\n/g, "<br>") + "</div>";
                }).join("") +
              "</div>"
            : ""
        ) +
      "</div>"
    );
  }

  function renderSteps(execution) {
    var steps = safeArray(execution.steps);

    var html =
      '<div class="nova-execution-steps">' +
      steps.map(function (step) {
        return renderStep(step, execution);
      }).join("") +
      "</div>";

    setTimeout(function () {
      document.querySelectorAll(".nova-execution-step").forEach(function (el) {
        el.onclick = function () {
          var id = el.getAttribute("data-step-id");
          expandedSteps[id] = !expandedSteps[id];

          var step = steps.find(function (s) {
            return "step_" + s.index === id;
          });

          if (step) {
            el.outerHTML = renderStep(step, execution);
          }
        };
      });

      var current = document.querySelector('.nova-execution-step[data-current="1"]');
      if (current) {
        current.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 0);

    return html;
  }

  function renderExecutionViewer(artifact) {
    var execution = normalizeExecutionFromArtifact(artifact);

    return (
      '<section class="nova-execution-viewer">' +
        '<h2>' + escapeHtml(execution.goal) + "</h2>" +
        renderStatusBadge(execution.status) +
        renderProgressBar(execution.progressPercent) +
        renderSteps(execution) +
        (execution.summary
          ? '<div class="nova-execution-viewer__summary">' +
              escapeHtml(execution.summary).replace(/\n/g, "<br>") +
            "</div>"
          : "") +
      "</section>"
    );
  }

  global.NovaExecutionViewer = {
    renderExecutionViewer: renderExecutionViewer,
    normalizeExecutionFromArtifact: normalizeExecutionFromArtifact,
  };

})(window);

