"use strict";
const $app = document.getElementById("app");
const HOME_HTML = $app ? $app.innerHTML : "";
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ICONS = { will: "📜", lpa_property: "🏦", lpa_health: "🩺", poa_ordinary: "📝", probate: "⚖️" };
const cache = {};

let ME = null;
const cookie = name => (document.cookie.split("; ").find(c => c.startsWith(name + "=")) || "").slice(name.length + 1);
async function ensureCsrf() {
  let token = cookie("sas_csrf");
  if (!token) {
    await fetch("/api/auth/me", { credentials: "same-origin", cache: "no-store" });
    token = cookie("sas_csrf");
  }
  return token;
}
async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;
  const headers = isForm ? {} : { "Content-Type": "application/json" };
  if (opts.method && opts.method !== "GET") headers["X-CSRF-Token"] = decodeURIComponent(await ensureCsrf());
  const res = await fetch(path, { ...opts, credentials: "same-origin", headers, body: opts.body === undefined ? undefined : isForm ? opts.body : JSON.stringify(opts.body) });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (res.status === 401 && !path.startsWith("/api/auth/")) { ME = null; nav(); location.hash = "#/login?next=" + encodeURIComponent(location.hash.slice(2)); throw Object.assign(new Error("Please sign in"), { quiet: true }); }
  if (!res.ok) throw Object.assign(new Error((data && (data.detail?.message || data.detail)) || "Something went wrong. Please try again."), { data, status: res.status });
  return data;
}
const service = async id => cache[id] ||= await api("/api/services/" + id);
const remember = () => {};
async function whoami() { ME = (await api("/api/auth/me")).user; nav(); }
function nav() {
  const el = document.getElementById("acct");
  if (!el) return;
  el.innerHTML = ME ? '<a href="#/mine">My documents</a>' + (ME.role === "admin" || ME.role === "staff" ? '<a href="/firm">Firm desk</a>' : "") + (ME.role === "admin" ? '<a href="#/admin">Admin</a>' : "") + '<button type="button" class="linkbtn" id="signout">Sign out</button>'
    : '<a href="#/login">Sign in</a><a href="#/register" class="btn small accent">Create account</a>';
  const so = document.getElementById("signout");
  if (so) so.onclick = async () => { await api("/api/auth/logout", { method: "POST" }); ME = null; nav(); location.hash = "#/"; };
}
const query = () => new URLSearchParams((location.hash.split("?")[1]) || "");
const focusMain = () => { const h = $app.querySelector("h1"); if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); } window.scrollTo(0, 0); };

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean);
  try {
    if (["login", "register", "forgot"].includes(parts[0])) return authPage(parts[0]);
    if (parts[0] === "reset") return resetPage(parts[1]);
    if (parts[0] === "mine") return await mine();
    if (parts[0] === "admin") return await adminPage(parts.slice(1));
    if (parts[0] === "how") return howPage();
    if (parts[0] === "about") return aboutPage();
    if (parts[0] === "pricing") return pricingPage();
    if (parts[0] === "faq") return faqPage();
    if (parts[0] === "terms") return legalPage("terms");
    if (parts[0] === "privacy") return legalPage("privacy");
    if (parts[0] === "complaints") return legalPage("complaints");
    if (parts[0] === "s") return await start(parts[1]);
    if (parts[0] === "d" && parts[2] === "review") return await review(parts[1]);
    if (parts[0] === "d") return await step(parts[1], Number(parts[2] || 0));
    return home();
  } catch (e) {
    if (e.quiet) return;
    $app.innerHTML = '<h1>Sorry, something went wrong</h1><div class="alert error">' + esc(e.message) + '</div><p><a class="btn ghost" href="#/">Back to the start</a></p>';
  } finally { focusMain(); }
}


function cardHtml(s) {
  return '<article class="card svc"><span class="icon" aria-hidden="true">' + (ICONS[s.id] || "📄") + '</span><h3>' + esc(s.title) + '</h3><p class="muted">' + esc(s.summary) + '</p><p class="meta">' + s.steps + ' steps · about ' + (s.steps * 3) + ' minutes</p><a class="btn" href="#/s/' + s.id + '" data-start="' + s.id + '">Start</a></article>';
}
function serviceGroups(list) {
  const order = [];
  const grouped = {};
  for (const s of list) {
    const cat = s.category || "Other";
    if (!grouped[cat]) { grouped[cat] = []; order.push(cat); }
    grouped[cat].push(s);
  }
  return order.map(cat => '<section class="svc-group"><h2>' + esc(cat) + '</h2><div class="grid">' + grouped[cat].map(cardHtml).join("") + '</div></section>').join("");
}
function businessSection() {
  return '<section class="card business-note"><h2>Business wills and business LPAs</h2>'
    + '<p>If you own a business, a farm, or shares in a company, you may want to keep those assets separate from your personal plans. Official OPG guidance (LP12) says you can make two property and financial affairs LPAs (form LP1F): one for your personal finances and one for your business affairs, so different attorneys can look after different things.</p>'
    + '<p>Talk to any co-owners, check the partnership or shareholders\' agreement, and choose attorneys who understand the business. A will can say who should inherit the business; some assets may qualify for Inheritance Tax Business Relief, but a solicitor must check this, especially for deaths on or after 6 April 2026, when 100% relief is capped. This is not legal advice.</p>'
    + '<p><a class="btn ghost" href="#/s/will" data-start="will">Start a will (includes a Business step)</a> <a class="btn ghost" href="#/s/lpa_property" data-start="lpa_property">Start a financial LPA (includes a Business step)</a></p>'
    + '<p class="muted small">Sources: <a href="https://www.gov.uk/government/publications/lasting-power-of-attorney-forms/lp12-make-and-register-your-lasting-power-of-attorney-a-guide-web-version" rel="noopener noreferrer" target="_blank">LP12</a> and <a href="https://www.gov.uk/business-relief-inheritance-tax" rel="noopener noreferrer" target="_blank">GOV.UK Business Relief</a>.</p></section>';
}

