"use strict";
const $app = document.getElementById("app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" }[c]));

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
async function whoami() { try { ME = (await api("/api/auth/me")).user; nav(); } catch(e) {} }
function nav() {
  const el = document.getElementById("acct");
  if (!el) return;
  el.innerHTML = ME ? '<a href="#/mine">My documents</a><button type="button" class="linkbtn" id="signout">Sign out</button>'
    : '<a href="#/login" class="btn ghost small">Client Login</a><a href="#/" class="btn">Get Started</a>';
  const so = document.getElementById("signout");
  if (so) so.onclick = async () => { await api("/api/auth/logout", { method: "POST" }); ME = null; nav(); location.hash = "#/"; };
}
const query = () => new URLSearchParams((location.hash.split("?")[1]) || "");

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean);
  try {
    if (["login", "register", "forgot"].includes(parts[0])) return authPage(parts[0]);
    if (parts[0] === "how") return howPage();
    if (parts[0] === "about") return aboutPage();
    if (parts[0] === "faq") return faqPage();
    if (parts[0] === "pricing") return pricingPage();
    if (parts[0] === "mine") return await mine();
    return await home();
  } catch (e) {
    $app.innerHTML = '<h1>Sorry, something went wrong</h1><p>' + esc(e.message) + '</p><p><a class="btn" href="#/">Home</a></p>';
  }
}

async function home() {
  $app.innerHTML = `
    <section class="hero-section">
      <div>
        <p class="eyebrow">Legal documents, made simple</p>
        <h1>Wills, LPA and Probate you can trust.</h1>
        <p class="lead">Signed and Sorted helps you plan ahead and sort what matters with clear, secure legal support for you and your family in England and Wales.</p>
        <div class="hero-actions">
          <a class="btn" href="#/s/will">Start Today →</a>
          <a class="btn ghost" href="#/how">How It Works</a>
        </div>
      </div>
      <div class="hero-image">
        <img src="https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80" alt="Lasting Power of Attorney document on a clipboard with pen">
      </div>
    </section>
    <section class="services-section">
      <h2>Our legal services</h2>
      <div class="service-grid">
        <article class="service-card">
          <div class="icon">📄</div>
          <h3>Will Writing</h3>
          <p>Make a will that protects your wishes and the people you care about.</p>
          <ul><li>Simple online process</li><li>Mirror, single and tailored wills</li><li>Securely signed and stored</li></ul>
          <a class="btn" href="#/s/will">Start Your Will →</a>
        </article>
        <article class="service-card">
          <div class="icon">🛡️</div>
          <h3>Lasting Power of Attorney (LPA)</h3>
          <p>Set up LPA for health and welfare, and property and financial decisions.</p>
          <ul><li>Property & Financial Affairs LPA</li><li>Health & Welfare LPA</li><li>Guidance at every step</li></ul>
          <a class="btn" href="#/s/lpa_property">Start Your LPA →</a>
        </article>
        <article class="service-card">
          <div class="icon">🏛️</div>
          <h3>Probate Assistance</h3>
          <p>Apply for probate and sort estate administration with confidence.</p>
          <ul><li>Probate application support</li><li>Document checking & guidance</li><li>Clear, fixed-fee options</li></ul>
          <a class="btn" href="#/s/probate">Start Probate →</a>
        </article>
      </div>
    </section>
    <section class="trust-bar">
      <div class="trust-inner">
        <div class="trust-item"><strong>Trusted across England and Wales</strong>Secure, compliant and regulated.</div>
        <div class="trust-item"><strong>Secure & confidential</strong></div>
        <div class="trust-item"><strong>Regulated legal services</strong></div>
        <div class="trust-item"><strong>Expert support when you need it</strong></div>
      </div>
    </section>
  `;
}

function howPage() { $app.innerHTML = '<h1>How it works</h1><p><a class="btn" href="#/">Get started</a></p>'; }
function aboutPage() { $app.innerHTML = '<h1>About Us</h1><p><a class="btn ghost" href="#/">Back to home</a></p>'; }
function faqPage() { $app.innerHTML = '<h1>Help & Support</h1><p><a class="btn ghost" href="#/">Back to home</a></p>'; }
function pricingPage() { $app.innerHTML = '<h1>Pricing</h1><p><a class="btn ghost" href="#/">Back to home</a></p>'; }

function authPage(kind) {
  $app.innerHTML = '<div class="narrow"><h1>' + (kind === 'login' ? 'Sign in' : 'Create account') + '</h1><form class="card" id="auth"><div id="msg"></div><div class="field"><label>Email</label><input id="email" type="email" required></div><div class="field"><label>Password</label><input id="password" type="password" required></div><p><button class="btn">Continue</button></p></form></div>';
  document.getElementById("auth").onsubmit = async e => {
    e.preventDefault();
    try {
      const r = await api("/api/auth/" + kind, { method: "POST", body: { email: document.getElementById("email").value.trim(), password: document.getElementById("password").value } });
      ME = r.user; nav(); location.hash = "#/";
    } catch (err) { document.getElementById("msg").innerHTML = '<div class="alert error">' + esc(err.message) + '</div>'; }
  };
}

async function mine() {
  if (!ME) { location.hash = "#/login"; return; }
  const list = await api("/api/drafts");
  $app.innerHTML = '<h1>My documents</h1>' + (list.length ? list.map(d => '<div class="card"><p>' + esc(d.title) + '</p></div>').join('') : '<p>No documents yet.</p>') + '<p><a class="btn" href="#/">Home</a></p>';
}

window.addEventListener("hashchange", route);
whoami().finally(() => route());
