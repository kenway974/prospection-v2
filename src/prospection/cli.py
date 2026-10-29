"""Commandes d'administration : `python -m prospection.cli hash-password | migrate |
generate-encryption-key | restore-backup <fichier>`."""

import sys
from collections.abc import Callable
from getpass import getpass
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy.exc import OperationalError

from prospection.application.password import hash_password
from prospection.config import ConfigError, load_settings
from prospection.storage.migrate import run_migrations

MIN_LENGTH = 12


DATABASE_DOWN = (
    "La base de données ne répond pas : vérifiez DATABASE_URL et que le service "
    "PostgreSQL de Railway est démarré."
)


def migrate() -> int:
    try:
        run_migrations(load_settings().database_url)
    except ConfigError as error:
        print(error)
        return 1
    except OperationalError:
        print(DATABASE_DOWN)
        return 1
    print("Base à jour.")
    return 0


def generate_encryption_key() -> int:
    print("Collez cette valeur dans la variable ENCRYPTION_KEY (et gardez-en une copie) :")
    print(Fernet.generate_key().decode())
    return 0


def generate_vapid_keys() -> int:
    from prospection.sources.web_push import generate_vapid_keys as new_keys

    private, public = new_keys()
    print("Notifications : collez ces valeurs dans Railway (les deux services) :")
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
    print("VAPID_SUBJECT=mailto:votre@adresse.fr")
    return 0


def restore_backup(path: str, ask: Callable[[str], str] = input) -> int:
    """C91 : remplace le contenu de la base par une sauvegarde déchiffrée."""
    from prospection.application.backup import read_backup
    from prospection.storage.backup_dump import BackupFailed, restore_database

    try:
        settings = load_settings()
        copy = read_backup(settings.encryption_key.get_secret_value(), Path(path).read_bytes())
    except (ConfigError, OSError, ValueError) as error:
        print(error)
        return 1
    if ask("Toutes les données actuelles seront remplacées. Tapez RESTAURER : ") != "RESTAURER":
        print("Rien n'a été changé.")
        return 1
    try:
        restore_database(settings.database_url, copy)
    except BackupFailed as error:
        print(f"Restauration impossible, base inchangée : {error}")
        return 1
    print("Base restaurée.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "restore-backup":
        return restore_backup(argv[1])
    if argv == ["migrate"]:
        return migrate()
    if argv == ["generate-vapid-keys"]:
        return generate_vapid_keys()
    if argv == ["generate-encryption-key"]:
        return generate_encryption_key()
    if argv != ["hash-password"]:
        print(
            "Usage : python -m prospection.cli hash-password | migrate | "
            "generate-encryption-key | generate-vapid-keys | restore-backup <fichier>"
        )
        return 2
    first = getpass("Mot de passe : ")
    if len(first) < MIN_LENGTH:
        print(f"Choisissez au moins {MIN_LENGTH} caractères.")
        return 1
    if getpass("Encore une fois : ") != first:
        print("Les deux saisies sont différentes.")
        return 1
    print("Collez cette valeur dans la variable APP_PASSWORD_HASH :")
    print(hash_password(first))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