function demoVideo(stem, title) {
  return videoHtml({
    id: stem,
    src: "/static/videos/" + stem + ".mp4",
    poster: "/static/videos/" + stem + ".jpg",
    captions: "/static/videos/" + stem + ".vtt",
    default_presenter: "female",
    presenters: [
      { id: "female", label: "Woman", src: "/static/videos/" + stem + ".mp4", poster: "/static/videos/" + stem + ".jpg", captions: "/static/videos/" + stem + ".vtt" },
      { id: "male", label: "Man", src: "/static/videos/" + stem + "_male.mp4", poster: "/static/videos/" + stem + "_male.jpg", captions: "/static/videos/" + stem + "_male.vtt" }
    ]
  }, title);
}
function howPage() {
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">How it works</p><h1>Four steps, with a video on each one</h1>'
    + '<p class="lead">Pick a woman or a man to present the video. Your choice is remembered on every later step.</p>'
    + demoVideo("will_intro", "Making your will")
    + '<div class="how"><div><b>1. Choose</b>Will, LPA, probate, prenup, postnup, cohabitation or an employment settlement.</div>'
    + '<div><b>2. Watch and answer</b>Each step has a short video, plain-English help, then a few questions. Answers save as you go.</div>'
    + '<div><b>3. Check</b>Read the draft, with a note on every clause, and fix anything flagged.</div>'
    + '<div><b>4. Solicitor review</b>Send it for review before anything is signed or filed.</div></div>'
    + '<p><a class="btn" href="#/s/will">Start a will</a> <a class="btn ghost" href="#/pricing">See pricing</a></p></div>';
}
function pricingPage() {
  const rows = [
    ["Will", "£149", "Single will, video on every step, solicitor review before you sign.", "#/s/will"],
    ["Lasting power of attorney", "£149 each", "Property and financial affairs, or health and welfare. Both together £249.", "#/s/lpa_property"],
    ["Health and welfare LPA", "£149", "Decisions about care and medical treatment if you cannot decide.", "#/s/lpa_health"],
    ["Ordinary power of attorney", "£99", "For while you still have capacity. It ends if you lose capacity.", "#/s/poa_ordinary"],
    ["Probate", "from £399", "Application support and document checking. Complex estates are quoted.", "#/s/probate"],
    ["Prenuptial agreement", "£349", "Before marriage. Full disclosure and solicitor review.", "#/s/prenup"],
    ["Postnuptial agreement", "£349", "After marriage. Solicitor review included.", "#/s/postnup"],
    ["Cohabitation agreement", "£249", "For unmarried couples, covering the home and money.", "#/s/cohabitation"],
    ["Employment settlement", "£299", "Agreed exit terms. The employee still needs independent advice.", "#/s/employment_settlement"]
  ];
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">Pricing</p><h1>Guide prices</h1>'
    + '<p class="lead">These are guide prices, not a quote. They can be changed. Solicitor review of the draft is included. You are not charged on this page.</p>'
    + '<div class="price-grid">' + rows.map(r => '<article class="service-card"><h3>' + esc(r[0]) + '</h3><p class="price">' + esc(r[1]) + '</p><p>' + esc(r[2]) + '</p><a class="btn" href="' + r[3] + '">Start</a></article>').join("") + '</div></div>';
}
function aboutPage() {
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">About us</p><h1>Signed and Sorted</h1>'
    + '<p class="lead">Wills, lasting powers of attorney, probate, and family and employment agreements for England and Wales.</p>'
    + '<p>You answer guided questions. A short video explains each step, and you can choose a woman or a man as the presenter. A solicitor checks the draft before you sign. This is not legal advice until that review is done.</p>'
    + '<p><a class="btn" href="#/">See the services</a></p></div>';
}
function legalPage(kind) {
  const pages = {
    terms: ["Terms", "Using Signed and Sorted does not create a solicitor-client relationship by itself. The questions and videos are guidance. A solicitor reviews the draft before you sign or file anything. Guide prices on the pricing page are not a quote and nothing is taken on this website until a payment step is switched on."],
    privacy: ["Privacy", "Your answers, uploads and account email are stored so you can finish a draft and so a solicitor can review it. They are not sold. Sign in to see your own documents. An administrator can see drafts for review. Do not put passwords in a will or an upload."],
    complaints: ["Complaints", "If something has gone wrong, email the address you used to contact Signed and Sorted and include your draft reference from My documents. We will reply with what will happen next. This page is not a regulator complaint form."]
  };
  const page = pages[kind];
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">Legal</p><h1>' + esc(page[0]) + '</h1><p class="lead">' + esc(page[1]) + '</p><p><a class="btn ghost" href="#/">Back to the services</a></p></div>';
}
function faqPage() {
  const qs = [
    ["Do I have to watch the video?", "No. It is there to explain the step. You can pause it or skip it and still answer the questions."],
    ["Can I choose a man or a woman?", "Yes. On any video, choose Woman or Man. The choice is saved in this browser and used on the next steps."],
    ["When do I pay?", "Not while you are drafting. Guide prices are on the pricing page. Nothing is taken on this site until a payment step is switched on."],
    ["Is this legal advice?", "The questions and videos are guidance. A solicitor reviews the draft before you sign or file anything."]
  ];
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">Help</p><h1>Help and support</h1>'
    + qs.map(q => '<h2>' + esc(q[0]) + '</h2><p>' + esc(q[1]) + '</p>').join("")
    + '<p><a class="btn ghost" href="#/how">How it works</a></p></div>';
}
function home() {
  if (HOME_HTML && HOME_HTML.indexOf("hero-section") !== -1) {
    $app.innerHTML = HOME_HTML;
    return;
  }
  return homeFromApi();
}
async function homeFromApi() {
  const list = await api("/api/services");
  $app.innerHTML = '<section class="hero"><div><p class="eyebrow">England and Wales</p><h1>Your will, power of attorney or probate, sorted step by step</h1>'
    + '<p class="lead">Short videos and plain-English help on every step. Upload your old documents and we suggest answers. A solicitor checks everything before you sign.</p></div>'
    + '<div class="hero-card" aria-label="What you get"><ul><li>Guided questions with a video on each step</li><li>Built on the official GOV.UK forms (LP1F, LP1H, PA1P, PA1A, IHT400)</li><li>Upload an old will, LPA or probate papers</li><li>Download a PDF and send it for solicitor review</li></ul></div></section>'
    + serviceGroups(list)
    + businessSection()
    + '<h2>How it works</h2><div class="how"><div><b>1. Answer</b>Watch the short video, read the help and answer a few questions. Your answers save automatically.</div><div><b>2. Check</b>See your draft with a plain-English note on every clause, and any points to fix.</div><div><b>3. Review</b>Send it to a solicitor. They check it with you before anything is signed or sent.</div></div>'
    + '<h2>Carry on where you left off</h2><div class="card">' + (ME ? '<p>You are signed in as <b>' + esc(ME.email) + '</b>.</p><p><a class="btn ghost" href="#/mine">Go to my documents</a></p>'
      : '<p>Your drafts and documents are kept in your account. Sign in to carry on.</p><p><a class="btn ghost" href="#/login">Sign in</a> <a class="btn ghost" href="#/register">Create an account</a></p>') + '</div>';
  bindStart();
}

