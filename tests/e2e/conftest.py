"""Bout en bout : l'app tourne déjà (image construite) à E2E_BASE_URL."""

import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict[str, object]:
    path = os.environ.get("E2E_CHROMIUM")
    return {"executable_path": path} if path else {}


@pytest.fixture(scope="session")
def browser_context_args() -> dict[str, object]:
    return {"viewport": {"width": 390, "height": 844}}
