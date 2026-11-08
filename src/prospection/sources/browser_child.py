"""Processus de lecture lancé par `browser_process` (C166) : lit une page avec Chromium et
écrit le résultat en JSON. Arguments : adresse, secondes, faux serveur local (ou vide).
CHROMIUM_PATH : Chromium installé ailleurs que l'emplacement de Playwright (poste local)."""

import json
import os
import sys

from prospection.sources.browser_reader import render_page
from prospection.sources.safe_network import make_web_client


def main(args: list[str]) -> str:
    url, seconds, fake = args[0], float(args[1]), args[2] or None
    with make_web_client(fake) as client:  # garde SSRF, ou faux local en test
        result = render_page(client, url, seconds, os.environ.get("CHROMIUM_PATH"))
    page = result.page
    if page is None:
        return json.dumps({"problem": result.problem})
    return json.dumps({"url": page.url, "html": page.html, "seconds": page.seconds,
                       "truncated": page.truncated})  # fmt: skip


if __name__ == "__main__":  # pragma: no cover (lancé dans un processus à part)
    sys.stdout.write(main(sys.argv[1:]))