function authPage(kind) {
  const next = query().get("next") || "mine";
  const titles = { login: "Sign in", register: "Create your account", forgot: "Reset your password" };
  $app.innerHTML = '<div class="narrow"><h1>' + titles[kind] + '</h1>'
    + (kind === "register" ? '<p class="muted">Your answers and uploaded documents are kept in your account, so only you (and our solicitors) can see them.</p>' : "")
    + (kind === "forgot" ? '<p class="muted">Enter the email you signed up with. We will send a link to choose a new password.</p>' : "")
    + '<form class="card" id="auth" novalidate><div id="msg" aria-live="polite"></div>'
    + '<div class="field"><label for="email">Email address</label><input id="email" type="email" autocomplete="email" required></div>'
    + (kind !== "forgot" ? '<div class="field"><label for="password">Password</label>' + (kind === "register" ? '<span class="hint" id="pwhint">At least 10 characters. A few random words works well.</span>' : "")
      + '<input id="password" type="password" autocomplete="' + (kind === "register" ? "new-password" : "current-password") + '" required minlength="' + (kind === "register" ? 10 : 1) + '"' + (kind === "register" ? ' aria-describedby="pwhint"' : "") + '></div>' : "")
    + '<p><button class="btn">' + ({ login: "Sign in", register: "Create account", forgot: "Send reset link" })[kind] + '</button></p>'
    + (kind === "login" ? '<p class="small"><a href="#/forgot">Forgotten your password?</a> · <a href="#/register?next=' + encodeURIComponent(next) + '">Create an account</a></p>' : "")
    + (kind === "register" ? '<p class="small">Already have an account? <a href="#/login?next=' + encodeURIComponent(next) + '">Sign in</a></p>' : "")
    + '</form></div>';
  const form = document.getElementById("auth"), msg = document.getElementById("msg");
  form.onsubmit = async e => {
    e.preventDefault();
    const btn = form.querySelector("button"); btn.disabled = true; msg.innerHTML = "";
    try {
      const email = document.getElementById("email").value.trim();
      if (kind === "forgot") { const r = await api("/api/auth/reset-request", { method: "POST", body: { email } }); msg.innerHTML = '<div class="alert ok">' + esc(r.message) + '</div>'; return; }
      const r = await api("/api/auth/" + kind, { method: "POST", body: { email, password: document.getElementById("password").value } });
      ME = r.user; nav(); location.hash = "#/" + next;
    } catch (err) { msg.innerHTML = '<div class="alert error" role="alert">' + esc(err.message) + '</div>'; }
    finally { btn.disabled = false; }
  };
}

function resetPage(token) {
  $app.innerHTML = '<div class="narrow"><h1>Choose a new password</h1><form class="card" id="auth"><div id="msg" aria-live="polite"></div><div class="field"><label for="password">New password</label><span class="hint" id="pwhint">At least 10 characters.</span><input id="password" type="password" autocomplete="new-password" minlength="10" aria-describedby="pwhint" required></div><p><button class="btn">Save and sign in</button></p></form></div>';
  document.getElementById("auth").onsubmit = async e => {
    e.preventDefault();
    try { const r = await api("/api/auth/reset", { method: "POST", body: { token, password: document.getElementById("password").value } }); ME = r.user; nav(); location.hash = "#/mine"; }
    catch (err) { document.getElementById("msg").innerHTML = '<div class="alert error" role="alert">' + esc(err.message) + ' <a href="#/forgot">Ask for a new link</a></div>'; }
  };
}

const STATUS = { draft: "In progress", submitted_for_review: "Sent for solicitor review" };
const when = iso => iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "";

async function mine() {
  if (!ME) { location.hash = "#/login?next=mine"; return; }
  const list = await api("/api/drafts");
  $app.innerHTML = '<h1>My documents</h1><p class="muted">Signed in as ' + esc(ME.email) + '</p>'
    + (list.length ? '<div class="table-wrap"><table class="tbl"><thead><tr><th>Document</th><th>Name</th><th>Status</th><th>Last saved</th><th></th></tr></thead><tbody>'
      + list.map(d => '<tr><td>' + esc(d.title) + '</td><td>' + esc(d.client_name || "—") + '</td><td><span class="pill">' + esc(STATUS[d.status] || d.status) + '</span></td><td>' + when(d.updated_at) + '</td><td><a class="btn small" href="#/d/' + d.id + '/' + (d.status === "draft" ? "0" : "review") + '">' + (d.status === "draft" ? "Continue" : "View") + '</a></td></tr>').join("")
      + '</tbody></table></div>' : '<div class="card"><p>You have not started anything yet.</p></div>')
    + '<h2>Start something new</h2><p><a class="btn ghost" href="#/">Choose a document</a></p>';
}

