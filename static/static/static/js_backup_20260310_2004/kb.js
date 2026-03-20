// KB v3 manager UI
// - lists docs + jobs
// - search with modes
// - scope selection per session (doc checkboxes)
// - view chunks
// - download, reindex, delete

function kb$(sel) { return document.querySelector(sel); }
function kbEl(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
function kbEsc(s) {
  return (s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function kbJson(url, opts) {
  const r = await fetch(url, opts || {});
  const t = await r.text();
  try { return JSON.parse(t); } catch { return { ok:false, error:t, status:r.status }; }
}

function kbGetSessionId() {
  return window.__NOVA_SESSION_ID__ || null;
}

async function kbEnsureSessionId() {
  if (window.__NOVA_SESSION_ID__) return window.__NOVA_SESSION_ID__;
  const j = await kbJson("/api/sessions");
  if (j.ok && j.sessions && j.sessions.length) {
    window.__NOVA_SESSION_ID__ = j.sessions[0].id;
    return window.__NOVA_SESSION_ID__;
  }
  const n = await kbJson("/api/sessions", { method: "POST" });
  window.__NOVA_SESSION_ID__ = n.id;
  return window.__NOVA_SESSION_ID__;
}

function kbModeValue() {
  return (kb$("#kbMode")?.value || "auto").toLowerCase();
}

function kbScopeEnabled() {
  return !!kb$("#kbScopeEnabled")?.checked;
}

function kbSelectedDocIds() {
  const boxes = document.querySelectorAll(".kb-doc-scope");
  const ids = [];
  boxes.forEach(b => {
    if (b.checked) ids.push(parseInt(b.getAttribute("data-doc-id"), 10));
  });
  return ids.filter(x => Number.isFinite(x));
}

async function kbLoadScope() {
  const sid = await kbEnsureSessionId();
  const j = await kbJson(`/api/sessions/${sid}/kb_scope`);
  if (!j.ok) return;

  const scoped = new Set((j.doc_ids || []).map(x => parseInt(x, 10)));
  const boxes = document.querySelectorAll(".kb-doc-scope");
  boxes.forEach(b => {
    const id = parseInt(b.getAttribute("data-doc-id"), 10);
    b.checked = scoped.has(id);
  });
}

async function kbSaveScope() {
  const sid = await kbEnsureSessionId();
  const enabled = kbScopeEnabled();
  const ids = enabled ? kbSelectedDocIds() : [];
  await kbJson(`/api/sessions/${sid}/kb_scope`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_ids: ids }),
  });
  const st = kb$("#kbScopeStatus");
  if (st) st.textContent = enabled ? `Scope saved (${ids.length} doc(s))` : "Scope saved (ALL docs)";
}

