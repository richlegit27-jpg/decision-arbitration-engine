
(function () {
  "use strict";

  // NOVA_MANAGE_CURRENT_SESSION_PANEL_20260610

function getCurrentSessionId() {
  return (
    localStorage.getItem("nova_active_session_id") ||
    localStorage.getItem("nova.session_id") ||
    localStorage.getItem("nova_session_id") ||
    localStorage.getItem("nova_desktop_active_session_id") ||
    ""
  ).trim();
}

  function setStatus(text) {
    var status = document.getElementById("nova-current-session-manager-status");
    if (status) status.textContent = text || "";
  }

  async function postJson(url, payload) {
    var response = await fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload || {})
    });

const raw = await response.text();

let data = {};
try {
  data = JSON.parse(raw);
} catch (e) {
  console.warn("Non-JSON response:", raw);
}

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.message || "Request failed");
    }

    return data;
  }

  async function getCurrentSession() {
    var sid = getCurrentSessionId();

    if (!sid) {
      throw new Error("No current session selected.");
    }

    var response = await fetch("/api/sessions/" + encodeURIComponent(sid), {
      headers: { "Accept": "application/json" }
    });

const raw = await response.text();

var data = {};
try {
  data = JSON.parse(raw);
} catch (e) {
  console.warn("Non-JSON response:", raw);
}
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.message || "Could not load current session.");
    }

    return data.session || data.data || data;
  }

  async function refreshSessionsIfPossible() {
    try {
      if (typeof window.loadDesktopSessions === "function") {
        await window.loadDesktopSessions();
      }

    } catch (error) {}

    try {
      if (typeof window.NovaDesktopOpenSessionsRescue === "function") {
        await window.NovaDesktopOpenSessionsRescue();
      }
    } catch (error) {}
  }

  async function renameCurrentSession() {
    try {
      var session = await getCurrentSession();
      var sid = session.id || getCurrentSessionId();
      var oldTitle = session.title || "Session";
      var nextTitle = prompt("Rename current session:", oldTitle);

      if (!nextTitle) return;

      nextTitle = String(nextTitle).trim();
      if (!nextTitle || nextTitle === oldTitle) return;

      await postJson("/api/sessions/rename", {
        session_id: sid,
        title: nextTitle
      });

      setStatus("Renamed to: " + nextTitle);
      await refreshSessionsIfPossible();
    } catch (error) {
      setStatus(error.message || "Rename failed.");
    }
  }

  async function togglePinCurrentSession() {
    try {
      var session = await getCurrentSession();
      var sid = session.id || getCurrentSessionId();
      var nextPinned = !Boolean(session.pinned);

      await postJson("/api/sessions/pin", {
        session_id: sid,
        pinned: nextPinned
      });

      setStatus(nextPinned ? "Pinned current session." : "Unpinned current session.");
      await refreshSessionsIfPossible();
    } catch (error) {
      setStatus(error.message || "Pin failed.");
    }
  }

  async function deleteCurrentSession() {
    try {
      var session = await getCurrentSession();
      var sid = session.id || getCurrentSessionId();
      var title = session.title || sid;

      if (!confirm("Delete current session?\n\n" + title)) return;

      var result = await postJson("/api/sessions/delete", {
        session_id: sid
      });

      var nextId = result && result.active_session_id ? result.active_session_id : "";

localStorage.removeItem("nova_desktop_session_id");
localStorage.removeItem("nova_desktop_active_session_id");
localStorage.removeItem("session_id");
localStorage.removeItem("active_session_id");

      if (nextId) {
        localStorage.setItem("nova.session_id", nextId);
        localStorage.setItem("nova_session_id", nextId);
        localStorage.setItem("nova_active_session_id", nextId);

        var sidInput = document.getElementById("sid");
        if (sidInput) sidInput.value = nextId;

        if (typeof window.NovaDesktopFetchSession === "function") {
          await window.NovaDesktopFetchSession(nextId);
        }
      } else {
        localStorage.removeItem("nova.session_id");
        localStorage.removeItem("nova_session_id");
        localStorage.removeItem("nova_active_session_id");

        var chat = document.getElementById("chat");
        if (chat) chat.innerHTML = "";
      }

      setStatus("Deleted session: " + title);
      await refreshSessionsIfPossible();

    } catch (error) {
      setStatus(error.message || "Delete failed.");
    }
  }

  function installManager() {
    if (document.getElementById("nova-current-session-manager")) return;

var host =
      document.querySelector(".session-current-card") ||
      document.querySelector(".session-list-shell") ||
      document.querySelector("aside") ||
      document.querySelector(".sidebar") ||
      document.querySelector(".side-panel") ||
      document.querySelector(".panel") ||
      document.body;

    var box = document.createElement("div");
    box.id = "nova-current-session-manager";

box.innerHTML =
  '<div id="nova-current-session-manager-title">Manage current session</div>' +
'<div class="nova-current-session-manager-row">' +
  '<button id="nova-manage-rename-session" class="nova-current-session-manager-btn" type="button">Rename</button>' +
  '<button id="nova-manage-pin-session" class="nova-current-session-manager-btn" type="button">Pin/Unpin</button>' +
  '<button id="nova-manage-delete-session" class="nova-current-session-manager-btn" type="button">Delete</button>' +
'</div>' +
'<div id="nova-delete-all-sessions-panel">' +
  '<button id="nova-manage-delete-all-sessions" class="nova-current-session-manager-btn" type="button">Delete All Conversations</button>' +
'</div>' +
  '</div>' +
  '<div id="nova-current-session-manager-status"></div>';

    if (host.firstChild) {
      host.insertBefore(box, host.firstChild);
    } else {
      host.appendChild(box);
    }

    document.getElementById("nova-manage-rename-session").onclick = renameCurrentSession;
    document.getElementById("nova-manage-pin-session").onclick = togglePinCurrentSession;
    document.getElementById("nova-manage-delete-session").onclick = deleteCurrentSession;
    document.getElementById("nova-manage-delete-all-sessions").onclick =
      deleteAllSessions;

    console.log("[Nova Current Session Manager] ready");
  }

