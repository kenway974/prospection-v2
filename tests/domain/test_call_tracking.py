"""C102, C103, C105, C107 : statuts, action proposée, contact, écran Aujourd'hui."""

from datetime import UTC, date, datetime, time

import pytest

from prospection.domain.agenda import AgendaItem, agenda
from prospection.domain.call_status import (
    CALL_RESULTS,
    InvalidStatus,
    check_result,
    proposed_action,
)
from prospection.domain.contact import BAD_PHONE, InvalidContact, clean_contact

PARIS = "Europe/Paris"


def test_C102_six_results_in_one_gesture() -> None:
    assert CALL_RESULTS == (
        "intéressé",
        "à rappeler",
        "pas intéressé",
        "messagerie",
        "pas joint",
        "faux numéro",
    )
    assert check_result("messagerie") == "messagerie"
    with pytest.raises(InvalidStatus):
        check_result("exporté")  # posé seulement par l'export


@pytest.mark.parametrize("status", ["à rappeler", "messagerie"])
def test_C103_callback_proposed_for_tomorrow(status: str) -> None:
    assert proposed_action(status, date(2026, 10, 26)) == ("rappeler", date(2026, 10, 27))


def test_C103_nothing_proposed_otherwise() -> None:
    assert proposed_action("pas intéressé", date(2026, 10, 26)) is None


def item(n: int, day: date, at: time | None = None) -> AgendaItem:
    return AgendaItem(n, n, f"Prospect {n}", "rappeler", day, at)


def test_C107_overdue_today_tomorrow_in_my_timezone() -> None:
    # 23h30 UTC le 25 = 0h30 le 26 à Paris : « aujourd'hui » est le 26
    now = datetime(2026, 10, 25, 23, 30, tzinfo=UTC)
    items = [
        item(1, date(2026, 10, 25)), item(2, date(2026, 10, 26)),
        item(3, date(2026, 10, 26), time(9, 0)), item(4, date(2026, 10, 27)),
        item(5, date(2026, 10, 30)),
    ]  # fmt: skip
    result = agenda(items, now, PARIS)
    assert [i.id for i in result.overdue] == [1]
    assert [i.id for i in result.today] == [3, 2]  # avec heure d'abord, puis dans la journée
    assert [i.id for i in result.tomorrow] == [4]


def test_C105_phone_message_says_what_to_do() -> None:
    assert BAD_PHONE == "Numéro invalide : vérifiez-le, ou écrivez-le avec l'indicatif (+33…)."


def test_C105_contact_cleaned_and_mobile_normalised() -> None:
    contact = clean_contact(" Marie Dupont ", "06 12 34 56 78", " Marie@Exemple.fr ", "FR")
    assert contact == ("Marie Dupont", "+33612345678", "marie@exemple.fr")
    assert clean_contact("", "", "", "FR") == (None, None, None)
    assert clean_contact("", "0470 12 34 56", "", "BE")[1] == "+32470123456"


@pytest.mark.parametrize(
    ("mobile", "email", "field", "message"),
    [
        ("12", "", "mobile", BAD_PHONE),
        ("", "marie@", "email", "Adresse email invalide : vérifiez-la."),
    ],
)  # fmt: skip
def test_C105_invalid_contact_says_what_to_fix(
    mobile: str, email: str, field: str, message: str
) -> None:
    with pytest.raises(InvalidContact) as error:
        clean_contact("Marie", mobile, email, "FR")
    assert error.value.errors == {field: message}
