"""Le site donné par la fiche Google parle-t-il bien de l'entreprise (C173) ?

Une fiche peut pointer vers une plateforme, un réseau ou un hébergeur : leur audit ne dit rien
du site de l'entreprise. Le site est confirmé s'il cite son nom (dans les pages lues ou dans
le nom de domaine), son téléphone ou sa rue.
"""

from collections.abc import Sequence
from urllib.parse import urlsplit

from prospection.domain.html_page import Page
from prospection.domain.place import Place
from prospection.domain.site_guess import confirmation
from prospection.domain.trades import normalize

MIN_STREET_WORDS = 3  # « 12 rue de Vesle » : assez précis pour ne pas venir d'ailleurs


def speaks_of(place: Place, url: str, pages: Sequence[Page], phones: Sequence[str]) -> bool:
    host = normalize(urlsplit(url).hostname or "")
    text = " ".join([host, *(f"{p.title} {p.text}" for p in pages)])
    if confirmation(text, place.name, place.phone, place.address, tuple(phones)):
        return True
    street = normalize(place.address.split(",")[0])
    return len(street.split()) >= MIN_STREET_WORDS and f" {street} " in f" {normalize(text)} "
