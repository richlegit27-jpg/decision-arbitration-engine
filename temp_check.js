(function () {
console.log("[NOVA CHAT STREAM LOADED - INPUT FIX TEST]");
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.chatStream = Nova.chatStream || {};
  Nova.chat = Nova.chat || {};

  const CONFIG = {
    stateEndpoint: "/api/state",
    chatEndpoint: "/api/chat",
    sessionNewEndpoint: "/api/session/new",
    sessionGetBase: "/api/chat/",
    defaultModel: "gpt-5.4",
  };

const state = Object.assign(

  Nova.state || {},
  {
    activeSessionId: null,
    sessions: [],
    messages: [],
    models: [],
    selectedModel: null,
    isSending: false,
    pendingAttachments: [],
    booted: false,
  }
);

Nova.state = Nova.state || state;

  const els = {};

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function uid(prefix = "id") {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;