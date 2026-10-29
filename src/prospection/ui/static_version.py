"""Version des fichiers statiques : le navigateur ne garde jamais un ancien script en cache."""

import hashlib

from prospection.ui.paths import STATIC_DIR

VERSIONED = ("app.css", "app.js", "notifications.js")


def static_version() -> str:
    digest = hashlib.sha256()
    for name in VERSIONED:
        digest.update((STATIC_DIR / name).read_bytes())
    return digest.hexdigest()[:12]
