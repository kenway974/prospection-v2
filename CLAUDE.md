# Prospection v2 · règles du projet

Outil de **sourcing de prospects** pour mon activité de freelance : trouver des entreprises (Google Maps, entreprises récemment créées), les qualifier selon des critères, les enrichir au maximum, préparer et suivre mes appels (statuts, relances, notes), exporter en CSV / Excel et les envoyer dans mon CRM (Notion ; HubSpot plus tard). **Un seul envoi de message** : le mail d'audit, relu puis envoyé par moi depuis la fiche (bouton). Jamais d'envoi automatique ni en masse, jamais de SMS : pour le reste, je contacte moi-même.

Un seul utilisateur (moi). Interface pensée **d'abord pour le mobile**. Déploiement sur Railway.

Ces règles s'appliquent à **chaque** modification, sans attendre qu'on les rappelle.

Règles générales (communes à tous les projets) :

@.claude/bonnes-pratiques.md

Ce qui suit précise ces règles pour ce projet.

## Référence des comportements

Les comportements à développer sont dans **[COMPORTEMENTS.md](COMPORTEMENTS.md)** (C01 à C120), validés par le propriétaire. Chaque comportement = un test qui échoue d'abord, puis le code ; le numéro (ex. `C07`) est cité dans le nom ou la docstring du test et dans le message de commit.

L'ancien dépôt `kenway974/prospection-bot` sert de **réserve de briques** (recherche Google, filtres, franchises, métiers, site retrouvé, audit, vérification d'email, dirigeants, score d'opportunité). On n'y copie jamais un fichier entier : on reprend seulement les fonctions dont le test a besoin, on les relit (sécurité, simplicité), on reprend leurs anciens tests, et le commit indique la source (fichier + version).

## Stack (détail dans `docs/superpowers/specs/2026-10-24-prospection-v2-design.md`)

- Python typé, `ruff` (lint), `mypy --strict` (types), `pytest` (tests, avec seuil de couverture), `pip-audit` (failles), `import-linter` (couches et cycles).
- PostgreSQL (pas de fichiers JSON pour les données).
- Travail long (campagnes) en tâche de fond, jamais dans l'interface.

## Architecture (une responsabilité par couche)

- `domain/` : règles métier **pures** (critères, qualification, score, déduplication). Pas de réseau, pas de base, pas d'horloge cachée : le temps est passé en paramètre.
- `sources/` : Google Places, Sirène / registre des entreprises, lecture des sites. Chaque réponse est validée.
- `crm/` : Notion, HubSpot plus tard (création, mise à jour sans écraser, reprise après panne).
- `storage/` : base PostgreSQL, migrations numérotées et testées.
- `application/` : orchestration d'une campagne (relie domaine, sources, CRM, stockage).
- `ui/` : interface ; affiche et délègue, aucune règle métier.

## Règles propres au sourcing (obligatoires)

1. **Budget** : aucun appel payant au-delà du budget configuré. Les critères gratuits s'appliquent avant les appels payants.
2. **CGU** : API officielles uniquement. Jamais de scraping de Google ni de LinkedIn. Délais et limites d'appels respectés.
3. **Aucun réseau dans les tests** : chaque service externe a un faux (fake) dans les tests ; les vérifications sur les vraies API tournent à part, hors CI.
4. **Sécurité des sites lus** : aucune visite d'adresse interne (SSRF), taille et durée de lecture limitées, redirections vérifiées.
5. **Textes externes neutralisés** : rien de ce qui vient d'un site ou d'une API n'est injecté brut dans l'interface, ni comme formule dans un CSV / Excel.
6. **Secrets** : clés API chiffrées en base, clé de chiffrement uniquement dans les variables d'environnement de l'hébergeur ; jamais de secret dans les journaux ni les exports.
7. **RGPD** : respecter les entrepreneurs non diffusibles (Sirène), purge des prospects non retenus, suppression sur demande.

## Méthode de travail

- **Circuit court par défaut** : test qui échoue (pour la bonne raison) → code minimal → lint, types, tests → commit. Un commit par comportement, message en français (avant / après).
- **Relecture** : un seul agent de relecture, à la fin de chaque groupe de comportements (pas un agent par étape, pour économiser les crédits).
- Si une information manque, on la demande ou on complète la spec ; on ne devine pas. Les hypothèses sont écrites.

## Contenu et textes

- Français, phrases courtes et concrètes, messages d'erreur qui disent quoi faire.

## Git et déploiement

- Une branche par travail, jamais directement sur `main`. Fusion dans `main` après validation du propriétaire et CI verte ; `main` déploie la production sur Railway.
