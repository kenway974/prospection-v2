// Enregistre le service worker (app installable, C116).
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
}

// Saisie non enregistrée : on le dit, la saisie reste à l'écran (C106).
function showSaveError(kind) {
  var banner = document.getElementById("erreur-reseau");
  if (!banner) { return; }
  banner.hidden = !kind;
  if (kind) { banner.textContent = banner.dataset[kind]; }
}
document.addEventListener("htmx:sendError", function () { showSaveError("offline"); });
document.addEventListener("htmx:responseError", function () { showSaveError("server"); });

// Une saisie pas encore enregistrée n'est jamais perdue sans prévenir.
var unsaved = new Set();
document.addEventListener("input", function (event) {
  var form = event.target.closest && event.target.closest("form[hx-post]");
  if (form) { unsaved.add(form.getAttribute("hx-post")); }
});
document.addEventListener("htmx:afterRequest", function (event) {
  var status = event.detail.xhr ? event.detail.xhr.status : 0;
  if (status >= 200 && status < 300) {  // une saisie refusée (422) reste « à enregistrer »
    showSaveError(null);
    unsaved.delete(event.detail.elt.getAttribute("hx-post"));
  }
});
window.addEventListener("beforeunload", function (event) {
  if (unsaved.size) { event.preventDefault(); }
});
