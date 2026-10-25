"""Génère src/prospection/data/villes_etrangeres.yaml depuis GeoNames.

Usage : python scripts/build_foreign_cities.py chemin/vers/cities1000.json
Le fichier `cities1000.json` vient du paquet PyPI geonamescache (données GeoNames,
CC-BY 4.0 ; villes de plus de 1 000 habitants). Lancé à la main, jamais par l'app.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

COUNTRIES = ("BE", "CH", "LU", "MC")
BIG_CITY = 15_000  # au-delà, on garde aussi les autres noms (« Bruxelles », « Gand »)
LATIN = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿŒœ' .-]{1,39}$")  # écriture latine, majuscule
OUT = Path(__file__).parent.parent / "src/prospection/data/villes_etrangeres.yaml"


def _other_names(city: dict[str, object]) -> list[str]:
    if int(str(city["population"])) < BIG_CITY:
        return []
    names = [str(n) for n in city["alternatenames"] if LATIN.match(str(n))]  # type: ignore[attr-defined]
    return sorted({n for n in names if n != city["name"] and not n.isupper()})


def _quote(text: str) -> str:
    return '"' + text.replace('"', "") + '"'


def main(source: str) -> None:
    cities = json.loads(Path(source).read_text("utf-8")).values()
    lines = [
        "# Villes de Belgique, Suisse, Luxembourg et Monaco (plus de 1 000 habitants).",
        "# Source : GeoNames (CC-BY 4.0, https://www.geonames.org), via geonamescache 3.0.2.",
        "# Généré par scripts/build_foreign_cities.py : ne pas modifier à la main.",
        "# [nom, code de région GeoNames, latitude, longitude, autres noms]",
    ]
    for country in COUNTRIES:
        lines.append(f"{country}:")
        kept: dict[tuple[str, str], dict[str, Any]] = {}
        for c in cities:  # un seul « Saint-Denis » par région : le plus peuplé
            key = (c["name"], c["admin1code"])
            if c["countrycode"] == country and (
                key not in kept or c["population"] > kept[key]["population"]
            ):
                kept[key] = c
        for c in sorted(kept.values(), key=lambda c: c["name"]):
            others = ", ".join(_quote(n) for n in _other_names(c))
            lines.append(
                f"- [{_quote(c['name'])}, {_quote(c['admin1code'])}, "
                f"{round(c['latitude'], 4)}, {round(c['longitude'], 4)}, [{others}]]"
            )
    OUT.write_text("\n".join(lines) + "\n", "utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
