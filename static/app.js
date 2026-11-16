const $app = document.getElementById("app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cache = {};
async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw Object.assign(new Error((data && (data.detail?.message || data.detail)) || "Something went wrong"), { data });
  return data;
}
const service = async id => cache[id] ||= await api("/api/services/" + id);
const remember = d => { localStorage.setItem("lastDraft", d.id); };

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  try {
    if (parts[0] === "s") return start(parts[1]);
    if (parts[0] === "d" && parts[2] === "review") return review(parts[1]);
    if (parts[0] === "d") return step(parts[1], Number(parts[2] || 0));
    return home();
  } catch (e) { $app.innerHTML = '<div class="err">' + esc(e.message) + '</div><p><a href="#/">Back to the start</a></p>'; }
}

async function home() {
  const list = await api("/api/services");
  const last = localStorage.getItem("lastDraft");
  $app.innerHTML = '<h1>Make your will, LPA or probate application, step by step</h1><p class="muted">Answer simple questions with guidance at every step. We prepare the draft and a solicitor checks it before you sign.</p>'
    + '<div class="grid">' + list.map(s => '<div class="card"><h3>' + esc(s.title) + '</h3><p class="muted">' + esc(s.summary) + '</p><p class="muted">' + s.steps + ' steps</p><a class="btn" href="#/s/' + s.id + '">Start</a></div>').join("") + '</div>'
    + '<h2>Carry on where you left off</h2><div class="card"><label for="ref">Your reference number</label><input id="ref" value="' + esc(last || "") + '" placeholder="e.g. 3f2b…"><p><button class="btn ghost" id="resume">Continue</button></p></div>';
  document.getElementById("resume").onclick = () => { const v = document.getElementById("ref").value.trim(); if (v) location.hash = "#/d/" + v + "/0"; };
}

async function start(id) {
  const d = await api("/api/drafts", { method: "POST", body: { service: id, answers: {} } });
  remember(d);
  location.replace("#/d/" + d.id + "/0");
}

function fieldHtml(f, value, path) {
  const id = path.join("__");
  const req = f.required ? " required" : "";
  if (f.type === "list") {
    const items = value && value.length ? value : Array.from({ length: f.min || 0 }, () => ({}));
    return '<fieldset class="card" data-list="' + id + '" data-max="' + f.max + '"><legend><b>' + esc(f.label) + '</b></legend>'
      + items.map((it, i) => '<div class="item"><div class="item-head"><b>' + (i + 1) + '</b>' + (i >= (f.min || 0) ? '<button type="button" class="btn ghost small" data-remove="' + id + '" data-i="' + i + '">Remove</button>' : "") + '</div>' + f.fields.map(sf => fieldHtml(sf, it[sf.name], path.concat(i, sf.name))).join("") + '</div>').join("")
      + (items.length < f.max ? '<p><button type="button" class="btn ghost small" data-add="' + id + '">Add another</button></p>' : "") + '</fieldset>';
  }
  if (f.type === "group") return '<fieldset class="card"><legend><b>' + esc(f.label) + '</b></legend>' + f.fields.map(sf => fieldHtml(sf, (value || {})[sf.name], path.concat(sf.name))).join("") + '</fieldset>';
  const label = '<label for="' + id + '">' + esc(f.label) + (f.required ? "" : "") + '</label>';
  if (f.type === "select") return label + '<select id="' + id + '" name="' + id + '"' + req + '><option value="">Choose…</option>' + f.options.map(o => '<option' + (o === value ? " selected" : "") + '>' + esc(o) + '</option>').join("") + '</select>';
  if (f.type === "textarea") return label + '<textarea id="' + id + '" name="' + id + '"' + req + '>' + esc(value) + '</textarea>';
  return label + '<input id="' + id + '" name="' + id + '" type="' + (f.type === "number" ? "number" : f.type) + '" step="any" value="' + esc(value) + '"' + req + '>';
}

function readForm(form) {
  const out = {};
  for (const el of form.querySelectorAll("[name]")) {
    const keys = el.name.split("__").map(k => /^\d+$/.test(k) ? Number(k) : k);
    let node = out;
    keys.forEach((k, i) => {
      if (i === keys.length - 1) { node[k] = el.value; return; }
      node[k] ??= typeof keys[i + 1] === "number" ? [] : {};
      node = node[k];
    });
  }
  return out;
}