function kbDocRow(doc) {
  const row = kbEl("div", "rounded-xl border border-zinc-800 bg-zinc-950/40 p-3");
  const top = kbEl("div", "flex items-start justify-between gap-3");
  const left = kbEl("div", "min-w-0");
  const name = kbEl("div", "font-semibold text-zinc-100 truncate");
  name.textContent = `#${doc.id} ${doc.filename}`;
  const meta = kbEl("div", "text-xs text-zinc-400 mt-1");
  meta.textContent = `${doc.ext} • ${doc.bytes} bytes • ${doc.status}${doc.error ? " • " + doc.error : ""}`;

  left.appendChild(name);
  left.appendChild(meta);

  const right = kbEl("div", "flex flex-col gap-2 items-end");

  const scopeWrap = kbEl("label", "flex items-center gap-2 text-xs text-zinc-300 select-none");
  const cb = kbEl("input", "kb-doc-scope");
  cb.type = "checkbox";
  cb.setAttribute("data-doc-id", doc.id);
  cb.className = "kb-doc-scope accent-zinc-200";
  scopeWrap.appendChild(cb);
  const scopeTxt = kbEl("span", "");
  scopeTxt.textContent = "Use in this chat";
  scopeWrap.appendChild(scopeTxt);

  const btns = kbEl("div", "flex flex-wrap gap-2 justify-end");
  function mkBtn(text) {
    const b = kbEl("button", "text-xs rounded-lg border border-zinc-800 px-3 py-2 hover:bg-zinc-900");
    b.type = "button";
    b.textContent = text;
    return b;
  }

  const bDownload = mkBtn("Download");
  bDownload.onclick = () => window.open(`/api/kb/docs/${doc.id}/download`, "_blank");

  const bChunks = mkBtn("View chunks");
  bChunks.onclick = () => kbShowChunks(doc.id);

  const bReindex = mkBtn("Reindex");
  bReindex.onclick = async () => {
    const j = await kbJson(`/api/kb/docs/${doc.id}/reindex`, { method: "POST" });
    kbToast(j.ok ? `Reindex queued (job #${j.job_id})` : `Reindex failed: ${j.error || "unknown"}`);
    kbRefresh();
  };

  const bDelete = mkBtn("Delete");
  bDelete.onclick = async () => {
    if (!confirm(`Delete doc #${doc.id} (${doc.filename}) ?`)) return;
    const j = await kbJson(`/api/kb/docs/${doc.id}`, { method: "DELETE" });
    kbToast(j.ok ? "Deleted." : `Delete failed: ${j.error || "unknown"}`);
    kbRefresh();
  };

  btns.appendChild(bDownload);
  btns.appendChild(bChunks);
  btns.appendChild(bReindex);
  btns.appendChild(bDelete);

  right.appendChild(scopeWrap);
  right.appendChild(btns);

  top.appendChild(left);
  top.appendChild(right);
  row.appendChild(top);
  return row;
}

function kbToast(msg) {
  const el = kb$("#kbToast");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2200);
}

async function kbShowChunks(docId) {
  const modal = kb$("#kbModal");
  const body = kb$("#kbModalBody");
  const title = kb$("#kbModalTitle");
  if (!modal || !body || !title) return;

  title.textContent = `Doc #${docId} chunks`;
  body.innerHTML = `<div class="text-sm text-zinc-400">Loading…</div>`;
  modal.classList.remove("hidden");

  const j = await kbJson(`/api/kb/docs/${docId}/chunks?limit=400&offset=0`);
  if (!j.ok) {
    body.innerHTML = `<div class="text-sm text-red-400 whitespace-pre-wrap">${kbEsc(j.error || "failed")}</div>`;
    return;
  }

  const chunks = j.chunks || [];
  if (!chunks.length) {
    body.innerHTML = `<div class="text-sm text-zinc-400">No chunks indexed yet.</div>`;
    return;
  }

  const wrap = kbEl("div", "space-y-3");
  chunks.forEach(c => {
    const card = kbEl("div", "rounded-xl border border-zinc-800 bg-zinc-950/40 p-3");
    const head = kbEl("div", "text-xs text-zinc-400");
    head.textContent = `chunk ${c.chunk_index}` + (c.page ? ` • p.${c.page}` : "");
    const txt = kbEl("div", "mt-2 text-sm text-zinc-200 whitespace-pre-wrap");
    txt.textContent = (c.text || "");
    card.appendChild(head);
    card.appendChild(txt);
    wrap.appendChild(card);
  });

  body.innerHTML = "";
  body.appendChild(wrap);
}

function kbCloseModal() {
  kb$("#kbModal")?.classList.add("hidden");
}

