// Enregistre le service worker (app installable, C116).
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
}

// Saisie non enregistrée (réseau coupé, serveur en panne) : on le dit, la saisie reste (C106).
function showSaveError(visible) {
  var banner = document.getElementById("erreur-reseau");
  if (banner) { banner.hidden = !visible; }
}
document.addEventListener("htmx:sendError", function () { showSaveError(true); });
document.addEventListener("htmx:responseError", function () { showSaveError(true); });
document.addEventListener("htmx:afterRequest", function (event) {
  if (event.detail.successful) { showSaveError(false); }
});
