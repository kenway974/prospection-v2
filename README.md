# Prospection v2

Outil personnel pour trouver des prospects (Google Maps, entreprises récemment créées), les qualifier, préparer et suivre ses appels, puis envoyer les intéressés dans Notion. Pensé d'abord pour le téléphone (Android), installable comme une app.

- Règles du projet : [CLAUDE.md](CLAUDE.md)
- Comportements à développer : [COMPORTEMENTS.md](COMPORTEMENTS.md)
- Spec : [docs/superpowers/specs/2026-10-24-prospection-v2-design.md](docs/superpowers/specs/2026-10-24-prospection-v2-design.md)
- Feuille de route : [docs/superpowers/plans/2026-10-24-feuille-de-route.md](docs/superpowers/plans/2026-10-24-feuille-de-route.md)

État : **lot 0 (socle)** — connexion, sécurité, coquille mobile, app installable. Les écrans Prospects, Terrain et Recherche sont encore vides.

## Lancer en local

Prérequis : Python 3.13, [uv](https://docs.astral.sh/uv/), PostgreSQL 16.

```bash
uv sync
cp .env.example .env                              # puis remplir les valeurs
uv run python -m prospection.cli hash-password    # mot de passe → valeur de APP_PASSWORD_HASH
set -a; . ./.env; set +a
uv run alembic upgrade head
uv run uvicorn prospection.ui.main:app --reload
```

Puis ouvrir http://localhost:8000.

## Vérifier avant de pousser

```bash
uv run ruff check . && uv run ruff format --check . && uv run lint-imports
uv run python scripts/check_file_size.py src
uv run mypy
TZ=America/Los_Angeles uv run pytest --cov --cov-fail-under=80
```

Les tests utilisent une base PostgreSQL temporaire sur `TEST_DATABASE_URL` (par défaut `postgresql+psycopg://postgres:postgres@localhost:5432/postgres`), créée puis supprimée à chaque lancement. Aucun appel réseau vers un service externe.

Les tests de bout en bout (`pytest -m e2e`) tournent dans la CI sur l'image Docker construite.

## Déployer sur Railway

1. Créer un projet Railway relié au dépôt GitHub (branche `main`).
2. Ajouter une base **PostgreSQL** au projet.
3. Dans le service de l'app, définir les variables (voir `.env.example`) :
   - `DATABASE_URL` : l'URL de la base Railway, en remplaçant `postgresql://` par `postgresql+psycopg://` ;
   - `SESSION_SECRET` : 32 caractères aléatoires ou plus ;
   - `APP_PASSWORD_HASH` : la sortie de `python -m prospection.cli hash-password` ;
   - `BEHIND_PROXY=true`, `TIMEZONE=Indian/Reunion`.
4. Dans les réglages du service, activer **« Wait for CI »** : `main` n'est déployée que si la CI est verte (C97).
5. Générer un domaine public (HTTPS fourni par Railway).

Le conteneur applique les migrations au démarrage, puis lance l'app. Railway vérifie `/sante`.

**En cas de souci**
- 5 essais ratés depuis une même adresse bloquent cette adresse 15 minutes ; 50 essais ratés en tout (attaque depuis de nombreuses adresses) bloquent tout le monde 15 minutes. Il suffit d'attendre.
- Une adresse qui s'est déjà connectée avec succès (dans les 90 jours) n'est jamais bloquée par les essais des autres.
- Une session dure 30 jours sans utilisation et 90 jours au plus après la connexion.
- Le journal des connexions garde 90 jours d'historique.
- Pour fermer tout de suite toutes les sessions ouvertes (téléphone perdu, par exemple), changer `SESSION_SECRET` ou le mot de passe.

## Installer l'app sur Android

Ouvrir l'adresse de l'app dans Chrome, se connecter, puis menu ⋮ → **« Installer l'application »**. L'app apparaît avec son icône et s'ouvre en plein écran. La session reste ouverte 30 jours (90 jours au plus après la connexion).
