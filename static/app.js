"use strict";
const $app = document.getElementById("app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ICONS = { will: "📜", lpa_property: "🏦", lpa_health: "🩺", probate: "⚖️" };
const cache = {};

async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;
  const res = await fetch(path, { ...opts, headers: isForm ? {} : { "Content-Type": "application/json" }, body: opts.body === undefined ? undefined : isForm ? opts.body : JSON.stringify(opts.body) });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw Object.assign(new Error((data && (data.detail?.message || data.detail)) || "Something went wrong. Please try again."), { data, status: res.status });
  return data;
}
const service = async id => cache[id] ||= await api("/api/services/" + id);
const remember = d => localStorage.setItem("lastDraft", d.id);
const focusMain = () => { const h = $app.querySelector("h1"); if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); } window.scrollTo(0, 0); };

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  try {
    if (parts[0] === "s") return await start(parts[1]);
    if (parts[0] === "d" && parts[2] === "review") return await review(parts[1]);
    if (parts[0] === "d") return await step(parts[1], Number(parts[2] || 0));
    return await home();
  } catch (e) {
    $app.innerHTML = '<h1>Sorry, something went wrong</h1><div class="alert error">' + esc(e.message) + '</div><p><a class="btn ghost" href="#/">Back to the start</a></p>';
  } finally { focusMain(); }
}

async function home() {
  const list = await api("/api/services");
  const last = localStorage.getItem("lastDraft");
  $app.innerHTML = '<section class="hero"><div><p class="eyebrow">England and Wales</p><h1>Your will, power of attorney or probate, sorted step by step</h1>'
    + '<p class="lead">Short videos and plain-English help on every step. Upload your old documents and we suggest answers. A solicitor checks everything before you sign.</p></div>'
    + '<div class="hero-card" aria-label="What you get"><ul><li>Guided questions with a video on each step</li><li>Built on the official GOV.UK forms (LP1F, LP1H, PA1P, PA1A, IHT400)</li><li>Upload an old will, LPA or probate papers</li><li>Download a PDF and send it for solicitor review</li></ul></div></section>'
    + '<h2>What would you like to do?</h2><div class="grid">' + list.map(s => '<article class="card svc"><span class="icon" aria-hidden="true">' + (ICONS[s.id] || "📄") + '</span><h3>' + esc(s.title) + '</h3><p class="muted">' + esc(s.summary) + '</p><p class="meta">' + s.steps + ' steps · about ' + (s.steps * 3) + ' minutes</p><a class="btn" href="#/s/' + s.id + '">Start</a></article>').join("") + '</div>'
    + '<h2>How it works</h2><div class="how"><div><b>1. Answer</b>Watch the short video, read the help and answer a few questions. Your answers save automatically.</div><div><b>2. Check</b>See your draft with a plain-English note on every clause, and any points to fix.</div><div><b>3. Review</b>Send it to a solicitor. They check it with you before anything is signed or sent.</div></div>'
    + '<h2>Carry on where you left off</h2><form class="card" id="resume"><label class="legend" for="ref">Your reference number</label><input id="ref" value="' + esc(last || "") + '" placeholder="for example 3f2b…" autocomplete="off"><p><button class="btn ghost">Continue</button></p></form>';
  document.getElementById("resume").onsubmit = e => { e.preventDefault(); const v = document.getElementById("ref").value.trim(); if (v) location.hash = "#/d/" + v + "/0"; };
}

async function start(id) {
  const d = await api("/api/drafts", { method: "POST", body: { service: id, answers: {} } });
  remember(d);
  location.replace("#/d/" + d.id + "/0");
}

const visible = (f, container) => !f.show_if || f.show_if.in.includes((container || {})[f.show_if.field]);