async function adminPage(parts) {
  if (!ME || ME.role !== "admin") { $app.innerHTML = '<h1>Admins only</h1><p><a href="#/login?next=admin">Sign in with an admin account</a></p>'; return; }
  const tab = parts[0] || "drafts";
  const tabs = '<nav class="tabs" aria-label="Admin sections">' + [["drafts", "Drafts"], ["users", "Clients"], ["uploads", "Uploads"], ["statements", "Statements"], ["audit", "Audit log"]].map(([k, t]) => '<a href="#/admin/' + k + '"' + (k === tab ? ' aria-current="page"' : "") + '>' + t + '</a>').join("") + '</nav>';
  const head = s => '<h1>Admin</h1><p class="muted small">' + s.clients + ' client' + (s.clients === 1 ? '' : 's') + ' · ' + s.drafts + ' draft' + (s.drafts === 1 ? '' : 's') + ' (' + s.submitted + ' sent for review) · ' + s.uploads + ' upload' + (s.uploads === 1 ? '' : 's') + ' · ' + (s.capacity_statements || 0) + ' statement' + ((s.capacity_statements || 0) === 1 ? '' : 's') + (s.unowned_drafts ? ' · ' + s.unowned_drafts + ' older drafts with no account' : "") + '</p>' + tabs;
  const s = await api("/api/admin/summary");
  const dl = u => '<a href="/api/admin/uploads/' + u.id + '/download">' + esc(u.filename) + '</a>';
  const bind = () => $app.querySelectorAll("[data-api]").forEach(b => b.onclick = async () => {
    if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
    try { await api(b.dataset.api, { method: b.dataset.method, body: b.dataset.body ? JSON.parse(b.dataset.body) : undefined }); route(); } catch (e) { alert(e.message); }
  });
  if (tab === "d") {
    const d = await api("/api/admin/drafts/" + parts[1]);
    $app.innerHTML = head(s) + '<h2>' + esc(d.title) + ' · ' + esc(d.client_name || "no name yet") + '</h2><p class="muted small">Owner ' + esc(d.owner_email || "none (made before accounts)") + ' · ' + esc(STATUS[d.status] || d.status) + ' · saved ' + when(d.updated_at) + ' · ref <span class="ref">' + esc(d.id) + '</span></p>'
      + issuesHtml(d.issues) + (d.missing.length ? '<div class="alert warning"><b>Unanswered</b><ul>' + d.missing.map(m => '<li>' + esc(m) + '</li>').join("") + '</ul></div>' : "")
      + '<h3>Uploads</h3>' + (d.uploads.length ? '<ul class="files">' + d.uploads.map(u => '<li><span>📄 ' + dl(u) + ' <span class="muted">· ' + esc(u.kind) + '</span></span></li>').join("") + '</ul>' : '<p class="muted">None</p>')
      + statementAdminList(d.capacity_statements || [])
      + '<h3>Answers</h3><pre class="answers">' + esc(JSON.stringify(d.answers, null, 2)) + '</pre>'
      + '<p><button class="btn ghost" data-api="/api/admin/drafts/' + d.id + '" data-method="DELETE" data-confirm="Delete this draft and its uploads for good?">Delete draft</button></p>';
    bind(); return;
  }
  if (tab === "statements") {
    if (parts[1]) {
      const st = await api("/api/admin/capacity-statements/" + parts[1]);
      $app.innerHTML = head(s) + statementAdminDetail(st);
      bind(); return;
    }
    const rows = await api("/api/admin/capacity-statements");
    const html = table(["When", "Client", "Owner", "Document", "Current", "Fingerprint", ""], rows.map(st => statementAdminRow(st)).join(""));
    $app.innerHTML = head(s) + html;
    bind(); return;
  }
  const rows = await api("/api/admin/" + tab + (tab === "audit" ? "?limit=300" : "") + (tab === "drafts" && query().get("user") ? "?user_id=" + encodeURIComponent(query().get("user")) : ""));
  const table = (cols, body) => '<div class="table-wrap"><table class="tbl"><thead><tr>' + cols.map(c => '<th>' + c + '</th>').join("") + '</tr></thead><tbody>' + (body || '<tr><td colspan="' + cols.length + '" class="muted">Nothing yet</td></tr>') + '</tbody></table></div>';
  let html = "";
  if (tab === "drafts") html = table(["Document", "Name", "Owner", "Status", "Uploads", "Saved", ""], rows.map(d => '<tr><td>' + esc(d.title) + '</td><td>' + esc(d.client_name || "—") + '</td><td>' + esc(d.owner_email || "—") + '</td><td>' + esc(STATUS[d.status] || d.status) + '</td><td>' + d.uploads + '</td><td>' + when(d.updated_at) + '</td><td class="nowrap"><a class="btn small" href="#/admin/d/' + d.id + '">View</a> <button class="btn ghost small" data-api="/api/admin/drafts/' + d.id + '" data-method="DELETE" data-confirm="Delete this draft and its uploads for good?">Delete</button></td></tr>').join(""));
  if (tab === "users") html = table(["Email", "Role", "Drafts", "Joined", "Last sign-in", ""], rows.map(u => '<tr><td>' + esc(u.email) + '</td><td>' + esc(u.role) + '</td><td><a href="#/admin/drafts?user=' + u.id + '">' + u.drafts + '</a></td><td>' + when(u.created_at) + '</td><td>' + when(u.last_login_at) + '</td><td class="nowrap">'
    + (u.id === ME.id ? '<span class="muted small">You</span>' : '<button class="btn ghost small" data-api="/api/admin/users/' + u.id + '" data-method="PATCH" data-body=\'' + JSON.stringify({ role: u.role === "admin" ? "client" : "admin" }) + '\' data-confirm="Change this account to ' + (u.role === "admin" ? "client" : "admin") + '?">' + (u.role === "admin" ? "Make client" : "Make admin") + '</button> <button class="btn ghost small" data-api="/api/admin/users/' + u.id + '" data-method="DELETE" data-confirm="Delete this account and all of its drafts and uploads for good?">Delete</button>') + '</td></tr>').join(""));
  if (tab === "uploads") html = table(["File", "Kind", "Owner", "Size", "Added", ""], rows.map(u => '<tr><td>' + dl(u) + '</td><td>' + esc(u.kind) + '</td><td>' + esc(u.owner_email || "—") + '</td><td>' + Math.ceil(u.size / 1024) + ' KB</td><td>' + when(u.created_at) + '</td><td class="nowrap"><a class="btn small" href="#/admin/d/' + u.draft_id + '">Draft</a> <button class="btn ghost small" data-api="/api/admin/uploads/' + u.id + '" data-method="DELETE" data-confirm="Delete this file for good?">Delete</button></td></tr>').join(""));
  if (tab === "audit") html = table(["When", "Who", "Action", "Item", "Detail", "IP"], rows.map(a => '<tr><td class="nowrap">' + when(a.at) + '</td><td>' + esc(a.actor_email || "—") + '</td><td>' + esc(a.action) + '</td><td class="small">' + esc((a.target_type || "") + " " + (a.target_id || "")) + '</td><td class="small">' + esc(a.detail && Object.keys(a.detail).length ? JSON.stringify(a.detail) : "") + '</td><td class="small">' + esc(a.ip || "") + '</td></tr>').join(""));
  $app.innerHTML = head(s) + html;
  bind();
}

function goToSignIn(next) {
  const dest = "#/register?next=" + encodeURIComponent(next);
  $app.innerHTML = '<h1>Please create an account or sign in</h1><p>You need an account to start a will, lasting power of attorney or probate draft. We will bring you back afterwards.</p><p><a class="btn accent" href="#/register?next=' + encodeURIComponent(next) + '">Create account</a> <a class="btn ghost" href="#/login?next=' + encodeURIComponent(next) + '">Sign in</a></p>';
  if (location.hash !== dest) location.hash = dest;
  else authPage("register");
}

async function previewService(id) {
  let s;
  try { s = await service(id); }
  catch (e) {
    $app.innerHTML = '<div class="inner-page"><h1>Sorry, that document was not found</h1><p>' + esc(e.message) + '</p><p><a class="btn ghost" href="#/">Back</a></p></div>';
    return;
  }
  const steps = s.steps || [];
  const st = steps.find(x => x.video) || steps[0] || {};
  const vid = st.video || s.review_video;
  const list = steps.map((step, i) => '<li><b>' + (i + 1) + '. ' + esc(step.title) + '</b>' + (step.video ? ' · video' : '') + '</li>').join("");
  const prepare = (s.prepare || []).map(stage => '<h3>' + esc(stage.title) + '</h3><ul>' + stage.items.map(it => '<li><b>' + esc(it.title) + '.</b> ' + esc(it.ask) + '</li>').join("") + '</ul>').join("");
  $app.innerHTML = '<div class="inner-page"><p class="eyebrow">' + steps.length + ' steps</p><h1>' + esc(s.title) + '</h1><p class="lead">' + esc(s.summary || "") + '</p>'
    + (prepare ? '<section class="card"><h2>What to have ready</h2><p>You do not need all of this on the first day. A photo or scan is enough to start, unless a step asks for an original.</p>' + prepare + '</section>' : '')
    + (vid ? videoHtml(vid, st.title || s.title) : '<p class="muted">This document is questions and solicitor review. A presenter video is not on this step yet.</p>')
    + (vid ? '<p>Choose Woman or Man. That choice is kept for the rest of the steps. If the man clip is not on the site yet, the woman plays and your choice is saved.</p>' : '')
    + '<ol class="step-list">' + list + '</ol>'
    + (ME ? '<p><button class="btn" type="button" id="go-start">Continue to step 1</button></p>'
      : '<p><a class="btn" href="#/register?next=' + encodeURIComponent("s/" + id) + '">Create an account to continue</a> <a class="btn ghost" href="#/login?next=' + encodeURIComponent("s/" + id) + '">Sign in</a></p>')
    + '</div>';
  const go = document.getElementById("go-start");
  if (go) go.onclick = () => beginDraft(id);
}
async function beginDraft(id) {
  $app.innerHTML = '<h1>Starting…</h1><p class="muted">Please wait.</p>';
  try {
    const d = await api("/api/drafts", { method: "POST", body: { service: id, answers: {} } });
    remember(d);
    location.replace("#/d/" + d.id + "/0");
  } catch (e) {
    if (e.quiet) return;
    if (e.status === 403) {
      await fetch("/api/auth/me", { credentials: "same-origin", cache: "no-store" });
      try {
        const d = await api("/api/drafts", { method: "POST", body: { service: id, answers: {} } });
        remember(d);
        location.replace("#/d/" + d.id + "/0");
        return;
      } catch (e2) {
        if (e2.quiet) return;
        e = e2;
      }
    }
    $app.innerHTML = '<h1>Sorry, something went wrong</h1><div class="alert error">' + esc(e.message) + '</div><p><a class="btn ghost" href="#/">Back to the start</a></p>';
  }
}
async function start(id) {
  if (!id) {
    $app.innerHTML = '<h1>Sorry, that document was not found</h1><p><a class="btn ghost" href="#/">Back to the start</a></p>';
    return;
  }
  if (!ME) { await previewService(id); return; }
  return beginDraft(id);
}

