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

// Une saisie pas encore enregistrée n'est jamais perdue sans prévenir (C106).
// Seules les fiches marquées data-garde comptent (note, contact, action) : lancer une
// campagne ou envoyer un formulaire n'affiche jamais « Quitter le site ? » (C130).
var unsaved = new Set();
document.addEventListener("input", function (event) {
  var form = event.target.closest && event.target.closest("form[hx-post][data-garde]");
  if (form) { unsaved.add(form.getAttribute("hx-post")); }
});
document.addEventListener("htmx:afterRequest", function (event) {
  var status = event.detail.xhr ? event.detail.xhr.status : 0;
  if (status >= 200 && status < 300) {  // une saisie refusée (422) reste « à enregistrer »
    showSaveError(null);
    unsaved.delete(event.detail.elt.getAttribute("hx-post"));
  }
});
document.addEventListener("submit", function (event) {
  if (event.submitter && event.submitter.getAttribute("aria-busy") === "true") {
    event.preventDefault();  // deuxième appui pendant l'attente : rien n'est envoyé deux fois
    return;
  }
  if (!event.defaultPrevented) {  // vrai envoi : la page change exprès
    unsaved.clear();
    markBusy(event.submitter);
  }
});

// Action longue (C135) : le bouton tourne et dit ce qui se passe, jusqu'à la réponse.
function markBusy(button) {
  if (!button) { return; }
  button.setAttribute("aria-busy", "true");
  if (button.dataset.attente) {
    button.dataset.libelle = button.textContent;
    button.textContent = button.dataset.attente;
  }
}
function markDone(button) {
  if (!button || button.getAttribute("aria-busy") !== "true") { return; }
  button.removeAttribute("aria-busy");
  if (button.dataset.libelle) { button.textContent = button.dataset.libelle; }
}
function submitterOf(event) {
  var config = event.detail.requestConfig;
  var trigger = config && config.triggeringEvent;
  return trigger ? trigger.submitter : null;
}
document.addEventListener("htmx:beforeRequest", function (event) { markBusy(submitterOf(event)); });
document.addEventListener("htmx:afterRequest", function (event) { markDone(submitterOf(event)); });
window.addEventListener("pageshow", function () {  // retour arrière : boutons rendus
  document.querySelectorAll('button[aria-busy="true"]').forEach(markDone);
});
window.addEventListener("beforeunload", function (event) {
  if (unsaved.size) { event.preventDefault(); }
});

// Liste des prospects (C129) : tout cocher d'un geste avant de supprimer.
var checkAll = document.getElementById("tout-cocher");
if (checkAll) {
  document.getElementById("tout-cocher-ligne").hidden = false;
  checkAll.addEventListener("change", function () {
    document.querySelectorAll('input[name="id"][form="selection"]').forEach(function (box) {
      box.checked = checkAll.checked;
    });
  });
}

// Ville (C134) : une fois la commune choisie, les autres propositions disparaissent.
var communes = document.getElementById("communes");
if (communes) {
  communes.addEventListener("change", function (event) {
    if (event.target.name !== "commune") { return; }
    communes.querySelectorAll("label.choice").forEach(function (label) {
      if (!label.contains(event.target)) { label.remove(); }
    });
  });
}

// Secteur (C132) : remplit le champ des métiers avec tous ses mots-clés, modifiables.
var sectorMenu = document.getElementById("secteur");
if (sectorMenu) {
  sectorMenu.addEventListener("change", function (event) {
    event.stopPropagation();  // le « change » du champ des métiers suffit (une seule estimation)
    var chosen = sectorMenu.selectedOptions[0];
    var trades = document.getElementById(sectorMenu.dataset.remplit);
    if (!chosen || !chosen.dataset.metiers || !trades) { return; }
    trades.value = chosen.dataset.metiers;
    document.getElementById("secteur-etat").textContent =
      "Métiers remplacés par ceux du secteur « " + chosen.textContent + " ».";
    trades.dispatchEvent(new Event("change", { bubbles: true }));  // synonymes, estimation
  });
}

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
