"""Fin d'une campagne programmée : nouvelles entreprises (C78) ou échec (C98), en alerte."""

from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.stop_reasons import is_failure
from prospection.storage.alerts import add_alert
from prospection.storage.campaigns import load_campaign, schedule_of
from prospection.storage.prospects import new_qualified


def after_campaign(engine: Engine, campaign_id: int, now: datetime) -> None:
    """Rien pour une campagne lancée à la main : je suis devant l'écran."""
    with engine.begin() as conn:
        if schedule_of(conn, campaign_id) is None:
            return
        campaign = load_campaign(conn, campaign_id)
        link, name = f"/campagnes/{campaign_id}", campaign.request.name
        if is_failure(campaign.stop_reason):
            message = f"Campagne programmée « {name} » en échec : {campaign.stop_reason or ''}"
            add_alert(conn, f"echec:{campaign_id}", "echec", message, link, now)
        fresh = new_qualified(conn, campaign_id)
        if fresh:
            words = "nouvelle entreprise" if fresh == 1 else "nouvelles entreprises"
            message = f"{fresh} {words} pour « {name} »"
            add_alert(conn, f"nouveaux:{campaign_id}", "nouveaux", message, link, now)
