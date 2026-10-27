"""File des pages Google à lire pour une campagne (C40 : reprise là où on s'était arrêté)."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, func, literal_column, select, update

from prospection.domain.google_cost import MAX_PAGES_PER_QUERY
from prospection.domain.place import Circle
from prospection.storage.campaign_codec import decode_circle
from prospection.storage.schema_campaigns import campaign_steps


@dataclass(frozen=True)
class StepSpec:
    query: str
    keyword: str
    zone_label: str
    bias: Circle | None
    restrict_to_bias: bool = False
    region: str | None = None  # département, province ou canton : on écarte ce qui en sort
    country: str = "FR"  # code région envoyé à Google
    kind: str = "google"  # ou « registre » : entreprises récemment créées (C11)
    registry: dict[str, Any] | None = None  # requête Sirene d'une étape « registre »


@dataclass(frozen=True)
class Step:
    id: int
    query: str
    keyword: str
    zone_label: str
    bias: Circle | None
    restrict_to_bias: bool
    region: str | None
    country: str
    page_token: str | None
    page_number: int
    attempts: int
    kind: str = "google"
    registry: dict[str, Any] | None = None
    pending_page: dict[str, Any] | None = None  # page déjà payée, pas encore enregistrée


def next_step(conn: Connection, campaign_id: int) -> Step | None:
    s = campaign_steps.c
    row = conn.execute(
        select(campaign_steps)
        .where(s.campaign_id == campaign_id, s.done.is_(False))
        .order_by(s.position)
        .limit(1)
    ).first()
    if row is None:
        return None
    return Step(
        row.id, row.query, row.keyword, row.zone_label, decode_circle(row.bias),
        row.restrict_to_bias, row.region, row.country,
        row.page_token, row.page_number, row.attempts, row.kind, row.registry_json,
        row.pending_page_json,
    )  # fmt: skip


def record_page(conn: Connection, step_id: int, next_token: str | None) -> None:
    """Page lue : on passe à la suivante, ou l'étape est finie (plus de page ou 3 lues)."""
    s = campaign_steps.c
    row = conn.execute(select(s.page_number, s.kind).where(s.id == step_id)).one()
    number = row.page_number + 1
    # Google : 3 pages au plus par requête ; registre : jusqu'à la fin des résultats
    done = next_token is None or (row.kind == "google" and number >= MAX_PAGES_PER_QUERY)
    conn.execute(
        update(campaign_steps).where(s.id == step_id).values(
            page_token=next_token, page_number=number, done=done, attempts=0,
            pending_page_json=None,
        )
    )  # fmt: skip


def skip_step(conn: Connection, step_id: int) -> None:
    s = campaign_steps.c
    conn.execute(
        update(campaign_steps).where(s.id == step_id)
        .values(done=True, skipped=True, pending_page_json=None)
    )  # fmt: skip


def keep_pending_page(conn: Connection, step_id: int, page: dict[str, Any]) -> None:
    """Page Google payée : gardée tout de suite, une reprise la relit sans la repayer (C40)."""
    s = campaign_steps.c
    conn.execute(update(campaign_steps).where(s.id == step_id).values(pending_page_json=page))


def skipped_steps(conn: Connection, campaign_id: int) -> int:
    s = campaign_steps.c
    query = select(func.count()).where(s.campaign_id == campaign_id, s.skipped.is_(True))
    return int(conn.execute(query).scalar_one())


def count_attempt(conn: Connection, step_id: int) -> int:
    s = campaign_steps.c
    return int(
        conn.execute(
            update(campaign_steps).where(s.id == step_id)
            .values(attempts=s.attempts + 1).returning(s.attempts)
        ).scalar_one()
    )  # fmt: skip


def mark_looked_up(conn: Connection, step_id: int, siren: str) -> None:
    """Entreprise déjà cherchée sur Google (appel payé) : jamais cherchée une seconde fois."""
    s = campaign_steps.c
    conn.execute(
        update(campaign_steps).where(s.id == step_id).values(
            registry_json=func.jsonb_set(
                s.registry_json, literal_column("ARRAY['looked_up']"),
                func.coalesce(s.registry_json["looked_up"], func.jsonb_build_array())
                .op("||")(func.jsonb_build_array(siren)),
            )
        )
    )  # fmt: skip


def looked_up(conn: Connection, campaign_id: int) -> list[str]:
    """Toutes les entreprises déjà cherchées sur Google pour cette campagne."""
    s = campaign_steps.c
    rows = conn.execute(
        select(func.jsonb_array_elements_text(s.registry_json["looked_up"]))
        .where(s.campaign_id == campaign_id, s.registry_json["looked_up"].is_not(None))
    )  # fmt: skip
    return [str(r[0]) for r in rows]


def claim_page(conn: Connection, step_id: int, page_number: int) -> bool:
    """Verrouille l'étape si cette page n'a pas déjà été enregistrée (par un autre worker
    qui aurait repris la campagne) : une page n'est jamais comptée deux fois (C40)."""
    s = campaign_steps.c
    row = conn.execute(
        select(s.id).where(s.id == step_id, s.page_number == page_number, s.done.is_(False))
        .with_for_update()
    ).first()  # fmt: skip
    return row is not None
