"""Faux Google Places pour le bout en bout : `python -m tests.e2e.fake_google 8099`.

Sert trois cuisinistes de Lyon, seulement si la clé envoyée est celle saisie dans l'app.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

FAKE_KEY = "AIza-fausse-cle-de-bout-en-bout"
NAMES = ("Cuisines Martin", "Cuisines Lefèvre", "Cuisines du Rhône")


def _place(n: int, name: str) -> dict[str, object]:
    return {
        "id": f"e2e-{n}", "displayName": {"text": name},
        "formattedAddress": f"{n} rue de la République, 69002 Lyon",
        "location": {"latitude": 45.76, "longitude": 4.83}, "types": ["furniture_store"],
        "nationalPhoneNumber": f"06 12 34 56 7{n}", "userRatingCount": 3,
    }  # fmt: skip


class FakeGoogle(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.headers.get("X-Goog-Api-Key") != FAKE_KEY:
            self._reply(403, {"error": {"status": "PERMISSION_DENIED"}})
        else:
            self._reply(200, {"places": [_place(n, name) for n, name in enumerate(NAMES)]})

    def _reply(self, status: int, body: dict[str, object]) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1])), FakeGoogle).serve_forever()
