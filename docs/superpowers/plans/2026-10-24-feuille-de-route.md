# Feuille de route · lots de construction

Spec : `docs/superpowers/specs/2026-10-24-prospection-v2-design.md`. Comportements : `COMPORTEMENTS.md`.

Chaque lot a son propre plan détaillé (`docs/superpowers/plans/AAAA-MM-JJ-lot-N-….md`), écrit **juste avant** de le construire, pour tenir compte de ce que les lots précédents ont appris. Chaque lot livre une app qui tourne, et se termine par une relecture (un seul agent, règle de CLAUDE.md), puis une validation du propriétaire.

| Lot | Contenu | Comportements |
|---|---|---|
| **0 · Socle** | Projet, outillage, CI, base, connexion, en-têtes de sécurité, coquille mobile (navigation flottante), PWA, déploiement Railway | C01, C82, C83, C84, C96, C97, C101, C116, C117 |
| 1 · Réglages et clés | Saisie, test et chiffrement des clés (Google, Notion, Sirène), budget, choix de la base Notion, fuseau | C02 à C09, C85, C86 |
| 2 · Campagne Google Maps | Formulaire de recherche, synonymes, estimation de coût, tâche de fond, critères gratuits puis payants, déduplication, suivi en direct, arrêt / reprise | C10 à C23, C30 à C43, C79, C119 |
| 3 · Suivi des appels | Liste des prospects, session d'appel, statuts, prochaine action, notes, contact, écran Aujourd'hui | C61, C102 à C107, C109, C120 |
| 4 · Registre officiel | Créations récentes (Sirène), rapprochement sûr, API Recherche d'entreprises, non-diffusibles | C24 à C27, C44, C45, C93 |
| 5 · Site web | Site retrouvé, lecture sécurisée (SSRF, taille, durée), technologie, audit, SEO local, score du site | C28, C29, C46 à C52, C87, C88 |
| 6 · Contact et préparation de l'appel | Emails, mobiles, lien LinkedIn, score d'opportunité, raison, confiance, fiche « Pour l'appel » par règles, indices de santé | C53 à C60, C110 à C112 |
| 7 · Exports et Notion | CSV / Excel neutralisés, onglet des exclus, export des intéressés vers Notion sans doublon ni écrasement, reprise après panne | C62 à C75, C89, C118 |
| 8 · Terrain | Petits commerces autour de moi, tournée, itinéraire, statut devant la boutique | C113 à C115 |
| 9 · Relances et suivi dans le temps | Notifications Web Push, campagnes programmées, mise à jour des campagnes passées, alertes | C76 à C78, C98, C108 |
| 10 · Pilotage, conformité, maintenance | Tableau de bord, journal des campagnes, purge RGPD, suppression sur demande, sauvegardes, vérification hebdomadaire des API, Sentry, Dependabot | C80, C81, C90, C91, C94, C95, C99, C100 |

Ordre choisi pour livrer tôt ce qui manque le plus au propriétaire : le **suivi des appels (lot 3)** arrive dès qu'il existe des prospects à appeler (lot 2), avant les enrichissements.