function fieldHtml(f, value, path, container) {
  if (!visible(f, container)) return "";
  const id = path.join("__");
  const hint = f.hint ? '<span class="hint" id="' + id + '__hint">' + esc(f.hint) + '</span>' : "";
  const desc = f.hint ? ' aria-describedby="' + id + '__hint"' : "";
  const req = f.required ? " required" : "";
  const opt = f.required ? "" : "";
  if (f.type === "list") {
    const items = value && value.length ? value : Array.from({ length: f.min || 0 }, () => ({}));
    return '<fieldset class="group" data-list="' + id + '"><legend class="legend">' + esc(f.label) + '</legend>' + hint
      + items.map((it, i) => '<div class="item"><div class="item-head"><span>' + (i + 1) + '</span>' + (i >= (f.min || 0) ? '<button type="button" class="btn ghost small" data-remove="' + id + '" data-i="' + i + '">Remove</button>' : "") + '</div>'
        + f.fields.map(sf => fieldHtml(sf, (it || {})[sf.name], path.concat(i, sf.name), it)).join("") + '</div>').join("")
      + (items.length < f.max ? '<p><button type="button" class="btn ghost small" data-add="' + id + '">+ Add ' + (items.length ? "another" : "one") + '</button></p>' : "") + '</fieldset>';
  }
  if (f.type === "group") return '<fieldset class="group"><legend class="legend">' + esc(f.label) + '</legend>' + hint + f.fields.map(sf => fieldHtml(sf, (value || {})[sf.name], path.concat(sf.name), value || {})).join("") + '</fieldset>';
  if (f.type === "checkbox") return '<div class="field"><label class="check"><input type="checkbox" id="' + id + '" name="' + id + '"' + (value === true ? " checked" : "") + req + desc + '><span>' + esc(f.label) + '</span></label>' + hint + '</div>';
  const label = '<label for="' + id + '">' + esc(f.label) + opt + '</label>' + hint;
  if (f.type === "select") return '<div class="field">' + label + '<select id="' + id + '" name="' + id + '"' + req + desc + '><option value="">Choose…</option>' + f.options.map(o => '<option' + (o === value ? " selected" : "") + '>' + esc(o) + '</option>').join("") + '</select></div>';
  if (f.type === "textarea") return '<div class="field">' + label + '<textarea id="' + id + '" name="' + id + '"' + req + desc + '>' + esc(value) + '</textarea></div>';
  const type = f.type === "number" ? "number" : f.type;
  const extra = f.type === "number" ? ' inputmode="decimal" step="any" min="0"' : f.type === "email" ? ' autocomplete="email"' : "";
  return '<div class="field">' + label + '<input id="' + id + '" name="' + id + '" type="' + type + '"' + extra + ' value="' + esc(value) + '"' + req + desc + '></div>';
}

function readForm(form) {
  const out = {};
  for (const el of form.querySelectorAll("[name]")) {
    const keys = el.name.split("__").map(k => /^\d+$/.test(k) ? Number(k) : k);
    let node = out;
    keys.forEach((k, i) => {
      if (i === keys.length - 1) { node[k] = el.type === "checkbox" ? el.checked : el.value; return; }
      node[k] ??= typeof keys[i + 1] === "number" ? [] : {};
      node = node[k];
    });
  }
  for (const fs of form.querySelectorAll("[data-list]")) {  // keep empty list items
    const keys = fs.dataset.list.split("__").map(k => /^\d+$/.test(k) ? Number(k) : k);
    let node = out;
    keys.forEach((k, i) => { if (i === keys.length - 1) { node[k] = (node[k] || []).map(x => x ?? {}); const n = fs.querySelectorAll(":scope > .item").length; while (node[k].length < n) node[k].push({}); } else node = node[k] ??= typeof keys[i + 1] === "number" ? [] : {}; });
  }
  return out;
}

