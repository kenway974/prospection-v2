// Service worker minimal (C116) : réseau d'abord ; seuls les fichiers de /static/
// sont gardés en cache, jamais une page de l'app. Hors réseau, page d'explication.
const CACHE = "prospection-statique-v3";
const OFFLINE = "/static/hors-ligne.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll([OFFLINE])));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || Response.error()))
    );
  } else if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE).then((offline) => offline || Response.error())
      )
    );
  }
});

// Notifications (Web Push) : le texte est déjà court et neutralisé par le serveur ; un appui
// ouvre la page de l'app indiquée (jamais une adresse extérieure).
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const url = typeof data.url === "string" && data.url.startsWith("/") && !data.url.startsWith("//")
    ? data.url : "/";
  event.waitUntil(self.registration.showNotification(String(data.title || "Prospection"), {
    body: String(data.body || "Nouvelle alerte"), tag: String(data.tag || "alerte"),
    icon: "/static/icons/icon-192.png", badge: "/static/icons/icon-192.png", data: { url },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data.url, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((client) => client.url.startsWith(self.location.origin));
      return open ? open.navigate(target).then((client) => client && client.focus()) : self.clients.openWindow(target);
    })
  );
});
