"""Exports CSV et Excel d'une campagne (C62 à C65, C89, C118).

Régénérés à la demande depuis la base (C66) ; aucun statut n'est modifié (C118). Repris de
prospection-bot (main.py::save_csv : utf-8-sig ; app.py : mise en forme openpyxl), version
530ba12, avec les cellules neutralisées contre les formules (C89).
"""

import csv
import io
from datetime import date, datetime
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import Engine

from prospection.application.mail_optouts import usable_emails
from prospection.application.prospect_view import all_domains, emails_of, insights
from prospection.domain.sheet_safe import clean, looks_like_formula, safe_cell
from prospection.storage.mail_domains import mail_servers
from prospection.storage.prospect_list import campaign_rows

PROSPECT_HEADER: list[object] = [
    "Score", "Entreprise", "Raison", "Statut", "Téléphone", "Mobile (contact)", "Email",
    "Dirigeant", "Site", "Fiche Google", "Adresse", "Métier", "SIREN", "À vérifier", "Accroche",
]  # fmt: skip
EXCLUDED_HEADER: list[object] = [
    "Entreprise",
    "Raison de l'exclusion",
    "Adresse",
    "Métier",
    "Fiche Google",
]
WIDTHS = [8, 30, 45, 14, 18, 18, 32, 25, 35, 40, 40, 16, 12, 40, 70]
_HEAD = PatternFill(start_color="1A3E8F", end_color="1A3E8F", fill_type="solid")


def _prospects(engine: Engine, campaign_id: int, today: date, pepper: bytes) -> list[list[object]]:
    with engine.connect() as conn:
        rows = campaign_rows(conn, campaign_id, qualified=True)
        servers = mail_servers(conn, all_domains([r for r, _ in rows]))
        emails = {row.id: usable_emails(conn, pepper, emails_of(row)) for row, _ in rows}  # C148
    lines = []
    for row, _ in rows:
        seen = insights(row, servers, today)
        siren = row.company.siren if row.company and row.registry_status == "sûr" else ""
        lines.append([
            seen.score, row.data.get("name"), seen.reason, row.status,
            seen.phones[0][0] if seen.phones else "", row.contact[1], ", ".join(emails[row.id]),
            row.contact[0], (row.site.url if row.site else None) or row.data.get("website"),
            row.data.get("maps_url"), row.data.get("address"), ", ".join(row.keywords), siren,
            " ; ".join(seen.flags), seen.sheet.hook,
        ])  # fmt: skip
    return sorted(lines, key=lambda line: -int(str(line[0])))  # C64 : meilleur score d'abord


def _excluded(engine: Engine, campaign_id: int) -> list[list[object]]:
    with engine.connect() as conn:
        rows = campaign_rows(conn, campaign_id, qualified=False)
    return [[r.data.get("name"), " ; ".join(reasons), r.data.get("address"),
             ", ".join(r.keywords), r.data.get("maps_url")] for r, reasons in rows]  # fmt: skip


def _table(
    engine: Engine, campaign_id: int, which: str, today: date, pepper: bytes
) -> list[list[object]]:
    if which == "exclus":
        return [EXCLUDED_HEADER, *_excluded(engine, campaign_id)]
    return [PROSPECT_HEADER, *_prospects(engine, campaign_id, today, pepper)]


def _today(now: datetime, timezone: str) -> date:
    """Jour du propriétaire (même score qu'à l'écran)."""
    return now.astimezone(ZoneInfo(timezone)).date()


def campaign_csv(
    engine: Engine, campaign_id: int, which: str, now: datetime, timezone: str = "Europe/Paris",
    *, pepper: bytes,
) -> bytes:  # fmt: skip
    """CSV lisible par Excel en français : « ; » et utf-8 avec BOM (C62)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    for line in _table(engine, campaign_id, which, _today(now, timezone), pepper):
        writer.writerow([safe_cell(v) for v in line])
    return out.getvalue().encode("utf-8-sig")


def campaign_xlsx(
    engine: Engine, campaign_id: int, now: datetime, timezone: str = "Europe/Paris",
    *, pepper: bytes,
) -> bytes:  # fmt: skip
    """Un fichier, deux onglets : Prospects et Exclus (C63, C65)."""
    book = Workbook()
    for index, (title, which) in enumerate((("Prospects", "prospects"), ("Exclus", "exclus"))):
        sheet = book.worksheets[0] if index == 0 else book.create_sheet()
        sheet.title = title
        for line in _table(engine, campaign_id, which, _today(now, timezone), pepper):
            sheet.append([clean(v) for v in line])
            for cell in sheet[sheet.max_row]:  # C89 : jamais une formule, sans apostrophe visible
                if isinstance(cell.value, str) and looks_like_formula(cell.value):
                    cell.data_type = "s"
        for col, width in enumerate(WIDTHS[: sheet.max_column], 1):
            sheet.column_dimensions[get_column_letter(col)].width = width
            head = sheet.cell(row=1, column=col)
            head.fill, head.font = _HEAD, Font(color="FFFFFF", bold=True)
            head.alignment = Alignment(vertical="center")
        sheet.freeze_panes = "A2"
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()
