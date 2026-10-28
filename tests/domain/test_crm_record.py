"""C68 à C71 : fiche Notion d'un prospect, sans jamais écraser une saisie manuelle."""

from datetime import date

from prospection.domain.crm_record import APP_COLUMNS, merge, to_properties

WANTED = {"Entreprise": "Atelier Bois", "Téléphone": "+33478123456", "Score": 75,
          "Email": "contact@atelier.fr", "Date action": date(2026, 11, 2), "Site": None,
          "Notes app": "Rappeler après 14 h"}  # fmt: skip


def test_C70_creation_writes_everything_known() -> None:
    assert merge(None, {}, WANTED) == {k: v for k, v in WANTED.items() if v is not None}


def test_C70_manual_edits_never_overwritten() -> None:
    current = {"Entreprise": "Atelier Bois", "Téléphone": "+33 6 99 99 99 99",  # changé à la main
               "Score": 60, "Email": None, "Notes app": "Rappeler après 14 h"}  # fmt: skip
    written_before = {"Téléphone": "+33478123456", "Score": 60, "Notes app": "ancienne note"}
    update = merge(current, written_before, WANTED)
    assert "Téléphone" not in update  # saisi à la main : gardé
    assert update["Score"] == 75  # porte encore la valeur de l'app : mis à jour
    assert update["Email"] == "contact@atelier.fr"  # vide : complété
    assert "Notes app" not in update  # déjà à jour (et modifié à la main avant : gardé)
    assert "Site" not in update  # rien à écrire


def test_C70_personal_columns_never_written() -> None:
    """Même si la fiche Notion porte « Notes perso », la fusion n'y touche jamais."""
    current = {"Notes perso": "client difficile", "Statut CRM": "RDV", "Entreprise": "Atelier"}
    update = merge(current, {}, {**WANTED, "Entreprise": "Atelier"})
    assert "Notes perso" not in update and "Statut CRM" not in update
    assert "Statut CRM" not in to_properties(update, creating=False)
    assert "Notes perso" not in APP_COLUMNS


def test_C68_notion_properties_by_type() -> None:
    props = to_properties({"Entreprise": "Atelier", "Score": 75, "Email": "a@b.fr",
                           "Date action": date(2026, 11, 2), "Fiche Google": "https://maps",
                           "Mobile": "+33612345678", "Ville": "Lyon"}, creating=True)  # fmt: skip
    assert props["Entreprise"] == {"title": [{"text": {"content": "Atelier"}}]}
    assert props["Score"] == {"number": 75} and props["Email"] == {"email": "a@b.fr"}
    assert props["Date action"] == {"date": {"start": "2026-11-02"}}
    assert props["Fiche Google"] == {"url": "https://maps"}
    assert props["Mobile"] == {"phone_number": "+33612345678"}
    assert props["Ville"] == {"rich_text": [{"text": {"content": "Lyon"}}]}
    assert props["Statut CRM"] == {"status": {"name": "Nouveau"}}  # à la création seulement
    assert "Statut CRM" not in to_properties({"Ville": "Lyon"}, creating=False)
