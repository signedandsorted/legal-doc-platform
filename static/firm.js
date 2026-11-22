"use strict";
const $desk = document.getElementById("desk");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
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
    + (rows.length ? rows.map(m => '<div class="matter-row"><div><a href="/firm?m=' + esc(m.id) + '">' + esc(m.title) + '</a><div class="muted small">' + esc(m.client_name || "No client name") + (m.deceased_name ? " · estate of " + esc(m.deceased_name) : "") + (m.figures ? " · net " + gbp(m.figures.net_probate) : "") + '</div></div><div>' + esc(m.kind_label) + '</div><div class="small">' + (m.next ? esc(m.next.title) : "Checklist complete") + '</div><div class="small">' + m.progress.done + "/" + m.progress.total + "</div></div>").join("") : '<p class="muted">No matters yet.</p>')
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

const gbp = n => new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(Number(n) || 0);
let TAB = "next";

async function matter(id) {
  nav();
  const [m, staff] = await Promise.all([api("/api/firm/matters/" + id), api("/api/firm/colleagues")]);
  const tabs = [["next", "Next"], ["money", "One set of figures"], ["accounts", "Accounts"], ["forms", "Forms"], ["papers", "Papers and filing"], ["letters", "Letters"]];
  const showTabs = m.kind === "probate" ? tabs : [tabs[0], tabs[5]];
  if (!showTabs.some(t => t[0] === TAB)) TAB = "next";
  const strip = m.figures ? '<div class="figure-strip">'
    + [["Probate gross", m.figures.gross_probate], ["Probate net", m.figures.net_probate], ["Tax estimate", m.figures.tax], ["Still to collect", m.accounts.totals.still_to_collect], ["Left to share", m.accounts.totals.expected_net]].map(([l, n]) => '<div><span>' + l + '</span><b>' + gbp(n) + '</b></div>').join("")
    + '<div><span>' + (m.figures.excepted ? "No full tax return" : "Full tax details") + '</span><b>' + esc(m.figures.route) + '</b></div></div>' : "";
  $desk.innerHTML = '<p><a href="/firm">All matters</a></p><h1>' + esc(m.title) + '</h1>'
    + '<p class="muted">' + esc(m.kind_label) + (m.deceased_name ? " · " + esc(m.deceased_name) : "") + " · " + esc(m.client_name || "No client yet") + '</p>'
    + strip
    + '<div class="firm-tabs">' + showTabs.map(([k, label]) => '<button type="button" class="btn ' + (TAB === k ? "" : "ghost") + '" data-tab="' + k + '">' + label + '</button>').join(" ") + '</div>'
    + '<div id="panel"></div>';
  $desk.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => { TAB = b.dataset.tab; matter(id); });
  const panel = document.getElementById("panel");
  if (TAB === "money") panel.innerHTML = moneyPanel(m, staff);
  else if (TAB === "accounts") panel.innerHTML = accountsPanel(m);
  else if (TAB === "forms") panel.innerHTML = formsPanel(m);
  if (TAB === "papers") panel.innerHTML = papersPanel(m);
  else if (TAB === "letters") panel.innerHTML = lettersPanel(m);
  else panel.innerHTML = nextPanel(m, staff);
  bind(id, m);
}

