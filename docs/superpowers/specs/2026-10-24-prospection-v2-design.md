# Prospection v2 · spec de conception

Statut : **validée par le propriétaire le 24 octobre 2026**. Date : 24 octobre 2026.
Maquettes validées : https://claude.ai/artifact/MxncTwxekn6dHL9i18YZ9o (7 écrans mobiles, données d'exemple).

Références : [CLAUDE.md](../../../CLAUDE.md) (règles), [COMPORTEMENTS.md](../../../COMPORTEMENTS.md) (C01 à C120).
Les choix marqués **[choix Claude]** n'ont pas été discutés avec le propriétaire : ils sont modifiables.

---

## 1. Intention

Un outil personnel, utilisé surtout **sur un téléphone Android**, pour un freelance de La Réunion qui prospecte des petites entreprises **par téléphone et en porte-à-porte**.

L'ancienne version (`prospection-bot`, Streamlit) trouvait des prospects mais laissait quatre manques, dits par le propriétaire :

1. **Pas de tri juste après l'appel.** Impossible de classer un prospect (OK, pas OK, à rappeler…) directement dans l'app ; Streamlit se déconnecte dès qu'on passe sur le téléphone ou sur Google, et le travail en cours est perdu.
2. **Pas de vision de l'entreprise.** On ne sait pas si elle fait du chiffre, si elle est débordée, comment elle s'organise.
3. **Pas d'angle d'appel.** On ne sait pas sur quelles douleurs appuyer.
4. **Pas de très petits commerces locaux** pour la prospection terrain.

La v2 devient donc le **poste de travail quotidien de prospection** : trouver, qualifier, préparer l'appel, appeler, noter le résultat, planifier la relance, puis envoyer les prospects intéressés au CRM.

**Réussite** = pendant une session d'appel, le propriétaire enchaîne les prospects sur son téléphone, note chaque résultat en un geste, et le lendemain l'écran « Aujourd'hui » lui dit exactement qui rappeler, sans rien avoir perdu.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Tout ce que liste COMPORTEMENTS.md (sourcing, qualification, enrichissement, export, CRM, sécurité, conformité), **ajusté** par la section 9.
- Suivi de prospection dans l'app : statut, prochaine action (tâche + date), note, écran « Aujourd'hui », notifications de relance.
- Fiche « Pour l'appel » générée par **règles fixes** (pas d'IA).
- Indices de santé de l'entreprise à partir de données publiques gratuites.
- Mode **Terrain** : petits commerces autour de moi, tournée ordonnée.
- App installable (PWA) sur Android, qui ne perd jamais une saisie.

**Non-objectifs**
- Aucun envoi de message (mail, SMS) : le propriétaire contacte lui-même (règle de CLAUDE.md).
- Pas de suivi client après le « Intéressé » : devis, projet, facturation restent dans le CRM.
- Pas d'IA générative (coût, imprévisibilité) ; on pourra y revenir plus tard.
- Pas de mode hors connexion (le propriétaire a toujours du réseau quand il appelle).
- Pas d'app native ni de Play Store.
- Pas de multi-utilisateur.
- Pas d'optimisation pour iPhone (le propriétaire est sur Android ; l'app reste un site web standard).

**Anti-objectifs (échec même si « ça marche »)**
- Une saisie perdue sans que le propriétaire le sache.
- Une dépense Google au-delà du budget.
- Une fiche d'appel qui affirme une info douteuse comme une certitude (CA inventé, mauvais rapprochement d'entreprise).
- Un écran lent ou chargé sur téléphone, ou une interface qui « fait générée par IA » (dégradés, emojis, cartes à bordure colorée).
- Un CRM pollué par des centaines de « pas intéressés ».

## 3. Contraintes

Toutes celles de CLAUDE.md et `.claude/bonnes-pratiques.md`, en particulier : couches `domain/ sources/ crm/ storage/ application/ ui/`, domaine pur (temps passé en paramètre), TDD avec numéro de comportement, aucun réseau dans les tests (faux pour chaque service), budget, CGU (API officielles seulement), SSRF, textes externes neutralisés (interface et CSV / Excel), secrets chiffrés, RGPD, PostgreSQL, travail long en tâche de fond, déploiement Railway, fichiers ≤ ~150 lignes.

