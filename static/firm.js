"use strict";
const $desk = document.getElementById("desk");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" }[c]));
const cookie = name => (document.cookie.split("; ").find(c => c.startsWith(name + "=")) || "").slice(name.length + 1);
const STATUSES = [["needed", "Needed"], ["asked", "Asked"], ["received", "Received"], ["done", "Done"], ["na", "Not needed"]];
const MATTER = [["open", "Open"], ["waiting", "Waiting on client"], ["working", "Working"], ["ready", "Ready for sign-off"], ["closed", "Closed"]];

async function ensureCsrf() {
  let token = cookie("sas_csrf");
  if (!token) {
    await fetch("/api/auth/me", { credentials: "same-origin", cache: "no-store" });
    token = cookie("sas_csrf");
  }
  return token;
}
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (opts.method && opts.method !== "GET") headers["X-CSRF-Token"] = decodeURIComponent(await ensureCsrf());
  const res = await fetch(path, { method: opts.method || "GET", credentials: "same-origin", headers, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error((data && (data.detail?.message || data.detail)) || "Something went wrong");
  return data;
}

let ME = null;
function route() {
  const id = new URLSearchParams(location.search).get("m");
  if (!ME) return login();
  if (id === "new") return newer();
  if (id) return matter(id);
  return list();
}
function nav() {
  const el = document.getElementById("firm-nav");
  if (!ME) { el.innerHTML = '<a href="/">Public site</a>'; return; }
  el.innerHTML = '<a href="/firm">Matters</a> <a href="/firm?m=new">New matter</a> <a href="/">Public site</a> <button type="button" class="linkbtn" id="out">Sign out</button>';
  document.getElementById("out").onclick = async () => { await api("/api/auth/logout", { method: "POST" }); ME = null; location.href = "/firm"; };
}

function login() {
  nav();
  $desk.innerHTML = '<div class="firm-card" style="max-width:460px;margin:40px auto"><p class="eyebrow">Staff only</p><h1>Firm desk</h1><p>For solicitors and staff drafting wills, LPAs and the other documents, and for running a probate matter. Clients use the public site.</p><form id="in"><label>Email<input name="email" type="email" required autocomplete="username"></label><label>Password<input name="password" type="password" required autocomplete="current-password"></label><p><button class="btn" type="submit">Sign in</button></p><p class="muted small" id="err" role="alert"></p></form></div>';
  document.getElementById("in").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const r = await api("/api/auth/login", { method: "POST", body: { email: fd.get("email"), password: fd.get("password") } });
      if (!r.user || (r.user.role !== "staff" && r.user.role !== "admin")) {
        document.getElementById("err").textContent = "This desk is for firm staff. Client accounts use the public site.";
        await api("/api/auth/logout", { method: "POST" });
        return;
      }
      ME = r.user;
      location.href = "/firm";
    } catch (err) { document.getElementById("err").textContent = err.message; }
  };
}

async function list() {
  nav();
  const rows = await api("/api/firm/matters");
  $desk.innerHTML = '<p class="eyebrow">Firm desk</p><h1>Matters</h1><p><a class="btn" href="/firm?m=new">New matter</a></p><div class="firm-card">'
    + (rows.length ? rows.map(m => '<div class="matter-row"><div><a href="/firm?m=' + esc(m.id) + '">' + esc(m.title) + '</a><div class="muted small">' + esc(m.client_name || "No client name") + (m.deceased_name ? " · estate of " + esc(m.deceased_name) : "") + '</div></div><div>' + esc(m.kind_label) + '</div><div class="small">' + (m.next ? esc(m.next.title) : "Checklist complete") + '</div><div class="small">' + m.progress.done + '/' + m.progress.total + '</div></div>').join("") : '<p class="muted">No matters yet.</p>')
    + '</div>';
}

async function newer() {
  nav();
  const kinds = await api("/api/firm/kinds");
  $desk.innerHTML = '<p><a href="/firm">All matters</a></p><div class="firm-card"><h1>New matter</h1><form id="new"><label>Type<select name="kind">' + kinds.map(k => '<option value="' + esc(k.id) + '">' + esc(k.label) + '</option>').join("") + '</select></label><label>Client name<input name="client_name" required></label><label>Client email<input name="client_email" type="email"></label><label>Title<input name="title" placeholder="Filled in for you if you leave this blank"></label><div id="prob"><label>Person who died<input name="deceased_name"></label><label>Date of death<input name="date_of_death" type="date"></label></div><p><button class="btn" type="submit">Open matter</button></p></form></div>';
  const kind = document.querySelector("[name=kind]");
  const prob = document.getElementById("prob");
  const sync = () => { prob.style.display = kind.value === "probate" ? "" : "none"; };
  kind.onchange = sync; sync();
  document.getElementById("new").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    const m = await api("/api/firm/matters", { method: "POST", body });
    location.href = "/firm?m=" + m.id;
  };
}

