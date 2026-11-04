"""C150 : registre national des entreprises (INPI) : objet social, activités, domaines."""

import pytest

from prospection.domain.key_check import KeyCheck
from prospection.sources.rne import (
    RneExpired,
    RneRefused,
    RneUnavailable,
    check_inpi_key,
    rne_company,
    rne_login,
)
from tests.fake_http import fake_client, json_reply, timeout

ACTIVITY = {"descriptionDetaillee": "Conception, vente et pose de cuisines équipées",
            "formeExercice": "ARTISANALE", "indicateurPrincipal": True}  # fmt: skip


def company(kind: str = "personneMorale") -> dict[str, object]:
    person = {
        "identite": {"description": {"objet": "  La conception et la pose de cuisines.  "},
                     "nomsDeDomaine": [{"nomDomaine": "cuisines-martin.fr"}]},
        "etablissementPrincipal": {"activites": [ACTIVITY, {"descriptionDetaillee": None}]},
    }  # fmt: skip
    return {"siren": "912345678", "formality": {"siren": "912345678", "content": {kind: person}}}


def test_C150_login_gives_a_token() -> None:
    client, recorder = fake_client(json_reply(200, {"token": "jeton"}))
    assert rne_login(client, "k@gmail.com", "secret") == "jeton"
    assert recorder.requests[0].url.path == "/api/sso/login"
    client, _ = fake_client(json_reply(401, {"message": "Bad credentials"}))
    with pytest.raises(RneRefused):
        rne_login(client, "k@gmail.com", "faux")


def test_C150_purpose_activities_and_domains_read() -> None:
    for kind in ("personneMorale", "personnePhysique", "exploitation"):
        client, recorder = fake_client(json_reply(200, company(kind)))
        details = rne_company(client, "jeton", "912345678")
        assert details is not None
        assert details.purpose == "La conception et la pose de cuisines."
        assert details.activities == (
            "Conception, vente et pose de cuisines équipées (artisanale)",
        )
        assert details.domains == ("cuisines-martin.fr",)
    assert recorder.requests[0].headers["Authorization"] == "Bearer jeton"
    assert recorder.requests[0].url.path == "/api/companies/912345678"


def test_C150_unknown_expired_or_down() -> None:
    client, _ = fake_client(json_reply(404, {}))
    assert rne_company(client, "jeton", "912345678") is None
    client, _ = fake_client(json_reply(401, {}))
    with pytest.raises(RneExpired):
        rne_company(client, "jeton", "912345678")
    for handler in (timeout, json_reply(503, {}), json_reply(200, ["liste"])):
        client, _ = fake_client(handler)
        with pytest.raises(RneUnavailable):
            rne_company(client, "jeton", "912345678")


def test_C150_key_is_email_colon_password() -> None:
    client, _ = fake_client(json_reply(200, {"token": "jeton"}))
    assert check_inpi_key(client, "k@gmail.com:secret") == KeyCheck(
        True, "Identifiants INPI valides."
    )
    assert not check_inpi_key(client, "sans-deux-points").ok
    client, _ = fake_client(json_reply(401, {}))
    assert "data.inpi.fr" in check_inpi_key(client, "k@gmail.com:faux").message