async function step(id, index) {
  const draft = await api("/api/drafts/" + id);
  remember(draft);
  const s = await service(draft.service);
  const st = s.steps[index];
  if (!st) { location.hash = "#/d/" + id + "/review"; return; }
  const answers = draft.answers[st.id] || {};
  const pct = Math.round((index / s.steps.length) * 100);
  $app.innerHTML = '<p class="muted">' + esc(s.title) + ' · reference <span class="ref">' + esc(id) + '</span></p>'
    + '<ul class="steps">' + s.steps.map((x, i) => '<li class="' + (i === index ? "on" : draft.answers[x.id] ? "done" : "") + '">' + (i + 1) + '. ' + esc(x.title) + '</li>').join("") + '<li>Review</li></ul>'
    + '<div class="progress"><span style="width:' + pct + '%"></span></div>'
    + '<h1>' + esc(st.title) + '</h1>'
    + (st.video ? '<video controls preload="metadata" src="' + esc(st.video) + '"></video>' : "")
    + '<div class="guide">' + st.guidance.map(p => '<p>' + esc(p) + '</p>').join("") + '</div>'
    + '<form id="f" novalidate>' + st.fields.map(f => fieldHtml(f, answers[f.name], [f.name])).join("")
    + '<div id="msg"></div><div class="row">' + (index ? '<a class="btn ghost" href="#/d/' + id + '/' + (index - 1) + '">Back</a>' : '<a class="btn ghost" href="#/">Home</a>') + '<button class="btn" type="submit">' + (index === s.steps.length - 1 ? "Save and review" : "Save and continue") + '</button></div></form>';
  const form = document.getElementById("f");
  const save = async () => {
    const all = { ...draft.answers, [st.id]: readForm(form) };
    if (draft.status !== "draft") return draft;
    return api("/api/drafts/" + id, { method: "PUT", body: { answers: all } });
  };
  form.onclick = async e => {
    const add = e.target.dataset.add, rem = e.target.dataset.remove;
    if (!add && !rem) return;
    const current = readForm(form);
    const key = (add || rem).split("__");
    let node = current; key.slice(0, -1).forEach(k => node = node[/^\d+$/.test(k) ? Number(k) : k]);
    const name = key[key.length - 1];
    node[name] = node[name] || [];
    if (add) node[name].push({}); else node[name].splice(Number(e.target.dataset.i), 1);
    draft.answers[st.id] = current;
    form.innerHTML = st.fields.map(f => fieldHtml(f, current[f.name], [f.name])).join("") + form.querySelector("#msg").outerHTML + form.querySelector(".row").outerHTML;
  };
  form.onsubmit = async e => {
    e.preventDefault();
    const missingHere = [...form.querySelectorAll("[required]")].filter(el => !el.value.trim());
    if (missingHere.length) { missingHere[0].focus(); document.getElementById("msg").innerHTML = '<div class="err">Please fill in the required answers before you continue.</div>'; return; }
    await save();
    location.hash = "#/d/" + id + "/" + (index + 1);
  };
}

async function review(id) {
  const draft = await api("/api/drafts/" + id);
  const s = await service(draft.service);
  if (draft.missing.length) {
    $app.innerHTML = '<h1>Almost there</h1><p>Some answers are still needed:</p><div class="err"><ul>' + draft.missing.map(m => '<li>' + esc(m) + '</li>').join("") + '</ul></div><p><a class="btn" href="#/d/' + id + '/0">Go back to the questions</a></p>';
    return;
  }
  const doc = await api("/api/drafts/" + id + "/document");
  $app.innerHTML = '<p class="muted">' + esc(s.title) + ' · reference <span class="ref">' + esc(id) + '</span></p><h1>Check your draft</h1>'
    + '<div class="doc"><h2>' + esc(doc.title) + '</h2><p class="notice">' + esc(doc.notice) + '</p>' + doc.sections.map(sec => '<h3>' + esc(sec.heading) + '</h3>' + sec.paragraphs.map(p => '<p>' + esc(p) + '</p>').join("")).join("") + '</div>'
    + '<h2>What happens next</h2><ol>' + doc.next_steps.map(n => '<li>' + esc(n) + '</li>').join("") + '</ol>'
    + '<div class="row"><a class="btn ghost" href="#/d/' + id + '/' + (s.steps.length - 1) + '">Change answers</a><span><a class="btn ghost" href="/api/drafts/' + id + '/pdf">Download PDF</a> '
    + (draft.status === "draft" ? '<button class="btn" id="submit">Send to a solicitor for review</button>' : '<span class="ok">Sent for solicitor review</span>') + '</span></div><div id="msg"></div>';
  const btn = document.getElementById("submit");
  if (btn) btn.onclick = async () => { btn.disabled = true; await api("/api/drafts/" + id + "/submit", { method: "POST" }); route(); };
}

window.addEventListener("hashchange", route);
route();