async function deleteAllSessions() {
  if (!confirm("Delete all conversations?\n\nThis cannot be undone.")) {
    return;
  }

  try {
    await postJson("/api/sessions/delete-all", {});

    localStorage.removeItem("nova.session_id");
    localStorage.removeItem("nova_session_id");
    localStorage.removeItem("nova_active_session_id");

    if (typeof window.loadDesktopSessions === "function") {
      await window.loadDesktopSessions();
    }

    setStatus("All conversations deleted.");
  } catch (error) {
    console.warn("[delete all sessions failed]", error);
    setStatus("Delete all failed.");
  }
}

  installManager();

  window.NovaInstallCurrentSessionManager = installManager;
})();
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function memorySection() {
    return document.querySelector(".tools-section.memory-section");
  }

  function memoryList() {
    return $("desktopMemoryList");
  }

  function memoryMetric() {
    var section = memorySection();
    return section ? section.querySelector(".metric") : null;
  }

  function normalizeMemoryItems(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;

    if (payload.data) {
      if (Array.isArray(payload.data.memory)) return payload.data.memory;
      if (Array.isArray(payload.data.items)) return payload.data.items;
      if (Array.isArray(payload.data.memories)) return payload.data.memories;
    }

    if (Array.isArray(payload.memory)) return payload.memory;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.memories)) return payload.memories;

    return [];
  }

  function itemText(item) {
    if (!item) return "";
    if (typeof item === "string") return item;

    return String(
      item.text ||
      item.content ||
      item.value ||
      item.memory ||
      item.summary ||
      JSON.stringify(item)
    );
  }

 
  function setVisible() {
    var section = memorySection();
    var list = memoryList();

    if (section) {
      section.style.display = "block";
      section.style.visibility = "visible";
      section.style.opacity = "1";
      section.style.width = "100%";
      section.style.minHeight = "220px";
    }

    if (list) {
      list.style.display = "grid";
      list.style.visibility = "visible";
      list.style.opacity = "1";
      list.style.width = "100%";
      list.style.minHeight = "180px";
    }
  }

  function renderMemory(payload) {
    var list = memoryList();
    var metric = memoryMetric();
    var items = normalizeMemoryItems(payload);

    setVisible();

var countEl = document.getElementById("desktopMemoryCount");
if (countEl) {
  countEl.textContent = String(items.length);
}

    if (!list) {
      console.warn("[Nova Desktop Memory Final Renderer] #desktopMemoryList not found");
      return;
    }

    list.innerHTML = "";

        if (!items.length) {
          var empty = document.createElement("div");
          empty.className = "session-placeholder";
          empty.innerHTML = [
            "<strong>No memory items yet.</strong>",
            "<br>",
            "<span>Saved facts, preferences, and project notes will show here.</span>"
          ].join("");
          list.appendChild(empty);
          return;
        }
      }


      function loadDesktopMemory() {

        var list = memoryList();

        setVisible();

        if (list) {
          list.innerHTML = '<div class="session-placeholder">Loading memory...</div>';
        }

        fetch("/api/memory", { cache: "no-store" })
          .then(async function (response) {
            const raw = await response.text();

            let data = null;

            try {
              data = JSON.parse(raw);
            } catch (e) {
              console.warn("Non-JSON response from /api/memory:", raw);
            }

            return data;
          })
          .then(function (payload) {
            renderMemory(payload);
          })
          .catch(function (error) {
            console.error("[Nova Desktop Memory Final Renderer] failed", error);

            if (list) {
              list.innerHTML =
                '<div class="session-placeholder">Memory failed to load.</div>';
            }
          });
      }


  function wire() {
    var button = $("openMemoryBtn");
    if (!button || button.dataset.novaMemoryFinalWired === "true") return;

    button.dataset.novaMemoryFinalWired = "true";
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      loadDesktopMemory();
    }, true);
  }

