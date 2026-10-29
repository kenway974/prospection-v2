"""Faux services externes pour le bout en bout : `python -m tests.e2e.fake_google 8099`.

Google : trois cuisinistes de Lyon, seulement si la clé envoyée est celle saisie dans l'app.
Registre des entreprises : aucun résultat. Sirène : aucune entreprise (404, comme l'INSEE).
Sites (/site?url=…) : « Cuisines Martin » a un site, retrouvé à partir de son nom ; les autres
domaines n'existent pas.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

FAKE_KEY = "AIza-fausse-cle-de-bout-en-bout"
NAMES = ("Cuisines Martin", "Cuisines Lefèvre", "Cuisines du Rhône")
MARTIN_SITE = """<html><head><title>Cuisines Martin</title></head><body>
<h1>Cuisines Martin</h1><p>Appelez le 06 12 34 56 70.</p>
<a href="https://www.facebook.com/cuisinesmartin">Facebook</a></body></html>"""


def _place(n: int, name: str) -> dict[str, object]:
    return {
        "id": f"e2e-{n}", "displayName": {"text": name},
        "formattedAddress": f"{n} rue de la République, 69002 Lyon",
        "location": {"latitude": 45.76, "longitude": 4.83}, "types": ["furniture_store"],
        "nationalPhoneNumber": f"06 12 34 56 7{n}", "userRatingCount": 3,
    }  # fmt: skip


PAGESPEED: dict[str, object] = {"lighthouseResult": {
    "categories": {"performance": {"score": 0.42}},
    "audits": {"largest-contentful-paint": {"score": 0.2, "numericValue": 5100},
               "uses-optimized-images": {"score": 0.3, "details": {"overallSavingsMs": 800}}},
}}  # fmt: skip


class FakeGoogle(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/site"):
            wanted = parse_qs(urlsplit(self.path).query).get("url", [""])[0]
            self._site(200 if urlsplit(wanted).hostname == "cuisinesmartin.fr" else 404)
        elif self.path.startswith("/pagespeedonline/"):  # PageSpeed Insights (C126)
            self._reply(200, PAGESPEED)
        elif self.path.startswith("/search"):
            self._reply(200, {"results": [], "total_results": 0, "page": 1, "per_page": 5,
                              "total_pages": 0})  # fmt: skip
        else:
            self._reply(404, {"header": {"statut": 404, "message": "Aucun élément trouvé"}})

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.headers.get("X-Goog-Api-Key") != FAKE_KEY:
            self._reply(403, {"error": {"status": "PERMISSION_DENIED"}})
        else:
            self._reply(200, {"places": [_place(n, name) for n, name in enumerate(NAMES)]})

    def _site(self, status: int) -> None:
        data = MARTIN_SITE.encode() if status == 200 else b"introuvable"
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _reply(self, status: int, body: dict[str, object]) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1])), FakeGoogle).serve_forever()
