"""C38 : un établissement trouvé par deux mots-clés n'est traité qu'une fois."""

from prospection.domain.dedup import new_places


def test_C38_same_place_two_keywords_once() -> None:
    assert new_places(["a", "b", "a", "c"], already_seen={"b"}) == ["a", "c"]
