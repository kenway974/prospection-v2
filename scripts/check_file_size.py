"""Vérifie qu'aucun fichier Python ne dépasse la taille maximale (bonnes pratiques)."""

import sys
from collections.abc import Iterable
from pathlib import Path

MAX_LINES = 150


def find_too_long(paths: Iterable[Path], max_lines: int) -> list[tuple[Path, int]]:
    """Rend les fichiers de plus de `max_lines` lignes, avec leur nombre de lignes."""
    too_long = []
    for path in paths:
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > max_lines:
            too_long.append((path, count))
    return too_long


def main(roots: list[str]) -> int:
    files = sorted(p for root in roots for p in Path(root).rglob("*.py"))
    too_long = find_too_long(files, MAX_LINES)
    for path, count in too_long:
        print(f"{path} : {count} lignes (maximum {MAX_LINES}). Découpez ce fichier.")
    return 1 if too_long else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["src"]))
