"""Commandes d'administration : `python -m prospection.cli hash-password | migrate`."""

import sys
from getpass import getpass

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


def main(argv: list[str]) -> int:
    if argv == ["migrate"]:
        return migrate()
    if argv != ["hash-password"]:
        print("Usage : python -m prospection.cli hash-password | migrate")
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
