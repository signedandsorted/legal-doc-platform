"use strict";
(function () {
  var app = document.getElementById("app");
  if (!app) return;
  var homeHTML = app.innerHTML;

  var names = {
    will: "Make a will",
    lpa_property: "Lasting power of attorney: financial decisions",
    lpa_health: "Lasting power of attorney: health and care decisions",
    probate: "Apply for probate",
    prenup: "Prenuptial agreement",
    postnup: "Postnuptial agreement",
    cohabitation: "Cohabitation agreement",
    employment_settlement: "Employment settlement agreement"
  };

  function show(title, text) {
    app.innerHTML = '<div class="inner-page"><h1>' + title + '</h1><p class="lead">' + text + '</p><p><a class="btn" href="#/">Back to home</a></p></div>';
    window.scrollTo(0, 0);
  }

  function route() {
    var raw = (location.hash || "").replace(/^#\/?/, "").split("?")[0];
    var parts = raw.split("/").filter(Boolean);
    if (!parts.length) {
      app.innerHTML = homeHTML;
      window.scrollTo(0, 0);
      return;
    }
    if (parts[0] === "how") return show("How it works", "1. Answer the questions for the document you need. 2. Check the draft. 3. A solicitor reviews it with you before anything is signed.");
    if (parts[0] === "about") return show("About us", "Signed and Sorted helps people in England and Wales prepare wills, lasting powers of attorney, probate papers and family or employment agreements, with a solicitor check before you sign.");
    if (parts[0] === "pricing") return show("Pricing", "Fees are fixed and include solicitor review. Open a service to start. Pricing can be adjusted later.");
    if (parts[0] === "faq" || parts[0] === "login") return show(parts[0] === "login" ? "Client login" : "Help and support", "Use Get Started to open a document. If you already have an account, sign-in is being reconnected to this new homepage and will use the same account as before.");
    if (parts[0] === "s") return show(names[parts[1]] || "Start a document", "This opens the guided questions for that document. The homepage is live. The full step-by-step screens, including the videos, are the next piece to put back under these buttons.");
    app.innerHTML = homeHTML;
  }

  window.addEventListener("hashchange", route);
  if (location.hash && location.hash !== "#" && location.hash !== "#/") route();
})();
