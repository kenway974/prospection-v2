"""Signatures repérées sur les sites (fichier `site_signals.yaml`, validé à la lecture)."""

from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel


class Signals(BaseModel):
    technologies: dict[str, list[str]]
    tracking: list[str]
    social: list[str]
    form_services: list[str]
    form_builders: list[str]
    contact_words: list[str]
    consent_trackers: list[str]
    consent_tools: list[str]
    legal_words: list[str]
    privacy_words: list[str]
    booking_services: list[str]
    booking_words: list[str]
    booking_trades: list[str]


@cache
def signals() -> Signals:
    text = resources.files("prospection.data").joinpath("site_signals.yaml").read_text("utf-8")
    return Signals.model_validate(yaml.safe_load(text))
