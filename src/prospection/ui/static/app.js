// Enregistre le service worker (app installable, C116). Aucun autre code ici.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
}
