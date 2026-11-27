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
  const view = new URLSearchParams(location.search).get("view");
  if (!ME) return login();
  if (view === "accounts") return accounts();
  if (id === "new") return newer();
  if (id) return matter(id);
  return list();
}
function nav() {
  const el = document.getElementById("firm-nav");
  if (!ME) { el.innerHTML = '<a href="/">Public site</a>'; return; }
  el.innerHTML = '<a href="/firm">Today</a><a href="/firm?view=accounts">Accounts</a><a href="/#/law">Law updates</a><a href="/firm?m=new">New matter</a><a href="/">Public site</a><button type="button" class="linkbtn" id="out">Sign out</button>';
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

async function accounts() {
  nav();
  const [data, book] = await Promise.all([api("/api/firm/accounts"), api("/api/firm/client-account")]);
  const t = data.totals;
  const options = (book.matters || []).map(m => '<option value="' + esc(m.id) + '">' + esc(m.title) + '</option>').join("");
  const ledgers = (book.ledgers || []).map(row => '<tr><td>' + esc(row.title) + '</td><td>' + gbp(row.balance) + '</td></tr>').join("");
  const movements = (book.entries || []).map(row => '<tr><td>' + esc(row.on || "") + '</td><td>' + esc(row.kind === "in" ? "In" : row.kind === "out" ? "Out" : "To office") + '</td><td>' + esc(row.what) + '</td><td>' + gbp(row.amount) + '</td></tr>').join("");
  const verdict = book.agrees ? "The cash book, the client ledgers and the bank statement agree." : "They do not agree. Cash book " + gbp(book.cash_book) + ", ledgers " + gbp(book.ledger_total) + ", bank after adjustments " + gbp(book.adjusted_bank) + ".";
  $desk.innerHTML = '<p class="eyebrow">Firm desk</p><h1>Accounts</h1><p><button type="button" class="btn ghost" id="accounts-excel">Excel</button></p>'
    + '<div class="firm-card"><h2>Office account</h2><p>Time, bills and money the firm has earned. This is not client money.</p>'
    + '<div class="figure-strip"><div><span>Not yet billed</span><b>' + gbp(t.unbilled) + '</b></div><div><span>Billed</span><b>' + gbp(t.billed) + '</b></div><div><span>Received</span><b>' + gbp(t.paid) + '</b></div><div><span>Still owed</span><b>' + gbp(t.outstanding) + '</b></div></div>'
    + '<table class="tbl"><thead><tr><th>Matter</th><th>Not yet billed</th><th>Billed</th><th>Still owed</th></tr></thead><tbody>'
    + data.matters.map(m => '<tr><td><a href="/firm?m=' + esc(m.id) + '">' + esc(m.title) + '</a><div class="small">' + esc(m.client_name) + ' · ' + esc(m.kind_label) + '</div></td><td>' + gbp(m.bill.unbilled) + '</td><td>' + gbp(m.bill.billed) + '</td><td>' + gbp(m.bill.outstanding) + '</td></tr>').join("")
    + '</tbody></table></div>'
    + '<div class="firm-card"><h2>Client account</h2><p>Money held for clients. A payment that would take a client below zero is refused. A transfer to the office account is also recorded as money received on that matter’s bill.</p>'
    + '<div class="figure-strip"><div><span>Cash book</span><b>' + gbp(book.cash_book) + '</b></div><div><span>Client ledgers</span><b>' + gbp(book.ledger_total) + '</b></div></div>'
    + '<form id="client-entry"><label>Matter<select name="matter_id" required>' + options + '</select></label>'
    + '<label>Movement<select name="kind"><option value="in">Money in</option><option value="out">Money out</option><option value="transfer">Transfer to the office account</option></select></label>'
    + '<label>Date<input type="date" name="on"></label><label>What<input name="what" required></label><label>Amount (£)<input name="amount" type="number" min="0.01" step="0.01" required></label><label>Reference<input name="reference"></label>'
    + '<p><button class="btn" type="submit">Post to the client account</button></p></form>'
    + (movements ? '<table class="tbl"><thead><tr><th>Date</th><th></th><th>What</th><th>Amount</th></tr></thead><tbody>' + movements + '</tbody></table>' : '')
    + '</div>'
    + '<div class="firm-card"><h2>Three-way reconciliation</h2><p>' + verdict + '</p>'
    + '<form id="client-statement"><label>Statement date<input type="date" name="on" value="' + esc(book.statement_on || "") + '"></label>'
    + '<label>Balance on the bank statement (£)<input name="balance" type="number" min="0" step="0.01" value="' + Number(book.statement || 0) + '"></label>'
    + '<label>Unpresented cheques (£)<input name="unpresented" type="number" min="0" step="0.01" value="' + Number(book.unpresented || 0) + '"></label>'
    + '<label>Paid in, not yet on the statement (£)<input name="outstanding" type="number" min="0" step="0.01" value="' + Number(book.outstanding || 0) + '"></label>'
    + '<p><button class="btn" type="submit">Reconcile</button></p></form>'
    + (ledgers ? '<table class="tbl"><thead><tr><th>Client ledger</th><th>Balance</th></tr></thead><tbody>' + ledgers + '</tbody></table>' : '<p class="small">No client money has been posted.</p>')
    + '<p><button type="button" class="btn" id="sign-off">Sign off this reconciliation</button> <button type="button" class="btn ghost" id="breach">Record a breach</button></p>'
    + '<p class="note">Sign-off is kept, and it is refused while the three figures do not agree. The bank figure is the one typed from the statement. This desk is not connected to the bank.</p>'
    + (book.signoffs && book.signoffs.length ? '<p class="small">Last signed off by ' + esc(book.signoffs[book.signoffs.length - 1].by) + ' on ' + esc((book.signoffs[book.signoffs.length - 1].at || "").slice(0, 10)) + '.</p>' : '')
    + ((book.breaches || []).length ? '<ul>' + book.breaches.slice().reverse().map(row => '<li>' + esc((row.at || "").slice(0, 10)) + ' · ' + esc(row.by) + ' · ' + esc(row.note) + '</li>').join("") + '</ul>' : '')
    + '</div>';
  document.getElementById("accounts-excel").onclick = () => downloadSheet("firm-accounts.csv", [["Matter", "Not yet billed", "Billed", "Still owed"]].concat(data.matters.map(m => [m.title, m.bill.unbilled, m.bill.billed, m.bill.outstanding])));
  document.getElementById("client-entry").onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target).entries());
    body.amount = Number(body.amount);
    try { await api("/api/firm/client-account/entries", { method: "POST", body }); accounts(); }
    catch (err) { alert(err.message); }
  };
  document.getElementById("client-statement").onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target).entries());
    ["balance", "unpresented", "outstanding"].forEach(key => { body[key] = Number(body[key] || 0); });
    try { await api("/api/firm/client-account/statement", { method: "PUT", body }); accounts(); }
    catch (err) { alert(err.message); }
  };
  document.getElementById("sign-off").onclick = async () => {
    const note = prompt("Note for the sign-off, if you want one") || "";
    try { await api("/api/firm/client-account/sign-off", { method: "POST", body: { note } }); accounts(); }
    catch (err) { alert(err.message); }
  };
  document.getElementById("breach").onclick = async () => {
    const note = prompt("What went wrong?");
    if (!note) return;
    try { await api("/api/firm/client-account/breach", { method: "POST", body: { note } }); accounts(); }
    catch (err) { alert(err.message); }
  };
}
async function list() {
  nav();
  const [rows, link, outlook, day] = await Promise.all([api("/api/firm/matters"), api("/api/firm/actionstep"), api("/api/firm/outlook"), api("/api/firm/today")]);
  const connect = ME && ME.role === "admin"
    ? '<form id="actionstep"><p class="small">An admin pastes the access token and the API address from Actionstep’s token response. The token is stored for the firm. It is not shown again.</p><label>API address<input name="api_endpoint" placeholder="' + esc(link.api_endpoint || "https://….actionstep.com/api/") + '"></label><label>Access token<input name="access_token" type="password" autocomplete="off"></label><label>Refresh token<input name="refresh_token" type="password" autocomplete="off"></label><label>Client id<input name="client_id" autocomplete="off"></label><label>Client secret<input name="client_secret" type="password" autocomplete="off"></label><p><button class="btn" type="submit">Save the Actionstep connection</button></p></form>'
    : '<p class="small">An admin connects Actionstep. Staff can then bring a matter across.</p>';
  const outlookForm = ME && ME.role === "admin"
    ? '<form id="outlook"><label>Access token<input name="access_token" type="password" autocomplete="off"></label><p><button class="btn" type="submit">Save the Outlook connection</button></p></form>'
    : '<p class="small">An admin connects Outlook. Staff can then file a message onto a matter.</p>';
  const matterOptions = rows.map(m => '<option value="' + esc(m.id) + '">' + esc(m.title) + '</option>').join("");
  const taskRows = (day.tasks || []).map(t => '<li><a href="/firm?m=' + esc(t.matter_id) + '">' + esc(t.title) + '</a> <span class="small">' + esc(t.matter) + (t.due ? " · " + esc(t.due) : "") + '</span></li>').join("");
  const apptRows = (day.appointments || []).map(t => '<li><a href="/firm?m=' + esc(t.matter_id) + '">' + esc(t.title) + '</a> <span class="small">' + esc(t.on || "No date") + (t.time ? " " + esc(t.time) : "") + " · " + esc(t.matter) + '</span></li>').join("");
  const nextRows = (day.next || []).map(t => '<li><a href="/firm?m=' + esc(t.id) + '">' + esc(t.title) + '</a> <span class="small">' + esc(t.next) + '</span></li>').join("");
  const left = (day.residuals || []).map(t => '<li><a href="/firm?m=' + esc(t.matter_id) + '">' + esc(t.title) + '</a> ' + gbp(t.balance) + '</li>').join("");
  $desk.innerHTML = '<p class="eyebrow">Firm desk</p><h1>Today</h1><p class="note">One place for the open files, the tasks, the appointments and the client account. The will, the powers of attorney, the tax forms and the estate account stay on the file. ' + esc(day.note || "") + '</p>'
    + '<form id="find-all" class="line-form"><input name="q" placeholder="Search a client, a matter, a task or an appointment" minlength="2" required><button class="btn" type="submit">Search</button></form><div id="found"></div>'
    + '<div class="figure-strip"><div><span>Open files</span><b>' + day.open + '</b></div><div><span>Tasks still to do</span><b>' + day.tasks_open + '</b></div><div><span>Client account</span><b>' + (day.client_agrees ? "Agrees" : "Does not agree") + '</b></div><div><span>Closed files still holding client money</span><b>' + (day.residuals || []).length + '</b></div></div>'
    + '<div class="firm-grid"><div class="firm-card"><h2>Tasks</h2>' + (taskRows ? '<ul>' + taskRows + '</ul>' : '<p class="small">No open task. Add one from the file.</p>') + '</div>'
    + '<div class="firm-card"><h2>Appointments</h2>' + (apptRows ? '<ul>' + apptRows + '</ul>' : '<p class="small">No appointment. Add one from the file.</p>') + '</div></div>'
    + '<div class="firm-grid"><div class="firm-card"><h2>Next on each file</h2>' + (nextRows ? '<ul>' + nextRows + '</ul>' : '<p class="small">No open file.</p>') + '</div>'
    + '<div class="firm-card"><h2>Client money on a closed file</h2>' + (left ? '<ul>' + left + '</ul>' : '<p class="small">None. A closed file should not still hold client money.</p>') + '</div></div>'
    + '<p><a class="btn" href="/firm?m=new">New matter</a> <button type="button" class="btn ghost" id="matters-excel">Excel</button></p>'
    + '<div class="firm-card"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Matter</th><th>Type</th><th>Next</th><th>Done</th></tr></thead><tbody>'
    + (rows.length ? rows.map(m => '<tr><td><a href="/firm?m=' + esc(m.id) + '">' + esc(m.title) + '</a><div class="muted small">' + esc(m.client_name || "No client name") + (m.deceased_name ? " · estate of " + esc(m.deceased_name) : "") + (m.figures ? " · net " + gbp(m.figures.net_probate) : "") + '</div></td><td>' + esc(m.kind_label) + '</td><td>' + (m.next ? esc(m.next.title) : "Checklist complete") + '</td><td>' + m.progress.done + "/" + m.progress.total + '</td></tr>').join("") : '<tr><td colspan="4" class="muted">No matters yet.</td></tr>')
    + '</tbody></table></div></div>'
    + '<details class="firm-card"><summary>Actionstep and Outlook</summary>'
    + '<h2>Actionstep</h2><p class="note">' + (link.connected ? "Connected" + (link.api_endpoint ? " · " + esc(link.api_endpoint) : "") + "." : "Not connected.") + ' <a href="https://docs.actionstep.com/authentication/" target="_blank" rel="noopener">How a firm gets a token</a></p>'
    + connect
    + (link.connected ? '<p><button class="btn" type="button" id="actionstep-load">Show matters in Actionstep</button></p><div id="actionstep-list"></div>' : "")
    + '<h2>Outlook</h2><p class="note">' + (outlook.connected ? "Connected. A message is filed only after Outlook has returned it." : "Not connected.") + ' <a href="https://learn.microsoft.com/en-us/graph/auth/" target="_blank" rel="noopener">How a firm gets a Microsoft Graph token</a></p>'
    + outlookForm
    + (outlook.connected ? '<p><button class="btn" type="button" id="outlook-load">Show Outlook mail</button></p><div id="outlook-list"></div>' : "")
    + '</details>';
  document.getElementById("matters-excel").onclick = () => downloadSheet("matters.csv", [["Matter", "Client", "Type", "Next", "Done"]].concat(rows.map(m => [m.title, m.client_name || "", m.kind_label, m.next ? m.next.title : "Checklist complete", m.progress.done + "/" + m.progress.total])));
  document.getElementById("find-all").onsubmit = async (e) => {
    e.preventDefault();
    const q = new FormData(e.target).get("q");
    const found = await api("/api/firm/find?q=" + encodeURIComponent(q));
    const hits = found.hits || [];
    document.getElementById("found").innerHTML = hits.length
      ? '<ul>' + hits.map(hit => '<li><span class="small">' + esc(hit.kind) + '</span> <a href="/firm?m=' + esc(hit.id) + '">' + esc(hit.label) + '</a> <span class="small">' + esc(hit.detail) + '</span></li>').join("") + '</ul>'
      : '<p class="note">Nothing on this desk matches.</p>';
  };
  const form = document.getElementById("actionstep");
  if (form) form.onsubmit = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/firm/actionstep", { method: "PUT", body });
    list();
  };
  const load = document.getElementById("actionstep-load");
  if (load) load.onclick = async () => {
    load.disabled = true;
    try {
      const found = await api("/api/firm/actionstep/matters", { method: "POST", body: {} });
      const box = document.getElementById("actionstep-list");
      const items = found.matters || [];
      box.innerHTML = items.length ? items.map(m => '<p><button type="button" class="btn ghost" data-action="' + esc(m.id) + '">Bring across</button> ' + esc(m.name) + (m.reference ? " · " + esc(m.reference) : "") + (m.status ? " · " + esc(m.status) : "") + "</p>").join("") : '<p class="small">Actionstep returned no matters.</p>';
      box.querySelectorAll("[data-action]").forEach(b => b.onclick = async () => {
        const made = await api("/api/firm/actionstep/import", { method: "POST", body: { action_id: b.dataset.action } });
        location.href = "/firm?m=" + made.id;
      });
    } catch (err) {
      load.disabled = false;
      alert(err.message);
    }
  };
  const outlookSave = document.getElementById("outlook");
  if (outlookSave) outlookSave.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("/api/firm/outlook", { method: "PUT", body: Object.fromEntries(new FormData(e.target).entries()) });
      list();
    } catch (err) { alert(err.message); }
  };
  const outlookLoad = document.getElementById("outlook-load");
  if (outlookLoad) outlookLoad.onclick = async () => {
    outlookLoad.disabled = true;
    try {
      const box = document.getElementById("outlook-list");
      const mail = await api("/api/firm/outlook/mailbox", { method: "POST", body: {} });
      const events = (mail.events || []).map(ev => '<li>' + esc(ev.start || "") + " " + esc(ev.subject) + "</li>").join("");
      box.innerHTML = (events ? '<p class="small">Diary</p><ul>' + events + '</ul>' : '')
        + (mail.messages || []).map(m => '<p><b>' + esc(m.subject) + '</b><br><span class="small">' + esc(m.from) + '</span><br>' + esc(m.preview) + '<br><label class="small">File on <select data-matter>' + matterOptions + '</select></label> <button type="button" class="btn ghost" data-mail="' + esc(m.id) + '">File this message</button></p>').join("");
      box.querySelectorAll("[data-mail]").forEach(b => b.onclick = async () => {
        const matter = b.parentElement.querySelector("[data-matter]").value;
        try {
          await api("/api/firm/outlook/file", { method: "POST", body: { message_id: b.dataset.mail, matter_id: matter } });
          b.textContent = "Filed";
          b.disabled = true;
        } catch (err) { alert(err.message); }
      });
    } catch (err) {
      outlookLoad.disabled = false;
      alert(err.message);
    }
  };
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
function downloadSheet(filename, rows) {
  const csv = rows.map(r => r.map(c => '"' + String(c ?? "").replace(/"/g, '""') + '"').join(",")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = filename;
  a.click();
}
let TAB = "next";
let OPEN = "";

async function matter(id) {
  nav();
  const [m, staff] = await Promise.all([api("/api/firm/matters/" + id), api("/api/firm/colleagues")]);
  if (OPEN !== id) { OPEN = id; TAB = m.kind === "probate" ? "papers" : "file"; }
  const tabs = [["next", "1. Next"], ["lexcel", "2. Lexcel"], ["papers", "3. Papers"], ["money", "4. Figures"], ["accounts", "5. Estate account"], ["forms", "6. Forms"], ["find", "7. Find accounts"], ["letters", "8. Letters"], ["file", "9. File"], ["scheme", "10. WIQS"], ["bill", "11. Bill"]];
  let showTabs = m.kind === "probate" ? tabs : [["next", "1. Next"], ["lexcel", "2. Lexcel"], ["letters", "3. Letters"], ["file", "4. File"], ["scheme", "5. WIQS"], ["bill", "6. Bill"]];
  if (m.kind === "trust") showTabs = [["next", "1. Next"], ["lexcel", "2. Lexcel"], ["trust", "3. Trust account"], ["letters", "4. Letters"], ["file", "5. File"], ["scheme", "6. WIQS"], ["bill", "7. Bill"]];
  if (m.kind === "deputyship") showTabs = [["next", "1. Next"], ["lexcel", "2. Lexcel"], ["deputy", "3. The person's money"], ["letters", "4. Letters"], ["file", "5. File"], ["scheme", "6. WIQS"], ["bill", "7. Bill"]];
  if (!showTabs.some(t => t[0] === TAB)) TAB = "next";
  const strip = m.figures ? '<div class="figure-strip">'
    + [["Probate gross", m.figures.gross_probate], ["Probate net", m.figures.net_probate], ["Tax estimate", m.figures.tax], ["Still to collect", m.accounts.totals.still_to_collect], ["Left to share", m.accounts.totals.expected_net]].map(([l, n]) => '<div><span>' + l + '</span><b>' + gbp(n) + '</b></div>').join("")
    + '<div><span>' + (m.figures.excepted ? "No full tax return" : "Full tax details") + '</span><b>' + esc(m.figures.route) + '</b></div></div>' : "";
  $desk.innerHTML = '<div class="matter-head"><div><p><a href="/firm">All matters</a></p><h1>' + esc(m.title) + '</h1>'
    + '<p class="muted">' + esc(m.kind_label) + (m.deceased_name ? " · " + esc(m.deceased_name) : "") + " · " + esc(m.client_name || "No client yet") + '</p></div>' + strip + '</div>'
    + '<div class="work"><nav class="steps" aria-label="Matter steps">' + showTabs.map(([k, label]) => '<button type="button" class="btn ' + (TAB === k ? "" : "ghost") + '" data-tab="' + k + '">' + label + '</button>').join("") + '</nav>'
    + '<div id="panel"></div></div>';
  $desk.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => { TAB = b.dataset.tab; matter(id); });
  const panel = document.getElementById("panel");
  if (TAB === "money") panel.innerHTML = moneyPanel(m, staff);
  else if (TAB === "accounts") panel.innerHTML = accountsPanel(m);
  else if (TAB === "forms") panel.innerHTML = formsPanel(m);
  else if (TAB === "find") panel.innerHTML = findPanel(m);
  else if (TAB === "papers") panel.innerHTML = papersPanel(m);
  else if (TAB === "file") panel.innerHTML = filePanel(m);
  else if (TAB === "scheme") panel.innerHTML = schemePanel(m);
  else if (TAB === "lexcel") panel.innerHTML = lexcelPanel(m);
  else if (TAB === "letters") panel.innerHTML = lettersPanel(m);
  else if (TAB === "bill") panel.innerHTML = billPanel(m);
  else if (TAB === "trust") panel.innerHTML = trustPanel(m);
  else if (TAB === "deputy") panel.innerHTML = deputyPanel(m);
  else panel.innerHTML = nextPanel(m, staff);
  bind(id, m);
}

function billPanel(m) {
  const b = m.bill || {};
  const rows = (m.bill_entries || []).map(e => '<tr><td>' + esc(e.on || "") + '</td><td>' + esc(e.kind) + '</td><td>' + esc(e.what) + '</td><td>' + gbp(e.amount) + '</td></tr>').join("");
  return '<div class="firm-card"><h2>Bill</h2><p class="note">Lexcel 6.4 and 7.4: the client still needs a written costs estimate at the start, and a further note before that estimate is exceeded. This list is the firm’s record. It is not that letter.</p>'
    + '<div class="figure-strip"><div><span>Not yet billed</span><b>' + gbp(b.unbilled) + '</b></div><div><span>Billed</span><b>' + gbp(b.billed) + '</b></div><div><span>Received</span><b>' + gbp(b.paid) + '</b></div><div><span>Still owed</span><b>' + gbp(b.outstanding) + '</b></div></div>'
    + (rows ? '<table class="tbl"><thead><tr><th>Date</th><th>Type</th><th>What</th><th>Amount</th></tr></thead><tbody>' + rows + '</tbody></table>' : '')
    + '<form id="bill"><label>Type<select name="kind"><option value="time">Time</option><option value="cost">Cost paid for the client</option><option value="bill">Bill</option><option value="paid">Money received</option></select></label>'
    + '<label>Date<input type="date" name="on"></label><label>What<input name="what" required></label>'
    + '<label>Hours<input name="hours" type="number" min="0" step="0.1"></label><label>Rate (£)<input name="rate" type="number" min="0" step="0.01"></label><label>Amount (£)<input name="amount" type="number" min="0" step="0.01"></label>'
    + '<p class="small">For time, hours times the rate is used when both are filled in.</p><p><button class="btn" type="submit">Add</button></p></form></div>';
}
function potPanel(m, key, title, note, pots) {
  const book = m[key] || { lines: [] };
  const rows = (book.lines || []).map(ln => '<tr><td>' + esc(ln.name) + '</td><td>' + esc(ln.pot) + '</td><td>' + (ln.out ? "Out" : "In") + '</td><td>' + gbp(ln.amount) + '</td></tr>').join("");
  const totals = pots.map(([id, label]) => {
    const t = book[id] || { in: 0, out: 0, balance: 0 };
    return '<div><span>' + label + '</span><b>' + gbp(t.balance) + '</b></div>';
  }).join("");
  return '<div class="firm-card"><h2>' + title + '</h2><p>' + note + '</p><div class="figure-strip">' + totals + '</div>'
    + (rows ? '<table class="tbl"><thead><tr><th>Item</th><th>Pot</th><th></th><th>Amount</th></tr></thead><tbody>' + rows + '</tbody></table>' : '')
    + '<form id="' + key + '"><label>Item<input name="name" required></label><label>Pot<select name="pot">' + pots.map(([id, label]) => '<option value="' + id + '">' + label + '</option>').join("") + '</select></label>'
    + '<label>In or out<select name="out"><option value="">In</option><option value="Yes">Out</option></select></label><label>Amount (£)<input name="amount" type="number" min="0" step="0.01" required></label>'
    + '<p><button class="btn" type="submit">Add</button></p></form></div>';
}
function trustPanel(m) {
  return potPanel(m, "trust", "Trust account", "Capital and income are kept apart. A solicitor approves the account before it goes to a beneficiary. Nothing is paid from this screen.", [["capital", "Capital"], ["income", "Income"]])
    + '<div class="firm-card"><h2>Register the trust</h2><p>If this is a trust in England and Wales, the lead trustee registers it on HMRC’s Trust Registration Service unless an exclusion applies. A trust that exists only in a will is not registered while the person is alive. This desk prepares the particulars. It does not send them.</p><p><button type="button" class="btn" id="trust-register">Prepare the registration pack</button></p></div>';
}
function deputyPanel(m) {
  return potPanel(m, "deputy", "The person's money", "This is the deputy's record. It is not mixed with the firm's money. The Office of the Public Guardian is not sent anything from here.", [["money", "Balance"]])
    + '<div class="firm-card"><p>This person is alive. If someone else might change their accounts, or a company should not sell to them, the firm can register them on the <a href="https://www.vulnerabilityregistrationservice.co.uk/" target="_blank" rel="noopener">Vulnerability Registration Service</a>. It is not used on a probate file.</p></div>';
}
function practiceForm(m) {
  const p = m.practice || {};
  const opt = (list, current) => list.map(v => '<option' + (current === v ? " selected" : "") + '>' + esc(v) + '</option>').join("");
  return '<form id="practice"><label>Identity<select name="identity">' + opt(["Not seen", "Seen", "Certified copy on the file"], p.identity) + '</select></label>'
    + '<label>Identity service<input name="id_provider" value="' + esc(p.id_provider || "") + '"></label><label>Their reference<input name="id_reference" value="' + esc(p.id_reference || "") + '"></label><label>Date of that check<input type="date" name="id_checked_on" value="' + esc(p.id_checked_on || "") + '"></label>'
    + '<p class="small">If the firm used an identity service, record it here. This desk does not run the check.</p>'
    + '<label>Source of funds<textarea name="source">' + esc(p.source || "") + '</textarea></label>'
    + '<label>Risk<select name="risk">' + opt(["Ordinary", "Higher"], p.risk) + '</select></label>'
    + '<label>Why the risk is higher<textarea name="risk_note">' + esc(p.risk_note || "") + '</textarea></label>'
    + '<label>Where the original will or deed is<select name="will_held">' + opt(["Not known yet", "With the firm", "With the client", "At a bank", "At the Principal Registry", "Not a will"], p.will_held) + '</select></label>'
    + '<label>Safe or reference<input name="will_ref" value="' + esc(p.will_ref || "") + '"></label>'
    + '<label>Names checked on<input type="date" name="conflict_checked_on" value="' + esc(p.conflict_checked_on || "") + '"></label>'
    + '<label>Conflict note<textarea name="conflict_note">' + esc(p.conflict_note || "") + '</textarea></label>'
    + '<p><button class="btn" type="submit">Save</button></p></form>';
}
function nextPanel(m, staff) {
  const deadlines = (m.deadlines || []).map(d => '<li><b>' + esc(d.label) + '</b>' + (d.date ? " · " + esc(d.date) : "") + '<div class="small">' + esc(d.note) + '</div></li>').join("");
  return '<div class="firm-next"><p class="eyebrow">Do this next</p><h2>' + esc(m.next ? m.next.title : "Checklist complete") + '</h2>'
    + (m.next ? '<p>' + esc(m.next.ask) + '</p><p class="small">' + esc(m.next.stage) + '</p>' : '<p>Every item is received, done, or not needed.</p>')
    + '<p class="small">Lexcel 7.1: this next step is the strategy on the file. Lexcel 5.7: the dates below must also sit in the firm’s own diary.</p></div>'
    + '<div class="firm-grid"><div class="firm-card"><h2>Tasks</h2>'
    + ((m.work && m.work.tasks || []).map(t => '<p><label class="check"><input type="checkbox" data-task="' + esc(t.id) + '"' + (t.done ? " checked" : "") + '> ' + esc(t.title) + (t.due ? " · " + esc(t.due) : "") + (t.who ? " · " + esc(t.who) : "") + '</label></p>').join("") || '<p class="small">No task yet.</p>')
    + '<form id="task" class="line-form"><input name="title" required placeholder="What has to be done"><input type="date" name="due"><input name="who" placeholder="Who"><button class="btn" type="submit">Add task</button></form></div>'
    + '<div class="firm-card"><h2>Appointments</h2>'
    + ((m.work && m.work.appointments || []).map(t => '<p>' + esc(t.on || "No date") + (t.time ? " " + esc(t.time) : "") + " · " + esc(t.title) + (t.where ? " · " + esc(t.where) : "") + '</p>').join("") || '<p class="small">No appointment yet.</p>')
    + '<form id="appointment" class="line-form"><input name="title" required placeholder="Who you are seeing"><input type="date" name="on"><input name="time" placeholder="Time"><input name="where" placeholder="Where"><button class="btn" type="submit">Add appointment</button></form></div></div>'
    + '<div class="firm-grid"><div class="firm-card"><form id="meta"><label>Status<select name="status">' + MATTER.map(([v, l]) => '<option value="' + v + '"' + (m.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></label>'
    + '<label>Worked by<select name="assigned_to"><option value="">Anyone</option>' + staff.map(s => '<option' + (m.assigned_to === s.email ? " selected" : "") + '>' + esc(s.email) + '</option>').join("") + '</select></label>'
    + '<label>Client<input name="client_name" value="' + esc(m.client_name) + '"></label><label>Email<input name="client_email" value="' + esc(m.client_email) + '"></label>'
    + (m.kind === "probate" ? '<label>Person who died<input name="deceased_name" value="' + esc(m.deceased_name) + '"></label><label>Date of death<input name="date_of_death" type="date" value="' + esc(m.date_of_death) + '"></label><label>Date of grant<input name="grant_date" type="date" value="' + esc(m.grant_date) + '"></label>' : "")
    + '<p><button class="btn" type="submit">Save details</button></p></form>'
    + (deadlines ? '<h3>Dates</h3><ul>' + deadlines + '</ul>' : "")
    + '<h3>What you need</h3>' + (m.stages || []).map(stage => '<section class="stage"><h3>' + esc(stage.title) + '</h3>' + stage.items.map(it => '<div class="item"><div><b>' + esc(it.title) + '</b> <span class="who">' + esc(it.who) + '</span><div class="small">' + esc(it.ask) + '</div></div><select data-item="' + esc(it.id) + '">' + STATUSES.map(([v, l]) => '<option value="' + v + '"' + (it.status === v ? " selected" : "") + '>' + l + '</option>').join("") + '</select></div>').join("") + '</section>').join("")
    + '</div><aside><div class="firm-card"><h2>Assistant</h2><p class="small">Writes from this file. It is not a solicitor and it does not file anything.</p><p><button class="btn" type="button" id="req">Write the client email</button></p><p><button class="btn ghost" type="button" id="chk">Check the draft</button></p><div id="assist"></div></div>'
    + '<div class="firm-card"><h2>Draft</h2><p class="small">The questions stay in step with the figures on this matter.</p><p><button class="btn" type="button" id="draft">' + (m.draft_id ? "Open the draft" : "Start the draft") + '</button></p></div>'
    + '<div class="firm-card"><h2>Before you act</h2><p class="small">Identity, where the original is kept, and whether these names are already on another matter. This is the firm’s own record. It is not an electronic identity check.</p>'
    + practiceForm(m)
    + '<div id="conflicts"></div></div>'
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
    + '<form id="add" class="line-form"><input name="name" required placeholder="House, bank, card…"><input name="holder" placeholder="Bank or organisation"><select name="side"><option value="asset">Asset</option><option value="debt">Debt</option></select><select name="kind"><option value="">Work out the type</option><option value="property">House or land</option><option value="bank">Bank account</option><option value="shares">Shares or funds</option><option value="goods">Goods</option><option value="pension">Pension</option><option value="other">Other</option></select><select name="ownership"><option value="sole">Owned alone</option><option value="joint_tenants">Joint tenants</option><option value="tenants_in_common">Tenants in common, their share</option></select><input name="value" type="number" min="0" step="0.01" required placeholder="Value at death"><input name="realised" type="number" min="0" step="0.01" placeholder="Collected, if different"><input name="income" type="number" min="0" step="0.01" placeholder="Income"><input name="costs" type="number" min="0" step="0.01" placeholder="Costs"><label class="check"><input name="joint" type="checkbox"> Joint debt</label><label class="check"><input name="abroad" type="checkbox"> Abroad</label><label class="check"><input name="funeral" type="checkbox"> Funeral</label><label class="check"><input name="paid" type="checkbox"> Paid</label><button class="btn" type="submit">Add</button></form></div>'
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
    + '<form id="person" class="line-form"><input name="name" required placeholder="Name"><input name="relationship" placeholder="Child, friend…"><input name="specific" type="number" min="0" step="0.01" placeholder="Specific gift"><input name="share" type="number" min="0" max="100" step="0.01" placeholder="% of the rest"><input name="paid" type="number" min="0" step="0.01" placeholder="Already paid"><button class="btn" type="submit">Add</button></form><p><button type="button" class="btn ghost" id="equal">Split the rest equally</button></p></div></div>';
}
function accountsPanel(m) {
  const a = m.accounts;
  if (!a) return '<div class="firm-card"><p>Accounts are kept on probate matters.</p></div>';
  const t = a.totals;
  const rows = a.capital.map(r => '<tr><td>' + esc(r.name) + '</td><td>' + gbp(r.dod) + '</td><td>' + gbp(r.collected) + '</td><td>' + gbp(r.still) + '</td><td>' + gbp(r.income) + '</td><td>' + gbp(r.costs) + '</td></tr>').join("");
  const out = a.outside.map(r => '<li><b>' + esc(r.name) + '</b> ' + gbp(r.value) + '<div class="small">' + esc(r.why) + '</div></li>').join("");
  const dist = a.people.map(p => '<tr><td>' + esc(p.name) + '</td><td>' + gbp(p.entitlement) + '</td><td>' + gbp(p.paid) + '</td><td>' + gbp(p.due) + '</td></tr>').join("");
  const step = a.step || {};
  const cap = step.capital_totals || {};
  return '<div class="firm-card"><h2>Estate account</h2><p>' + esc(step.note || "") + '</p><p class="lead">' + gbp(t.expected_net) + ' left to share</p>'
    + (a.warnings || []).map(w => '<p class="alert">' + esc(w) + '</p>').join("")
    + '<h3>Capital account</h3><table class="tbl"><thead><tr><th>Item</th><th>At death</th><th>Collected</th><th>Still to collect</th><th>Income</th><th>Costs</th></tr></thead><tbody>' + (rows || '<tr><td colspan="6" class="muted">No assets in the probate estate yet.</td></tr>') + '</tbody></table>'
    + '<p>At death ' + gbp(cap.at_death) + '. Gains ' + gbp(cap.gains) + '. Losses ' + gbp(cap.losses) + '. Debts ' + gbp(cap.debts) + '. Funeral ' + gbp(cap.funeral) + '. Tax ' + gbp(cap.tax) + '. Specific gifts ' + gbp(cap.legacies) + '.</p><p><b>Balance of capital ' + gbp(cap.balance) + '.</b> Income account ' + gbp(step.income_total) + '.</p>'
    + (out ? '<h3>Not in this account</h3><ul>' + out + '</ul>' : "")
    + '<h3>Distribution account</h3><table class="tbl"><thead><tr><th>Person</th><th>Their share</th><th>Paid</th><th>Still due</th></tr></thead><tbody>' + (dist || '<tr><td colspan="4" class="muted">Add the people on the figures tab. Leave the shares blank to split the rest equally, or type a percentage.</td></tr>') + '</tbody></table>'
    + '<h3>Cash</h3><p>In ' + gbp((step.cash || {}).receipts) + '. Out ' + gbp((step.cash || {}).payments) + '. Should be in hand ' + gbp((step.cash || {}).in_hand) + '.</p>'
    + '<p class="actions"><a class="btn" href="/api/firm/matters/' + esc(m.id) + '/account.xlsx">Excel</a> <a class="btn ghost" href="/api/firm/matters/' + esc(m.id) + '/account.pdf">PDF</a> <a class="btn ghost" href="/api/firm/matters/' + esc(m.id) + '/account.html">Copy you can edit</a></p>'
    + noticePanel(m) + '</div>';
}
function noticePanel(m) {
  const n = ((m.books || {}).notice) || {};
  const land = ((m.books || {}).lines || []).some(ln => ln.kind === "property" && ln.side !== "debt");
  const due = (m.deadlines || []).find(d => d.label.indexOf("Section 27") === 0);
  return '<div class="firm-card"><h2>Section 27 notice</h2><p>The firm places this. The Gazette takes the notice, and in the same order it can place the advert in a local newspaper. You do not need Estatesearch for either. This desk drafts the words and counts the two months. It does not pay The Gazette and it does not send the notice.</p>'
    + (land ? '<p class="alert">There is land on the file, so a local newspaper is required as well as The London Gazette.</p>' : '<p class="small">If land is added later, a local newspaper is required as well.</p>')
    + (due && due.date ? '<p><b>Last day for claims: ' + esc(due.date) + '.</b> ' + esc(due.note) + '</p>' : '<p class="small">The two-month date appears here once you record the day the notice was placed.</p>')
    + '<form id="notice"><label>Date the notice was placed<input type="date" name="placed_on" value="' + esc(n.placed_on || "") + '"></label>'
    + '<label>Gazette reference<input name="gazette_ref" value="' + esc(n.gazette_ref || "") + '"></label>'
    + '<label>Local newspaper<input name="local_paper" value="' + esc(n.local_paper || "") + '" placeholder="Name of the paper, if there is land"></label>'
    + '<label>Where claims should be sent<textarea name="claims_to">' + esc(n.claims_to || "") + '</textarea></label>'
    + '<p><button class="btn" type="submit">Save the notice record</button> <button class="btn ghost" type="button" data-letter="notice">Draft the notice</button></p></form>'
    + '<p><a href="https://www.thegazette.co.uk/wills-and-probate/place-a-deceased-estates-notice" target="_blank" rel="noopener">Place the notice on The Gazette</a></p>'
    + '<p class="small">Paying everyone also waits at least six months from the grant. The section 27 notice does not replace that, and it does not shut out a claim the firm already knows about.</p></div>';
}
function searchPanel(m) {
  const search = ((m.books || {}).asset_search) || { fee: 150, paid: false, items: [] };
  const items = search.items || [];
  const open = items.filter(i => !i.status);
  const live = items.filter(i => i.status);
  const choices = open.map(i => '<label class="check"><input type="checkbox" name="target" value="' + esc(i.id) + '"' + (i.group === "extra" ? "" : " checked") + "> " + esc(i.name) + "</label>").join("");
  const rows = live.map(i => '<tr><td>' + esc(i.name) + '</td><td><select data-search="' + esc(i.id) + '">'
    + [["ready", "Letter drafted"], ["sent", "Sent by the firm"], ["found", "They hold something"], ["nothing", "Nothing held"]].map(([v, l]) => '<option value="' + v + '"' + (i.status === v ? " selected" : "") + '>' + l + '</option>').join("")
    + '</select></td></tr>').join("");
  return '<div class="firm-card"><h2>Letters to institutions</h2><p>This is the part of an asset search the firm can do itself. Tick who to write to. The desk drafts the letter. The firm posts or emails it, then marks what came back. A find is typed on One set of figures, or ticked in from the report. The software does not write to the bank.</p>'
    + '<p><b>Fee on this estate: ' + gbp(search.fee || 0) + (search.paid ? ". Marked as paid." : ". Not marked as paid.") + '</b></p>'
    + (open.length ? '<form id="search"><label>Your fee (£)<input name="fee" type="number" min="0" step="0.01" value="' + (search.fee || 150) + '"></label>'
      + '<label class="check"><input name="paid" type="checkbox"' + (search.paid ? " checked" : "") + '> The fee has been paid</label>'
      + '<div class="stage">' + choices + '</div><p><button class="btn" type="submit">Draft the enquiries and add the fee</button></p></form>' : '<p class="small">Every institution on the list already has a letter.</p>')
    + (rows ? '<table class="tbl"><thead><tr><th>Institution</th><th>Where it stands</th></tr></thead><tbody>' + rows + '</tbody></table>' : '')
    + '<p class="small">A credit-file result is still a report you upload. This list does not replace that, and it does not place the Section 27 notice or send the IHT400.</p></div>';
}
function ordersBlock(m) {
  const orders = ((m.books || {}).orders) || [];
  const statuses = [["not_ordered", "Not ordered"], ["ordered", "Ordered in their portal"], ["report_in", "Report is on the file"], ["nothing", "Nothing found"], ["not_using", "Not using"]];
  const rows = orders.map(p => '<tr><td><b>' + esc(p.name) + '</b><br><span class="small">' + esc(p.covers) + '</span></td><td>' + esc(p.price) + '</td><td><select name="status-' + esc(p.id) + '">'
    + statuses.map(([v, l]) => '<option value="' + v + '"' + (p.status === v ? " selected" : "") + '>' + l + '</option>').join("")
    + '</select></td><td><input name="ref-' + esc(p.id) + '" value="' + esc(p.reference || "") + '" placeholder="Their reference"></td><td><input name="fee-' + esc(p.id) + '" type="number" min="0" step="0.01" value="' + (p.fee || "") + '" placeholder="Fee"></td></tr>').join("");
  const will = ((m.books || {}).will_search) || {};
  const covers = ((m.books || {}).covers) || [];
  const decisions = [["not_considered", "Not considered"], ["asked", "Quote asked"], ["bought", "Policy bought"], ["not_buying", "Not buying"]];
  const coverRows = covers.map(c => '<tr><td>' + esc(c.name) + '</td><td><select name="decision-' + esc(c.id) + '">'
    + decisions.map(([v, l]) => '<option value="' + v + '"' + (c.decision === v ? " selected" : "") + '>' + l + '</option>').join("")
    + '</select></td><td><input name="cref-' + esc(c.id) + '" value="' + esc(c.reference || "") + '" placeholder="Policy reference"></td></tr>').join("");
  return '<div class="firm-card"><h2>Go to the supplier</h2><p>These are the companies that hold the data. A link opens their own page. Nothing is ordered inside this desk, and nothing comes back until they have agreed an account.</p>'
    + '<table class="tbl"><thead><tr><th>What you need</th><th>Who has it</th></tr></thead><tbody>'
    + '<tr><td>Section 27 notice, and the local paper</td><td><a href="https://www.thegazette.co.uk/wills-and-probate/place-a-deceased-estates-notice" target="_blank" rel="noopener">The Gazette</a></td></tr>'
    + '<tr><td>A will that may be registered</td><td><a href="https://www.nationalwillregister.co.uk/" target="_blank" rel="noopener">National Will Register</a>. Law Society members: <a href="https://www.lawsociety.org.uk/en/membership/offers/certainty" target="_blank" rel="noopener">their offer</a>. Proved wills: <a href="https://www.gov.uk/search-will-probate" target="_blank" rel="noopener">GOV.UK</a>.</td></tr>'
    + '<tr><td>Tell several banks of the death</td><td><a href="https://www.deathnotificationservice.co.uk/" target="_blank" rel="noopener">Death Notification Service</a>. Lost accounts: <a href="https://www.mylostaccount.org.uk/" target="_blank" rel="noopener">My Lost Account</a>.</td></tr>'
    + '<tr><td>A credit report after the grant</td><td><a href="https://www.experian.co.uk/consumer/data-access/thirdparty.html" target="_blank" rel="noopener">Experian, for a representative</a>. This is one report. It is not a search of every bank.</td></tr>'
    + '<tr><td>Deaths, to clean a will bank</td><td><a href="https://www.experian.co.uk/business-products/contact-suppressions/" target="_blank" rel="noopener">Experian contact suppressions</a>. Ask them for the deceased file.</td></tr>'
    + '<tr><td>Identity and anti-money-laundering</td><td><a href="https://www.smartsearch.com/sectors/legal" target="_blank" rel="noopener">SmartSearch for solicitors</a>. They offer an API. <a href="https://www.thirdfort.com/" target="_blank" rel="noopener">Thirdfort</a> is the other checker firms use.</td></tr>'
    + '<tr><td>Share value, transfer or sale</td><td><a href="https://equiniti.com/uk/help-and-support/bereavement/" target="_blank" rel="noopener">Equiniti</a>, <a href="https://www.mpms.mufg.com/en/for-individuals/uk/legal-representatives/bereavement-services" target="_blank" rel="noopener">MUFG</a> (Link), and Computershare’s bereavement team. Prices for the quarter-up sum: <a href="https://www.londonstockexchange.com/" target="_blank" rel="noopener">London Stock Exchange</a>.</td></tr>'
    + '<tr><td>MOT, tax, finance</td><td><a href="https://www.gov.uk/check-mot-history" target="_blank" rel="noopener">MOT</a> and <a href="https://www.gov.uk/check-vehicle-tax" target="_blank" rel="noopener">tax</a> are free. Outstanding finance is a paid HPI check, not on those pages.</td></tr>'
    + '<tr><td>Empty house, missing will, missing beneficiary</td><td><a href="https://insuristic.co.uk/" target="_blank" rel="noopener">Insuristic</a> for probate cover. <a href="https://www.guardcover.co.uk/unoccupied-property-solicitor" target="_blank" rel="noopener">GuardCover</a> for an empty house. The firm buys the policy. This desk does not.</td></tr>'
    + '</tbody></table></div>'
    + '<div class="firm-card"><h2>One supplier, if you would rather not contract each of them</h2><p>Estatesearch bundles the credit file, the bank sweep and the insurance. Use them only if you do not want a contract with each company above. Their <a href="https://www.estatesearch.co.uk/services/" target="_blank" rel="noopener">portal</a> is where the firm orders. This desk still only stores the reference and the report.</p>'
    + '<p><button class="btn" type="button" data-letter="estatesearch">Draft the email to Estatesearch</button></p>'
    + '<form id="orders"><table class="tbl"><thead><tr><th>Search</th><th>Their price</th><th>Where it stands</th><th>Reference</th><th>Fee charged</th></tr></thead><tbody>' + rows + '</tbody></table>'
    + '<p><button class="btn" type="submit">Save the search orders</button></p></form></div>'
    + '<div class="firm-card"><h2>Will search</h2><p>A proved will can be read on GOV.UK. A search of the National Will Register, or Estatesearch’s will search, is paid for in their system. Record what came back. Nothing is searched from here.</p>'
    + '<p><a href="https://www.gov.uk/search-will-probate" target="_blank" rel="noopener">Search wills that have been proved</a> · <a href="https://www.nationalwillregister.co.uk/" target="_blank" rel="noopener">National Will Register</a></p>'
    + '<form id="will-search"><label>Result<select name="result">'
    + [["not_searched", "Not searched"], ["none_found", "No will found"], ["will_found", "A will was found"], ["later_will", "A later will was found"]].map(([v, l]) => '<option value="' + v + '"' + (will.result === v ? " selected" : "") + '>' + l + '</option>').join("")
    + '</select></label><label>Where<input name="where" value="' + esc(will.where || "") + '" placeholder="GOV.UK, Certainty, Estatesearch"></label>'
    + '<label>Reference<input name="reference" value="' + esc(will.reference || "") + '"></label>'
    + '<label>Note<textarea name="note">' + esc(will.note || "") + '</textarea></label>'
    + '<p><button class="btn" type="submit">Save the will search</button></p></form></div>'
    + '<div class="firm-card"><h2>Insurance a firm can buy</h2><p>Unoccupied property, a missing will, no section 27 notice, a missing beneficiary, early distribution, and a lost share certificate. An insurer sells these. Record the decision and the policy number. This desk does not quote or bind a policy.</p>'
    + '<form id="covers"><table class="tbl"><thead><tr><th>Cover</th><th>Decision</th><th>Policy reference</th></tr></thead><tbody>' + coverRows + '</tbody></table>'
    + '<p><button class="btn" type="submit">Save the insurance record</button></p></form></div>'
    + '<div class="firm-card"><h2>A share, from prices you type</h2><p>There is no share-price feed. If you have the lower price, the higher price and the mid price, the figure used is the lower of the quarter-up price and the mid price. That is the usual Inheritance Tax basis. Estatesearch will produce the same figure if you order a valuation from them.</p>'
    + '<form id="share"><label>Company<input name="company" required></label><label>How many<input name="qty" type="number" min="0" step="any" required></label><label>Lower price (£)<input name="lower" type="number" min="0" step="0.0001"></label><label>Higher price (£)<input name="higher" type="number" min="0" step="0.0001"></label><label>Mid price (£)<input name="mid" type="number" min="0" step="0.0001"></label><label>Or a price you were given (£)<input name="price" type="number" min="0" step="0.0001"></label><label>Ex-dividend (£)<input name="xd" type="number" min="0" step="0.01"></label><p><button class="btn" type="submit">Add the holding</button></p></form></div>'
    + '<div class="firm-card"><h2>A vehicle</h2><p><a href="https://www.gov.uk/check-mot-history" target="_blank" rel="noopener">Check the MOT</a> and <a href="https://www.gov.uk/check-vehicle-tax" target="_blank" rel="noopener">check the tax</a> on GOV.UK. Type the open-market value. Outstanding finance is not on those pages. It is added only if a report prints it.</p>'
    + '<form id="vehicle"><label>Registration and make<input name="name" required placeholder="AB12 CDE, Ford Focus"></label><label>Value at death (£)<input name="value" type="number" min="0" step="0.01" required></label><p><button class="btn" type="submit">Add the vehicle</button></p></form></div>';
}
function findPanel(m) {
  const credit = ((m.books || {}).credit) || {};
  const onFile = new Set(((m.books || {}).lines || []).map(ln => ln.name));
  const hits = (m.papers || []).filter(p => p.kind === "Credit report").flatMap(p => (p.suggestions || []).filter(s => s.mode === "append").map(s => {
    const already = onFile.has((s.value && s.value.description) || "");
    return '<label class="check"><input type="checkbox" name="pick" value="' + esc(s.id) + '"' + (already ? " disabled" : " checked") + "> " + esc(s.label) + (s.value && s.value.side === "debt" ? " — a debt" : " — an asset") + (already ? " — already on the list" : "") + "</label>";
  })).join("");
  const rows = ((m.books || {}).discovery || []).map(d => '<article class="stage"><h3>' + esc(d.place) + '</h3><p>' + esc(d.ask) + '</p>'
    + (d.url ? '<p><a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.url_title || d.url) + '</a></p>' : "")
    + '<form class="find" data-id="' + esc(d.id) + '"><label>Status<select name="status">'
    + [["not_asked", "Not asked"], ["asked", "Asked"], ["found", "Found, add it to the list"], ["nothing", "Nothing there"]].map(([v, l]) => '<option value="' + v + '"' + (d.status === v ? " selected" : "") + '>' + l + '</option>').join("")
    + '</select></label><label>Note<input name="note" value="' + esc(d.note || "") + '"></label><button class="btn" type="submit">Save</button></form></article>').join("");
  return searchPanel(m) + ordersBlock(m)
    + '<div class="firm-card"><h2>Credit report</h2><p>This desk does not search a credit file. Experian, Equifax, TransUnion and Estatesearch run that search in their own system, after the firm has an account with them. Record the order here, upload the report they send, and tick only the accounts printed on it. A card or a loan is added as a debt. A bank balance is added as an asset. Nothing else is added.</p>'
    + '<p><a href="https://www.estatesearch.co.uk/" target="_blank" rel="noopener">Open Estatesearch</a></p>'
    + '<form id="credit"><label>Agency<select name="agency"><option value="">Not ordered</option>'
    + ["Experian", "Equifax", "TransUnion", "Estatesearch"].map(a => '<option' + (credit.agency === a ? " selected" : "") + '>' + a + '</option>').join("")
    + '</select></label><label>Their reference<input name="reference" value="' + esc(credit.reference || "") + '"></label>'
    + '<label>Date ordered<input type="date" name="ordered_on" value="' + esc(credit.ordered_on || "") + '"></label>'
    + '<label>Date the report arrived<input type="date" name="received_on" value="' + esc(credit.received_on || "") + '"></label>'
    + '<label>Their fee (£)<input name="fee" type="number" min="0" step="0.01" value="' + (credit.fee || "") + '"></label>'
    + '<label class="check"><input name="bill_fee" type="checkbox"> Add that fee to the bill as a cost paid for the client</label>'
    + '<label>Note<textarea name="note">' + esc(credit.note || "") + '</textarea></label>'
    + '<p><button class="btn" type="submit">Save</button> <button class="btn ghost" type="button" data-letter="credit">Draft the request</button></p></form>'
    + '<form id="credit-up"><label>The report they sent<input type="file" name="file" required accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.heic,.webp"></label> <button class="btn" type="submit">Upload the report</button></form>'
    + (hits ? '<form id="credit-apply"><div class="stage">' + hits + '</div><p><button class="btn" type="submit">Add the ticked accounts</button></p></form>' : '<p class="small">When the report is uploaded, each account it prints is listed here. Tick the ones that belong on the estate.</p>')
    + '</div>'
    + '<div class="firm-card"><h2>Find accounts the family did not know about</h2><p>This is an in-house job. A member of staff writes to the banks the family name, and uses the official free tracing services below for the rest. There is no search button on this page. When a reply finds something, add it on One set of figures.</p>' + rows + '</div>';
}
function formsPanel(m) {
  const f = m.forms;
  if (!f) return '<div class="firm-card"><p>Court and tax working papers are kept on probate matters.</p></div>';
  return '<div class="firm-card"><h2>' + esc(f.grant) + '</h2><p>' + esc(f.route) + '. ' + (f.excepted ? "Full details are not sent to HMRC on these answers." : "These answers need full details on form IHT400.") + '</p><p>A member of staff copies each block onto HMRC’s own form and ticks it. That form is Crown copyright. No separate government licence is needed to complete it for a client. Their form must be the one that is printed and posted. This page is only the working paper, and nothing is sent to HMRC from here.</p><p class="small">' + esc(f.notice) + '</p>'
    + (f.blockers || []).map(x => '<p class="alert">' + esc(x) + '</p>').join("")
    + (f.reasons || []).map(x => '<p class="small">' + esc(x) + '</p>').join("")
    + f.schedule.map(s => '<section class="stage"><h3>' + esc(s.code) + ' — ' + esc(s.label) + '</h3><table class="tbl">' + s.rows.map(r => '<tr><th>' + esc(r[0]) + '</th><td>' + esc(r[1]) + '</td></tr>').join("") + '</table>'
      + '<p><button type="button" class="btn ghost" data-copied="' + esc(s.code) + '">' + (((m.books || {}).copied || []).indexOf(s.code) >= 0 ? "Copied onto the official form" : "Mark as copied onto the official form") + '</button></p></section>').join("")
    + '<p><a class="btn" href="/api/firm/matters/' + esc(m.id) + '/iht400.pdf">Download the IHT400 filled from these figures</a> '
    + '<a class="btn ghost" href="/api/firm/matters/' + esc(m.id) + '/schedules.zip">Download the extra forms this estate needs</a></p>'
    + '<div class="stage"><h3>Forms for this estate</h3><p>The ticked forms are the ones the figures asked for. Untick one that does not apply, or tick one the figures missed. The download follows these ticks.</p>'
    + '<form id="form-choice">' + (f.catalogue || []).map(c => {
        const on = (f.chosen || []).some(x => x.code === c.code);
        const suggested = (f.suggested || []).some(x => x.code === c.code);
        return '<label class="check"><input type="checkbox" name="form" value="' + esc(c.code) + '"' + (on ? ' checked' : '') + '> ' + esc(c.code) + ' — ' + esc(c.label) + (suggested ? ' <span class="small">(from the figures)</span>' : '') + '</label>';
      }).join("")
    + '<p><button class="btn" type="submit">Save the forms</button></p></form>'
    + ((f.chosen || []).length ? '<ul>' + f.chosen.map(c => '<li><b>' + esc(c.code) + '.</b> ' + esc(c.why) + (c.ready ? '' : ' The official file is not stored, so it is named here and not filled.') + '</li>').join("") + '</ul>' : '<p class="small">No extra Inheritance Tax schedule is ticked.</p>')
    + '</div>'
    + '<p class="small">This writes into HMRC’s own file. The asset boxes on page 7 are not fields in that file, so those amounts are written on the additional information page. Nothing is sent to HMRC. An administrator can replace the file with the one currently on GOV.UK.</p>'
    + (ME && ME.role === "admin" ? '<p><button type="button" class="btn ghost" id="refresh-iht">Get the latest IHT400 from GOV.UK</button></p>' : '')
    + '<p><a href="https://www.gov.uk/government/publications/inheritance-tax-inheritance-tax-account-iht400" target="_blank" rel="noopener">Open the official IHT400</a></p>'
    + '<p><a class="btn ghost" href="/api/firm/matters/' + esc(m.id) + '/export">Download the file for the case system</a></p></div>';
}
function lexcelPanel(m) {
  const x = m.lexcel || { items: [], cannot: [], links: [], notice: "", quote: {} };
  const q = x.quote || {};
  const field = (name, label, value) => '<label>' + label + '<input name="' + name + '" value="' + esc(value || "") + '"></label>';
  let section = "";
  const rows = (x.items || []).map(item => {
    const head = item.section !== section ? (section = item.section, '<h3>' + esc(section) + '</h3>') : "";
    return head + '<article class="stage"><p><b>' + esc(item.clause) + '.</b> ' + esc(item.requirement) + '</p>'
      + '<p class="note">' + esc(item.desk) + '</p>'
      + '<label class="check"><input type="checkbox" name="done" value="' + esc(item.id) + '"' + (item.done ? " checked" : "") + '> On the file</label></article>';
  }).join("");
  const saved = ((m.books || {}).letters || []).filter(letter => /client-care|costs estimate|progress report|change of person|complaint|file review|undertaking|conflict search/i.test(letter.title || ""));
  const savedHtml = saved.length ? '<ul>' + saved.slice().reverse().map(letter => '<li>' + esc(letter.title) + ' · <a href="/api/firm/matters/' + esc(m.id) + '/letters/' + esc(letter.id) + '.pdf">PDF</a> · <a href="/api/firm/matters/' + esc(m.id) + '/letters/' + esc(letter.id) + '.docx">Word</a></li>').join("") + '</ul>' : '<p class="note">No Lexcel letter has been kept on this file yet.</p>';
  return '<div class="firm-card"><h2>Lexcel v6.1</h2><p>' + esc(x.notice || "") + '</p>'
    + (x.cannot || []).map(line => '<p class="note">' + esc(line) + '</p>').join("")
    + '<p>' + (x.links || []).map(link => '<a href="' + esc(link.url) + '" target="_blank" rel="noopener">' + esc(link.title) + '</a>').join(" · ") + '</p></div>'
    + '<div class="firm-card"><h2>Conflict search</h2><p class="note">Lexcel 5.8. This looks through the matters already on this desk. It is not a search of other firms, and it is not an identity check.</p>'
    + '<form id="conflict-search" class="line-form"><input name="q" value="' + esc(x.conflict_q || m.client_name || "") + '" placeholder="Name, or several names separated by commas"><button class="btn" type="submit">Search</button></form>'
    + '<div id="conflict-hits"></div><p><button type="button" class="btn ghost" data-letter="lex_conflict">Write the conflict note</button></p></div>'
    + '<div class="firm-card"><h2>Quote and client-care letter</h2><p class="note">Lexcel 6.2 and 6.4. Save the figures, then draft the letter. The letter is kept on the file. It is not sent from here.</p>'
    + '<form id="lexcel-quote">'
    + field("objectives", "What the client wants", q.objectives)
    + field("next_steps", "What we will do next", q.next_steps)
    + field("will_not", "What we will not do", q.will_not)
    + field("timescale", "Timescale", q.timescale)
    + field("funding", "How it is paid for", q.funding)
    + field("fee", "Our fee (£)", q.fee)
    + field("disbursements", "Payments to other people", q.disbursements)
    + field("extras", "Costs that can still arise", q.extras)
    + field("fee_earner", "Person doing the work", q.fee_earner)
    + field("fee_earner_status", "Their status", q.fee_earner_status)
    + field("supervisor", "Supervisor", q.supervisor)
    + field("supervisor_status", "Supervisor’s status", q.supervisor_status)
    + field("data_officer", "Data-protection contact", q.data_officer)
    + '<p><button class="btn" type="submit">Save the quote</button></p></form>'
    + '<p><button type="button" class="btn" data-letter="lex_care">Client-care letter</button> <button type="button" class="btn ghost" data-letter="lex_quote">Costs estimate</button> <button type="button" class="btn ghost" data-letter="lex_progress">Progress report</button></p>'
    + '<p><button type="button" class="btn ghost" data-letter="lex_change">Change of person</button> <button type="button" class="btn ghost" data-letter="lex_complaint">Complaint acknowledgement</button> <button type="button" class="btn ghost" data-letter="lex_review">File-review note</button> <button type="button" class="btn ghost" data-letter="lex_undertaking">Undertaking record</button></p>'
    + savedHtml + '<div id="preview"></div></div>'
    + '<form id="lexcel" class="firm-card"><h2>Requirements still to mark</h2>' + rows + '<p><button class="btn" type="submit">Save what is on the file</button></p>'
    + '<p class="small">' + (x.open || 0) + ' requirements are still open. A tick is not the letter.</p></form>';
}

function schemePanel(m) {
  const s = m.scheme || { items: [], cannot: [], links: [], notice: "", last_report: "" };
  const groups = {};
  (s.items || []).forEach(item => { (groups[item.area] = groups[item.area] || []).push(item); });
  const names = { practice: "Every matter", will: "Wills", estate: "Estate administration", lpa: "Powers of attorney", agreement: "Agreements", trust: "Trusts and deputyships" };
  const blocks = Object.keys(groups).map(area => '<section class="stage"><h3>' + esc(names[area] || area) + '</h3>'
    + groups[area].map(item => '<label class="check"><input type="checkbox" name="done" value="' + esc(item.id) + '"' + (item.done ? ' checked' : '') + '> ' + esc(item.point) + '</label>').join("")
    + '</section>').join("");
  const watch = m.watch || {};
  const changes = (watch.changes || []).slice(0, 5).map(c => '<li><a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + esc(c.title) + '</a> · ' + esc((c.at || '').slice(0, 10)) + ' · ' + esc(c.note || '') + '</li>').join("");
  const r = m.retainer || {};
  return '<div class="firm-card"><h2>Wills and Inheritance Quality Scheme</h2><p>' + esc(s.notice || '') + '</p>'
    + (s.cannot || []).map(line => '<p class="small">' + esc(line) + '</p>').join("")
    + '<p>' + (s.links || []).map(link => '<a href="' + esc(link.url) + '" target="_blank" rel="noopener">' + esc(link.title) + '</a>').join(' · ') + '</p>'
    + '<section class="stage"><h3>Retainer — every section</h3><p>' + esc(r.effect || "No retainer is recorded on this matter.") + '</p>'
    + '<p>One signed retainer covers wills, both lasting powers, the ordinary power, probate, the nuptial and cohabitation agreements, the employment settlement, trusts and deputyships. Signing asks the firm to start during the 14 days. It does not waive the right. The right for a section ends only when that section is fully performed.</p>'
    + '<form id="retainer"><label>Client’s name<input name="signed_name" required value="' + esc(r.signed_name || m.client_name || "") + '"></label>'
    + '<label>Date signed<input type="date" name="signed_on" required value="' + esc(r.signed_on || "") + '"></label>'
    + '<label>Where it was signed<select name="place">' + ["At the firm’s office", "At my home, or someone else’s home", "At a hospital or care home", "At my workplace", "Online or by telephone, not in person"].map(p => '<option' + (r.place === p ? ' selected' : '') + '>' + esc(p) + '</option>').join("") + '</select></label>'
    + '<label class="check"><input type="checkbox" name="finished"' + ((r.finished || []).indexOf(m.kind) >= 0 ? ' checked' : '') + '> This section has been fully performed, so the right to cancel this section has ended</label>'
    + '<p><button class="btn" type="submit">Save the signed retainer</button> <button class="btn ghost" type="button" data-letter="retainer">Draft the retainer</button></p></form></section>'
    + '<form id="scheme">' + blocks
    + '<label>Date of the last progress report to the client<input type="date" name="last_report" value="' + esc(s.last_report || '') + '"></label>'
    + '<p><button class="btn" type="submit">Save the scheme record</button></p></form>'
    + '<p class="small">' + (s.open || 0) + ' points on this matter are still open. A tick is a reminder. It is not the attendance note.</p></div>'
    + '<div class="firm-card"><h2>Official pages</h2><p>' + esc(watch.note || 'The desk reads the Law Society scheme pages and the GOV.UK pages once a day.') + '</p>'
    + '<p class="small">Last check: ' + esc(watch.checked_at ? watch.checked_at.slice(0, 16).replace('T', ' ') + ' UTC' : 'not yet') + '. ' + (watch.pages || '') + ' pages are on the list.</p>'
    + (changes ? '<ul>' + changes + '</ul>' : '<p class="small">No change is waiting for a person.</p>')
    + '<p><button type="button" class="btn ghost" id="source-check">Check the official pages now</button></p><div id="source-msg"></div></div>';
}

function filePanel(m) {
  const downloads = m.draft_id
    ? '<p><a class="btn" href="/api/firm/matters/' + m.id + '/draft.pdf">Draft PDF</a> <a class="btn ghost" href="/api/firm/matters/' + m.id + '/draft.docx">Draft Word</a> <a class="btn ghost" href="/api/firm/matters/' + m.id + '/summary.pdf">Summary PDF</a></p><div id="versions"><p class="muted">Loading versions…</p></div><p><button type="button" class="btn ghost" id="keep-version">Keep this version</button> <button type="button" class="btn ghost" id="final-version">Note that the final copy was sent</button> <button type="button" class="btn ghost" id="email-summary">Email the summary to the client</button></p>'
    : '<p class="muted">Start the client draft from the matter before a Word or PDF of the document can be downloaded. The letters below can still be drafted.</p>';
  return '<div class="firm-card"><h2>File protection</h2>'
    + '<p>File protection is the record of how the document was made, kept so that someone who was not in the room can explain it years later. It is the attendance note, the family and the assets, capacity, why anyone was left out, whether wills are mirror or mutual, how the paper was signed, and any earlier will. It is what the file uses if there is a Larke v Nugus request, a 1975 Act claim, or a negligence claim. It does <b>not</b> make the firm immune from a claim or a complaint. A tick is not a doctor’s note and it does not stop a court claim.</p>'
    + '<p>The Law Society’s practice note on file retention (1 November 2018) treats an original will the firm stores as the client’s property, and after death as the estate’s. Keep it until after the death or until it is returned. There is no fixed period. Some firms keep wills indefinitely, and some for fifty years. Ask the client before an original is destroyed. Keep a copy of a revoked will. A claim about drafting often arises on death, so the preparation file is kept on the same basis.</p>'
    + '<ol><li>See the client alone and write the attendance note the same day.</li><li>If capacity may be doubted, ask a doctor. Do not delay the will so long that it is never signed.</li><li>If someone is left out, keep a statement of reasons off the will.</li><li>If the drafter, their family or an employee benefits, independent advice or stop acting, unless a real exception applies.</li><li>Say whether the wills are mirror (each can change, including after the first death) or mutual (the survivor may be bound after the first death). A mirror will says on its face that it is not mutual. A mutual will is a warning, not a finished clause.</li><li>If you acted for both, a later secret change by one of them is usually a conflict. Say so on the file.</li><li>If an old will is uploaded, a person reads the original. The machine reading is not the review. Do not cross it out and do not destroy it. Read the flags before the new one is signed.</li><li>Keep each version. Note when the final copy was sent. It is still not signed until the paper is signed.</li></ol>'
    + '<p><button class="btn" type="button" data-letter="act1975">1975 Act letter</button> <button class="btn ghost" type="button" data-letter="golden">Golden rule note</button> <button class="btn ghost" type="button" data-letter="couple">Mirror and mutual letter</button> <button class="btn ghost" type="button" data-letter="old_will">Old will review</button> <button class="btn ghost" type="button" data-letter="file_summary">Summary letter</button></p>'
    + '<p class="small"><a href="/#/law">Law updates</a> for every area this desk covers. The register is dated. It is not a live feed from Parliament.</p>'
    + downloads
    + '<div id="preview"></div></div>';
}

function papersPanel(m) {
  const f = m.filing || { blockers: [], steps: [], hmrc: {}, hmcts: {}, notice: "" };
  const h = f.hmrc || {};
  const groups = {};
  (m.papers || []).forEach(p => { (groups[p.kind || "Other"] = groups[p.kind || "Other"] || []).push(p); });
  const papers = Object.keys(groups).map(kind => '<h3>' + esc(kind) + '</h3>' + groups[kind].map(p => {
    const ideas = (p.suggestions || []).filter(s => s.mode !== "note" || String(s.label).startsWith("Executor")).map(s => '<label class="check"><input type="checkbox" name="pick" value="' + esc(s.id) + '" checked> ' + esc(s.label) + "</label>").join("");
    const when = p.created_at ? new Date(p.created_at).toLocaleDateString("en-GB") : "";
    return '<article class="stage"><b>' + esc(p.filename) + '</b> <span class="who">' + esc(when) + "</span>"
      + (p.read_as === "scanned-pdf" || p.read_as === "image" ? '<p class="small">Nothing could be read from this picture. Type the figures, or upload a clearer photo.</p>' : "")
      + (ideas ? '<form class="apply">' + ideas + '<p><button class="btn" type="submit">Add the ticked items to the estate</button></p></form>' : '<p class="small">Nothing on this paper can be copied across.</p>')
      + '<p><a href="/api/firm/matters/' + esc(m.id) + "/uploads/" + esc(p.id) + '">Download</a></p></article>';
  }).join("")).join("");
  const court = f.hmcts || {};
  const ids = (m.papers || []).flatMap(p => (p.suggestions || []).filter(s => s.mode !== "note" || String(s.label).startsWith("Executor")).map(s => s.id));
  return '<div class="firm-card"><h2>Estate papers</h2><p>This is step 1. Upload the will, the death certificate, bank letters and pension statements, including a photo or a scan. They stay on this matter, grouped by what they are, and you can add more as replies arrive. Fill the estate from what can be read. A blurry picture may still have to be typed. Nothing is filed from here.</p>'
    + '<form id="up"><label>What it is<select name="kind"><option>Will</option><option>Codicil</option><option>Death certificate</option><option>Bank or valuation letter</option><option>Pension statement</option><option>Credit report</option><option>Other</option></select></label>'
    + '<input type="file" name="file" required accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.heic,.webp"> <button class="btn" type="submit">Add to the file</button></form>'
    + '<form id="seek"><input name="q" placeholder="Find a paper or a figure" required minlength="2"><button class="btn ghost" type="submit">Search</button></form><div id="hits"></div>'
    + (ids.length ? '<p><button type="button" class="btn" id="fill-all">Fill the estate from these papers</button></p>' : "")
    + (papers || '<p class="muted">No papers yet.</p>') + "</div>"
    + '<div class="firm-card"><h2>Filing</h2><p>' + esc(f.notice) + "</p>"
    + (f.blockers || []).map(b => '<p class="alert">' + esc(b) + "</p>").join("")
    + "<ol>" + (f.steps || []).map(s => "<li>" + esc(s) + "</li>").join("") + "</ol>"
    + (h.needed ? '<p><a href="' + esc(h.url) + '">Official IHT400</a> · <a href="' + esc(h.pay_url) + '">Pay Inheritance Tax</a></p>' : "<p>These answers do not ask for a full IHT400.</p>")
    + '<p><a class="btn" href="' + esc(court.case_url || "https://manage-case.platform.hmcts.net") + '" target="_blank" rel="noopener">Sign in to MyHMCTS</a> '
    + '<a class="btn ghost" href="' + esc(court.org_url || "https://manage-org.platform.hmcts.net") + '" target="_blank" rel="noopener">Organisation account</a> '
    + '<a href="' + esc(court.register_url || "https://www.gov.uk/guidance/register-for-myhmcts-online-case-management-for-professionals") + '" target="_blank" rel="noopener">Register the firm</a></p>'
    + '<p class="small">These open HMCTS. The desk is not connected to their account and cannot send the application.</p>'
    + '<p><a href="' + esc(court.url || "") + '" target="_blank" rel="noopener">How a firm files a probate application</a></p>'
    + '<p><a class="btn" href="/api/firm/matters/' + esc(m.id) + '/pack">Download the working pack</a></p>'
    + '<form id="filed"><label>HMRC code, when they send it<input name="hmrc_code" value="' + esc(h.hmrc_code || "") + '"></label>'
    + '<label>Date the IHT400 was posted<input type="date" name="hmrc_posted_on" value="' + esc(h.hmrc_posted_on || "") + '"></label>'
    + '<label>Date the grant was filed<input type="date" name="grant_filed_on" value="' + esc(h.grant_filed_on || "") + '"></label>'
    + '<label>MyHMCTS reference<input name="grant_reference" value="' + esc(h.grant_reference || "") + '"></label>'
    + '<p><button class="btn" type="submit">Record what the firm has filed</button></p><p class="small">This updates your file only. It does not contact HMRC or HMCTS.</p></form></div>';
}
function lettersPanel(m) {
  const saved = ((m.books || {}).letters || []).slice().reverse().map(l => '<article class="stage"><h3>' + esc(l.title) + '</h3><p class="muted small">' + esc(l.by) + (l.id ? ' · <a href="/api/firm/matters/' + m.id + '/letters/' + esc(l.id) + '.pdf">PDF</a> · <a href="/api/firm/matters/' + m.id + '/letters/' + esc(l.id) + '.docx">Word</a>' : '') + '</p><div class="letter">' + esc(l.body) + '</div></article>').join("");
  return '<div class="firm-card"><h2>Letters from these figures</h2><p>Each letter uses the list you have already typed. Nothing is sent from this desk.</p>'
    + '<p><button class="btn" type="button" data-letter="bank">Ask for date-of-death values</button> <button class="btn ghost" type="button" data-letter="beneficiary">Update the beneficiaries</button> <button class="btn ghost" type="button" data-letter="grant">Write after the grant</button> <button class="btn ghost" type="button" data-letter="notice">Draft a section 27 notice</button></p>'
    + '<h2>Find a will</h2><p>These are the addresses the letters use. A proved will is searched on GOV.UK. These bodies do not hold every will in the country.</p>'
    + '<table class="tbl"><thead><tr><th>Who</th><th>Email</th><th>Post</th><th>Phone</th></tr></thead><tbody>'
    + '<tr><td>Institute of Professional Willwriters</td><td>enquiries@ipw.org.uk</td><td>Trinity Point, New Road, Halesowen, B63 3HY</td><td>0345 257 2570</td></tr>'
    + '<tr><td>The Society of Will Writers</td><td>info@willwriters.com</td><td>Chancery House, Whisby Way, Lincoln, LN6 3LQ</td><td>01522 687888</td></tr>'
    + '<tr><td>HMCTS Probate</td><td>contactprobate@justice.gov.uk</td><td>PO Box 12625, Harlow, CM20 9QF</td><td>0300 303 0648</td></tr>'
    + '<tr><td>A local solicitor or will writer</td><td>You address it</td><td>One letter, sent by you to each firm near the last address</td><td><a href="https://solicitors.lawsociety.org.uk/" target="_blank" rel="noopener">Law Society directory</a></td></tr>'
    + '</tbody></table>'
    + '<p><button class="btn" type="button" data-letter="will_ipw">Draft the IPW letter</button> <button class="btn ghost" type="button" data-letter="will_sww">Draft the Society of Will Writers letter</button> <button class="btn ghost" type="button" data-letter="will_probate">Draft the probate registry letter</button> <button class="btn ghost" type="button" data-letter="will_local">Draft the local firms letter</button></p>'
    + '<h2>Pension figures</h2><p>From 6 April 2027 the unused pension is needed for Inheritance Tax. There is no connection that pulls every scheme. The Pension Tracing Service finds who to write to. You send this email. You type the reply on the pension step.</p>'
    + '<p><a href="https://www.gov.uk/find-pension-contact-details" target="_blank" rel="noopener">Find pension contact details</a></p>'
    + '<p><button class="btn" type="button" data-letter="pension">Draft the email to the scheme</button></p>'
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
  const task = document.getElementById("task");
  if (task) task.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id + "/tasks", { method: "POST", body: Object.fromEntries(new FormData(e.target).entries()) });
    reload();
  };
  $desk.querySelectorAll("[data-task]").forEach(box => box.onchange = async () => {
    await api("/api/firm/matters/" + id + "/tasks/" + box.dataset.task, { method: "POST", body: { done: box.checked } });
  });
  const appointment = document.getElementById("appointment");
  if (appointment) appointment.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id + "/appointments", { method: "POST", body: Object.fromEntries(new FormData(e.target).entries()) });
    reload();
  };
  const scheme = document.getElementById("scheme");
  if (scheme) scheme.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    await api("/api/firm/matters/" + id + "/scheme", { method: "POST", body: { done: fd.getAll("done"), last_report: fd.get("last_report") || "" } });
    reload();
  };
  const lexcel = document.getElementById("lexcel");
  if (lexcel) lexcel.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id + "/lexcel", { method: "POST", body: { done: new FormData(e.target).getAll("done") } });
    reload();
  };
  const quote = document.getElementById("lexcel-quote");
  if (quote) quote.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id + "/lexcel", { method: "POST", body: { quote: Object.fromEntries(new FormData(e.target).entries()) } });
    reload();
  };
  const conflict = document.getElementById("conflict-search");
  if (conflict) conflict.onsubmit = async (e) => {
    e.preventDefault();
    const q = new FormData(e.target).get("q") || "";
    await api("/api/firm/matters/" + id + "/lexcel", { method: "POST", body: { conflict_q: q } });
    const found = await api("/api/firm/matters/" + id + "/conflicts?q=" + encodeURIComponent(q));
    const hits = document.getElementById("conflict-hits");
    const rows = found.matches || [];
    hits.innerHTML = rows.length
      ? '<ul>' + rows.map(hit => '<li><a href="/firm?m=' + esc(hit.id) + '">' + esc(hit.title) + '</a> · ' + esc(hit.client_name || "") + (hit.deceased_name ? " · " + esc(hit.deceased_name) : "") + '</li>').join("") + '</ul>'
      : '<p class="note">No other matter on this desk uses these names.</p>';
  };
  const retainer = document.getElementById("retainer");
  if (retainer) retainer.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    await api("/api/firm/matters/" + id + "/retainer", { method: "POST", body: { signed_name: fd.get("signed_name"), signed_on: fd.get("signed_on"), place: fd.get("place"), finished: !!fd.get("finished") } });
    reload();
  };
  const source = document.getElementById("source-check");
  if (source) source.onclick = async () => {
    const box = document.getElementById("source-msg");
    source.disabled = true;
    box.innerHTML = '<p class="muted">Reading the official pages…</p>';
    try {
      const r = await api("/api/firm/source-check", { method: "POST", body: {} });
      const n = (r.found || []).length;
      box.innerHTML = '<div class="alert">' + (n ? n + ' page' + (n === 1 ? '' : 's') + ' changed. A person needs to read them. No clause was rewritten.' : 'No change on the pages that could be read.') + '</div>';
    } catch (err) {
      box.innerHTML = '<div class="alert error">' + esc(err.message) + '</div>';
    }
    source.disabled = false;
  };
  const add = document.getElementById("add");
  if (add) add.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    books.lines.push({ name: fd.get("name"), holder: fd.get("holder"), side: fd.get("side"), kind: fd.get("kind"), ownership: fd.get("ownership"), value: fd.get("value"), realised: fd.get("realised"), income: fd.get("income"), costs: fd.get("costs"), joint: fd.get("joint") ? "Yes" : "No", abroad: fd.get("abroad") ? "Yes" : "No", funeral: !!fd.get("funeral"), paid: !!fd.get("paid") });
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
  const equal = document.getElementById("equal");
  if (equal) equal.onclick = async () => {
    const books = m.books;
    const people = books.people || [];
    if (!people.length) return;
    const each = Math.floor(10000 / people.length) / 100;
    books.people = people.map((p, i) => ({ ...p, share: i === people.length - 1 ? Math.round((100 - each * (people.length - 1)) * 100) / 100 : each }));
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  };
  $desk.querySelectorAll("form.find").forEach(form => form.onsubmit = async (e) => {
    e.preventDefault();
    const books = m.books;
    const fd = new FormData(form);
    books.discovery = (books.discovery || []).map(d => d.id === form.dataset.id ? { ...d, status: fd.get("status"), note: fd.get("note") } : d);
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  });
  const seek = document.getElementById("seek");
  if (seek) seek.onsubmit = async (e) => {
    e.preventDefault();
    const q = new FormData(e.target).get("q");
    const found = await api("/api/firm/matters/" + id + "/search?q=" + encodeURIComponent(q));
    const bits = (found.items || []).map(it => '<li>' + esc(it.where) + ': ' + esc(it.label) + '</li>').concat((found.papers || []).map(p => '<li>' + esc(p.filename) + ': ' + esc(p.snippet) + '</li>'));
    document.getElementById("hits").innerHTML = bits.length ? '<ul>' + bits.join("") + '</ul>' : '<p class="muted">Nothing matched.</p>';
  };
  const bill = document.getElementById("bill");
  if (bill) bill.onsubmit = async (e) => {
    e.preventDefault();
    const entry = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { bill: { entries: (m.bill_entries || []).concat([entry]) } } });
    TAB = "bill";
    reload();
  };
  ["trust", "deputy"].forEach(key => {
    const form = document.getElementById(key);
    if (!form) return;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const book = { ...(m[key] || {}), lines: ((m[key] || {}).lines || []).concat([{ name: fd.get("name"), pot: fd.get("pot"), out: fd.get("out") || "", amount: fd.get("amount") }]) };
      const body = {};
      body[key] = book;
      await api("/api/firm/matters/" + id, { method: "PATCH", body });
      TAB = key;
      reload();
    };
  });
  const trustRegister = document.getElementById("trust-register");
  if (trustRegister) trustRegister.onclick = async () => {
    const r = await api("/api/firm/matters/" + id + "/trust-register", { method: "POST", body: {} });
    location.href = "/#/d/" + r.draft_id + "/0";
  };
  for (const key of ["trust", "deputy"]) {
    const form = document.getElementById(key);
    if (!form) continue;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const line = Object.fromEntries(new FormData(e.target).entries());
      const book = m[key] || { lines: [] };
      book.lines = (book.lines || []).concat([line]);
      const body = {};
      body[key] = book;
      await api("/api/firm/matters/" + id, { method: "PATCH", body });
      TAB = key;
      reload();
    };
  }
  const practice = document.getElementById("practice");
  if (practice) practice.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { practice: Object.fromEntries(new FormData(e.target).entries()) } });
    reload();
  };
  const hits = document.getElementById("conflicts");
  if (hits) {
    api("/api/firm/matters/" + id + "/conflicts").then(r => {
      const rows = r.matches || [];
      hits.innerHTML = rows.length
        ? '<p class="alert">These names are already on another matter.</p><ul>' + rows.map(h => '<li><a href="/firm?m=' + esc(h.id) + '">' + esc(h.title) + '</a> · ' + esc(h.client_name) + (h.deceased_name ? " · estate of " + esc(h.deceased_name) : "") + '</li>').join("") + '</ul>'
        : '<p class="small">No other matter uses this client’s name or the name of the person who died.</p>';
    }).catch(() => { hits.innerHTML = ""; });
  }
  const formChoice = document.getElementById("form-choice");
  if (formChoice) formChoice.onsubmit = async (e) => {
    e.preventDefault();
    const ticked = new Set(new FormData(e.target).getAll("form"));
    const suggested = new Set((m.forms.suggested || []).map(s => s.code));
    const books = m.books;
    books.form_choice = {
      on: [...ticked].filter(code => !suggested.has(code)),
      off: [...suggested].filter(code => !ticked.has(code)),
    };
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "forms";
    reload();
  };
  const refreshIht = document.getElementById("refresh-iht");
  if (refreshIht) refreshIht.onclick = async () => {
    refreshIht.disabled = true;
    try {
      await api("/api/firm/iht400/refresh", { method: "POST", body: {} });
      refreshIht.textContent = "The latest IHT400 is stored";
    } catch (err) {
      refreshIht.disabled = false;
      refreshIht.textContent = err.message;
    }
  };
  const searchForm = document.getElementById("search");
  if (searchForm) searchForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    await api("/api/firm/matters/" + id + "/asset-search", { method: "POST", body: { fee: Number(fd.get("fee") || 0), paid: !!fd.get("paid"), targets: fd.getAll("target") } });
    TAB = "find";
    reload();
  };
  $desk.querySelectorAll("[data-search]").forEach(sel => sel.onchange = async () => {
    const books = m.books;
    books.asset_search.items = (books.asset_search.items || []).map(it => it.id === sel.dataset.search ? { ...it, status: sel.value } : it);
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
  });
  const creditForm = document.getElementById("credit");
  if (creditForm) creditForm.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    const credit = Object.fromEntries(fd.entries());
    delete credit.bill_fee;
    books.credit = credit;
    const body = { books };
    const fee = Number(credit.fee || 0);
    const what = (credit.agency || "Credit") + " search" + (credit.reference ? " " + credit.reference : "");
    const already = (m.bill_entries || []).some(entry => entry.kind === "cost" && entry.what === what && Number(entry.amount) === fee);
    if (fd.get("bill_fee") && fee > 0 && !already) {
      body.bill = { entries: (m.bill_entries || []).concat([{ kind: "cost", what, amount: fee }]) };
    }
    await api("/api/firm/matters/" + id, { method: "PATCH", body });
    TAB = "find";
    reload();
  };
  const creditUp = document.getElementById("credit-up");
  if (creditUp) creditUp.onsubmit = async (e) => {
    e.preventDefault();
    const headers = { "X-CSRF-Token": decodeURIComponent(await ensureCsrf()) };
    const fd = new FormData(e.target);
    fd.append("kind", "Credit report");
    const res = await fetch("/api/firm/matters/" + id + "/uploads", { method: "POST", credentials: "same-origin", headers, body: fd });
    const data = await res.json().catch(() => null);
    if (!res.ok) { alert((data && data.detail) || "Upload failed"); return; }
    TAB = "find";
    reload();
  };
  const creditApply = document.getElementById("credit-apply");
  if (creditApply) creditApply.onsubmit = async (e) => {
    e.preventDefault();
    const suggestion_ids = [...e.target.querySelectorAll("input:checked")].map(i => i.value);
    await api("/api/firm/matters/" + id + "/apply", { method: "POST", body: { suggestion_ids } });
    TAB = "find";
    reload();
  };
  const orders = document.getElementById("orders");
  if (orders) orders.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books;
    books.orders = (books.orders || []).map(p => ({ id: p.id, status: fd.get("status-" + p.id), reference: fd.get("ref-" + p.id), fee: fd.get("fee-" + p.id), ordered_on: p.ordered_on || "" }));
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "find";
    reload();
  };
  const willSearch = document.getElementById("will-search");
  if (willSearch) willSearch.onsubmit = async (e) => {
    e.preventDefault();
    const books = m.books;
    books.will_search = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "find";
    reload();
  };
  const covers = document.getElementById("covers");
  if (covers) covers.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books;
    books.covers = (books.covers || []).map(c => ({ id: c.id, decision: fd.get("decision-" + c.id), reference: fd.get("cref-" + c.id) }));
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "find";
    reload();
  };
  const share = document.getElementById("share");
  if (share) share.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const qty = Number(fd.get("qty") || 0);
    const lower = Number(fd.get("lower") || 0);
    const higher = Number(fd.get("higher") || 0);
    const mid = Number(fd.get("mid") || 0);
    let price = Number(fd.get("price") || 0);
    let basis = "price given";
    if (lower > 0 && higher >= lower) {
      const quarter = lower + (higher - lower) / 4;
      price = mid > 0 ? Math.min(quarter, mid) : quarter;
      basis = mid > 0 ? "lower of quarter-up and mid" : "quarter-up";
    }
    if (!(qty > 0) || !(price > 0)) return;
    const xd = Number(fd.get("xd") || 0);
    const books = m.books;
    const name = fd.get("company") + " — " + qty + " at £" + Math.round(price * 10000) / 10000;
    books.lines.push({ name, holder: (xd ? "Ex-dividend £" + xd + ". " : "") + basis, side: "asset", kind: "shares", ownership: "sole", value: Math.round((qty * price + xd) * 100) / 100 });
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "money";
    reload();
  };
  const vehicle = document.getElementById("vehicle");
  if (vehicle) vehicle.onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const books = m.books;
    books.lines.push({ name: fd.get("name"), holder: "", side: "asset", kind: "goods", ownership: "sole", value: fd.get("value") });
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    TAB = "money";
    reload();
  };
  const notice = document.getElementById("notice");
  if (notice) notice.onsubmit = async (e) => {
    e.preventDefault();
    const books = m.books || { lines: [], people: [], case: {}, letters: [] };
    books.notice = Object.fromEntries(new FormData(e.target).entries());
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  };
  $desk.querySelectorAll("[data-copied]").forEach(b => b.onclick = async () => {
    const books = m.books;
    const code = b.dataset.copied;
    const have = new Set(books.copied || []);
    if (have.has(code)) have.delete(code); else have.add(code);
    books.copied = [...have];
    await api("/api/firm/matters/" + id, { method: "PATCH", body: { books } });
    reload();
  });
  const filed = document.getElementById("filed");
  if (filed) filed.onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/firm/matters/" + id, { method: "PATCH", body: Object.fromEntries(new FormData(e.target).entries()) });
    reload();
  };
  const fillAll = document.getElementById("fill-all");
  if (fillAll) fillAll.onclick = async () => {
    const suggestion_ids = (m.papers || []).flatMap(p => (p.suggestions || []).filter(s => s.mode !== "note" || String(s.label).startsWith("Executor")).map(s => s.id));
    await api("/api/firm/matters/" + id + "/apply", { method: "POST", body: { suggestion_ids } });
    TAB = "money";
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
    const preview = document.getElementById("preview");
    try {
      const r = await api("/api/firm/matters/" + id + "/letters", { method: "POST", body: { kind: b.dataset.letter } });
      const last = ((r.matter.books || {}).letters || []).slice(-1)[0];
      const files = last ? '<p><a class="btn" href="/api/firm/matters/' + id + '/letters/' + esc(last.id) + '.pdf">PDF</a> <a class="btn ghost" href="/api/firm/matters/' + id + '/letters/' + esc(last.id) + '.docx">Word</a></p>' : "";
      if (preview) preview.innerHTML = '<h3>' + esc(r.letter.title) + '</h3><div class="letter">' + esc(r.letter.body) + '</div>' + files;
      m.books = r.matter.books;
    } catch (err) {
      if (preview) preview.innerHTML = '<div class="alert">' + esc(err.message) + '</div>';
      else alert(err.message);
    }
  });
  const versions = document.getElementById("versions");
  if (versions && m.draft_id) {
    api("/api/firm/matters/" + id + "/versions").then(rows => {
      versions.innerHTML = rows.length
        ? '<ol>' + rows.map(v => '<li>Version ' + v.number + ' · ' + esc(v.label) + (v.note ? ' · ' + esc(v.note) : '') + '</li>').join("") + '</ol>'
        : '<p class="muted">No version kept yet. Sending the client draft for review keeps one. You can also keep one here.</p>';
    }).catch(() => { versions.innerHTML = '<p class="muted">Versions could not be loaded.</p>'; });
  }
  const keepVersion = document.getElementById("keep-version");
  if (keepVersion) keepVersion.onclick = async () => { await api("/api/firm/matters/" + id + "/versions", { method: "POST", body: { label: "Kept", note: "Working version kept from the firm file." } }); matter(id); };
  const finalVersion = document.getElementById("final-version");
  if (finalVersion) finalVersion.onclick = async () => { await api("/api/firm/matters/" + id + "/versions", { method: "POST", body: { label: "Final copy sent", note: "The final draft was sent. It is still not signed until the paper is signed." } }); matter(id); };
  const emailSummary = document.getElementById("email-summary");
  if (emailSummary) emailSummary.onclick = async () => {
    const preview = document.getElementById("preview");
    const r = await api("/api/firm/matters/" + id + "/summary-email", { method: "POST", body: {} });
    if (preview) preview.innerHTML = '<p>' + esc(r.message) + '</p>';
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
  try {
    const me = await api("/api/auth/me");
    ME = me.user && (me.user.role === "staff" || me.user.role === "admin") ? me.user : null;
    route();
  } catch (err) {
    if ($desk) $desk.innerHTML = '<div class="firm-card" style="max-width:460px;margin:40px auto"><h1>Firm desk</h1><p>' + esc(err.message || "The desk could not load.") + '</p><p><a class="btn" href="/firm">Try again</a></p></div>';
  }
})();
