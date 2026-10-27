"""Page Google payée <-> JSON, pour la garder avant son traitement (C40)."""

from typing import Any

from prospection.sources.google_search import SearchPage
from prospection.storage.campaign_codec import decode_place, encode_place


def encode_page(page: SearchPage) -> dict[str, Any]:
    places = [encode_place(p) for p in page.places]
    return {"places": places, "next_token": page.next_token, "skipped": page.skipped}


def decode_page(data: dict[str, Any]) -> SearchPage:
    places = [decode_place(p) for p in data["places"]]
    return SearchPage(places, data["next_token"], int(data["skipped"]))
