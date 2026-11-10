"""C173 : le site donné par la fiche Google doit parler de l'entreprise (nom, téléphone ou
adresse) ; sinon il est « à vérifier » (plateforme, réseau ou hébergeur ?)."""

import dataclasses

from prospection.domain.site_card import site_lines
from tests.application.test_site_check import AZ, check
from tests.application.test_site_check_contact_page import pages

PLACE = dataclasses.replace(AZ, website="https://reseau-artisans.fr/")
PLATFORM = """<html><head><title>Réseau Artisans : trouvez un pro</title></head><body>
<h1>Trouvez un artisan près de chez vous</h1><p>Plus de 3 000 professionnels.</p>
<form><input type="email" name="email"><textarea name="message"></textarea></form>
</body></html>"""


def test_C173_platform_page_is_to_be_checked() -> None:
    report = check(pages({"/": PLATFORM}), PLACE)
    assert report.audit is not None and report.unconfirmed
    lines = dict(site_lines(report))
    assert "plateforme" in lines["Site à vérifier"]


def test_C173_company_name_phone_or_domain_confirm_the_site() -> None:
    for page in (PLATFORM.replace("Plus de", "AZ Énergie, plus de"),
                 PLATFORM.replace("Plus de", "Appelez le 03 26 12 34 56. Plus de")):  # fmt: skip
        assert not check(pages({"/": page}), PLACE).unconfirmed
    own_domain = dataclasses.replace(AZ, website="https://az-energie.fr/")
    assert not check(pages({"/": PLATFORM}), own_domain).unconfirmed


def test_C173_old_reports_are_to_be_checked() -> None:
    from prospection.storage.site_codec import decode_site, encode_site

    report = check(pages({"/": PLATFORM}), PLACE)
    data = encode_site(report)
    del data["unconfirmed"]
    old = decode_site(data)
    assert old is not None and old.unconfirmed  # relecture : jamais vérifié, donc à vérifier


def test_C174_domain_shared_by_three_companies_is_a_platform() -> None:
    from prospection.application.site_check import check_site

    seen: list[tuple[str, str]] = []

    def shared(host: str, name: str) -> int:
        seen.append((host, name))
        return 2

    report = check_site(pages({"/": PLATFORM}), PLACE, ("electricien",), 2026, shared=shared)
    assert report.url is None and report.parked and report.audit is None
    assert report.problem is not None and "plusieurs entreprises" in report.problem
    assert seen == [("reseau-artisans.fr", "AZ Énergie")]
    alone = check_site(pages({"/": PLATFORM}), PLACE, ("electricien",), 2026,
                       shared=lambda host, name: 1)  # fmt: skip
    assert alone.url == "https://reseau-artisans.fr/"


def test_C174_known_directories_are_not_sites() -> None:
    from prospection.domain.not_site import not_a_site

    for url in ("https://www.yelp.fr/biz/az", "https://www.tripadvisor.fr/x",
                "https://www.societe.com/societe/az.html", "https://www.leboncoin.fr/x",
                "https://www.travaux.com/pro/az"):  # fmt: skip
        assert not_a_site(url), url
