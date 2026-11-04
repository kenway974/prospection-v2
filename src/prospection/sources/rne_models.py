"""Réponse du registre national des entreprises (INPI), seulement les champs utilisés (C150).

Noms repris du modèle public d'annuaire-entreprises (search-infra, rne_model.py).
"""

from pydantic import BaseModel


class Activity(BaseModel):
    descriptionDetaillee: str | None = None
    formeExercice: str | None = None


class Domain(BaseModel):
    nomDomaine: str | None = None


class Description(BaseModel):
    objet: str | None = None


class Identity(BaseModel):
    description: Description | None = None
    nomsDeDomaine: list[Domain] | None = None


class Establishment(BaseModel):
    activites: list[Activity] | None = None
    nomsDeDomaine: list[Domain] | None = None


class Person(BaseModel):
    identite: Identity | None = None
    etablissementPrincipal: Establishment | None = None


class Content(BaseModel):
    personneMorale: Person | None = None
    personnePhysique: Person | None = None
    exploitation: Person | None = None


class Formality(BaseModel):
    content: Content


class Company(BaseModel):
    formality: Formality