function nextPanel(m, staff) {
  const deadlines = (m.deadlines || []).map(d => '<li><b>' + esc(d.label) + '</b>' + (d.date ? " · " + esc(d.date) : "") + '<div class="small">' + esc(d.note) + '</div></li>').join("");
  return '<div class="firm-next"><p class="eyebrow">Do this next</p><h2>' + esc(m.next ? m.next.title : "Checklist complete") + '</h2>'
    + (m.next ? '<p>' + esc(m.next.ask) + '</p><p class="small">' + esc(m.next.stage) + '</p>' : '<p>Every item is received, done, or not needed.</p>') + '</div>'
    + '<div class="firm-grid"><div class="firm-card"><form id="meta"><label>Status<select name="status">' + MATTER.map(([v, l]) => '<option value="' + v + '"' + (m.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></label>'
    + '<label>Worked by<select name="assigned_to"><option value="">Anyone</option>' + staff.map(s => '<option' + (m.assigned_to === s.email ? " selected" : "") + '>' + esc(s.email) + '</option>').join("") + '</select></label>'
    + '<label>Client<input name="client_name" value="' + esc(m.client_name) + '"></label><label>Email<input name="client_email" value="' + esc(m.client_email) + '"></label>'
    + (m.kind === "probate" ? '<label>Person who died<input name="deceased_name" value="' + esc(m.deceased_name) + '"></label><label>Date of death<input name="date_of_death" type="date" value="' + esc(m.date_of_death) + '"></label><label>Date of grant<input name="grant_date" type="date" value="' + esc(m.grant_date) + '"></label>' : "")
    + '<p><button class="btn" type="submit">Save details</button></p></form>'
    + (deadlines ? '<h3>Dates</h3><ul>' + deadlines + '</ul>' : "")
    + '<h3>What you need</h3>' + (m.stages || []).map(stage => '<section class="stage"><h3>' + esc(stage.title) + '</h3>' + stage.items.map(it => '<div class="item"><div><b>' + esc(it.title) + '</b> <span class="who">' + esc(it.who) + '</span><div class="small">' + esc(it.ask) + '</div></div><select data-item="' + esc(it.id) + '">' + STATUSES.map(([v, l]) => '<option value="' + v + '"' + (it.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></div>').join("") + '</section>').join("")
    + '</div><aside><div class="firm-card"><h2>Assistant</h2><p class="small">Writes from this file. It is not a solicitor and it does not file anything.</p><p><button class="btn" type="button" id="req">Write the client email</button></p><p><button class="btn ghost" type="button" id="chk">Check the draft</button></p><div id="assist"></div></div>'
    + '<div class="firm-card"><h2>Draft</h2><p class="small">The questions stay in step with the figures on this matter.</p><p><button class="btn" type="button" id="draft">' + (m.draft_id ? "Open the draft" : "Start the draft") + '</button></p></div>'
    + '<div class="firm-card"><h2>File note</h2><form id="note"><textarea name="note" rows="4" required></textarea><p><button class="btn ghost" type="submit">Add note</button></p></form>'
    + (m.notes || []).slice().reverse().map(n => '<p class="small"><b>' + esc(n.by) + '</b><br>' + esc(n.text) + '</p>').join("") + '</div></aside></div>';
}

function opt(list, current) {
  return list.map(v => '<option' + (v === current ? " selected" : "") + '>' + esc(v) + '</option>').join("");
}
function moneyPanel(m) {
  const b = m.books || { lines: [], people: [], case: {} };
  const c = b.case || {};
  const rows = b.lines.map(ln => '<tr><td>' + esc(ln.name) + (ln.holder ? '<div class="muted small">' + esc(ln.holder) + '</div>' : "") + '</td><td>' + (ln.funeral ? "Funeral" : ln.side === "debt" ? "Debt" : "Asset") + '</td><td>' + gbp(ln.value) + '</td><td>' + (ln.realised == null ? "Not yet" : gbp(ln.realised)) + '</td><td><button type="button" class="btn ghost small" data-drop="' + esc(ln.id) + '">Remove</button></td></tr>').join("");
  const people = b.people.map(p => '<tr><td>' + esc(p.name) + '</td><td>' + gbp(p.specific) + '</td><td>' + p.share + '%</td><td>' + gbp(p.paid) + '</td><td><button type="button" class="btn ghost small" data-drop-person="' + esc(p.id) + '">Remove</button></td></tr>').join("");
  return '<div class="firm-card"><h2>Type each item once</h2><p>The grant figures, the accounts, the tax working paper and the letters all use this list. Joint tenants and assets abroad stay out of the probate figures.</p>'
    + '<table class="tbl"><thead><tr><th>Item</th><th>Type</th><th>At death</th><th>Collected</th><th></th></tr></thead><tbody>' + (rows || '<tr><td colspan="5" class="muted">Nothing entered yet.</td></tr>') + '</tbody></table>'
    + '<form id="add" class="line-form"><input name="name" required placeholder="House, bank, card…"><input name="holder" placeholder="Bank or organisation"><select name="side"><option value="asset">Asset</option><option value="debt">Debt</option></select><select name="ownership"><option value="sole">Owned alone</option><option value="joint_tenants">Joint tenants</option><option value="tenants_in_common">Tenants in common, their share</option></select><input name="value" type="number" min="0" step="0.01" required placeholder="Value at death"><input name="realised" type="number" min="0" step="0.01" placeholder="Collected, if different"><input name="income" type="number" min="0" step="0.01" placeholder="Income"><input name="costs" type="number" min="0" step="0.01" placeholder="Costs"><label class="check"><input name="joint" type="checkbox"> Joint debt</label><label class="check"><input name="abroad" type="checkbox"> Abroad</label><label class="check"><input name="funeral" type="checkbox"> Funeral</label><label class="check"><input name="paid" type="checkbox"> Paid</label><button class="btn" type="submit">Add</button></form></div>'
    + '<div class="firm-grid"><form id="case" class="firm-card"><h2>The people and the tax answers</h2>'
    + '<label>Will<select name="has_will">' + opt(["", "Yes, I have the original", "Yes, but the original is lost", "No", "Not sure"], c.has_will) + '</select></label>'
    + '<label>Applying as<select name="applicant_role">' + opt(["", "Executor named in the will or a codicil", "Husband, wife or civil partner", "Child aged 18 or over", "Other relative", "Unmarried partner", "Someone else (for example an attorney or a beneficiary)"], c.applicant_role) + '</select></label>'
    + '<label>Lived in England or Wales<select name="domicile">' + opt(["Yes", "No, elsewhere in the UK", "No, outside the UK"], c.domicile || "Yes") + '</select></label>'
    + '<label>Marital status<select name="marital_status">' + opt(["", "Married or in a civil partnership", "Widowed or a surviving civil partner", "Divorced or civil partnership dissolved", "Separated", "Never married"], c.marital_status) + '</select></label>'
    + '<label>Last address<textarea name="address">' + esc(c.address || "") + '</textarea></label>'
    + '<label>Left to a spouse or civil partner (£)<input name="to_spouse" type="number" min="0" step="0.01" value="' + (c.to_spouse || 0) + '"></label>'
    + '<label>Left to charity (£)<input name="to_charity" type="number" min="0" step="0.01" value="' + (c.to_charity || 0) + '"></label>'
    + '<label>Gifts in the 7 years (£)<input name="gifts_7_years" type="number" min="0" step="0.01" value="' + (c.gifts_7_years || 0) + '"></label>'
    + '<label class="check"><input name="home_to_descendants" type="checkbox"' + (c.home_to_descendants === "Yes" ? " checked" : "") + '> Home to children or grandchildren</label>'
    + '<label>Value of that home (£)<input name="home_value_to_descendants" type="number" min="0" step="0.01" value="' + (c.home_value_to_descendants || 0) + '"></label>'
    + '<label class="check"><input name="earlier_spouse_died" type="checkbox"' + (c.earlier_spouse_died === "Yes" ? " checked" : "") + '> An earlier spouse or civil partner died first</label>'
    + '<label>Unused threshold from them (%)<input name="unused_nrb_percent" type="number" min="0" max="100" step="0.01" value="' + (c.unused_nrb_percent ?? 100) + '"></label>'
    + '<label>Tax already paid (£)<input name="tax_paid" type="number" min="0" step="0.01" value="' + (c.tax_paid || 0) + '"></label>'
    + '<p><button class="btn" type="submit">Update the figures</button></p></form>'
    + '<div class="firm-card"><h2>Who inherits</h2><table class="tbl"><thead><tr><th>Name</th><th>Specific gift</th><th>Share of the rest</th><th>Paid</th><th></th></tr></thead><tbody>' + (people || '<tr><td colspan="5" class="muted">No one yet. If you leave the shares blank, they split the rest equally.</td></tr>') + '</tbody></table>'
    + '<form id="person" class="line-form"><input name="name" required placeholder="Name"><input name="relationship" placeholder="Child, friend…"><input name="specific" type="number" min="0" step="0.01" placeholder="Specific gift"><input name="share" type="number" min="0" max="100" step="0.01" placeholder="% of the rest"><input name="paid" type="number" min="0" step="0.01" placeholder="Already paid"><button class="btn" type="submit">Add</button></form></div></div>';
}
function accountsPanel(m) {
  const a = m.accounts;
  if (!a) return '<div class="firm-card"><p>Accounts are kept on probate matters.</p></div>';
  const t = a.totals;
  const cap = a.capital.map(r => '<tr><td>' + esc(r.name) + '</td><td>' + gbp(r.dod) + '</td><td>' + gbp(r.collected) + '</td><td>' + gbp(r.still) + '</td><td>' + gbp(r.income) + '</td><td>' + gbp(r.costs) + '</td></tr>').join("");
  const out = a.outside.map(r => '<li><b>' + esc(r.name) + '</b> ' + gbp(r.value) + '<div class="small">' + esc(r.why) + '</div></li>').join("");
  const dist = a.people.map(p => '<tr><td>' + esc(p.name) + '</td><td>' + gbp(p.entitlement) + '</td><td>' + gbp(p.paid) + '</td><td>' + gbp(p.due) + '</td></tr>').join("");
  return '<div class="firm-card"><h2>What is left to share</h2><p class="lead">' + gbp(t.expected_net) + '</p><p>Collected ' + gbp(t.collected) + ' plus still to collect ' + gbp(t.still_to_collect) + ' and income ' + gbp(t.income) + ', after costs ' + gbp(t.costs) + ', debts ' + gbp(t.debts) + ', funeral ' + gbp(t.funeral) + ' and the tax estimate ' + gbp(t.tax) + '. Cash held now is ' + gbp(t.cash_in_hand) + '.</p>'
    + (a.warnings || []).map(w => '<p class="alert">' + esc(w) + '</p>').join("")
    + '<h3>In the estate</h3><table class="tbl"><thead><tr><th>Item</th><th>At death</th><th>Collected</th><th>Still to collect</th><th>Income</th><th>Costs</th></tr></thead><tbody>' + (cap || '<tr><td colspan="6" class="muted">No assets in the probate estate yet.</td></tr>') + '</tbody></table>'
    + (out ? '<h3>Not in these figures</h3><ul>' + out + '</ul>' : "")
    + '<h3>Shares</h3><table class="tbl"><thead><tr><th>Person</th><th>Their share</th><th>Paid</th><th>Still due</th></tr></thead><tbody>' + (dist || '<tr><td colspan="4" class="muted">Add the people on the figures tab.</td></tr>') + '</tbody></table></div>';
}
function formsPanel(m) {
  const f = m.forms;
  if (!f) return '<div class="firm-card"><p>Court and tax working papers are kept on probate matters.</p></div>';
  return '<div class="firm-card"><h2>' + esc(f.grant) + '</h2><p>' + esc(f.route) + '. ' + (f.excepted ? "Full details are not sent to HMRC on these answers." : "These answers need full details on form IHT400.") + '</p><p class="small">' + esc(f.notice) + '</p>'
    + (f.blockers || []).map(x => '<p class="alert">' + esc(x) + '</p>').join("")
    + (f.reasons || []).map(x => '<p class="small">' + esc(x) + '</p>').join("")
    + f.schedule.map(s => '<section class="stage"><h3>' + esc(s.code) + ' — ' + esc(s.label) + '</h3><table class="tbl">' + s.rows.map(r => '<tr><th>' + esc(r[0]) + '</th><td>' + esc(r[1]) + '</td></tr>').join("") + '</table></section>').join("")
    + '<p><a class="btn ghost" href="/api/firm/matters/' + esc(m.id) + '/export">Download the file for the case system</a></p></div>';
}
function papersPanel(m) {
  const f = m.filing || { blockers: [], steps: [], hmrc: {}, hmcts: {}, notice: "" };
  const h = f.hmrc || {};
  const papers = (m.papers || []).map(p => {
    const ideas = (p.suggestions || []).filter(s => s.mode !== "note" || String(s.label).startsWith("Executor")).map(s => '<label class="check"><input type="checkbox" name="pick" value="' + esc(s.id) + '" checked> ' + esc(s.label) + "</label>").join("");
    return '<article class="stage"><b>' + esc(p.filename) + '</b> <span class="who">' + esc(p.kind) + "</span>"
      + (p.read_as === "scanned-pdf" || p.read_as === "image" ? '<p class="small">No text could be read from this scan. Type the figures, or upload a file that contains text.</p>' : "")
      + (ideas ? '<form class="apply">' + ideas + '<p><button class="btn" type="submit">Add the ticked items to the estate</button></p></form>' : '<p class="small">Nothing on this paper can be copied across.</p>')
      + '<p><a href="/api/firm/matters/' + esc(m.id) + "/uploads/" + esc(p.id) + '">Download</a></p></article>';
  }).join("");
  return '<div class="firm-card"><h2>Upload the papers</h2><p>Will, death certificate or bank letter. The desk reads the text and offers the names and amounts. Nothing is added until you tick it.</p>'
    + '<form id="up"><label>What it is<select name="kind"><option>Will</option><option>Codicil</option><option>Death certificate</option><option>Bank or valuation letter</option><option>Other</option></select></label>'
    + '<input type="file" name="file" required accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.heic,.webp"> <button class="btn" type="submit">Upload</button></form>' + papers + "</div>"
    + '<div class="firm-card"><h2>Filing</h2><p>' + esc(f.notice) + "</p>"
    + (f.blockers || []).map(b => '<p class="alert">' + esc(b) + "</p>").join("")
    + "<ol>" + (f.steps || []).map(s => "<li>" + esc(s) + "</li>").join("") + "</ol>"
    + (h.needed ? '<p><a href="' + esc(h.url) + '">Official IHT400</a> · <a href="' + esc(h.pay_url) + '">Pay Inheritance Tax</a></p>' : "<p>These answers do not ask for a full IHT400.</p>")
    + '<p><a href="' + esc((f.hmcts || {}).url || "") + '">MyHMCTS: how a firm files the grant</a></p>'
    + '<p><a class="btn" href="/api/firm/matters/' + esc(m.id) + '/pack">Download the working pack</a></p>'
    + '<form id="filed"><label>HMRC code, when they send it<input name="hmrc_code" value="' + esc(h.hmrc_code || "") + '"></label>'
    + '<label>Date the IHT400 was posted<input type="date" name="hmrc_posted_on" value="' + esc(h.hmrc_posted_on || "") + '"></label>'
    + '<label>Date the grant was filed<input type="date" name="grant_filed_on" value="' + esc(h.grant_filed_on || "") + '"></label>'
    + '<label>MyHMCTS reference<input name="grant_reference" value="' + esc(h.grant_reference || "") + '"></label>'
    + '<p><button class="btn" type="submit">Record what the firm has filed</button></p><p class="small">This updates your file only. It does not contact HMRC or HMCTS.</p></form></div>';
}
function lettersPanel(m) {
  const saved = ((m.books || {}).letters || []).slice().reverse().map(l => '<article class="stage"><h3>' + esc(l.title) + '</h3><p class="muted small">' + esc(l.by) + '</p><div class="letter">' + esc(l.body) + '</div></article>').join("");
  return '<div class="firm-card"><h2>Letters from these figures</h2><p>Each letter uses the list you have already typed. Keep a copy on the file.</p>'
    + '<p><button class="btn" type="button" data-letter="bank">Ask for date-of-death values</button> <button class="btn ghost" type="button" data-letter="beneficiary">Update the beneficiaries</button> <button class="btn ghost" type="button" data-letter="grant">Write after the grant</button></p>'
    + '<div id="preview"></div>' + saved + '</div>';
}
function bind(id, m) {
  const reload = () => matter(id);
  const meta = document.getElementById("meta");
  if (meta) meta.onsubmit = async (e) => { e.preventDefault(); await api("/api/firm/matters/" + id, { method: "PATCH", body: Object.fromEntries(new FormData(e.target).entries()) }); reload(); };
  $desk.querySelectorAll("[data-item]").forEach(sel => sel.onchange = async () => { await api("/api/firm/matters/" + id, { method: "PATCH", body: { item_id: sel.dataset.item, item_status: sel.value } }); });
  const req = document.getElementById("req");
  if (req) req.onclick = async () => showAssist(await api("/api/firm/matters/" + id + "/assist", { method: "POST", body: { action: "request" } }));
  const chk = document.getElementById("chk");
  if (chk) chk.onclick = async () => showAssist(await api("/api/firm/matters/" + id + "/assist", { method: "POST", body: { action: "check" } }));
  const draft = document.getElementById("draft");
  if (draft) draft.onclick = async () => { const r = await api("/api/firm/matters/" + id + "/draft", { method: "POST", body: {} }); location.href = "/#/d/" + r.draft_id + "/0"; };
  const note = document.getElementById("note");
  if (note) note.onsubmit = async (e) => { e.preventDefault(); await api("/api/firm/matters/" + id, { method: "PATCH", body: { note: new FormData(e.target).get("note") } }); reload(); };
  const add = document.getElementById("add");
  if (add) add.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    books.lines.push({ name: fd.get("name"), holder: fd.get("holder"), side: fd.get("side"), ownership: fd.get("ownership"), value: fd.get("value"), realised: fd.get("realised"), income: fd.get("income"), costs: fd.get("costs"), joint: fd.get("joint") ? "Yes" : "No", abroad: fd.get("abroad") ? "Yes" : "No", funeral: !!fd.get("funeral"), paid: !!fd.get("paid") });
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  };
  $desk.querySelectorAll("[data-drop]").forEach(b => b.onclick = async () => {
    const books = m.books;
    books.lines = books.lines.filter(ln => ln.id !== b.dataset.drop);
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  });
  const person = document.getElementById("person");
  if (person) person.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    books.people.push({ name: fd.get("name"), relationship: fd.get("relationship"), specific: fd.get("specific"), share: fd.get("share"), paid: fd.get("paid") });
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  };
  $desk.querySelectorAll("[data-drop-person]").forEach(b => b.onclick = async () => {
    const books = m.books;
    books.people = books.people.filter(p => p.id !== b.dataset.dropPerson);
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  });
  const caseForm = document.getElementById("case");
  if (caseForm) caseForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    const c = Object.fromEntries(fd.entries());
    c.home_to_descendants = fd.get("home_to_descendants") ? "Yes" : "No";
    c.earlier_spouse_died = fd.get("earlier_spouse_died") ? "Yes" : "No";
    books.case = c;
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  };
  const filed = document.getElementById("filed");
  if (filed) filed.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id, { method: "PATCH", body: Object.fromEntries(new FormData(e.target).entries()) });
    reload();
  };
  const up = document.getElementById("up");
  if (up) up.onsubmit = async (e) => {
    e.preventDefault();
    const headers = { "X-CSRF-Token": decodeURIComponent(await ensureCsrf()) };
    const res = await fetch("/api/firm/matters/" + id + "/uploads", { method: "POST", credentials: "same-origin", headers, body: new FormData(e.target) });
    const data = await res.json().catch(() => null);
    if (!res.ok) { alert((data && data.detail) || "Upload failed"); return; }
    reload();
  };
  $desk.querySelectorAll("form.apply").forEach(form => form.onsubmit = async (e) => {
    e.preventDefault();
    const suggestion_ids = [...form.querySelectorAll("input:checked")].map(i => i.value);
    await api("/api/firm/matters/" + id + "/apply", { method: "POST", body: { suggestion_ids } });
    reload();
  });
  $desk.querySelectorAll("[data-letter]").forEach(b => b.onclick = async () => {
    const r = await api("/api/firm/matters/" + id + "/letters", { method: "POST", body: { kind: b.dataset.letter } });
    document.getElementById("preview").innerHTML = '<h3>' + esc(r.letter.title) + '</h3><div class="letter">' + esc(r.letter.body) + '</div>';
    m.books = r.matter.books;
  });
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
  try {
    const me = await api("/api/auth/me");
    ME = me.user && (me.user.role === "staff" || me.user.role === "admin") ? me.user : null;
    route();
  } catch (err) {
    if ($desk) $desk.innerHTML = '<div class="firm-card" style="max-width:460px;margin:40px auto"><h1>Firm desk</h1><p>' + esc(err.message || "The desk could not load.") + '</p><p><a class="btn" href="/firm">Try again</a></p></div>';
  }
})();
