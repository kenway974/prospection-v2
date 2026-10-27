"""C48 : contacts lus sur le site ; C51 : SEO local (métier et ville bien placés)."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_contacts import find_contacts
from prospection.domain.site_seo import local_seo

PAGE = parse_page("""<html><head><title>Cuisines sur mesure - Martin</title></head><body>
<h1>Votre cuisiniste à Villeurbanne</h1><p>Nous posons des cuisines équipées à Lyon.</p>
<img src="a.jpg" alt="Cuisine en chêne"><img src="b.jpg" alt="">
<a href="mailto:contact@martin-cuisines.fr?subject=Devis">Écrire</a>
<p>Appelez le 04 78 12 34 56 ou le 06.12.34.56.78. Webmaster : web@sentry.io</p>
<a href="https://www.facebook.com/martincuisines/">Facebook</a>
<a href="https://www.facebook.com/sharer/sharer.php?u=x">Partager</a>
<a href="https://instagram.com/martin.cuisines">Instagram</a>
<a href="https://fr.linkedin.com/company/martin-cuisines">LinkedIn</a>
<a href="https://www.linkedin.com/in/jean-martin">Profil de Jean</a>
<a href="tel:+33478123456">Appeler</a></body></html>""")


def test_C51_trade_and_city_located_on_the_page() -> None:
    seo = local_seo(PAGE, ("cuisiniste",), "Lyon")
    assert seo.trade == {"titre": True, "h1": True, "texte": True, "images": True}
    assert seo.city == {"titre": False, "h1": False, "texte": True, "images": False}
    assert seo.problems == ("La ville n'apparaît ni dans le titre ni dans le H1",)


def test_C51_nothing_local_said_plainly() -> None:
    seo = local_seo(parse_page("<title>Accueil</title><h1>Bienvenue</h1>"), ("plombier",), "Reims")
    assert seo.problems == (
        "Le métier n'apparaît ni dans le titre ni dans le H1",
        "La ville n'apparaît ni dans le titre ni dans le H1",
    )


def test_C48_emails_phones_and_company_pages_found() -> None:
    found = find_contacts(PAGE, "FR")
    assert found.emails == ("contact@martin-cuisines.fr",)  # sentry.io ignoré
    assert found.phones == ("+33478123456", "+33612345678")
    assert found.social == (
        "https://www.facebook.com/martincuisines/",
        "https://instagram.com/martin.cuisines",
        "https://fr.linkedin.com/company/martin-cuisines",
    )  # ni bouton de partage, ni profil personnel


def test_C48_nothing_found_is_empty() -> None:
    found = find_contacts(parse_page("<p>Bonjour</p>"), "FR")
    assert (found.emails, found.phones, found.social) == ((), (), ())


def test_C88_long_text_without_email_read_quickly() -> None:
    import time

    page = parse_page("<p>" + "a" * 99_000 + "</p>")
    start = time.perf_counter()
    assert find_contacts(page, "FR").emails == ()
    assert time.perf_counter() - start < 1