function videoHtml(v, title) {
  if (!v) return "";
  return '<div class="video"><video controls preload="none" playsinline' + (v.poster ? ' poster="' + esc(v.poster) + '"' : "") + ' aria-label="Video: ' + esc(title) + '"><source src="' + esc(v.src) + '" type="video/mp4">'
    + (v.captions ? '<track kind="captions" srclang="en" label="English" src="' + esc(v.captions) + '" default>' : "") + '</video></div>';
}
const sourcesHtml = list => list && list.length ? '<details class="sources"><summary>Official GOV.UK guidance for this step</summary><ul>' + list.map(s => '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + '</a></li>').join("") + '</ul></details>' : "";
const issuesHtml = issues => ["error", "warning", "info"].map(level => { const xs = (issues || []).filter(i => i.level === level); return xs.length ? '<div class="alert ' + level + '" role="' + (level === "error" ? "alert" : "status") + '"><b>' + ({ error: "Please change", warning: "Please check", info: "Good to know" })[level] + '</b><ul>' + xs.map(i => '<li>' + esc(i.message) + '</li>').join("") + '</ul></div>' : ""; }).join("");

function sideHtml(s, draft, index) {
  const done = s.steps.filter(x => draft.answers[x.id]).length;
  const pct = Math.round((done / s.steps.length) * 100);
  return '<aside class="side" aria-label="Progress"><h2>' + esc(s.short_title || s.title) + '</h2><p class="muted ref">Reference <span class="ref">' + esc(draft.id) + '</span></p>'
    + '<div class="progress" role="progressbar" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100" aria-label="Progress"><span style="width:' + pct + '%"></span></div><p class="muted small">' + pct + '% complete</p>'
    + '<ol class="stepper">' + s.steps.map((x, i) => '<li class="' + (i === index ? "on" : draft.answers[x.id] ? "done" : "") + '"><a href="#/d/' + draft.id + '/' + i + '"' + (i === index ? ' aria-current="step"' : "") + '>' + esc(x.title) + '</a></li>').join("")
    + '<li class="' + (index < 0 ? "on" : "") + '"><a href="#/d/' + draft.id + '/review">Check and send</a></li></ol></aside>';
}

function uploadsHtml(st, draft) {
  if (!st.uploads) return "";
  const sugg = draft.uploads.flatMap(u => u.suggestions || []);
  return '<h2>Upload documents</h2>'
    + (draft.status === "draft" ? '<label class="drop" id="drop"><input type="file" id="file" multiple accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.heic,.webp"><b>Choose files</b> or drag them here<br><span class="muted small">PDF, Word, text or photos · up to 10 MB each</span></label>'
      + '<div class="field"><label for="kind">What is it?</label><select id="kind"><option value="">Work it out for me</option>' + st.uploads.map(k => '<option>' + esc(k) + '</option>').join("") + '</select></div>' : "")
    + '<div id="upmsg" aria-live="polite"></div>'
    + (draft.uploads.length ? '<ul class="files">' + draft.uploads.map(u => '<li><span>📄 <a href="/api/drafts/' + draft.id + '/uploads/' + u.id + '">' + esc(u.filename) + '</a> <span class="muted">· ' + esc(u.kind) + ' · ' + ({ pdf: "text read", docx: "text read", text: "text read", image: "photo kept for your solicitor", "scanned-pdf": "scan kept for your solicitor", unreadable: "could not read, kept for your solicitor" })[u.read_as] + '</span></span>' + (draft.status === "draft" ? '<button type="button" class="btn ghost small" data-del="' + u.id + '">Delete</button>' : "") + '</li>').join("") + '</ul>' : "")
    + (sugg.length ? '<div class="sugg"><h3>Suggestions from your documents</h3><ul>' + sugg.map(s => '<li><span>' + esc(s.label) + ' <span class="muted small">(' + esc(s.source) + ')</span></span>' + (s.mode !== "note" && draft.status === "draft" ? '<button type="button" class="btn small" data-sugg="' + esc(s.id) + '">Add</button>' : "") + '</li>').join("") + '</ul></div>' : "");
}

async function step(id, index) {
  const draft = await api("/api/drafts/" + id);
  remember(draft);
  const s = await service(draft.service);
  const st = s.steps[index];
  if (!st) { location.hash = "#/d/" + id + "/review"; return; }
  let cur = structuredClone(draft.answers[st.id] || {});
  const editable = draft.status === "draft";
  const last = index === s.steps.length - 1;
  $app.innerHTML = '<div class="layout">' + sideHtml(s, draft, index) + '<section>'
    + '<p class="eyebrow">Step ' + (index + 1) + ' of ' + s.steps.length + (st.form_section ? ' · <span class="pill">' + esc(st.form_section) + '</span>' : "") + '</p>'
    + '<h1>' + esc(st.title) + '</h1>' + videoHtml(st.video, st.title)
    + '<div class="guide">' + st.guidance.map(p => '<p>' + esc(p) + '</p>').join("") + '</div>' + sourcesHtml(st.sources)
    + (editable ? "" : '<div class="alert ok">This draft has been sent for solicitor review, so it can no longer be changed.</div>')
    + '<form id="f" novalidate><div id="fields">' + st.fields.map(f => fieldHtml(f, cur[f.name], [f.name], cur)).join("") + '</div>' + uploadsHtml(st, draft)
    + '<div id="msg" aria-live="assertive"></div><div class="actions">' + (index ? '<a class="btn ghost" href="#/d/' + id + '/' + (index - 1) + '">← Back</a>' : '<a class="btn ghost" href="#/">Home</a>')
    + '<span class="saved" id="saved" aria-live="polite"></span><button class="btn" type="submit">' + (last ? "Check my draft →" : "Save and continue →") + '</button></div></form></section></div>';
  const form = document.getElementById("f"), fields = document.getElementById("fields"), saved = document.getElementById("saved");
  if (!editable) form.querySelectorAll("input,select,textarea").forEach(el => el.disabled = true);
  const rerender = () => { fields.innerHTML = st.fields.map(f => fieldHtml(f, cur[f.name], [f.name], cur)).join(""); };
  let timer;
  const save = async () => {
    clearTimeout(timer);
    if (!editable) return;
    draft.answers = { ...draft.answers, [st.id]: cur };
    saved.textContent = "Saving…";
    try { const d = await api("/api/drafts/" + id, { method: "PUT", body: { answers: draft.answers } }); draft.uploads = d.uploads; saved.textContent = "Saved"; }
    catch (e) { saved.textContent = "Not saved: " + e.message; }
  };
  form.addEventListener("input", () => { cur = { ...cur, ...readForm(fields) }; saved.textContent = ""; clearTimeout(timer); timer = setTimeout(save, 800); });
  form.addEventListener("change", e => {
    cur = { ...cur, ...readForm(fields) };
    const controls = st.fields.some(f => JSON.stringify(f).includes('"field":"' + e.target.name.split("__").pop() + '"'));
    if (controls) { const name = e.target.name; rerender(); document.getElementById(name)?.focus(); }
  });
  form.addEventListener("click", async e => {
    const t = e.target.closest("button"); if (!t) return;
    if (t.dataset.add || t.dataset.remove) {
      cur = { ...cur, ...readForm(fields) };
      const key = (t.dataset.add || t.dataset.remove).split("__");
      let node = cur; key.slice(0, -1).forEach(k => node = node[/^\d+$/.test(k) ? Number(k) : k]);
      const name = key[key.length - 1]; node[name] = node[name] || [];
      if (t.dataset.add) node[name].push({}); else node[name].splice(Number(t.dataset.i), 1);
      rerender(); save();
    }
    if (t.dataset.del) { await api("/api/drafts/" + id + "/uploads/" + t.dataset.del, { method: "DELETE" }); route(); }
    if (t.dataset.sugg) {
      const sg = draft.uploads.flatMap(u => u.suggestions || []).find(x => x.id === t.dataset.sugg);
      const sec = { ...(draft.answers[sg.step] || {}) };
      if (sg.mode === "append") { const list = (sec[sg.field] || []).filter(x => x && Object.values(x).some(v => v)); if (!list.some(x => x.full_name && x.full_name === sg.value.full_name && sg.value.full_name)) list.push(sg.value); sec[sg.field] = list; }
      else sec[sg.field] = sg.value;
      draft.answers = { ...draft.answers, [st.id]: cur, [sg.step]: sec };
      await api("/api/drafts/" + id, { method: "PUT", body: { answers: draft.answers } });
      t.replaceWith(Object.assign(document.createElement("span"), { className: "muted small", textContent: "Added ✓" }));
    }
  });
  const fileInput = document.getElementById("file"), drop = document.getElementById("drop");
  const sendFiles = async files => {
    const msg = document.getElementById("upmsg");
    for (const f of files) {
      msg.innerHTML = '<div class="alert info">Uploading ' + esc(f.name) + '…</div>';
      const fd = new FormData(); fd.append("file", f); fd.append("kind", document.getElementById("kind").value);
      try { await api("/api/drafts/" + id + "/uploads", { method: "POST", body: fd }); }
      catch (e) { msg.innerHTML = '<div class="alert error">' + esc(f.name) + ': ' + esc(e.message) + '</div>'; return; }
    }
    await save(); route();
  };
  if (fileInput) {
    fileInput.onchange = () => sendFiles([...fileInput.files]);
    ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", e => sendFiles([...e.dataTransfer.files]));
  }
  form.onsubmit = async e => {
    e.preventDefault();
    cur = { ...cur, ...readForm(fields) };
    const bad = [...fields.querySelectorAll("[required]")].filter(el => el.type === "checkbox" ? !el.checked : !el.value.trim());
    fields.querySelectorAll("[aria-invalid]").forEach(el => el.removeAttribute("aria-invalid"));
    if (bad.length && editable) {
      bad.forEach(el => el.setAttribute("aria-invalid", "true")); bad[0].focus();
      document.getElementById("msg").innerHTML = '<div class="alert error">Please answer the ' + bad.length + ' highlighted question' + (bad.length > 1 ? "s" : "") + ' before you continue.</div>';
      return;
    }
    await save();
    location.hash = "#/d/" + id + "/" + (index + 1);
  };
}

async function review(id) {
  const draft = await api("/api/drafts/" + id);
  remember(draft);
  const s = await service(draft.service);
  const stepOf = m => Math.max(0, s.steps.findIndex(st => m.startsWith(st.title)));
  const head = '<div class="layout">' + sideHtml(s, draft, -1) + '<section><p class="eyebrow">Check and send</p>';
  const errors = draft.issues.filter(i => i.level === "error");
  if (draft.missing.length || errors.length) {
    $app.innerHTML = head + '<h1>Almost there</h1>' + videoHtml(s.review_video, "Check and send")
      + (draft.missing.length ? '<div class="alert error"><b>Some answers are still needed</b><ul>' + draft.missing.map(m => '<li><a href="#/d/' + id + '/' + stepOf(m) + '">' + esc(m) + '</a></li>').join("") + '</ul></div>' : "")
      + issuesHtml(draft.issues) + '<p><a class="btn" href="#/d/' + id + '/' + (draft.missing.length ? stepOf(draft.missing[0]) : 0) + '">Go to the first question</a></p></section></div>';
    return;
  }
  const doc = await api("/api/drafts/" + id + "/document");
  $app.innerHTML = head + '<h1>Check your draft</h1>' + videoHtml(s.review_video, "Check and send") + issuesHtml(doc.issues)
    + '<article class="doc"><h2>' + esc(doc.title) + '</h2><p class="notice">' + esc(doc.notice) + '</p>'
    + doc.sections.map(sec => '<h3>' + esc(sec.heading) + '</h3>' + sec.paragraphs.map((p, i) => '<div class="clause"><p>' + esc(p) + '</p>' + (sec.notes && sec.notes[i] ? '<p class="note">💡 ' + esc(sec.notes[i].replace(/^\d+\.\s*/, "")) + '</p>' : "") + '</div>').join("")).join("") + '</article>'
    + '<h2>What happens next</h2><ol>' + doc.next_steps.map(n => '<li>' + esc(n) + '</li>').join("") + '</ol>' + sourcesHtml(doc.sources)
    + '<div class="actions"><a class="btn ghost" href="#/d/' + id + '/0">Change answers</a><span><a class="btn ghost" href="/api/drafts/' + id + '/pdf">Download PDF</a> '
    + (draft.status === "draft" ? '<button class="btn accent" id="submit">Send to a solicitor for review</button>' : '<span class="alert ok">Sent for solicitor review</span>') + '</span></div><div id="msg" aria-live="polite"></div></section></div>';
  const btn = document.getElementById("submit");
  if (btn) btn.onclick = async () => { if (!confirm("Send this draft to a solicitor for review? You will not be able to change it afterwards.")) return; btn.disabled = true; await api("/api/drafts/" + id + "/submit", { method: "POST" }); route(); };
}

window.addEventListener("hashchange", route);
route();
