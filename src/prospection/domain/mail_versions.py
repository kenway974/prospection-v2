"""Versions d'un mail d'audit (C162) : modèle d'objet, modèle d'accroche, structure ; et ce
qu'on garde de chaque envoi pour les statistiques."""

import re
from dataclasses import dataclass

from prospection.domain.audit_mail import STRUCTURES
from prospection.domain.audit_mail_rules import load_mail_rules

_CODE = re.compile(r"o(\d{1,3})-a(-1|\d{1,3})-s(\d)")


@dataclass(frozen=True)
class MailVersions:
    subject: str  # modèle d'objet (mail_rules.yaml)
    hook: str | None  # modèle d'accroche, None sans accroche
    structure: str


@dataclass(frozen=True)
class SendDetails:
    versions: MailVersions
    edited: bool  # texte modifié avant l'envoi
    points: tuple[str, ...]  # titres des points cités
    profile: dict[str, str]  # profil du lead (lead_profile)


def encode_versions(v: MailVersions) -> str:
    """Code court des versions, gardé dans le formulaire de l'écran du mail."""
    rules = load_mail_rules()
    hooks = [h.texte for h in rules.accroches]
    hook = hooks.index(v.hook) if v.hook in hooks else -1
    return f"o{rules.objets.index(v.subject)}-a{hook}-s{STRUCTURES.index(v.structure)}"


def decode_versions(code: str) -> MailVersions | None:
    """None si le code est inconnu ou ne correspond plus au fichier de règles."""
    found = _CODE.fullmatch(code.strip())
    rules = load_mail_rules()
    if not found:
        return None
    subject, hook, structure = (int(x) for x in found.groups())
    if subject >= len(rules.objets) or hook >= len(rules.accroches) or structure >= len(STRUCTURES):
        return None
    hook_text = rules.accroches[hook].texte if hook >= 0 else None
    return MailVersions(rules.objets[subject], hook_text, STRUCTURES[structure])