Contexte local : le propriétaire est à **La Réunion (UTC+4, `Indian/Reunion`)**. Les dates « aujourd'hui / demain / en retard » et les heures de rappel se calculent dans ce fuseau **[choix Claude : fuseau configurable dans les réglages, `Indian/Reunion` par défaut]**. Les tests sont rejoués dans un fuseau éloigné (ex. `America/Los_Angeles`).

## 4. Décisions prises avec le propriétaire

| Sujet | Décision |
|---|---|
| Rôle de l'app vs CRM | **Option C** : l'app gère la prospection jusqu'à « Intéressé ». Le CRM reçoit seulement les intéressés, **dans un seul sens**, et sert ensuite au suivi client. |
| Déclenchement de l'envoi au CRM | **Bouton manuel** « Exporter », jamais automatique. Relecture possible avant envoi (décocher un prospect). |
| Déconnexions | Site web classique, chaque action est une requête courte et **enregistrée immédiatement** ; pas de dépendance à une connexion permanente. |
| Plateforme | **PWA installable sur Android** (Chrome) : icône, plein écran, notifications. |
| Hors connexion | **Non**. Si un enregistrement échoue, message clair et la saisie reste dans le champ pour réessayer. |
| Suivi « façon Pipedrive » | Chaque prospect a une **prochaine action** (type + date + heure facultative). Écran **Aujourd'hui** recalculé chaque jour, avec **notifications** de relance. |
| Fiche « Pour l'appel » | **Règles fixes, gratuites**, dans un fichier de règles lisible et modifiable ; enrichies avec le temps. |
| Navigation | Barre **flottante**, une seule ligne, 4 onglets : Aujourd'hui, Prospects, Terrain, Recherche. |
| Style | Épuré, proche d'iOS (police système, listes groupées, beaucoup d'air), **petite touche 974** (logo volcan + rayons, bleu océan). Aucune « marque » d'interface générée par IA. |
| Maquettes | Les 7 écrans sont validés en l'état. |
| CRM | **Notion seulement** au départ (HubSpot reporté). Base dédiée créée dans DEV : page « 11. Prospection v2 (CRM) », base **Prospects v2** (https://app.notion.com/p/ebbf6ef71a4945bf8575a326c745d824). |

## 5. Parcours et écrans

Référence visuelle : les maquettes. Résumé fonctionnel :

0. **Aujourd'hui** (écran d'ouverture) : session d'appel à reprendre (campagne, position), actions **en retard**, actions **du jour** (heure, prospect, note courte), activité en fond (recherche en cours, nombre d'intéressés à exporter), aperçu de demain. Cocher une action la termine.
1. **Recherche** : mode Appels / Terrain ; métier + synonymes (retirables), ville + rayon (ou départements), sources, nombre de qualifiés voulus, modèle de critères, option fiche d'appel ; coût estimé et budget restant **avant** le bouton « Lancer ».
2. **Suivi en direct** : qualifiés / voulus, trouvés, exclus, dépensé, étape en cours, raisons d'exclusion ; « Appeler les N déjà prêts » sans attendre la fin ; « Arrêter » (on garde ce qui est trouvé).
3. **Prospects** : recherche texte, filtres par statut avec compteurs, score, raison de qualification, drapeau « à vérifier » ; « Démarrer la session d'appel ».
4. **Session d'appel** (écran clé) : précédent / suivant dans la file, position (4 / 12) ; nom, métier, ville, distance, étiquettes (score, signaux) ; boutons **Appeler** (`tel:`), fiche Google, recherche Google, recherche du dirigeant (lien de recherche LinkedIn, sans scraping) ; bloc **Pour l'appel** (accroche + douleurs, mention « indices à confirmer ») ; **Résultat** ; **Prochaine action** (type, date rapide, heure) ; **Note** ; **Contact** modifiable (dirigeant, mobile, email) ; **L'entreprise** (création, effectif, CA si publié, horaires, forme, SIREN). Tout s'enregistre au fil de la saisie.
5. **Exporter** : intéressés pas encore envoyés, cases à décocher, prospects « à vérifier » décochés par défaut, destination (CRM configuré, Excel, CSV), bilan du dernier envoi.
6. **Terrain** : filtres (petits commerces, moins de N avis, sans site, ouvert maintenant), carte de la tournée, bouton « Ouvrir l'itinéraire », liste dans l'ordre de passage, statut en un geste (Intéressé / Repasser / Non).

