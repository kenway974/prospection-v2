"""Commandes d'administration : `python -m prospection.cli hash-password`."""

import sys
from getpass import getpass

from prospection.application.password import hash_password

MIN_LENGTH = 12


def main(argv: list[str]) -> int:
    if argv != ["hash-password"]:
        print("Usage : python -m prospection.cli hash-password")
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
