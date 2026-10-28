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

// Terrain (C113) : la position du téléphone, avec son accord, remplit le formulaire
var positionButton = document.getElementById("ma-position");
if (positionButton && navigator.geolocation) {
  positionButton.addEventListener("click", function () {
    var state = document.getElementById("position-etat");
    state.textContent = "Recherche de votre position…";
    navigator.geolocation.getCurrentPosition(function (where) {
      document.getElementById("lat").value = where.coords.latitude.toFixed(6);
      document.getElementById("lon").value = where.coords.longitude.toFixed(6);
      state.textContent = "Position trouvée : lancez la recherche.";
    }, function () {
      state.textContent = "Position refusée ou introuvable : écrivez une adresse.";
    }, { enableHighAccuracy: true, timeout: 10000 });
  });
}