Écrans non maquettés (classiques, à faire au fil des comportements) : connexion, réglages (clés, CRM, budget, fuseau, notifications, liste noire, règles), modèles de campagne, historique et exports passés, journal, tableau de bord.

## 6. Modèle métier (ajouts)

**Statuts d'un prospect** (un seul à la fois) :
`à appeler` (défaut après qualification) · `intéressé` · `à rappeler` · `pas intéressé` · `messagerie` · `pas joint` · `faux numéro` · `exporté` (posé par l'export réussi).
En terrain, les boutons Intéressé / Repasser / Non posent `intéressé` / `à rappeler` (action « Passer ») / `pas intéressé`.
`pas intéressé` propose (sans l'imposer) l'ajout à la liste noire (C33). **[choix Claude]**

**Prochaine action** : au plus **une action ouverte** par prospect **[choix Claude, simple ; l'historique garde les actions terminées]**. Champs : type (`Rappeler`, `Envoyer un devis`, `Rendez-vous`, `Passer`), date, heure facultative, faite / pas faite. Choisir `à rappeler` ou `messagerie` préremplit « Rappeler · demain ».

**Note** : texte libre par prospect, horodaté ; plusieurs notes possibles (historique des échanges).

**Écran Aujourd'hui** = fonction pure du domaine : `(actions, maintenant, fuseau) → en retard / aujourd'hui / demain`, triées par heure puis par score.

**Notifications** : rappel **15 min avant** une action avec heure, et à **8 h** pour les actions du jour sans heure **[choix Claude, réglable]**. Envoi par **Web Push** (clés VAPID en variables d'environnement, bibliothèque `pywebpush`), depuis la tâche de fond. Aucun texte externe brut dans la notification (nom du prospect neutralisé).

**Fiche « Pour l'appel »** :
- Entrée : signaux déjà calculés (pas de site, site faible et ses problèmes, HTTPS, mobile, formulaire, prise de rendez-vous en ligne, date de création, nombre et rythme des avis, réponses aux avis, horaires, effectif, CA publié ou non…).
- Règles dans un **fichier de données versionné et validé** (YAML ou JSON, schéma strict, chargé au démarrage ; une règle invalide fait échouer le démarrage et les tests). Une règle = conditions sur les signaux → douleur(s) + accroche(s), avec variables `{métier}`, `{ville}`, `{nom}`, `{ancienneté}`, `{note}`.
- Sortie : 1 accroche + 3 douleurs maximum, triées par priorité de règle ; toujours la mention « indices à confirmer ».
- Fonction pure du domaine, testée règle par règle. Modifier les règles = éditer le fichier puis déployer **[choix Claude : pas d'éditeur dans l'app au début]**.

**Indices de santé** (aucune donnée inventée ; « non publié » quand absent) :
- **API Recherche d'entreprises** (recherche-entreprises.api.gouv.fr, gratuite, sans clé) : CA et résultat quand publiés, effectif, dirigeants, création, état actif, non-diffusibles respectés (C93).
- Sirène (INSEE) pour les créations récentes (C24 à C27).
- Google Places : horaires, nombre d'avis et dates des avis récents, réponses du propriétaire, photos.
- Audit du site (déjà prévu C49 à C52).

**Terrain** :
- Position : géolocalisation du navigateur (avec accord) ou adresse saisie.
- Recherche Google Places autour de la position (rayon court, catégories de commerces de proximité), mêmes critères gratuits d'abord, même budget.
- Ordre de passage : heuristique du **plus proche voisin** à vol d'oiseau, calculée localement, gratuite **[choix Claude]**.
- « Ouvrir l'itinéraire » : lien Google Maps (itinéraire à pied avec étapes, URL officielle ; au-delà de la limite d'étapes de l'URL, découpage en plusieurs tronçons).

## 7. Stack et architecture

| Besoin | Choix |
|---|---|
| Langage | Python 3.13, typé, `mypy --strict`, `ruff` |
| Serveur web | **FastAPI** + gabarits **Jinja2** rendus côté serveur |
| Interactions sans rechargement | **HTMX** (fichier statique servi par l'app, version épinglée) |
| CSS | Une feuille de style unique avec variables (thème centralisé) ; pas de framework CSS **[choix Claude]** |
| PWA | `manifest.webmanifest` + `service-worker.js` minimal (cache de la coquille statique, réception des notifications) |
| Base | **PostgreSQL** ; accès par SQLAlchemy 2 (Core) + **Alembic** pour les migrations numérotées et testées **[choix Claude]** |
| Tâches de fond | **Processus « worker » séparé** (2e service Railway, même image) qui lit une table de tâches avec `SELECT … FOR UPDATE SKIP LOCKED` ; pas de Redis **[choix Claude]**. Il gère campagnes, reprise après coupure (C40), envois CRM réessayés (C73), rappels et notifications, campagnes programmées (C77) |
| Progression en direct | Rafraîchissement HTMX périodique (toutes les 2 à 3 s) de l'écran Suivi, seulement quand il est affiché **[choix Claude, plus léger qu'une connexion permanente]** |
| Authentification | Mot de passe unique haché (**argon2**), limite d'essais (C82), cookie de session signé `HttpOnly; Secure; SameSite=Lax`, durée **30 jours** glissants |
| Secrets | Clés API chiffrées en base (**Fernet**, bibliothèque `cryptography`) ; clé de chiffrement et clés VAPID en variables d'environnement Railway |
| HTTP sortant | `httpx` avec délais, taille maximale, redirections vérifiées, garde SSRF commune (C87, C88) |
| Excel | `openpyxl` (neutralisation des formules, C89) |
| Tests | `pytest` (+ `pytest-cov`, seuil de couverture **90 %** sur `domain/`, **80 %** global **[choix Claude]**), faux pour chaque service, base de test PostgreSQL éphémère en CI ; bout en bout avec **Playwright** sur l'image construite |
| Dépendances | **uv** + `uv.lock` commité ; `pip-audit` ; `import-linter` (couches et cycles) ; Dependabot |
| Erreurs | Sentry (offre gratuite), sans données personnelles ni secrets |
| CI | GitHub Actions, dans l'ordre des bonnes pratiques (installation, audit, lint, types, tests, image, bout en bout) |
| Déploiement | Railway : service web + service worker + PostgreSQL ; `main` déploie la production |

Sécurité HTTP : CSP stricte (`default-src 'self'`, pas de script en ligne : HTMX est compatible), `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy`, HSTS, HTTPS uniquement.

Briques reprises de `prospection-bot` (fonction par fonction, relues, avec leurs tests, source citée dans le commit) : recherche Google, filtres, franchises, métiers et synonymes, site retrouvé, audit, vérification d'email, dirigeants, score d'opportunité.

## 8. Ce qui est laissé au constructeur

Découpage exact des modules dans chaque couche, schéma détaillé des tables, textes des messages (français, courts, qui disent quoi faire), icônes, contenu initial du fichier de règles (à partir des signaux disponibles), format exact des colonnes d'export, ordre des lots (proposé dans le plan).

## 9. Changements apportés à COMPORTEMENTS.md

Appliqués après validation (voir COMPORTEMENTS.md, qui fait foi) :
- **Modifiés** pour suivre les décisions : C02, C05, C06, C09 (Notion seulement), C33 (liste noire proposée), C43 (photos « probable »), C67, C68 (export manuel des intéressés, statut « exporté »), C73, C75 (Notion), C94 (6 mois), C98, C99 (notification au lieu d'email).
- **Ajoutés** : C102 à C109 (suivi des appels), C110 à C112 (préparation de l'appel), C113 à C115 (terrain), C116 et C117 (app sur le téléphone), C118 (export fichier sans changement de statut), C119 (appeler pendant la recherche), C120 (recherche et filtres de la liste).

## 10. Hypothèses et points ouverts

**Limites des API officielles (Google Places)** **[choix Claude]**
- Places renvoie au plus 5 avis par fiche, sans les réponses du propriétaire. Le « rythme des avis » est donc une **approximation** (dates des avis renvoyés + évolution du nombre total entre deux passages), affichée « probable ». Les « réponses aux avis » sont **retirées** : impossibles sans scraping.
- C43 (photos ajoutées par le propriétaire ou des clients) : approximation à partir de l'attribution des photos renvoyées, affichée « probable ».
- Les champs coûteux (avis, photos, horaires détaillés) ne sont demandés **qu'après** les critères gratuits et seulement pour les prospects encore en lice ; l'estimation de coût (C16) suit les tarifs par palier de champs, dans un fichier de tarifs versionné.

**Deux exports distincts** **[choix Claude]**
- **Fichier de campagne** (C61 à C66) : à tout moment, tous les qualifiés + onglet des exclus ; **ne change aucun statut**.
- **Envoi au CRM** (écran Exporter) : seulement les intéressés cochés ; pose `exporté` uniquement si l'envoi CRM réussit. Sans CRM configuré, l'écran Exporter propose Excel / CSV des intéressés et pose `exporté` après téléchargement.

**RGPD et liste noire** **[choix Claude]**
- Purge (C94) après **6 mois** sans activité (réglable) : prospects exclus, `pas intéressé`, `pas joint`, `messagerie`, `faux numéro`, `à appeler` jamais appelés. Jamais purgés : `intéressé`, `exporté`, `à rappeler` avec action ouverte.
- La liste noire ne garde que le strict nécessaire pour ne pas re-proposer : SIREN, identifiant Google, nom normalisé, date. Suppression sur demande (C95) : efface aussi l'entrée de liste noire sauf si le propriétaire choisit de la garder.

**Alertes au propriétaire** **[choix Claude]**
- C98 et C99 utilisent la **notification Web Push** déjà prévue (pas de service d'email, pas de secret de plus). Si le propriétaire tient à l'email, on ajoutera un fournisseur ensuite.
- C99 (vérification hebdomadaire des vraies API) tourne dans le **worker Railway**, qui lit les clés en base ; aucune copie des clés dans GitHub.

**Sauvegardes (C91)** **[choix Claude]** : `pg_dump` quotidien lancé par le worker vers un stockage objet compatible S3 (ex. Cloudflare R2, offre gratuite), chiffré, 30 jours conservés ; restauration testée. Si l'offre Railway du propriétaire inclut des sauvegardes natives, on les utilise à la place.

**Base Notion « Prospects v2 »** (créée le 24/10/2026)
- Une ligne par entreprise (Notion n'a pas de modèle entreprise / contact : le dirigeant est en colonnes). Colonnes : Entreprise (titre), Statut CRM, Prochaine action, Date action, Dirigeant, Mobile, Téléphone, Email, Site, Fiche Google, Métier, Ville, SIREN, Score, Raison, Notes app, Notes perso, Campagne, Exporté le, ID app.
- Doublons (C69) : recherche par « ID app », puis par SIREN. Ne pas écraser (C70) : l'app n'écrit que ses colonnes, et seulement si la cellule est vide ou porte encore la valeur qu'elle y avait mise ; « Notes perso » jamais ; « Statut CRM » seulement à la création (« Nouveau »).
- Exclusion « déjà dans le CRM » (C32) : lecture de la base par SIREN, identifiant Google et nom normalisé.
- Mise en service : créer une intégration Notion, partager la base avec elle, saisir la clé dans l'app (C02, C03).

**Autres**

- La file d'une session d'appel = prospects `à appeler` de la campagne choisie, triés par score décroissant ; les `à rappeler` dus aujourd'hui passent par l'écran Aujourd'hui. **[choix Claude]**
- Les comportements C19 à C33 (critères) s'appliquent aussi au mode Terrain, avec un modèle de critères « Petit commerce » par défaut. **[choix Claude]**
- **Aucune reprise** des données de l'ancienne app (liste noire, prospects contactés, franchises perso), décidé par le propriétaire : on repart de zéro avec une nouvelle approche d'appel. La liste de franchises fournie (C30) est reprise comme brique de code, pas comme donnée perso.
