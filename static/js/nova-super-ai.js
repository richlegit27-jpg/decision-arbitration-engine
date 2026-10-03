(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const state = {
    sessions: [],
    sessionId: "",
    projectId: "",
    model: "",
    lastPrompt: "",
    abortController: null,
    assistantNode: null,
    stopped: false,
  };

  function unwrap(payload) {
    return payload && typeof payload.data === "object" ? payload.data : payload;
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
      headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) },
    });
    const text = await response.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (_) { throw new Error("Nova returned an unreadable response."); }
    const data = unwrap(body);
    if (!response.ok || body.ok === false || data?.ok === false) {
      throw new Error(data?.error || data?.message || body.error || body.message || `Request failed (${response.status}).`);
    }
    return { body, data };
  }

  function setConnection(text, status = "ready") {
    const el = $("connectionState");
    el.textContent = text;
    el.dataset.state = status;
  }

  function setError(message) {
    const el = $("composerError");
    el.textContent = message || "";
    el.hidden = !message;
  }

  function escapeText(value) {
    return String(value ?? "");
  }

  function renderMessage(message, options = {}) {
    const empty = $("emptyState");
    if (empty) empty.remove();
    const role = message.role === "user" ? "user" : "assistant";
    const wrap = document.createElement("article");
    wrap.className = "message";
    wrap.dataset.role = role;
    const label = document.createElement("div");
    label.className = "message-role";
    label.textContent = role === "user" ? "YOU" : "NOVA";
    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = escapeText(message.content || message.text || "");
    wrap.append(label, content);
    const attachments = Array.isArray(message.attachments) ? message.attachments : [];
    for (const item of attachments) {
      const name = typeof item === "string" ? item : (item.name || item.filename || item.url || "Attachment");
      const line = document.createElement("small");
      line.className = "message-meta";
      line.textContent = `Attachment: ${name}`;
      content.append(document.createElement("br"), line);
    }
    if (options.error) wrap.classList.add("message-error");
    $("messageList").appendChild(wrap);
    $("messageList").scrollTop = $("messageList").scrollHeight;
    return { wrap, content };
  }

  function normalizedSessionId(session) {
    return String(session?.id || session?.session_id || session?.client_session_id || "").trim();
  }

  async function loadSessionList() {
    const { data } = await api("/api/sessions");
    state.sessions = Array.isArray(data.sessions) ? data.sessions : (Array.isArray(data.items) ? data.items : []);
    const list = $("sessionList");
    list.replaceChildren();
    if (!state.sessions.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No saved conversations yet.";
      list.appendChild(empty);
      return;
    }
    for (const session of state.sessions) {
      const id = normalizedSessionId(session);
      if (!id) continue;
      const button = document.createElement("button");
      button.className = "session-item";
      button.type = "button";
      button.setAttribute("aria-current", id === state.sessionId ? "true" : "false");
      const title = document.createElement("span");
      title.className = "session-title";
      title.textContent = session.title || session.name || "New conversation";
      const meta = document.createElement("span");
      meta.className = "session-meta";
      meta.textContent = session.updated_at ? new Date(session.updated_at).toLocaleDateString() : "Saved session";
      button.append(title, meta);
      button.addEventListener("click", () => selectSession(id));
      list.appendChild(button);
    }
  }

  async function loadSession(id) {
    const { data } = await api(`/api/sessions/${encodeURIComponent(id)}`);
    const session = data.session || data;
    state.sessionId = normalizedSessionId(session) || id;
    localStorage.setItem("nova.super_ai.session", state.sessionId);
    $("conversationTitle").textContent = session.title || session.name || "Conversation";
    $("messageList").replaceChildren();
    const messages = Array.isArray(session.messages) ? session.messages : [];
    for (const message of messages) renderMessage({ ...message, content: message.content ?? message.text });
    state.lastPrompt = [...messages].reverse().find((message) => message.role === "user")?.content || [...messages].reverse().find((message) => message.role === "user")?.text || "";
    if (!messages.length) showEmptyState();
    await loadSessionList();
    $("retryBtn").disabled = !state.lastPrompt;
  }

  function showEmptyState() {
    const empty = document.createElement("div");
    empty.id = "emptyState";
    empty.className = "empty-state";
    empty.innerHTML = '<div class="orb" aria-hidden="true">✦</div><h2>What are we working on?</h2><p>Ask a question, explore an idea, or turn a goal into an executable project.</p>';
    $("messageList").appendChild(empty);
  }

  async function selectSession(id) {
    setError("");
    try {
      await loadSession(id);
    } catch (error) {
      setError(error.message);
    }
  }

  async function createSession() {
    const { data } = await api("/api/sessions/new", { method: "POST", body: JSON.stringify({ title: "New Chat" }) });
    const session = data.session || data.item || data;
    const id = normalizedSessionId(session) || data.active_session_id || data.session_id;
    if (!id) throw new Error("Nova did not return the new conversation ID.");
    await loadSessionList();
    await loadSession(id);
    $("composerInput").focus();
  }

  async function loadModels() {
    const { data } = await api("/api/models");
    const models = Array.isArray(data.models) ? data.models : [];
    const details = Array.isArray(data.model_details) ? data.model_details : [];
    const select = $("modelSelect");
    select.replaceChildren();
    if (!models.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No model provider available";
      select.appendChild(option);
      select.disabled = true;
      state.model = "";
      setError("No model is currently invocable. Configure a supported provider and its server-side client to start a conversation.");
      $("sendBtn").disabled = true;
      return;
    }
    select.disabled = false;
    for (const id of models) {
      const detail = details.find((item) => item.id === id);
      const option = document.createElement("option");
      option.value = id;
      option.textContent = detail?.label || id;
      option.title = detail?.description || id;
      select.appendChild(option);
    }
    const saved = localStorage.getItem("nova.super_ai.model");
    state.model = models.includes(saved) ? saved : (data.default_model && models.includes(data.default_model) ? data.default_model : models[0]);
    select.value = state.model;
  }

  async function consumeStream(response, assistantContent) {
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Chat request failed (${response.status}).`);
    }
    if (!response.body) throw new Error("This browser cannot read Nova's chat stream.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let gotDone = false;
    let gotError = "";
    const handleBlock = (block) => {
      const raw = block.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
      if (!raw) return;
      let event;
      try { event = JSON.parse(raw); } catch (_) { return; }
      if (event.type === "token") {
        assistantContent.textContent += event.content || "";
        $("messageList").scrollTop = $("messageList").scrollHeight;
      } else if (event.type === "message") {
        assistantContent.textContent = event.content || assistantContent.textContent;
      } else if (event.type === "error") {
        gotError = event.content || "Nova could not complete this response.";
      } else if (event.type === "done") {
        gotDone = true;
        if (!assistantContent.textContent && event.assistant_message?.text) assistantContent.textContent = event.assistant_message.text;
      }
    };
    while (!gotDone) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        handleBlock(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (gotDone) break;
      }
      if (gotError) break;
    }
    if (gotError) throw new Error(gotError);
    if (!gotDone) throw new Error("Nova's response stream ended before completion.");
  }

  async function sendMessage(prompt, regenerate = false) {
    const text = String(prompt || "").trim();
    if (!text || state.abortController) return;
    if (!state.model) { setError("No configured model is currently available."); return; }
    setError("");
    if (!state.sessionId) await createSession();
    state.lastPrompt = text;
    state.stopped = false;
    if (!regenerate) renderMessage({ role: "user", content: text });
    const { content, wrap } = renderMessage({ role: "assistant", content: "" });
    content.textContent = "Thinking…";
    state.assistantNode = content;
    state.abortController = new AbortController();
    $("sendBtn").disabled = true;
    $("stopBtn").hidden = false;
    $("streamNotice").hidden = false;
    setConnection("Working", "busy");
    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ content: text, session_id: state.sessionId, model: state.model, regenerate }),
        signal: state.abortController.signal,
      });
      content.textContent = "";
      await consumeStream(response, content);
      setConnection(state.model ? "Ready" : "No model available", state.model ? "ready" : "error");
      await Promise.allSettled([loadSessionList(), refreshArtifacts()]);
      $("retryBtn").disabled = false;
    } catch (error) {
      if (error.name === "AbortError") {
        state.stopped = true;
        content.textContent = "Response view stopped. The server may have completed this request; reload the conversation to check its saved result.";
        wrap.classList.add("message-error");
        setConnection("Stopped", "ready");
      } else {
        content.textContent = error.message;
        wrap.classList.add("message-error");
        setConnection("Chat error", "error");
      }
      $("retryBtn").disabled = false;
    } finally {
      state.abortController = null;
      state.assistantNode = null;
      $("sendBtn").disabled = false;
      $("stopBtn").hidden = true;
      $("streamNotice").hidden = true;
    }
  }

  async function loadMemory() {
    const list = $("memoryList");
    try {
      const { data } = await api("/api/memory");
      const items = Array.isArray(data.memory) ? data.memory : (Array.isArray(data.items) ? data.items : []);
      list.replaceChildren();
      if (!items.length) {
        const empty = document.createElement("div"); empty.className = "muted"; empty.textContent = "No saved memory yet."; list.appendChild(empty); return;
      }
      for (const item of items.slice(0, 12)) {
        const node = document.createElement("div"); node.className = "context-item";
        node.textContent = item.text || item.content || item.title || "Saved context";
        list.appendChild(node);
      }
    } catch (error) { list.textContent = `Memory unavailable: ${error.message}`; }
  }

  async function refreshArtifacts() {
    const list = $("artifactList");
    try {
      const { data } = await api("/api/artifacts");
      const items = Array.isArray(data.artifacts) ? data.artifacts : (Array.isArray(data.items) ? data.items : []);
      list.replaceChildren();
      if (!items.length) { const empty = document.createElement("div"); empty.className = "muted"; empty.textContent = "No generated artifacts yet."; list.appendChild(empty); return; }
      for (const item of items.slice(0, 10)) {
        const node = document.createElement("div"); node.className = "context-item";
        const label = item.name || item.filename || item.title || "Generated artifact";
        const id = item.id || item.artifact_id;
        if (id) { const link = document.createElement("a"); link.href = `/api/artifacts/${encodeURIComponent(id)}`; link.target = "_blank"; link.rel = "noopener"; link.textContent = label; node.appendChild(link); }
        else node.textContent = label;
        list.appendChild(node);
      }
    } catch (error) { list.textContent = `Artifacts unavailable: ${error.message}`; }
  }

  function normalizeExecution(value) {
    if (value?.execution && typeof value.execution === "object") return value.execution;
    if (value?.state && typeof value.state === "object") return value.state;
    return value || {};
  }

  function renderExecution(value) {
    const execution = normalizeExecution(value);
    const status = String(execution.status || "pending").toLowerCase();
    const statusEl = $("executionStatus");
    statusEl.dataset.status = status;
    statusEl.replaceChildren();
    const dot = document.createElement("span"); dot.className = "status-dot";
    const label = document.createElement("span"); label.textContent = `${status}${execution.current_step ? ` · ${execution.current_step}` : ""}${execution.error ? ` · ${execution.error}` : ""}`;
    statusEl.append(dot, label);
    const steps = Array.isArray(execution.steps) ? execution.steps : [];
    const list = $("executionSteps"); list.replaceChildren();
    for (const [index, step] of steps.entries()) {
      const node = document.createElement("div"); node.className = "execution-step"; node.dataset.status = String(step.status || "pending");
      node.textContent = `${index + 1}. ${step.title || step.action || "Step"} · ${step.status || "pending"}`;
      if (step.error || step.result || step.output) { const detail = document.createElement("small"); detail.textContent = String(step.error || step.result || step.output); node.appendChild(detail); }
      list.appendChild(node);
    }
  }

  async function refreshProjects(preferredId = "") {
    const [{ data: projectsData }, { data: activeData }] = await Promise.all([api("/api/projects"), api("/api/projects/active")]);
    const projects = Array.isArray(projectsData.projects) ? projectsData.projects : [];
    const activeId = preferredId || activeData.project?.id || projects.find((project) => project.active)?.id || "";
    const select = $("projectSelect"); select.replaceChildren();
    const none = document.createElement("option"); none.value = ""; none.textContent = projects.length ? "Choose a project" : "No projects yet"; select.appendChild(none);
    for (const project of projects) { const option = document.createElement("option"); option.value = project.id; option.textContent = project.name || project.title || "Untitled project"; select.appendChild(option); }
    state.projectId = projects.some((project) => project.id === activeId) ? activeId : "";
    select.value = state.projectId;
    $("runProjectBtn").disabled = !state.projectId;
    $("continueProjectBtn").disabled = !state.projectId;
    $("stopProjectBtn").disabled = !state.projectId;
    if (state.projectId) await refreshExecution();
    else { $("executionStatus").textContent = projects.length ? "Select a project to view execution." : "Create a project plan to begin."; $("executionSteps").replaceChildren(); }
  }

  async function refreshExecution() {
    if (!state.projectId) return;
    const { data } = await api(`/api/projects/${encodeURIComponent(state.projectId)}/execution`);
    renderExecution(data);
  }

  async function controlExecution(action) {
    if (!state.projectId) return;
    ["runProjectBtn", "continueProjectBtn", "stopProjectBtn"].forEach((id) => { $(id).disabled = true; });
    try {
      await api(`/api/projects/${encodeURIComponent(state.projectId)}/execution/control`, { method: "POST", body: JSON.stringify({ action }) });
      await Promise.all([refreshExecution(), refreshArtifacts()]);
    } catch (error) {
      $("executionStatus").textContent = `Execution action failed: ${error.message}`;
    } finally {
      $("runProjectBtn").disabled = !state.projectId;
      $("continueProjectBtn").disabled = !state.projectId;
      $("stopProjectBtn").disabled = !state.projectId;
    }
  }

  async function createProjectPlan() {
    const goal = $("planGoal").value.trim();
    if (!goal) { $("planStatus").textContent = "Describe a project goal first."; return; }
    $("planBtn").disabled = true;
    $("planStatus").textContent = "Building a plan and saving executable tasks…";
    $("planList").replaceChildren();
    try {
      const { data } = await api("/api/projects/new", { method: "POST", body: JSON.stringify({ name: goal.slice(0, 80), description: goal, session_id: state.sessionId }) });
      const project = data.project;
      const plan = data.builder_result?.plan || project?.plan || {};
      const tasks = Array.isArray(plan.tasks) ? plan.tasks : (Array.isArray(project?.tasks) ? project.tasks : []);
      if (!project?.id) throw new Error("The project service returned no saved project.");
      const title = document.createElement("strong"); title.className = "context-item"; title.textContent = project.name || project.title || "Project plan"; $("planList").appendChild(title);
      for (const task of tasks) { const item = document.createElement("div"); item.className = "context-item"; item.textContent = task.title || task.name || task.description || "Planned task"; $("planList").appendChild(item); }
      if (!tasks.length) { const note = document.createElement("div"); note.className = "muted"; note.textContent = "The project is saved, but no tasks were returned."; $("planList").appendChild(note); }
      $("planStatus").textContent = `${tasks.length} saved task${tasks.length === 1 ? "" : "s"} · project ${project.id}`;
      await refreshProjects(project.id);
      await refreshArtifacts();
    } catch (error) { $("planStatus").textContent = `Planning failed: ${error.message}`; }
    finally { $("planBtn").disabled = false; }
  }

  async function initialize() {
    setConnection("Loading");
    try {
      await loadModels();
      const savedId = localStorage.getItem("nova.super_ai.session") || "";
      await loadSessionList();
      const exists = state.sessions.some((item) => normalizedSessionId(item) === savedId);
      if (exists) await loadSession(savedId);
      else if (state.sessions.length) await loadSession(normalizedSessionId(state.sessions[0]));
      else await createSession();
      setConnection(state.model ? "Ready" : "No model available", state.model ? "ready" : "error");
    } catch (error) {
      setConnection("Unavailable", "error");
      setError(error.message);
    }
    await Promise.allSettled([loadMemory(), refreshArtifacts(), refreshProjects()]);
  }

  $("composerForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("composerInput");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendMessage(text);
  });
  $("composerInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("composerForm").requestSubmit(); }
  });
  $("stopBtn").addEventListener("click", () => state.abortController?.abort());
  $("retryBtn").addEventListener("click", () => state.lastPrompt && sendMessage(state.lastPrompt, true));
  $("newSessionBtn").addEventListener("click", () => createSession().catch((error) => setError(error.message)));
  $("modelSelect").addEventListener("change", async (event) => {
    const requested = event.target.value;
    try {
      const { data } = await api("/api/models/select", { method: "POST", body: JSON.stringify({ model: requested }) });
      state.model = data.selected_model || requested;
      localStorage.setItem("nova.super_ai.model", state.model);
      event.target.value = state.model;
    } catch (error) { setError(error.message); }
  });
  $("planBtn").addEventListener("click", createProjectPlan);
  $("refreshMemoryBtn").addEventListener("click", loadMemory);
  $("refreshArtifactsBtn").addEventListener("click", refreshArtifacts);
  $("refreshExecutionBtn").addEventListener("click", () => refreshExecution().catch((error) => { $("executionStatus").textContent = error.message; }));
  $("projectSelect").addEventListener("change", async (event) => {
    state.projectId = event.target.value;
    if (state.projectId) {
      try { await api(`/api/projects/${encodeURIComponent(state.projectId)}/activate`, { method: "POST", body: "{}" }); } catch (_) { /* fetch persisted state below */ }
    }
    await refreshProjects(state.projectId).catch((error) => { $("executionStatus").textContent = error.message; });
  });
  $("runProjectBtn").addEventListener("click", () => controlExecution("run_all"));
  $("continueProjectBtn").addEventListener("click", () => controlExecution("continue"));
  $("stopProjectBtn").addEventListener("click", () => controlExecution("stop"));
  $("mobileSessionsToggle").addEventListener("click", () => $("sessionRail").classList.toggle("mobile-open"));
  document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => { $("composerInput").value = button.dataset.prompt; $("composerInput").focus(); }));
  initialize();
})();
