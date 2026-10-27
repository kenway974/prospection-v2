"""C46, C47 : site retrouvé à partir du nom, jamais celui d'un homonyme."""

from prospection.domain.site_guess import STRONG, WEAK, candidate_domains, confirmation

ADDRESS = "12 rue de Vesle, 51100 Reims, France"


def test_C46_domains_guessed_from_the_name() -> None:
    assert candidate_domains("AZ Énergie SARL", "FR", ("electricien",), "Reims") == [
        "azenergie.fr", "az-energie.fr", "azenergie.com", "az-energie.com",
    ]  # fmt: skip
    assert "boulangeriemartin.be" in candidate_domains("Boulangerie Martin", "BE", (), "Liège")


def test_C47_generic_name_is_never_guessed() -> None:
    """« Plomberie Reims » : le domaine deviné serait celui d'un autre plombier."""
    assert candidate_domains("Plomberie Reims", "FR", ("plombier",), "Reims") == []
    assert candidate_domains("Le Fournil", "FR", (), "Reims") != []
    assert candidate_domains("SARL", "FR", (), None) == []


def test_C46_same_phone_confirms() -> None:
    page_phones = ("+33326123456",)
    assert confirmation("Contact", "AZ Énergie", "+33326123456", ADDRESS, page_phones) == STRONG


def test_C47_stray_digits_never_confirm() -> None:
    """Des nombres sans rapport, mis bout à bout, ne valent pas le même téléphone."""
    text = "prix 3 26 € ref 12-34 code 56"
    assert confirmation(text, "Autre", "+33326123456", ADDRESS) is None


def test_C46_full_name_and_postal_code_confirm() -> None:
    text = "AZ Énergie, votre électricien au 4 place d'Erlon, 51100 Reims"
    assert confirmation(text, "AZ Énergie SARL", None, ADDRESS) == STRONG


def test_C47_name_alone_or_single_word_name_is_only_probable() -> None:
    assert confirmation("AZ Énergie à Lille", "AZ Énergie", None, ADDRESS) == WEAK
    assert confirmation("Martin, artisan à Reims 51100", "Martin", None, ADDRESS) == WEAK
    assert confirmation("Autre chose", "AZ Énergie", "+33326123456", ADDRESS, ()) is None


def test_C46_link_words_kept_on_both_sides() -> None:
    """« Boulangerie de la Gare » : la page n'enlève pas « de la », le domaine non plus."""
    name = "Boulangerie de la Gare"
    page = "Boulangerie de la Gare, 3 place de la Gare, 51100 Reims"
    assert confirmation(page, name, None, ADDRESS) == STRONG
    assert "boulangeriedelagare.fr" in candidate_domains(name, "FR", (), "Reims")
