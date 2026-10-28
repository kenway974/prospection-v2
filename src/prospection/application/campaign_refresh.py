"""Mettre à jour une campagne passée (C76) : chaque fiche retenue relue chez Google, une par
une, par la tâche de fond, dans le budget ; les changements vont au journal de la campagne."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.budget_settings import current_budget
from prospection.application.step_flow import reserve_call
from prospection.domain.call_status import TO_CALL
from prospection.domain.google_cost import Estimate, Pricing, billing_month, estimate
from prospection.domain.place_changes import place_changes
from prospection.domain.services import Service
from prospection.sources.google_details import place_details
from prospection.sources.google_search import GoogleBusy, GoogleRefused
from prospection.storage import refresh as store
from prospection.storage.alerts import add_alert
from prospection.storage.campaign_codec import decode_place, encode_place
from prospection.storage.campaigns import add_event, load_campaign
from prospection.storage.google_usage import month_usage
from prospection.storage.secret_box import SecretBox

CLOSED_FOR_GOOD = "Fermé définitivement"


@dataclass(frozen=True)
class RefreshInfo:
    places: int
    pending: int
    cost: Estimate


def refresh_info(engine: Engine, pricing: Pricing, campaign_id: int, now: datetime) -> RefreshInfo:
    """Combien de fiches et coût au pire (une fiche = un appel), avant de lancer."""
    budget = current_budget(engine)
    with engine.connect() as conn:
        places = store.refresh_targets(conn, campaign_id)
        pending = store.pending_refresh(conn, campaign_id)
        calls, spent = month_usage(conn, billing_month(now))
    return RefreshInfo(places, pending, estimate(pricing, places, calls, spent, budget))


def request_refresh(engine: Engine, campaign_id: int, now: datetime) -> int:
    """Seulement pour une campagne finie ; renvoie le nombre de fiches mises en file."""
    with engine.begin() as conn:
        if load_campaign(conn, campaign_id).status != "done":
            return 0
        count = store.queue_refresh(conn, campaign_id)
        add_event(conn, campaign_id, now, "info", f"Mise à jour demandée : {count} fiches")
    return count


def _stop(engine: Engine, campaign_id: int, now: datetime, why: str) -> None:
    with engine.begin() as conn:
        store.cancel_refresh(conn, campaign_id)
        add_event(conn, campaign_id, now, "warning", f"Mise à jour arrêtée : {why}")


def refresh_next(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, now: datetime
) -> bool:
    """Relit une fiche en file ; vrai s'il y en avait une."""
    with engine.begin() as conn:
        item = store.take_refresh(conn)
    if item is None:
        return False
    key = read_key(engine, box, Service.GOOGLE)
    if key is None:
        _stop(engine, item.campaign_id, now, "clé Google absente (Réglages → Clés API).")
    elif not reserve_call(engine, pricing, item.campaign_id, now):
        _stop(engine, item.campaign_id, now, "plafond Google atteint (Réglages → Budget).")
    else:
        _read(engine, client, key, item, now)
    _finish_if_done(engine, item.campaign_id, now)
    return True


def _read(
    engine: Engine, client: httpx.Client, key: str, item: store.ToRefresh, now: datetime
) -> None:
    old = decode_place(item.data)
    try:
        new = place_details(client, key, item.place_id)
    except GoogleBusy:
        message, new = f"{old.name} : fiche non relue (Google trop sollicité)", None
    except GoogleRefused as refused:
        _stop(engine, item.campaign_id, now, str(refused))
        return
    else:
        message = f"{old.name} : plus trouvé sur Google (fermé ?)" if new is None else ""
    with engine.begin() as conn:
        if new is not None:
            changes = place_changes(old, new)
            closed = CLOSED_FOR_GOOD in changes and item.status == TO_CALL
            store.save_refresh(conn, item.prospect_id, encode_place(new),
                               CLOSED_FOR_GOOD if closed else None)  # fmt: skip
            message = f"{old.name} : {', '.join(changes)}" if changes else ""
        if message:
            add_event(conn, item.campaign_id, now, "info", message)


def _finish_if_done(engine: Engine, campaign_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        if store.pending_refresh(conn, campaign_id):
            return
        name = load_campaign(conn, campaign_id).request.name
        add_event(conn, campaign_id, now, "info", "Mise à jour terminée")
        message = f"Mise à jour de « {name} » terminée : changements dans le journal."
        add_alert(conn, f"maj:{campaign_id}:{now.isoformat()}", "maj", message,
                  f"/campagnes/{campaign_id}", now)  # fmt: skip
