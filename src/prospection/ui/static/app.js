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

// Notifications sur ce téléphone (Web Push) : abonnement avec l'accord de l'utilisateur.
var pushButton = document.getElementById("notifications-activer");
if (pushButton) {
  var pushState = document.getElementById("notifications-etat");
  var pushOff = document.getElementById("notifications-couper");
  var keyBytes = function (base64) {
    var padded = (base64 + "===".slice((base64.length + 3) % 4)).replace(/-/g, "+").replace(/_/g, "/");
    return Uint8Array.from(atob(padded), function (c) { return c.charCodeAt(0); });
  };
  var post = function (path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), credentials: "same-origin" });
  };
  var show = function (subscribed, text) {
    pushState.textContent = text;
    pushButton.hidden = subscribed;
    pushOff.hidden = !subscribed;
  };
  var ON = "Notifications activées sur ce téléphone.";
  var OFF = "Notifications désactivées sur ce téléphone.";
  // Le serveur garde l'abonnement : on le lui renvoie (il a pu l'oublier entre-temps).
  var register = function (subscription) {
    return post("/notifications/abonnement", subscription.toJSON()).then(function (response) {
      if (response.ok) { show(true, ON); return null; }
      return response.json().catch(function () { return {}; }).then(function (body) {
        show(false, body.erreur || "Abonnement refusé : réessayez.");
      });
    });
  };
  var subscribe = function (registration) {
    var options = { userVisibleOnly: true, applicationServerKey: keyBytes(pushButton.dataset.vapidKey) };
    return registration.pushManager.subscribe(options).catch(function (error) {
      if (error.name !== "InvalidStateError") { throw error; }
      // Abonnement pris avec une ancienne clé : on le remplace.
      return registration.pushManager.getSubscription()
        .then(function (old) { return old && old.unsubscribe(); })
        .then(function () { return registration.pushManager.subscribe(options); });
    });
  };
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    show(false, "Ce navigateur ne reçoit pas de notifications (sur iPhone : installez d'abord l'app sur l'écran d'accueil).");
    pushButton.hidden = true;
  } else {
    var waiting = setTimeout(function () {
      show(false, "Notifications indisponibles pour l'instant : rechargez la page.");
    }, 8000);
    navigator.serviceWorker.ready.then(function (registration) {
      clearTimeout(waiting);
      registration.pushManager.getSubscription().then(function (current) {
        if (current) { register(current).catch(function () { show(true, ON); }); } else { show(false, OFF); }
      });
      pushButton.addEventListener("click", function () {
        Notification.requestPermission().then(function (choice) {
          if (choice !== "granted") {
            show(false, "Notifications refusées : autorisez-les dans les réglages du navigateur.");
            return null;
          }
          return subscribe(registration).then(register);
        }).catch(function () { show(false, "Activation impossible : vérifiez le réseau puis réessayez."); });
      });
      pushOff.addEventListener("click", function () {
        registration.pushManager.getSubscription().then(function (current) {
          if (!current) { show(false, OFF); return null; }
          return post("/notifications/desabonnement", { endpoint: current.endpoint })
            .then(function () { return current.unsubscribe(); })
            .then(function () { show(false, OFF); });
        }).catch(function () { show(true, "Impossible de couper sans réseau : réessayez."); });
      });
    });
  }
}