function bindStart() {
  $app.querySelectorAll("[data-start]").forEach(a => {
    a.addEventListener("click", ev => {
      ev.preventDefault();
      const sid = a.getAttribute("data-start");
      const dest = "#/s/" + sid;
      if (location.hash === dest) start(sid);
      else location.hash = dest;
    });
  });
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
  if (f.type === "checkbox") {
    const wording = f.wording ? '<p class="wording">Official wording to copy into ' + esc(f.section || "section 7") + ': “' + esc(f.wording) + '”</p>' : "";
    const warn = f.warning ? '<div class="alert warning">' + esc(f.warning) + '</div>' : "";
    return '<div class="field' + (f.wording ? " preset" : "") + '"><label class="check"><input type="checkbox" id="' + id + '" name="' + id + '"' + (value === true ? " checked" : "") + req + desc + '><span>' + esc(f.label) + '</span></label>' + wording + warn + hint + '</div>';
  }
  const label = '<label for="' + id + '">' + esc(f.label) + opt + '</label>' + hint;
  if (f.type === "select") return '<div class="field">' + label + '<select id="' + id + '" name="' + id + '"' + req + desc + '><option value="">Choose…</option>' + f.options.map(o => '<option' + (o === value ? " selected" : "") + '>' + esc(o) + '</option>').join("") + '</select></div>';
  if (f.type === "textarea") return '<div class="field">' + label + '<textarea id="' + id + '" name="' + id + '"' + req + desc + '>' + esc(value) + '</textarea></div>';
  const type = f.type === "number" ? "number" : f.type;
  const extra = f.type === "number" ? ' inputmode="decimal" step="any" min="0"' : f.type === "email" ? ' autocomplete="email"' : "";
  return '<div class="field">' + label + '<input id="' + id + '" name="' + id + '" type="' + type + '"' + extra + ' value="' + esc(value) + '"' + req + desc + '></div>';
}

function safeFormKey(k) {
  return typeof k === "number" || (k !== "__proto__" && k !== "constructor" && k !== "prototype");
}
function readForm(form) {
  const out = Object.create(null);
  for (const el of form.querySelectorAll("[name]")) {
    const keys = el.name.split("__").map(k => /^\d+$/.test(k) ? Number(k) : k);
    if (keys.some(k => !safeFormKey(k))) continue;
    let node = out;
    keys.forEach((k, i) => {
      if (i === keys.length - 1) { node[k] = el.type === "checkbox" ? el.checked : el.value; return; }
      node[k] ??= typeof keys[i + 1] === "number" ? [] : {};
      node = node[k];
    });
  }
  for (const fs of form.querySelectorAll("[data-list]")) {  // keep empty list items
    const keys = fs.dataset.list.split("__").map(k => /^\d+$/.test(k) ? Number(k) : k);
    if (keys.some(k => !safeFormKey(k))) continue;
    let node = out;
    keys.forEach((k, i) => { if (i === keys.length - 1) { node[k] = (node[k] || []).map(x => x ?? {}); const n = fs.querySelectorAll(":scope > .item").length; while (node[k].length < n) node[k].push({}); } else node = node[k] ??= typeof keys[i + 1] === "number" ? [] : {}; });
  }
  return out;
}

