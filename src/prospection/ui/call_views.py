"""Contexte des gabarits de la fiche d'appel (affichage seulement, sans règle métier)."""

from urllib.parse import urlencode

from prospection.application.prospect_card import Card
from prospection.domain.call_status import ACTION_KINDS, CALL_RESULTS
from prospection.ui.formatting import short_datetime


def list_query(status: str | None, query: str, sort: str) -> str:
    return urlencode({"statut": status or "", "q": query, "tri": sort})


def action_values(card: Card) -> dict[str, str]:
    """L'action prévue, sinon la proposition (« Rappeler demain »), sinon un formulaire vide."""
    if card.action:
        at = card.action.due_time.strftime("%H:%M") if card.action.due_time else ""
        return {"type": card.action.kind, "date": card.action.due_date.isoformat(), "heure": at}
    if card.proposal:
        return {"type": card.proposal[0], "date": card.proposal[1].isoformat(), "heure": ""}
    return {"type": "rappeler", "date": "", "heure": ""}


def contact_values(card: Card) -> dict[str, str]:
    name, mobile, email = card.prospect.contact
    return {"dirigeant": name or "", "mobile": mobile or "", "email": email or ""}


def google_search(card: Card) -> str:
    data = card.prospect.data
    return "https://www.google.com/search?" + urlencode(
        {"q": f"{data.get('name', '')} {data.get('address', '')}"}
    )


def card_context(
    card: Card, timezone: str, *, errors: dict[str, str] | None = None,
    saved: str | None = None, action: dict[str, str] | None = None,
    contact: dict[str, str] | None = None, note_text: str = "",
) -> dict[str, object]:  # fmt: skip
    return {
        "tab": "prospects", "card": card, "p": card.prospect, "search_url": google_search(card),
        "results": CALL_RESULTS, "kinds": ACTION_KINDS, "errors": errors or {}, "saved": saved,
        "action": action or action_values(card), "contact": contact or contact_values(card),
        "notes": [(short_datetime(n.created_at, timezone), n.text) for n in card.notes],
        "note_text": note_text,
    }  # fmt: skip
