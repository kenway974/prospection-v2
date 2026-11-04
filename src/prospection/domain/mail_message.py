"""Message du mail d'audit : texte simple, désinscription toujours ajoutée (C146, C148).

Rien d'injectable : en-têtes nettoyés (aucun retour à la ligne), corps en texte brut.
"""

import hashlib
from email.message import EmailMessage
from email.utils import formataddr

from prospection.domain.audit_mail_rules import load_mail_rules
from prospection.domain.text import without_controls

MAX_SUBJECT, MAX_BODY = 200, 20_000


class InvalidMail(ValueError):
    """Objet ou texte refusés : le message dit quoi corriger."""


def _header(text: str, limit: int) -> str:
    return " ".join(without_controls(text).split())[:limit]


def check_draft(subject: str, body: str) -> tuple[str, str]:
    """Objet et texte saisis, nettoyés ; InvalidMail si vides ou trop longs."""
    clean_subject = _header(subject, MAX_SUBJECT)
    clean_body = without_controls(body.replace("\r\n", "\n"), keep_lines=True).strip()
    if not clean_subject:
        raise InvalidMail("Écrivez un objet.")
    if not clean_body:
        raise InvalidMail("Écrivez le texte du mail.")
    if len(clean_body) > MAX_BODY:
        raise InvalidMail("Texte trop long : 20 000 caractères au plus.")
    return clean_subject, clean_body


def unsubscribe_footer(link: str) -> str:
    return load_mail_rules().pied_desinscription.format_map({"lien": link})


def build_message(
    sender_name: str, sender: str, to: str, subject: str, body: str, unsubscribe: str
) -> bytes:
    message = EmailMessage()
    message["From"] = formataddr((_header(sender_name, 80), _header(sender, 254)))
    message["To"] = _header(to, 254)
    message["Subject"] = _header(subject, MAX_SUBJECT)
    message["List-Unsubscribe"] = f"<{_header(unsubscribe, 500)}>"
    message["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    message.set_content(f"{body}\n\n--\n{unsubscribe_footer(unsubscribe)}\n")
    return message.as_bytes()


def email_fingerprint(email: str) -> str:
    """Empreinte d'une adresse : la désinscription la garde sans garder l'adresse (C148)."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()
