"""C96 : la taille maximale des fichiers est vérifiée automatiquement."""

from pathlib import Path

from scripts.check_file_size import find_too_long


def test_C96_flags_files_over_limit(tmp_path: Path) -> None:
    long = tmp_path / "long.py"
    long.write_text("x = 1\n" * 151)
    short = tmp_path / "short.py"
    short.write_text("x = 1\n" * 150)
    assert find_too_long([long, short], max_lines=150) == [(long, 151)]
