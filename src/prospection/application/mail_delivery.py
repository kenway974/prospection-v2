"""Remise du mail d'audit à Gmail (C146) : jeton puis envoi, et ce qu'il faut dire quand
cela échoue. Un jeton refusé est un problème de l'app (identifiants), jamais du destinataire :
la file d'envoi s'arrête au lieu d'accuser son adresse (relecture du groupe C168 à C181)."""

import httpx

from prospection.application.audit_mail_context import MailBlocked
from prospection.sources.gmail import (
    GmailOAuth,
    GmailRefused,
    GmailRevoked,
    GmailUnavailable,
    access_token,
    send_raw,
)

REVOKED = "Connexion Gmail expirée : reliez Gmail à nouveau dans Réglages → Mail d'audit."
DOWN = "Gmail ne répond pas : réessayez dans un instant (votre texte est gardé)."
REFUSED = "Gmail a refusé ce mail : vérifiez l'adresse du destinataire."
SETUP = ("Google refuse la connexion de l'app (identifiants Gmail changés ?) : reliez Gmail à "
         "nouveau dans Réglages → Mail d'audit.")  # fmt: skip
UNCERTAIN = (
    "Envoi incertain (réponse de Gmail perdue) : regardez dans « Messages envoyés » de Gmail. "
    "Le prospect est marqué « envoyé » pour ne jamais lui écrire deux fois."
)


def deliver(client: httpx.Client, refresh: str, oauth: GmailOAuth, raw: bytes) -> str | None:
    """Envoie ; rend la conversation Gmail du mail (réponses repérées ensuite, C163)."""
    try:
        token = access_token(client, oauth, refresh)
    except GmailRefused:  # problème de l'app, pas du destinataire
        raise MailBlocked(SETUP) from None
    except GmailRevoked:
        raise MailBlocked(REVOKED) from None
    except GmailUnavailable:
        raise MailBlocked(DOWN) from None
    try:
        return send_raw(client, token, raw)
    except GmailRevoked:
        raise MailBlocked(REVOKED) from None
    except GmailUnavailable:
        raise MailBlocked(DOWN) from None
    except GmailRefused:
        raise MailBlocked(REFUSED) from None