async function matter(id) {
  nav();
  const m = await api("/api/firm/matters/" + id);
  const deadlines = (m.deadlines || []).map(d => '<li><b>' + esc(d.label) + '</b>' + (d.date ? ' · ' + esc(d.date) : '') + '<div class="small">' + esc(d.note) + '</div></li>').join("");
  $desk.innerHTML = '<p><a href="/firm">All matters</a></p>'
    + '<div class="firm-next"><p class="eyebrow">Do this next</p><h1>' + esc(m.next ? m.next.title : "Checklist complete") + '</h1>'
    + (m.next ? '<p>' + esc(m.next.ask) + '</p><p class="small">' + esc(m.next.stage) + '</p>' : '<p>Every item is received, done, or not needed.</p>')
    + '</div>'
    + '<div class="firm-grid"><div><div class="firm-card"><h2>' + esc(m.title) + '</h2><p class="muted">' + esc(m.kind_label) + ' · ' + m.progress.done + ' of ' + m.progress.total + '</p>'
    + '<form id="meta"><label>Status<select name="status">' + MATTER.map(([v, l]) => '<option value="' + v + '"' + (m.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></label>'
    + '<label>Client<input name="client_name" value="' + esc(m.client_name) + '"></label><label>Email<input name="client_email" value="' + esc(m.client_email) + '"></label>'
    + (m.kind === "probate" ? '<label>Person who died<input name="deceased_name" value="' + esc(m.deceased_name) + '"></label><label>Date of death<input name="date_of_death" type="date" value="' + esc(m.date_of_death) + '"></label><label>Date of grant<input name="grant_date" type="date" value="' + esc(m.grant_date) + '"></label>' : '')
    + '<p><button class="btn" type="submit">Save details</button></p></form>'
    + (deadlines ? '<h3>Dates</h3><ul>' + deadlines + '</ul>' : '')
    + '<h3>What you need</h3>'
    + m.stages.map(stage => '<section class="stage"><h3>' + esc(stage.title) + '</h3>' + stage.items.map(it => '<div class="item"><div><b>' + esc(it.title) + '</b> <span class="who">' + esc(it.who) + '</span><div class="small">' + esc(it.ask) + '</div><div class="muted small">' + esc(it.why) + '</div></div><select data-item="' + esc(it.id) + '">' + STATUSES.map(([v, l]) => '<option value="' + v + '"' + (it.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></div>').join("") + '</section>').join("")
    + '</div></div><aside><div class="firm-card"><h2>Assistant</h2><p class="small">Uses this checklist and the draft checks. Not a solicitor. Nothing is filed from here.</p>'
    + '<p><button class="btn" type="button" id="req">Write the client email</button></p><p><button class="btn ghost" type="button" id="chk">Check the draft</button></p><div id="assist"></div></div>'
    + '<div class="firm-card"><h2>Draft</h2><p class="small">Same questions as the public site, filled in by you for the client.</p><p><button class="btn" type="button" id="draft">' + (m.draft_id ? "Open the draft" : "Start the draft") + '</button></p></div>'
    + '<div class="firm-card"><h2>File note</h2><form id="note"><textarea name="note" rows="4" required placeholder="What was said or received"></textarea><p><button class="btn ghost" type="submit">Add note</button></p></form>'
    + (m.notes || []).slice().reverse().map(n => '<p class="small"><b>' + esc(n.by) + '</b> · ' + esc(n.at).replace("T", " ").slice(0, 16) + '<br>' + esc(n.text) + '</p>').join("")
    + '</div></aside></div>';
  document.getElementById("meta").onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/firm/matters/" + id, { method: "PATCH", body });
    matter(id);
  };
  $desk.querySelectorAll("[data-item]").forEach(sel => sel.onchange = async () => {
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { item_id: sel.dataset.item, item_status: sel.value } });
  });
  document.getElementById("req").onclick = async () => showAssist(await api("/api/firm/matters/" + id + "/assist", { method: "POST", body: { action: "request" } }));
  document.getElementById("chk").onclick = async () => showAssist(await api("/api/firm/matters/" + id + "/assist", { method: "POST", body: { action: "check" } }));
  document.getElementById("draft").onclick = async () => {
    const r = await api("/api/firm/matters/" + id + "/draft", { method: "POST", body: {} });
    location.href = "/#/d/" + r.draft_id + "/0";
  };
  document.getElementById("note").onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { note: new FormData(e.target).get("note") } });
    matter(id);
  };
}
function showAssist(data) {
  const box = document.getElementById("assist");
  if (data.letter) box.innerHTML = '<p class="small"><b>' + esc(data.letter.subject) + '</b></p><div class="letter">' + esc(data.letter.body) + '</div>';
  else if (data.check) {
    const missing = data.check.missing || [];
    const issues = data.check.issues || [];
    box.innerHTML = '<p>' + esc(data.check.detail || (missing.length || issues.length ? "The draft still has points to look at." : "Nothing flagged on the answers so far.")) + '</p>'
      + (missing.length ? '<ul>' + missing.map(x => '<li>' + esc(x) + '</li>').join("") + '</ul>' : '')
      + (issues.length ? '<ul>' + issues.map(x => '<li>' + esc(x.message || x) + '</li>').join("") + '</ul>' : '');
  }
}

(async () => {
  const me = await api("/api/auth/me");
  ME = me.user && (me.user.role === "staff" || me.user.role === "admin") ? me.user : null;
  route();
})();