function withBothPresenters(v) {
  if (typeof v === "string") {
    v = { id: v, src: "/static/videos/" + v + ".mp4", poster: "/static/videos/" + v + ".jpg", captions: "/static/videos/" + v + ".vtt", default_presenter: "female", presenters: [] };
  }
  if (!v || !v.src) return v;
  const presenters = (v.presenters || []).slice();
  const female = presenters.find(p => p.id === "female") || {
    id: "female", label: "Woman", src: v.src, poster: v.poster, captions: v.captions
  };
  if (!presenters.some(p => p.id === "female")) presenters.unshift(female);
  if (!presenters.some(p => p.id === "male")) {
    const src = (female.src || v.src || "").replace(/(_female)?\.mp4(\?.*)?$/, "_male.mp4");
    presenters.push({ id: "male", label: "Man", src: src, poster: (female.poster || "").replace(/(_female)?\.jpg(\?.*)?$/, "_male.jpg"), captions: (female.captions || v.captions || "").replace(/(_female)?\.vtt(\?.*)?$/, "_male.vtt") });
  }
  presenters.forEach(p => { if (p.id === "female") p.label = "Woman"; if (p.id === "male") p.label = "Man"; });
  return Object.assign({}, v, { presenters: presenters, default_presenter: v.default_presenter || "female" });
}
function chosenPresenter(v) {
  v = withBothPresenters(v);
  const list = (v && v.presenters) || [];
  if (!list.length) return null;
  const want = localStorage.getItem("ldp-presenter") || v.default_presenter || "female";
  return list.find(p => p.id === want) || list[0];
}
function videoHtml(v, title) {
  if (!v) return "";
  v = withBothPresenters(v);
  const ch = chosenPresenter(v) || v;
  const choice = (v.presenters && v.presenters.length > 1)
    ? '<fieldset class="presenter-choice"><legend>Choose a presenter</legend>'
      + v.presenters.map(p => {
          const on = ch && ch.id === p.id;
          return '<label class="presenter-opt"><input type="radio" name="ldp-presenter" value="' + esc(p.id) + '"' + (on ? " checked" : "") + '><span>' + esc(p.label) + '</span></label>';
        }).join("")
      + '</fieldset>'
    : "";
  return choice
    + '<div class="video"><video controls preload="none" playsinline' + (ch.poster ? ' poster="' + esc(ch.poster) + '"' : "") + ' aria-label="Video: ' + esc(title) + '"><source src="' + esc(ch.src) + '" type="video/mp4">'
    + (ch.captions ? '<track kind="captions" srclang="en" label="English" src="' + esc(ch.captions) + '" default>' : "") + '</video></div>'
    + '<p class="ai-label small"><span aria-hidden="true">ⓘ</span> AI-generated video: the presenter is not a real person and the voice is an AI-generated voice.</p>';
}
document.addEventListener("change", e => {
  const t = e.target;
  if (!t || t.name !== "ldp-presenter") return;
  localStorage.setItem("ldp-presenter", t.value);
  if (typeof route === "function") route();
});
document.addEventListener("error", e => {
  const el = e.target;
  if (!el || el.tagName !== "VIDEO") return;
  const source = el.querySelector("source");
  const src = (source && source.getAttribute("src")) || "";
  if (src.indexOf("_male.mp4") === -1) return;
  const box = el.closest(".video");
  if (!box || box.dataset.fellback) return;
  box.dataset.fellback = "1";
  const female = src.replace("_male.mp4", ".mp4");
  if (source) source.setAttribute("src", female);
  el.load();
  box.insertAdjacentHTML("afterend", '<p class="muted small">The man presenter is not on the site for this clip yet, so the woman is playing. Your choice is saved for the clips that have both.</p>');
}, true);
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
    + (draft.uploads.length ? '<ul class="files">' + draft.uploads.map(u => '<li><span>📄 <a href="/api/drafts/' + draft.id + '/uploads/' + u.id + '">' + esc(u.filename) + '</a> <span class="muted">· ' + esc(u.kind) + ' · ' + ({ pdf: "text read", docx: "text read", text: "text read", ocr: "read from the photo or scan", image: "photo kept, nothing could be read", "scanned-pdf": "scan kept, nothing could be read", unreadable: "could not read, kept for your solicitor" })[u.read_as] + '</span></span>' + (draft.status === "draft" ? '<button type="button" class="btn ghost small" data-del="' + u.id + '">Delete</button>' : "") + '</li>').join("") + '</ul>' : "")
    + (sugg.some(s => s.mode !== "note") && draft.status === "draft" ? '<p><button type="button" class="btn" id="fill-papers">Fill in what these papers show</button></p><p class="small">This is the point where the papers are written into the draft. It does not finish questions the papers do not answer, and it does not file anything.</p>' : "")
    + (sugg.length ? '<div class="sugg"><h3>Read from your documents</h3><ul>' + sugg.map(s => '<li><span>' + esc(s.label) + ' <span class="muted small">(' + esc(s.source) + ')</span></span>' + (s.mode !== "note" && draft.status === "draft" ? '<button type="button" class="btn small" data-sugg="' + esc(s.id) + '">Add</button>' : "") + '</li>').join("") + '</ul></div>' : "");
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
    + (st.tool ? '<div id="tool" class="tool"></div>' : "")
    + '<form id="f" novalidate><div id="fields">' + st.fields.map(f => fieldHtml(f, cur[f.name], [f.name], cur)).join("") + '</div>' + uploadsHtml(st, draft)
    + '<div id="msg" aria-live="assertive"></div><div class="actions">' + (index ? '<a class="btn ghost" href="#/d/' + id + '/' + (index - 1) + '">← Back</a>' : '<a class="btn ghost" href="#/">Home</a>')
    + '<span class="saved" id="saved" aria-live="polite"></span><button class="btn" type="submit">' + (last ? "Check my draft →" : "Save and continue →") + '</button></div></form></section></div>';
  const form = document.getElementById("f"), fields = document.getElementById("fields"), saved = document.getElementById("saved");
  if (st.tool && TOOLS[st.tool]) TOOLS[st.tool](document.getElementById("tool"), draft);
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
    if (t.id === "fill-papers") {
      const d = await api("/api/drafts/" + id + "/fill", { method: "POST", body: {} });
      document.getElementById("upmsg").innerHTML = '<div class="alert ok"><b>Filled from the papers</b><ul>' + (d.filled_from_papers || []).map(x => '<li>' + esc(x) + '</li>').join("") + '</ul><p>' + (d.missing.length ? d.missing.length + ' questions are still blank. Check each step.' : 'Check each step, then continue.') + '</p></div>';
      return;
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
      + issuesHtml(draft.issues) + '<div id="statement-panel"></div><p><a class="btn" href="#/d/' + id + '/' + (draft.missing.length ? stepOf(draft.missing[0]) : 0) + '">Go to the first question</a></p></section></div>';
    mountStatementPanel(id);
    return;
  }
  const doc = await api("/api/drafts/" + id + "/document");
  $app.innerHTML = head + '<h1>Check your draft</h1>' + videoHtml(s.review_video, "Check and send") + issuesHtml(doc.issues)
    + '<article class="doc"><h2>' + esc(doc.title) + '</h2><p class="notice">' + esc(doc.notice) + '</p>'
    + doc.sections.map(sec => '<h3>' + esc(sec.heading) + '</h3>' + sec.paragraphs.map((p, i) => '<div class="clause"><p>' + esc(p) + '</p>' + (sec.notes && sec.notes[i] ? '<p class="note">💡 ' + esc(sec.notes[i].replace(/^\d+\.\s*/, "")) + '</p>' : "") + '</div>').join("")).join("") + '</article>'
    + '<h2>What happens next</h2><ol>' + doc.next_steps.map(n => '<li>' + esc(n) + '</li>').join("") + '</ol>' + sourcesHtml(doc.sources)
    + '<div id="statement-panel"></div>'
    + '<div class="actions"><a class="btn ghost" href="#/d/' + id + '/0">Change answers</a><span><a class="btn ghost" href="/api/drafts/' + id + '/pdf">Download PDF</a> '
    + (draft.status === "draft" ? '<button class="btn accent" id="submit">Send to a solicitor for review</button>' : '<span class="alert ok">Sent for solicitor review</span>') + '</span></div><div id="msg" aria-live="polite"></div></section></div>';
  const btn = document.getElementById("submit");
  if (btn) btn.onclick = async () => { if (!confirm("Send this draft to a solicitor for review? You will not be able to change it afterwards.")) return; btn.disabled = true; await api("/api/drafts/" + id + "/submit", { method: "POST" }); route(); };
  mountStatementPanel(id);
}

window.addEventListener("hashchange", route);
whoami().catch(() => {}).finally(route);


function shortHash(h) {
  return h ? h.slice(0, 12) + "…" : "";
}

function statementAdminList(rows) {
  if (!rows.length) return '<h3>Supporting video statements</h3><p class="muted">None</p>';
  return '<h3>Supporting video statements</h3><ul class="files">' + rows.map(st => '<li><span>🎥 <a href="#/admin/statements/' + st.id + '">' + esc(st.filename) + '</a> <span class="muted">· ' + when(st.recorded_at) + (st.is_current ? ' · current' : ' · earlier take') + (st.matches_current_document === false ? ' · recorded against an earlier version of the answers' : "") + '</span></span></li>').join("") + '</ul>';
}

