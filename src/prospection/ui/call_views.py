"""Contexte des gabarits de la fiche d'appel (affichage seulement, sans règle métier)."""

from urllib.parse import urlencode

from prospection.application.prospect_card import Card
from prospection.domain.call_status import ACTION_KINDS, CALL_RESULTS
from prospection.ui.formatting import short_datetime


def queue_query(status: str | None, query: str) -> str:
    return urlencode({"statut": status or "", "q": query})


def action_values(card: Card) -> dict[str, str]:
    action = card.action
    if action is None:
        return {"type": "rappeler", "date": "", "heure": ""}
    at = action.due_time.strftime("%H:%M") if action.due_time else ""
    return {"type": action.kind, "date": action.due_date.isoformat(), "heure": at}


def contact_values(card: Card) -> dict[str, str]:
    name, mobile, email = card.prospect.contact
    return {"dirigeant": name or "", "mobile": mobile or "", "email": email or ""}


def card_context(
    card: Card, timezone: str, qs: str, *, errors: dict[str, str] | None = None,
    saved: str | None = None, action: dict[str, str] | None = None,
    contact: dict[str, str] | None = None, note_text: str = "",
) -> dict[str, object]:  # fmt: skip
    return {
        "tab": "prospects", "card": card, "p": card.prospect, "qs": qs,
        "results": CALL_RESULTS, "kinds": ACTION_KINDS, "errors": errors or {}, "saved": saved,
        "action": action or action_values(card), "contact": contact or contact_values(card),
        "notes": [(short_datetime(n.created_at, timezone), n.text) for n in card.notes],
        "note_text": note_text,
    }  # fmt: skip