window.NovaOpenDesktopMemoryLegacy = window.loadDesktopMemoryLegacy;
window.NovaDesktopOpenMemoryRescueLegacy = window.loadDesktopMemoryLegacy;
window.NovaLoadMemoryLegacy = window.loadDesktopMemoryLegacy;
window.loadMemoryLegacy = window.loadDesktopMemoryLegacy;
window.loadMemoriesLegacy = window.loadDesktopMemoryLegacy;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }

  setTimeout(wire, 500);
  setTimeout(wire, 1500);

  console.log("[Nova Desktop Memory Final Renderer] ready");
})();
(function () {
  "use strict";

function executionSection() {
    return document.querySelector("#nova-desktop-execution-native");
}
  function executionNote() {
    return document.getElementById("executionNote");
  }

  function executionMetrics() {
    var section = executionSection();
    return section ? Array.from(section.querySelectorAll(".metric")) : [];
  }

  function setMetric(metric, label, value) {
    if (!metric) return;
    metric.innerHTML = [
      '<span style="opacity:.72;font-size:12px;">' + label + '</span>',
      '<strong style="font-size:18px;">' + value + '</strong>'
    ].join("");
  }

  function renderExecution(payload) {
    var section = executionSection();
    var note = executionNote();
    var metrics = executionMetrics();

    if (!section) {
      console.warn("[Nova Desktop Execution Final Renderer] execution section not found");
      return;
    }

    section.style.display = "block";
    section.style.visibility = "visible";
    section.style.opacity = "1";
    section.hidden = false;
    section.removeAttribute("hidden");

    var overall = payload.overall_backend_readiness;
    var execution = payload.execution_percent;
    var records = payload.execution_records;

    setMetric(metrics[0], "Execution", String(execution ?? 0) + "%");
    setMetric(metrics[1], "Records", String(records ?? 0));

    if (note) {
      note.innerHTML = [
        '<strong>Execution ready.</strong>',
        '<br>',
        '<span>Overall backend readiness: ' + String(overall ?? 0) + '%</span>',
        '<br>',
        '<span>Planner: ' + String(payload.planner_percent ?? 0) + '% Â· Memory: ' + String(payload.memory_percent ?? 0) + '% Â· Sessions: ' + String(payload.session_percent ?? 0) + '%</span>'
      ].join("");
    }
  }

  function loadDesktopExecution() {
    var note = executionNote();
    if (note) {
      note.textContent = "Loading execution status...";
    }

fetch("/api/backend/readiness", { cache: "no-store" })
  .then(async function (response) {
    const raw = await response.text();

    let data = null;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      console.warn("Non-JSON response from /api/backend/readiness:", raw);
    }

    return data;
  })

      .then(function (payload) {
        renderExecution(payload || {});
      })
      .catch(function (error) {
        console.error("[Nova Desktop Execution Final Renderer] failed", error);
        var note = executionNote();
        if (note) {
          note.textContent = "Execution failed to load. Check console/server log.";
        }
      });
  }

  window.NovaLoadDesktopExecution = loadDesktopExecution;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadDesktopExecution);
  } else {
    loadDesktopExecution();
  }

  setTimeout(loadDesktopExecution, 500);

  console.log("[Nova Desktop Execution Final Renderer] ready");
})();
(function () {
  "use strict";

  function list() {
    return document.getElementById("desktopMemoryList");
  }

  function metric() {
    var section = document.querySelector(".tools-section.memory-section");
    return section ? section.querySelector(".metric") : null;
  }

  function normalize(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (payload.data && Array.isArray(payload.data.memory)) return payload.data.memory;
    if (payload.data && Array.isArray(payload.data.items)) return payload.data.items;
    if (Array.isArray(payload.memory)) return payload.memory;
    if (Array.isArray(payload.items)) return payload.items;
    return [];
  }

function render(payload) {
  var box = list();
  var countEl = document.getElementById("desktopMemoryCount");
  if (!box) return;

  var rawItems = normalize(payload);

  if (countEl) countEl.textContent = String(rawItems.length);

  function itemText(item) {
    return String(
      item.text ||
      item.content ||
      item.value ||
      item.memory ||
      item.summary ||
      item.note ||
      JSON.stringify(item)
    );
  }

  function itemType(item, text) {
    return String(
      item.type ||
      item.kind ||
      item.category ||
      item.tag ||
      ""
    ).toLowerCase() || text.toLowerCase();
  }

  function priority(item) {
    var text = itemText(item).toLowerCase();
    var type = itemType(item, text);

    if (item.pinned || text.includes("[pinned]")) return 1000;
    if (type.includes("project_state") || text.includes("current task") || text.includes("blocker") || text.includes("active file") || text.includes("last checkpoint")) return 900;
    if (type.includes("project_focus") || text.includes("current project focus")) return 850;
    if (type.includes("preference") || text.includes("[preference]")) return 700;
    if (type.includes("project")) return 650;

    return 100;
  }

  function cleanText(text) {
    return String(text || "")
      .replace(/\n{3,}/g, "\n\n")
      .trim()
      .slice(0, 360);
  }

  var seen = {};
  var items = rawItems
    .filter(function (item) {
      var key = cleanText(itemText(item)).toLowerCase();
      if (!key || seen[key]) return false;
      seen[key] = true;
      return true;
    })
    .sort(function (a, b) {
      return priority(b) - priority(a);
    });

  box.innerHTML = "";

  if (!items.length) {
    var empty = document.createElement("div");
    empty.className = "session-placeholder";
    empty.innerHTML = "<strong>No memory items yet.</strong><br><span>Saved facts, preferences, and project notes will show here.</span>";
    box.appendChild(empty);
    return;
  }

  items.slice(0, 40).forEach(function (item) {
    var text = cleanText(itemText(item));
    var type = itemType(item, text);

    var row = document.createElement("div");
    row.className = "memory-item";
    row.style.cssText = "padding:10px 12px;border:1px solid rgba(255,255,255,.12);border-radius:12px;margin-bottom:10px;white-space:pre-wrap;word-break:break-word;";

    var label = document.createElement("div");
    label.style.cssText = "font-size:11px;opacity:.7;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;";
    label.textContent =
      priority(item) >= 900 ? "PROJECT STATE" :
      priority(item) >= 850 ? "PROJECT FOCUS" :
      priority(item) >= 700 ? "PREFERENCE" :
      type ? type.slice(0, 32) : "MEMORY";

    var body = document.createElement("div");
    body.textContent = text;

row.appendChild(label);
row.appendChild(body);

var id = item.memory_id || item.id || item.uuid || "";

var deleteBtn = document.createElement("button");
deleteBtn.type = "button";
deleteBtn.className = "nova-memory-delete-btn";
deleteBtn.dataset.memoryId = id;
deleteBtn.textContent = "🗑";
deleteBtn.title = "Delete memory";
deleteBtn.style.marginTop = "10px";

deleteBtn.addEventListener("click", async function () {
    if (!id) {
        console.warn("[Nova Memory] missing id");
        return;
    }

    if (!confirm("Delete this memory?")) {
        return;
    }

    try {
        const response = await fetch("/api/memory/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                id: id,
                memory_id: id
            })
        });

        console.log("[Nova Memory] delete response", await response.json());

        load();

    } catch (error) {
        console.error("[Nova Memory] delete failed", error);
    }
});

row.appendChild(deleteBtn);
box.appendChild(row);

  });
}

  function load() {
    fetch("/api/memory", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function (err) {
        console.error("[Nova Desktop Memory Hardlock] failed", err);
        var box = list();
        if (box) box.innerHTML = '<div class="session-placeholder">Memory failed to load.</div>';
      });
  }

  function hardlock() {
    var box = list();
    if (!box || box.dataset.novaMemoryHardlock === "true") return;

    box.dataset.novaMemoryHardlock = "true";

    var observer = new MutationObserver(function () {
      var text = String(box.textContent || "").trim().toLowerCase();
      if (text === "loading" || text === "loading..." || text.indexOf("loading memory") !== -1) {
        load();
      }
    });

    observer.observe(box, { childList: true, subtree: true, characterData: true });

    load();
  }

  window.NovaDesktopMemoryHardlock = load;