function statementAdminRow(st) {
  return '<tr><td class="nowrap">' + when(st.recorded_at) + '</td><td>' + esc(st.client_name || "—") + '</td><td>' + esc(st.owner_email || "—") + '</td><td><a href="#/admin/d/' + st.draft_id + '">' + esc(st.service) + '</a></td><td>' + (st.is_current ? "Yes" : "No") + '</td><td class="small ref">' + esc(shortHash(st.content_sha256)) + '</td><td class="nowrap"><a class="btn small" href="#/admin/statements/' + st.id + '">View</a></td></tr>';
}

function statementAdminDetail(st) {
  return '<h2>Supporting video statement</h2>'
    + '<p class="muted small">Owner ' + esc(st.owner_email || "—") + ' · ' + esc(st.client_name || "") + ' · recorded ' + when(st.recorded_at) + (st.is_current ? ' · current take' : ' · earlier take') + '</p>'
    + '<div class="statement-video"><video controls preload="metadata" src="/api/admin/capacity-statements/' + st.id + '/video"></video></div>'
    + '<dl class="audit-dl">'
    + '<div><dt>Recorded at (UTC)</dt><dd>' + esc(st.recorded_at || "") + '</dd></div>'
    + '<div><dt>User id</dt><dd class="ref">' + esc(st.user_id || "") + '</dd></div>'
    + '<div><dt>Document id</dt><dd class="ref">' + esc(st.draft_id || "") + '</dd></div>'
    + '<div><dt>Document version hash</dt><dd class="ref">' + esc(st.document_version_hash || "") + (st.matches_current_document === false ? ' <span class="muted">(answers have changed since this was recorded)</span>' : "") + '</dd></div>'
    + '<div><dt>SHA-256 fingerprint</dt><dd class="ref">' + esc(st.content_sha256 || "") + '</dd></div>'
    + '<div><dt>Source</dt><dd>' + esc(st.source || "") + ' · ' + Math.ceil((st.size || 0) / 1024) + ' KB' + (st.duration_seconds ? ' · ' + st.duration_seconds + 's' : "") + '</dd></div>'
    + '<div><dt>Prompt set</dt><dd>' + esc(st.prompt_set_id || "") + '</dd></div>'
    + '<div><dt>IP address</dt><dd>' + esc(st.ip || "—") + '</dd></div>'
    + '<div><dt>Browser</dt><dd class="small">' + esc(st.user_agent || "—") + '</dd></div>'
    + '<div><dt>Medical assessment interest</dt><dd>' + (st.medical_assessment_interest ? "Yes, the client asked to talk about a medical capacity assessment" : "No") + '</dd></div>'
    + '</dl>'
    + '<p><a class="btn ghost" href="#/admin/d/' + st.draft_id + '">Open the draft</a></p>';
}

