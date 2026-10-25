"""C13 : départements (fichier de données officiel)."""

from prospection.domain.campaign_request import DepartmentZone
from prospection.domain.departments import find_department, load_departments


def test_101_departments_including_overseas() -> None:
    departments = load_departments()
    assert len(departments) == 101
    assert departments["974"] == "La Réunion"
    assert departments["2A"] == "Corse-du-Sud"


def test_find_department_by_code_or_name() -> None:
    assert find_department("974") == DepartmentZone("974", "La Réunion")
    assert find_department(" la réunion ") == DepartmentZone("974", "La Réunion")
    assert find_department("69") == DepartmentZone("69", "Rhône")
    assert find_department("9") is None
    assert find_department("Atlantide") is None


def test_departments_file_is_validated() -> None:
    import pytest

    from prospection.domain.departments import InvalidDepartmentFile, parse_departments

    assert parse_departments("'974': La Réunion\n") == {"974": "La Réunion"}
    for broken in ("'974': ''\n", "'9999': Nulle part\n", "- 974\n"):
        with pytest.raises(InvalidDepartmentFile):
            parse_departments(broken)


def test_C13_department_read_from_postal_code() -> None:
    from prospection.domain.departments import postal_department

    assert postal_department("12 rue de la République, 69002 Lyon, France") == "69"
    assert postal_department("1 rue de Paris, 97400 Saint-Denis") == "974"
    assert postal_department("Cours Napoléon, 20000 Ajaccio") == "2A"
    assert postal_department("Rue César Campinchi, 20200 Bastia") == "2B"
    assert postal_department("Lyon") is None
