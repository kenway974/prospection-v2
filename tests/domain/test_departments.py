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
