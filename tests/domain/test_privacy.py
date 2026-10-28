"""C94, C95 : purge des prospects non retenus et suppression sur demande (RGPD)."""

from datetime import UTC, datetime

from prospection.domain.privacy import PURGEABLE, erasure_key, purge_cutoff


def test_C94_cutoff_counts_calendar_months() -> None:
    now = datetime(2026, 8, 31, 12, tzinfo=UTC)
    assert purge_cutoff(now, 6) == datetime(2026, 2, 28, 12, tzinfo=UTC)  # fin de mois
    assert purge_cutoff(now, 12) == datetime(2025, 8, 31, 12, tzinfo=UTC)


def test_C94_never_interested_exported_or_callback() -> None:
    assert {"intéressé", "exporté", "à rappeler"}.isdisjoint(PURGEABLE)
    assert {"à appeler", "pas intéressé", "messagerie", "pas joint", "faux numéro"} == PURGEABLE


def test_C95_erasure_key_keeps_no_readable_identifier() -> None:
    key = erasure_key("ChIJ123")
    assert key == erasure_key("ChIJ123") and "ChIJ123" not in key and len(key) == 64
    assert erasure_key("siren:123456789") != key


def test_C95_erased_company_never_taken_again() -> None:
    from prospection.domain.criteria import Criteria, Exclusions, evaluate
    from tests.storage.test_campaigns import PLACE

    exclusions = Exclusions(frozenset(), frozenset(), frozenset(),
                            erased=frozenset({erasure_key(PLACE.place_id)}))  # fmt: skip
    verdict = evaluate(PLACE, None, Criteria(phone="any"), exclusions)
    assert not verdict.qualified and verdict.reasons == ("Suppression demandée (RGPD)",)
