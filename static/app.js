"use strict";
const $app = document.getElementById("app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&", "<": "<", ">": ">", '"': """, "'": "&#39;" }[c]));

function home() {
  $app.innerHTML = `
    <section class="hero-section">
      <div>
        <p class="eyebrow">Legal documents, made simple</p>
        <h1>Wills, LPA and Probate<br>you can trust.</h1>
        <p class="lead">Signed and Sorted helps you plan ahead and sort what matters with clear, secure legal support for you and your family in England and Wales.</p>
        <div class="hero-actions">
          <a class="btn" href="#/s/will">Start Today →</a>
          <a class="btn ghost" href="#/how">▶ How It Works</a>
        </div>
      </div>
      <div class="hero-image">
        <img src="https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=1000&q=80" alt="Lasting Power of Attorney on a clipboard with pen">
      </div>
    </section>

    <section class="services-section">
      <h2>Our legal services</h2>
      <div class="service-grid">
        <article class="service-card">
          <div class="icon">📄</div>
          <h3>Will Writing</h3>
          <p>Make a will that protects your wishes and the people you care about.</p>
          <ul>
            <li>Simple online process</li>
            <li>Mirror, single and tailored wills</li>
            <li>Securely signed and stored</li>
          </ul>
          <a class="btn" href="#/s/will">Start Your Will →</a>
        </article>
        <article class="service-card">
          <div class="icon">🛡️</div>
          <h3>Lasting Power of Attorney (LPA)</h3>
          <p>Set up LPA for health and welfare, and property and financial decisions.</p>
          <ul>
            <li>Property & Financial Affairs LPA</li>
            <li>Health & Welfare LPA</li>
            <li>Guidance at every step</li>
          </ul>
          <a class="btn" href="#/s/lpa_property">Start Your LPA →</a>
        </article>
        <article class="service-card">
          <div class="icon">🏛️</div>
          <h3>Probate Assistance</h3>
          <p>Apply for probate and sort estate administration with confidence.</p>
          <ul>
            <li>Probate application support</li>
            <li>Document checking & guidance</li>
            <li>Clear, fixed-fee options</li>
          </ul>
          <a class="btn" href="#/s/probate">Start Probate →</a>
        </article>
      </div>

      <h2 style="margin-top:48px">Agreements</h2>
      <div class="service-grid">
        <article class="service-card">
          <div class="icon">💍</div>
          <h3>Prenuptial Agreement</h3>
          <p>Set out how assets should be treated if the marriage ends.</p>
          <ul>
            <li>Full disclosure guidance</li>
            <li>Independent advice arranged</li>
            <li>Solicitor review included</li>
          </ul>
          <a class="btn" href="#/s/prenup">Start Prenup →</a>
        </article>
        <article class="service-card">
          <div class="icon">📜</div>
          <h3>Postnuptial Agreement</h3>
          <p>An agreement signed after marriage covering assets and intentions.</p>
          <ul>
            <li>Clear asset treatment</li>
            <li>Both parties protected</li>
            <li>Solicitor checked</li>
          </ul>
          <a class="btn" href="#/s/postnup">Start Postnup →</a>
        </article>
        <article class="service-card">
          <div class="icon">🏠</div>
          <h3>Cohabitation Agreement</h3>
          <p>For unmarried couples covering property, money and separation.</p>
          <ul>
            <li>Property ownership clear</li>
            <li>Separation arrangements</li>
            <li>Solicitor review</li>
          </ul>
          <a class="btn" href="#/s/cohabitation">Start Cohabitation →</a>
        </article>
        <article class="service-card">
          <div class="icon">💼</div>
          <h3>Employment Settlement</h3>
          <p>End employment on agreed terms with proper advice.</p>
          <ul>
            <li>Clear settlement terms</li>
            <li>Independent advice required</li>
            <li>Solicitor checked</li>
          </ul>
          <a class="btn" href="#/s/employment_settlement">Start Settlement →</a>
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

function howPage() { $app.innerHTML = '<h1>How it works</h1><p class="lead">Answer guided questions, preview your draft, then send it for solicitor review.</p><p><a class="btn" href="#/">Get started</a></p>'; }
function aboutPage() { $app.innerHTML = '<h1>About Us</h1><p>Making wills and probate simple, clear and accessible.</p><p><a class="btn ghost" href="#/">Back to home</a></p>'; }
function faqPage() { $app.innerHTML = '<h1>Help & Support</h1><p>Questions? We are here to help.</p><p><a class="btn ghost" href="#/">Back to home</a></p>'; }
function pricingPage() { $app.innerHTML = '<h1>Pricing</h1><p>Fixed fees. Solicitor review included.</p><p><a class="btn ghost" href="#/">Back to home</a></p>'; }

function startPage(id) {
  const titles = {
    will: "Make a will",
    lpa_property: "Lasting power of attorney: financial decisions",
    lpa_health: "Lasting power of attorney: health and care decisions",
    probate: "Apply for probate",
    prenup: "Prenuptial agreement",
    postnup: "Postnuptial agreement",
    cohabitation: "Cohabitation agreement",
    employment_settlement: "Employment settlement agreement"
  };
  $app.innerHTML = '<h1>' + esc(titles[id] || "Start") + '</h1><p class="lead">The guided step-by-step flow will open here.</p><p><a class="btn" href="#/">Back to home</a></p>';
}

function route() {
  const hash = (location.hash || "#/").replace(/^#\/?/, "").split("?")[0];
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "how") return howPage();
  if (parts[0] === "about") return aboutPage();
  if (parts[0] === "faq") return faqPage();
  if (parts[0] === "pricing") return pricingPage();
  if (parts[0] === "s" && parts[1]) return startPage(parts[1]);
  return home();
}

window.addEventListener("hashchange", route);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", route);
} else {
  route();
}