async function kbSearch() {
  const q = (kb$("#kbSearch")?.value || "").trim();
  const mode = kbModeValue();

  const enabled = kbScopeEnabled();
  const sid = await kbEnsureSessionId();
  let docIds = [];
  if (enabled) {
    // use saved scope OR current checked
    docIds = kbSelectedDocIds();
    await kbJson(`/api/sessions/${sid}/kb_scope`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_ids: docIds }),
    });
  } else {
    // all docs
    await kbJson(`/api/sessions/${sid}/kb_scope`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_ids: [] }),
    });
  }

  const qs = new URLSearchParams();
  qs.set("q", q);
  qs.set("k", "12");
  qs.set("mode", mode);
  if (enabled && docIds.length) qs.set("doc_ids", docIds.join(","));

  const j = await kbJson(`/api/kb/search?${qs.toString()}`);
  const out = kb$("#kbSearchResults");
  if (!out) return;

  if (!q) {
    out.innerHTML = `<div class="text-xs text-zinc-400">Type a query to search.</div>`;
    return;
  }

  if (!j.ok) {
    out.innerHTML = `<div class="text-xs text-red-400 whitespace-pre-wrap">${kbEsc(j.error || "search failed")}</div>`;
    return;
  }

  const sources = j.sources || [];
  if (!sources.length) {
    out.innerHTML = `<div class="text-xs text-zinc-400">No results.</div>`;
    return;
  }

  const wrap = kbEl("div", "space-y-3");
  sources.forEach((s, idx) => {
    const card = kbEl("div", "rounded-xl border border-zinc-800 bg-zinc-950/40 p-3");
    const head = kbEl("div", "text-xs text-zinc-300 font-semibold");
    head.textContent = `${idx + 1}. ${s.filename}` + (s.page ? ` (p.${s.page})` : "") + ` • doc #${s.doc_id}`;
    const snip = kbEl("div", "mt-2 text-sm text-zinc-200 whitespace-pre-wrap");
    snip.textContent = (s.snippet || "");
    card.appendChild(head);
    card.appendChild(snip);
    wrap.appendChild(card);
  });

  out.innerHTML = "";
  out.appendChild(wrap);
}

async function kbRefresh() {
  const docsBox = kb$("#kbDocs");
  const jobsBox = kb$("#kbJobs");
  if (!docsBox || !jobsBox) return;

  const docs = await kbJson("/api/kb/docs");
  const jobs = await kbJson("/api/kb/jobs");

  docsBox.innerHTML = "";
  jobsBox.innerHTML = "";

  if (docs.ok && docs.docs) {
    if (!docs.docs.length) {
      docsBox.innerHTML = `<div class="text-xs text-zinc-400">No docs yet. Upload something.</div>`;
    } else {
      docs.docs.forEach(d => docsBox.appendChild(kbDocRow(d)));
    }
  } else {
    docsBox.innerHTML = `<div class="text-xs text-red-400 whitespace-pre-wrap">${kbEsc(docs.error || "failed")}</div>`;
  }

  if (jobs.ok && jobs.jobs) {
    const top = jobs.jobs.slice(0, 8);
    if (!top.length) {
      jobsBox.innerHTML = `<div class="text-xs text-zinc-400">No jobs.</div>`;
    } else {
      const ul = kbEl("ul", "space-y-2");
      top.forEach(j => {
        const li = kbEl("li", "text-xs text-zinc-400");
        li.textContent = `#${j.id} • ${j.status} • doc #${j.doc_id} • ${j.filename}`;
        ul.appendChild(li);
      });
      jobsBox.appendChild(ul);
    }
  }

  // after rendering docs, load saved scope and set checkboxes
  await kbLoadScope();
}

function kbWire() {
  kb$("#kbRefreshBtn")?.addEventListener("click", kbRefresh);
  kb$("#kbSearchBtn")?.addEventListener("click", kbSearch);
  kb$("#kbSearch")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      kbSearch();
    }
  });

  kb$("#kbScopeEnabled")?.addEventListener("change", async () => {
    await kbSaveScope();
  });

  kb$("#kbSaveScopeBtn")?.addEventListener("click", async () => {
    await kbSaveScope();
  });

  kb$("#kbModalClose")?.addEventListener("click", kbCloseModal);
  kb$("#kbModalBackdrop")?.addEventListener("click", kbCloseModal);

  // initial
  kbRefresh();
  setInterval(kbRefresh, 2500);
}

document.addEventListener("DOMContentLoaded", kbWire);