async function mountStatementPanel(draftId) {
  const el = document.getElementById("statement-panel");
  if (!el) return;
  let guide;
  try {
    guide = await api("/api/drafts/" + draftId + "/capacity-statement");
  } catch (e) {
    if (e.status === 404) return;
    el.innerHTML = '<div class="alert warning">' + esc(e.message) + '</div>';
    return;
  }
  let recorder = null;
  let stream = null;
  let chunks = [];
  let blob = null;
  let startedAt = 0;
  let timer = null;
  let duration = 0;
  let medicalInterest = false;
  let cancelled = false;

  const stopStream = () => { if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; } };
  const clearTimer = () => { if (timer) { clearInterval(timer); timer = null; } };

  const render = (mode, err) => {
    const prompts = '<ol class="prompt-list">' + guide.prompts.map(p => '<li><b>' + esc(p.title) + '</b><span>' + esc(p.text) + '</span></li>').join("") + '</ol>';
    const disclaimer = '<div class="alert warning"><b>This recording supports, but does not prove, capacity.</b><p>' + esc(guide.disclaimer) + '</p><p class="small">' + esc(guide.golden_rule) + '</p><p class="small muted">' + esc(guide.legal_basis) + '</p></div>';
    const current = guide.current;
    let body = '<h2>' + esc(guide.title) + '</h2>' + disclaimer;
    if (current) {
      body += '<div class="card statement-current"><p>You recorded a supporting statement on ' + when(current.recorded_at) + '.'
        + (current.matches_current_document === false ? ' This was recorded against an earlier version of your answers. If you have changed anything important, please record it again.' : "")
        + '</p><div class="statement-video"><video controls preload="metadata" src="/api/drafts/' + draftId + '/capacity-statements/' + current.id + '/video"></video></div>'
        + '<p class="muted small">Fingerprint ' + esc(shortHash(current.content_sha256)) + ' · document version ' + esc(shortHash(current.document_version_hash)) + '</p></div>';
    }
    if (mode === "idle") {
      body += '<p>This is optional. You can record a short video of yourself, in your own words, answering the questions below. If your camera does not work, you can upload a video instead.</p>'
        + prompts
        + '<label class="check"><input type="checkbox" id="st-consent"> <span>' + esc(guide.consent) + '</span></label>'
        + '<label class="check"><input type="checkbox" id="st-medical"> <span>Please ask the solicitor who reviews my draft to talk with me about arranging a medical capacity assessment.</span></label>'
        + (err ? '<div class="alert error" role="alert">' + esc(err) + '</div>' : "")
        + '<p class="actions statement-actions"><button type="button" class="btn" id="st-start">Record a statement</button> <label class="btn ghost">Upload a video instead<input type="file" id="st-file" accept="video/*" hidden></label></p>'
        + '<p class="muted small">Maximum about ' + Math.round(guide.max_seconds / 60) + ' minutes or ' + Math.round(guide.max_bytes / (1024 * 1024)) + ' MB. You can retake it before you confirm.</p>';
    } else if (mode === "record") {
      body += '<p>Work through the questions in your own words. Press stop when you have finished.</p>' + prompts
        + '<div class="statement-video recording"><video id="st-preview" autoplay muted playsinline></video><span class="rec-dot" aria-hidden="true"></span><span class="rec-time" id="st-time">0:00</span></div>'
        + (err ? '<div class="alert error" role="alert">' + esc(err) + '</div>' : "")
        + '<p class="actions statement-actions"><button type="button" class="btn accent" id="st-stop">Stop recording</button> <button type="button" class="btn ghost" id="st-cancel">Cancel</button></p>';
    } else if (mode === "preview") {
      body += '<p>Please watch your recording. If you are happy with it, confirm it. If not, you can retake it. It is not saved until you confirm.</p>'
        + prompts
        + '<div class="statement-video"><video id="st-preview" controls playsinline></video></div>'
        + (err ? '<div class="alert error" role="alert">' + esc(err) + '</div>' : "")
        + '<p class="actions statement-actions"><button type="button" class="btn accent" id="st-confirm">Confirm and save this recording</button> <button type="button" class="btn ghost" id="st-retake">Retake</button></p>';
    } else if (mode === "saving") {
      body += '<p class="muted">Saving your recording…</p>';
    }
    el.innerHTML = '<section class="card statement-panel">' + body + '</section>';
    bind(mode);
  };

  const clock = s => Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");

  const pickFile = file => {
    if (!file) return;
    if (file.size > guide.max_bytes) { render("idle", "That video is too large. Please try a shorter one."); return; }
    blob = file;
    duration = 0;
    render("preview");
  };

  const startRecording = async () => {
    const consent = document.getElementById("st-consent");
    if (!consent || !consent.checked) { render("idle", "Please read and tick the consent box before you record."); return; }
    medicalInterest = !!(document.getElementById("st-medical") && document.getElementById("st-medical").checked);
    stopStream();
    chunks = [];
    blob = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    } catch (e) {
      render("idle", "The camera or microphone could not be started. You can upload a video instead, or check the browser permission.");
      return;
    }
    const types = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"];
    const mime = types.find(t => window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || "";
    try {
      recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    } catch (e) {
      stopStream();
      render("idle", "This browser cannot record a video here. Please upload a short video instead.");
      return;
    }
    recorder.ondataavailable = ev => { if (ev.data && ev.data.size) chunks.push(ev.data); };
    recorder.onstop = () => {
      clearTimer();
      stopStream();
      if (cancelled) { cancelled = false; blob = null; render("idle"); return; }
      duration = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
      blob = new Blob(chunks, { type: recorder.mimeType || "video/webm" });
      render("preview");
    };
    render("record");
    const preview = document.getElementById("st-preview");
    if (preview) { preview.srcObject = stream; preview.play().catch(() => {}); }
    startedAt = Date.now();
    recorder.start(250);
    timer = setInterval(() => {
      const s = Math.round((Date.now() - startedAt) / 1000);
      const t = document.getElementById("st-time");
      if (t) t.textContent = clock(s);
      if (s >= guide.max_seconds && recorder && recorder.state === "recording") recorder.stop();
    }, 250);
  };

  const bind = mode => {
    const start = document.getElementById("st-start");
    if (start) start.onclick = startRecording;
    const file = document.getElementById("st-file");
    if (file) file.onchange = ev => {
      const consent = document.getElementById("st-consent");
      if (!consent || !consent.checked) { ev.target.value = ""; render("idle", "Please read and tick the consent box before you upload."); return; }
      medicalInterest = !!(document.getElementById("st-medical") && document.getElementById("st-medical").checked);
      pickFile(ev.target.files && ev.target.files[0]);
    };
    const stop = document.getElementById("st-stop");
    if (stop) stop.onclick = () => { cancelled = false; if (recorder && recorder.state === "recording") recorder.stop(); };
    const cancel = document.getElementById("st-cancel");
    if (cancel) cancel.onclick = () => { cancelled = true; if (recorder && recorder.state === "recording") recorder.stop(); else { stopStream(); clearTimer(); blob = null; render("idle"); } };
    const retake = document.getElementById("st-retake");
    if (retake) retake.onclick = () => { blob = null; render("idle"); };
    const confirm = document.getElementById("st-confirm");
    if (confirm) confirm.onclick = submit;
    const preview = document.getElementById("st-preview");
    if (mode === "preview" && preview && blob) preview.src = URL.createObjectURL(blob);
  };

  const submit = async () => {
    if (!blob) { render("idle", "Please record or choose a video first."); return; }
    const medical = document.getElementById("st-medical");
    const form = new FormData();
    const type = blob.type || "video/webm";
    const ext = type.includes("mp4") ? ".mp4" : type.includes("ogg") ? ".ogv" : ".webm";
    form.append("file", blob, "statement" + ext);
    form.append("consent", "true");
    form.append("confirmed", "true");
    form.append("prompt_set_id", guide.prompt_set_id);
    form.append("source", blob instanceof File ? "upload" : "camera");
    if (duration) form.append("duration_seconds", String(duration));
    form.append("medical_assessment_interest", (medical && medical.checked) || medicalInterest ? "true" : "false");
    render("saving");
    try {
      guide = await api("/api/drafts/" + draftId + "/capacity-statements", { method: "POST", body: form });
      blob = null;
      render("idle");
    } catch (e) {
      render("preview", e.message);
    }
  };

  render("idle");
}

// Read-only lookup tools shown above a step's questions. They search official lists only; the
// family records what they found in the step's own questions. Nothing is filed or submitted.
const TOOLS = {
  bona_vacantia(box, draft) {
    const dec = (draft.answers || {}).deceased || {};
    const parts = String(dec.full_name || "").trim().split(/\s+/);
    const sur = parts.length > 1 ? parts[parts.length - 1] : (parts[0] || ""), fore = parts.length > 1 ? parts[0] : "";
    box.innerHTML = '<div class="card"><h2>Search the unclaimed estates list</h2><form id="bv"><div class="field"><label for="bv_s">Surname</label><input id="bv_s" value="' + esc(sur) + '" required minlength="2"></div>'
      + '<div class="field"><label for="bv_f">First name (optional)</label><input id="bv_f" value="' + esc(fore) + '"></div><p><button class="btn" type="submit">Search the list</button></p></form><div id="bv_out" aria-live="polite"></div></div>';
    box.querySelector("#bv").onsubmit = async e => {
      e.preventDefault();
      const out = box.querySelector("#bv_out"), s = box.querySelector("#bv_s").value.trim(), f = box.querySelector("#bv_f").value.trim();
      if (s.length < 2) { out.innerHTML = '<div class="alert error">Type at least 2 letters of the surname.</div>'; return; }
      out.innerHTML = '<p class="muted">Searching…</p>';
      try {
        const r = await api("/api/probate/bona-vacantia?surname=" + encodeURIComponent(s) + "&forename=" + encodeURIComponent(f));
        const rows = r.matches.map(m => '<tr><td>' + esc(m.bv_reference) + '</td><td>' + esc(m.forename + " " + m.surname) + '</td><td>' + esc(m.date_of_death) + '</td><td>' + esc(m.place_of_death) + '</td></tr>').join("");
        out.innerHTML = (r.note ? '<div class="alert warning">' + esc(r.note) + '</div>' : "")
          + (rows ? '<table class="table"><thead><tr><th>BV reference</th><th>Name</th><th>Date of death</th><th>Place of death</th></tr></thead><tbody>' + rows + '</tbody></table>' : '<div class="alert info">No match for that name on the list.</div>')
          + '<p class="small">List fetched ' + esc(r.fetched_at || "") + ' (UTC) from <a href="' + esc(r.page_url) + '" target="_blank" rel="noopener">GOV.UK</a>. ' + esc(r.licence) + ' To claim, follow <a href="' + esc(r.claim_url) + '" target="_blank" rel="noopener">the GOV.UK claim guidance</a>. You make the claim yourself.</p>';
      } catch (err) { out.innerHTML = '<div class="alert error">' + esc(err.message) + '</div>'; }
    };
  },
};