window.NovaOpenDesktopMemoryLegacy = load;
window.NovaDesktopOpenMemoryRescueLegacy = load;
window.NovaLoadMemoryLegacy = load;
window.loadMemoryLegacy = load;
window.loadMemoriesLegacy = load;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", hardlock);
  } else {
    hardlock();
  }

  setTimeout(hardlock, 500);
  setTimeout(hardlock, 1500);

  console.log("[Nova Desktop Memory Hardlock] ready");
})();

(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function inputBox() {
    return $("messageInput") ||
      $("desktopInput") ||
      $("promptInput") ||
      $("input") ||
      document.querySelector("textarea") ||
      document.querySelector("input[type='text']");
  }

  function sendButton() {
    return $("sendBtn") ||
      document.querySelector("button[type='submit']");
  }

  function sendPrompt(prompt) {
    var input = inputBox();
    var send = sendButton();

    if (!input) {
      console.warn("[Nova Desktop Quick Buttons] input not found");
      return;
    }

    input.value = prompt;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.focus();

    if (send) {
      send.click();
      return;
    }

    input.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Enter",
      code: "Enter",
      bubbles: true
    }));
  }

  var prompts = {
    "continue": "Continue from where we left off. Keep it direct and tell me the next move.",
    "summarize": "Summarize the current situation in plain English and tell me what matters most.",
    "improve": "Improve this and make it cleaner, more direct, and more useful.",
    "next": "What should I do next? Give me the best next step only.",
    "summarize now": "Summarize the current chat and key work completed so far."
  };

  function labelFor(button) {
    return String(
      button.textContent ||
      button.value ||
      button.getAttribute("aria-label") ||
      button.title ||
      ""
    ).trim().toLowerCase().replace(/\s+/g, " ");
  }

  function promptFor(button) {
    var label = labelFor(button);

    if (label.indexOf("summarize now") === 0) return prompts["summarize now"];
    if (label.indexOf("continue") === 0) return prompts["continue"];
    if (label.indexOf("summarize") === 0) return prompts["summarize"];
    if (label.indexOf("improve") === 0) return prompts["improve"];
    if (label.indexOf("next") === 0) return prompts["next"];

    return "";
  }

  function wire() {
    Array.from(document.querySelectorAll("button, a, [role='button']")).forEach(function (button) {
      var prompt = promptFor(button);
      if (!prompt) return;

      if (button.dataset.novaQuickButtonWired === "true") return;
      button.dataset.novaQuickButtonWired = "true";

      button.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        sendPrompt(prompt);
      }, true);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }

  setTimeout(wire, 500);
  setTimeout(wire, 1500);

  console.log("[Nova Desktop Quick Buttons Final] ready");

})();
(function () {
  "use strict";

  var recognition = null;
  var listening = false;
  var speaking = false;

  function $(id) {
    return document.getElementById(id);
  }

  function inputBox() {
    return $("messageInput") ||
      $("desktopInput") ||
      $("promptInput") ||
      $("input") ||
      document.querySelector("textarea") ||
      document.querySelector("input[type='text']");
  }

  function sendButton() {
    return $("sendBtn");
  }

  function composer() {
    var send = sendButton();
    if (send && send.parentElement) return send.parentElement;

    var attach = $("attachBtn");
    if (attach && attach.parentElement) return attach.parentElement;

    return document.querySelector(".composer") || document.body;
  }

  function latestAssistantText() {
    var chat = $("chat") || document.querySelector("#chat") || document.body;
    var candidates = Array.from(chat.querySelectorAll(".msg.assistant .bubble, .assistant .bubble, .msg.assistant, [data-role='assistant']"));

    if (!candidates.length) {
      candidates = Array.from(chat.querySelectorAll(".bubble, .msg"));
    }

    for (var i = candidates.length - 1; i >= 0; i--) {
      var text = String(candidates[i].innerText || candidates[i].textContent || "").trim();
      text = text.replace(/^ASSISTANT\s*/i, "").trim();
      if (text && text.length > 2) return text;
    }

    return "";
  }

function ensureButton(id, text, title) {
    var existing = $(id);

    if (existing) {
        existing.textContent = text;
        existing.title = title || text;
        return existing;
    }

    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = id;
    btn.textContent = text;
    btn.title = title || text;
    btn.className = "desktop-voice-tts-button";
    btn.style.cssText = "min-height:38px;padding:0 12px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.08);color:inherit;cursor:pointer;";

    var host = composer();
    var send = sendButton();

    if (send && send.parentElement === host) {
        host.insertBefore(btn, send);
    } else {
        host.appendChild(btn);
    }

    return btn;
}

function setVoiceButtonState(btn) {
  if (!btn) return;

  btn.textContent = listening
    ? "🛑 Stop Listening"
    : "🎤 Voice";

  btn.title = listening
    ? "Stop voice input"
    : "Dictate into the message box";

  btn.classList.toggle("listening", listening);
}
  function toggleVoice() {
    var btn = $("desktopVoiceBtn");

    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    if (listening && recognition) {
      recognition.stop();
      listening = false;
      setVoiceButtonState(btn);
      return;
    }

    var input = inputBox();
    if (!input) {
      alert("Message input not found.");
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onstart = function () {
      listening = true;
      setVoiceButtonState(btn);
    };

    recognition.onend = function () {
      listening = false;
      setVoiceButtonState(btn);
    };

    recognition.onerror = function (event) {
      listening = false;
      setVoiceButtonState(btn);
      console.warn("[Nova Desktop Voice] error", event);
      alert("Voice input failed or microphone permission was blocked.");
    };

    recognition.onresult = function (event) {
      var finalText = "";
      var interimText = "";

      for (var i = event.resultIndex; i < event.results.length; i++) {
        var chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += chunk;
        } else {
          interimText += chunk;
        }
      }

      var existing = String(input.value || "").trim();
      var spoken = String(finalText || interimText || "").trim();

      if (spoken) {
        input.value = existing ? existing + " " + spoken : spoken;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
      }
    };

    recognition.start();
  }

  function stopSpeech() {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {}
    speaking = false;
    var btn = $("desktopSpeakBtn");
    if (btn) {
    btn.textContent = "🔊 Speak";
    btn.title = "Read the latest assistant reply aloud";
    btn.classList.remove("speaking");
}
  }

  function toggleSpeak() {
    var btn = $("desktopSpeakBtn");

    if (!("speechSynthesis" in window)) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (speaking) {
      stopSpeech();
      return;
    }

    var text = latestAssistantText();
    if (!text) {
      alert("No assistant message found to speak.");
      return;
    }

    stopSpeech();

    var utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onstart = function () {
      speaking = true;
      if (btn) {
    btn.textContent = "⏹ Stop Speaking";
    btn.title = "Stop text-to-speech";
    btn.classList.add("speaking");
}
    };

utterance.onend = function () {
  speaking = false;

  if (btn) {
    btn.textContent = "🔊 Speak";
    btn.title = "Read the latest assistant reply aloud";
    btn.classList.remove("speaking");
  }
};

utterance.onerror = function () {
  speaking = false;

  if (btn) {
    btn.textContent = "🔊 Speak";
    btn.title = "Read the latest assistant reply aloud";
    btn.classList.remove("speaking");
  }
};
    window.speechSynthesis.speak(utterance);
  }

function wire() {
  var voice = ensureButton("desktopVoiceBtn", "🎤 Voice", "Dictate into the message box");
  var speak = ensureButton("desktopSpeakBtn", "🔊 Speak", "Read the latest assistant reply aloud");

  setVoiceButtonState(voice);

    if (voice.dataset.novaVoiceWired !== "true") {
      voice.dataset.novaVoiceWired = "true";
      voice.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        toggleVoice();
      }, true);
    }

    if (speak.dataset.novaSpeakWired !== "true") {
      speak.dataset.novaSpeakWired = "true";
      speak.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        toggleSpeak();
      }, true);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }

  setTimeout(wire, 500);
  setTimeout(wire, 1500);

  console.log("[Nova Desktop Voice/TTS Final] ready");
})();
