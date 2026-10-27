"""Source « entreprises récemment créées » : règles (C11, C24, C26, C125)."""

from datetime import date

from prospection.domain.company import Company

GOOGLE, REGISTRY = "google", "registre"
LOOKUPS_PER_TARGET = 5  # recherches Google au plus par prospect voulu (budget prévisible)
SOURCES = (GOOGLE, REGISTRY)
MAX_DAYS = 365
# Tranches d'effectif INSEE, de la plus petite à la plus grande (NN et 00 : aucun salarié)
WORKFORCE_ORDER = (
    "NN", "00", "01", "02", "03", "11", "12", "21", "22", "31", "32", "41", "42", "51", "52",
    "53",
)  # fmt: skip
UNAVAILABLE = {  # C125 : pourquoi il n'y a pas de registre ouvert hors de France
    "BE": "Belgique : pas de registre officiel ouvert gratuitement (le service en ligne de la "
    "BCE est payant).",
    "CH": "Suisse : le registre Zefix demande des identifiants à demander à l'Office fédéral "
    "de la justice ; dites-le si vous voulez l'ajouter.",
    "LU": "Luxembourg : pas d'accès ouvert connu au registre des entreprises.",
    "MC": "Monaco : pas d'accès ouvert connu au registre des entreprises.",
}
ONLY_GOOGLE = " Choisissez la source Google Maps pour ce pays."


def registry_unavailable(country: str) -> str | None:
    """Message à afficher si le registre n'est pas utilisable pour ce pays, sinon None."""
    if country == "FR":
        return None
    return UNAVAILABLE.get(country, "Pas de registre ouvert pour ce pays.") + ONLY_GOOGLE


def workforce_ok(tranche: str | None, at_most: str | None) -> bool:
    """Effectif inconnu : gardé (on ne devine pas) ; sinon au plus la tranche choisie."""
    if at_most is None or tranche not in WORKFORCE_ORDER or at_most not in WORKFORCE_ORDER:
        return True
    return WORKFORCE_ORDER.index(tranche) <= WORKFORCE_ORDER.index(at_most)


def source_errors(sources: tuple[str, ...], countries: set[str], days: int) -> dict[str, str]:
    """Erreurs du choix des sources (C11, C24, C125), champ par champ."""
    errors: dict[str, str] = {}
    if not any(s in SOURCES for s in sources):
        errors["sources"] = "Choisissez au moins une source."
    if REGISTRY in sources:
        refused = [m for c in sorted(countries) if (m := registry_unavailable(c))]
        if refused:
            errors["sources"] = refused[0]
        if not 1 <= days <= MAX_DAYS:
            errors["days"] = "Choisissez entre 1 et 365 jours."
    return errors


def is_candidate(company: Company, since: date, naf_prefixes: tuple[str, ...]) -> bool:
    """Active aujourd'hui, entreprise (pas seulement l'établissement) créée depuis `since`,
    activité du métier sur la période en cours (C24, C25, C27). Inconnu = gardé."""
    recent = company.created is None or company.created >= since
    trade = not company.naf or any(company.naf.startswith(p) for p in naf_prefixes)
    return company.active and recent and trade


def lookup_name(company: Company) -> str | None:
    """Nom à chercher sur Google : l'enseigne d'abord ; jamais le nom d'une personne
    (entrepreneur individuel sans enseigne : pas de recherche, numéro à chercher)."""
    if company.other_names:
        return company.other_names[0]
    person = (company.legal_form or "").startswith("1")
    return None if person else company.name
