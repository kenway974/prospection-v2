"""C90 : dépendances tenues à jour et vérifiées automatiquement."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_C90_dependabot_watches_python_actions_and_image_every_week() -> None:
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    watched = {u["package-ecosystem"]: u["schedule"]["interval"] for u in config["updates"]}
    assert watched == {"uv": "weekly", "github-actions": "weekly", "docker": "weekly"}


def test_C90_ci_blocks_on_known_vulnerabilities_and_locked_install() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "uv sync --frozen" in ci and "pip-audit" in ci and "--strict" in ci
