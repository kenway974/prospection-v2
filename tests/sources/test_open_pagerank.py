"""C143 : autorité d'un domaine (Open PageRank) et test de la clé, avec un message clair."""

import pytest

from prospection.domain.key_check import KeyCheck
from prospection.sources.open_pagerank import (
    AuthorityUnavailable,
    check_openpagerank_key,
    page_rank,
)
from tests.fake_http import fake_client, html_reply, json_reply, timeout

KEY = "cle-opr-de-test"


def answer(domain: str, rank: object, status: int = 200) -> dict[str, object]:
    item = {"status_code": status, "error": "", "page_rank_decimal": rank, "domain": domain}
    return {"status_code": 200, "response": [item]}


def test_C143_rank_of_a_domain() -> None:
    client, recorder = fake_client(json_reply(200, answer("plombier.fr", 2.54)))
    assert page_rank(client, KEY, "plombier.fr") == 2.54
    request = recorder.requests[0]
    assert request.url.host == "openpagerank.com" and request.headers["API-OPR"] == KEY
    assert request.url.params.get_list("domains[]") == ["plombier.fr"]


def test_C143_domain_unknown_to_the_index_has_no_authority() -> None:
    client, _ = fake_client(json_reply(200, answer("inconnu.fr", "", 404)))
    assert page_rank(client, KEY, "inconnu.fr") == 0.0


def test_C143_service_down_or_odd_answer_is_unavailable() -> None:
    for handler in (timeout, html_reply(502), json_reply(200, {"response": "x"})):
        client, _ = fake_client(handler)
        with pytest.raises(AuthorityUnavailable):
            page_rank(client, KEY, "plombier.fr")


def test_C143_key_checked() -> None:
    client, _ = fake_client(json_reply(200, answer("google.com", 10)))
    assert check_openpagerank_key(client, KEY) == KeyCheck(True, "Clé Open PageRank valide.")
    client, _ = fake_client(json_reply(401, {"error": "Invalid API key"}))
    refused = check_openpagerank_key(client, KEY)
    assert not refused.ok and "openpagerank.com" in refused.message
