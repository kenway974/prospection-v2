# Lot 2 · Campagne Google Maps — plan de construction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** le propriétaire lance une recherche depuis son téléphone : métiers, zone, nombre de qualifiés voulu, critères. Il voit le coût estimé, qui vaut 0 € tant qu'on reste dans le quota gratuit de Google. Une tâche de fond cherche sur Google Maps, applique les critères, déduplique et s'arrête au bon moment en disant pourquoi. L'écran Suivi montre la progression en direct. On peut arrêter la recherche, et elle reprend toute seule après un redémarrage.

**Architecture :**
- `domain/` : règles pures (demande de campagne, critères, dédoublonnage, coût et plafond, condition d'arrêt).
- `sources/` : Google Places (New) Text Search et `geo.api.gouv.fr`, qui donne le centre des communes (gratuit, sans clé).
- `storage/` : campagnes, file des requêtes, prospects, consommation Google, journal.
- `application/` : une **étape** de campagne idempotente, que la tâche de fond rejoue jusqu'à la fin.
- **Worker** : un processus séparé (`python -m prospection.worker`), 2ᵉ service Railway, même image.
- `ui/` : formulaire Recherche, écran Suivi avec rafraîchissement HTMX toutes les 3 s.

**Tech Stack :** celle des lots 0 et 1, plus `phonenumbers` (mobile ou fixe) et des fichiers de données YAML validés (`pyyaml`).

**Spec :** `docs/superpowers/specs/2026-10-24-prospection-v2-design.md` (sections 4, 5 [écrans 1 et 2], 6, 7, 10). Feuille de route : `docs/superpowers/plans/2026-10-24-feuille-de-route.md`.

**Comportements :** C10 à C23, C30 à C43, C79, C119, et la seconde moitié de C07 (refus de dépasser le plafond). C43 manquait dans la feuille de route : il est rattaché ici, car les photos arrivent dans la même réponse Google.

## Global Constraints

Celles des lots 0 et 1, plus :

**Google Places : API officielle seulement** (règle CGU)
- On utilise **Text Search (New)** : `POST https://places.googleapis.com/v1/places:searchText`, `pageSize` 20, au plus 3 pages par requête via `nextPageToken`.
- **Masque de champs exact :** `places.id,places.displayName,places.formattedAddress,places.location,places.types,places.primaryType,places.businessStatus,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.regularOpeningHours,places.googleMapsUri,places.photos,nextPageToken`.
- Ce masque correspond au palier **« Text Search Enterprise »** : 1 000 appels gratuits par mois, puis 35 $ les 1 000. Un appel = une page de 20 établissements.

**Tarifs dans un fichier de données versionné** : `data/google_pricing.yaml`
- contenu : palier, quota gratuit mensuel, prix pour 1 000 appels en dollars, taux € par $ ;
- validé au démarrage ;
- source citée dans le fichier : page des tarifs Google Maps Platform, à vérifier quand Google la change.

**Plafond (C07)**
- Avant **chaque** appel payant, l'app vérifie : `appels_du_mois + 1 ≤ quota_gratuit`, ou que le coût de cet appel tient dans `plafond − dépensé_ce_mois`.
- Sinon, pas d'appel : la campagne s'arrête avec la raison « Quota gratuit de Google atteint pour ce mois (plafond 0 €). Relevez le plafond dans Réglages → Budget Google, ou attendez le 1er. »
- Le mois se compte dans le fuseau de l'app. La consommation ne compte que les appels de l'app (dit à l'écran).

**Ordre des critères (C39)**
- Les critères gratuits (catégorie, nom, franchise, liste noire, doublon, distance, site, téléphone, avis) s'appliquent sur la page déjà payée.
- Aucun appel payant n'est fait pour un établissement déjà exclu (concerne les enrichissements des lots suivants).

**Textes externes**
- Noms, adresses et catégories Google ne sont jamais injectés bruts : échappement Jinja, longueurs bornées à la validation pydantic.

**Couches**
- Le worker est un point d'entrée hors couches, comme `cli.py` ; il appelle seulement `application/`.

## Review Focus

1. **Plafond à 0 € atteint en plein milieu d'une campagne** : arrêt propre, prospects déjà trouvés gardés, raison affichée, aucun appel au-delà. → Tasks 2 et 6.
2. **Le worker redémarre pendant un appel Google** (déploiement Railway) : la campagne reprend sans refaire les pages déjà traitées ni compter deux fois un appel. → Tasks 6 et 7.
3. **Réponse Google partielle ou étrange** (établissement sans nom, sans téléphone, type inconnu, `nextPageToken` absent, 429 « trop de requêtes ») : l'établissement fautif est ignoré, la campagne continue (C41), et un 429 est retenté plus tard. → Tasks 3 et 6.
4. **Saisie de zone ambiguë** (« Saint-Denis » : 93 ou 974 ; ville inconnue ; rayon de 0) : l'app propose les communes possibles ou dit quoi corriger. Elle ne choisit jamais en silence. → Tasks 1 et 3.
5. **Deux campagnes lancées en même temps** : chacune avance, le plafond reste global et respecté. → Tasks 2 et 7.

---

### Task 1 : Demande de campagne, métiers et synonymes (C10 à C15, C17)

**Files :** create `src/prospection/domain/campaign_request.py`, `src/prospection/domain/trades.py`, `data/trades.yaml` ; tests `tests/domain/test_campaign_request.py`, `tests/domain/test_trades.py`.

**Interfaces :**
- `Zone` est l'un de :
  - `CityZone(name, insee_code, lat, lon)` ;
  - `RadiusZone(city: CityZone, radius_km: int)`, avec un rayon de 1 à 50 ;
  - `DepartmentZone(code, name)`.
- `CampaignRequest(name, trades: tuple[str, ...], zones: tuple[Zone, ...], target: int, criteria: Criteria, synonyms_on: bool)`.
- `validate_request(raw: RawRequest) -> CampaignRequest`. Elle lève `InvalidRequest(errors: dict[champ, message])`, avec ces messages exacts :

| Cas | Message |
|---|---|
| Métier vide | « Indiquez au moins un métier. » |
| Zone vide | « Indiquez au moins une ville, un département ou un rayon. » |
| Nom vide | « Donnez un nom à la campagne. » |
| Nombre hors limites | « Choisissez entre 1 et 200 prospects. » |

- `trades.yaml` : une entrée par métier, avec `id`, `label`, `aliases`, `queries` (synonymes), `name_words`, `off_target_types`. On y reprend les métiers du bâtiment de `prospection-bot/trades.py` (version `530ba12`) et on ajoute les petits commerces : fleuriste, boulangerie, coiffeur, esthéticienne, garage, restaurant indépendant.
- `expand_queries(trades, synonyms_on) -> list[str]` : renvoie les mots-clés, plus leurs synonymes s'ils sont activés. Un métier inconnu reste tel quel, sans doublon.

- [ ] **Tests :**
  - `test_C17_missing_trade_or_zone_refused_with_reason` ;
  - `test_C10_name_required` ;
  - `test_C14_target_bounds` ;
  - `test_C12_several_trades` ;
  - `test_C15_cuisiniste_expands_to_cuisine_sur_mesure` ;
  - `test_C15_unknown_trade_kept_as_is` ;
  - `test_trades_file_is_valid` (un fichier invalide fait échouer le chargement).
- [ ] Implémenter ; tout vert ; **commit** (citer la source `prospection-bot/trades.py@530ba12`).

### Task 2 : Coût, quota gratuit et plafond (C07, C16, C79)

**Files :** create `src/prospection/domain/google_cost.py`, `data/google_pricing.yaml` ; tests `tests/domain/test_google_cost.py`.

**Interfaces :**
- `Pricing(free_per_month: int, usd_per_1000: Decimal, eur_per_usd: Decimal)`, chargée depuis le YAML.
- `call_cost_cents(pricing, calls_this_month: int) -> int` : 0 tant qu'on est dans le quota, sinon le prix d'un appel arrondi au centime supérieur.
- `can_call(pricing, calls_this_month, spent_cents, budget_cents) -> bool`.
- `estimate(pricing, pages: int, calls_this_month, spent_cents, budget_cents) -> Estimate(pages, free_pages, paid_cents, fits: bool)`.
- `pages_needed(queries: int, zones: int, max_pages: int = 3) -> int`. C'est le maximum possible : la campagne s'arrête souvent avant.

- [ ] **Tests :**
  - `test_C07_zero_budget_allows_free_quota_only` (999 appels → oui ; 1 000 → non) ;
  - `test_C07_budget_allows_paid_calls_until_spent` ;
  - `test_C16_estimate_zero_euros_inside_free_quota` ;
  - `test_C16_estimate_beyond_quota` ;
  - `test_pricing_file_is_valid`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 3 : Sources Google Places (C42, C43) et communes (C13)

**Files :** create `src/prospection/sources/google_search.py`, `src/prospection/sources/geo_communes.py`, `src/prospection/domain/place.py` ; tests `tests/sources/test_google_search.py`, `tests/sources/test_geo_communes.py`.

**Interfaces :**
- `Place` (domaine, gelé) :
  - `place_id`, `name`, `address`, `lat`, `lon`, `types`, `primary_type`, `business_status`, `phone`, `website`, `rating: float | None`, `review_count: int`, `opening_hours: list[str]`, `maps_url`, `photo_count: int`, `owner_photo_estimate: str` (« probable propriétaire », « clients seulement », « inconnu »).
  - Textes tronqués à 300 caractères.
- `search_page(client, key, query, bias: Circle | None, page_token) -> SearchPage(places: list[Place], next_token: str | None, skipped: int)`.
  - Un établissement invalide est **ignoré et compté**, pas une erreur.
  - Un 429 ou un 5xx lève `GoogleBusy` (à retenter) ; un 400 ou un 403 lève `GoogleRefused(message)`.
- `owner_photo_estimate` : si une photo est attribuée au nom de l'établissement → « probable propriétaire » ; s'il y a des photos sans cette attribution → « clients seulement » ; sinon « inconnu ».
- `find_communes(client, name) -> list[CityZone]` : `GET https://geo.api.gouv.fr/communes?nom=…&fields=nom,code,codeDepartement,centre&boost=population&limit=5`. Le libellé indique le département, par exemple « Saint-Denis (974) ».

- [ ] **Tests** (faux serveur) :
  - `test_C42_fields_parsed` ;
  - `test_exact_field_mask_and_page_size_sent` ;
  - `test_C43_photo_count_and_owner_estimate` ;
  - `test_invalid_place_skipped_and_counted` ;
  - `test_next_page_token_followed` ;
  - `test_429_raises_busy` ;
  - `test_403_raises_refused_with_message` ;
  - `test_communes_ambiguous_name_returns_all_with_department` ;
  - `test_unknown_commune_returns_empty`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 4 : Critères de qualification (C19 à C23, C30, C31, C33, C38)

**Files :** create `src/prospection/domain/criteria.py`, `src/prospection/domain/phones.py`, `src/prospection/domain/franchises.py`, `data/franchises.yaml` ; tests correspondants dans `tests/domain/`.

**Interfaces :**
- `Criteria(min_reviews: int | None, max_reviews: int | None, website: Literal["any","with","without"], phone: Literal["any","with","mobile"], exclude_franchises: bool)`.
- `Verdict(qualified: bool, reasons: tuple[str, ...], to_check: tuple[str, ...])`.
- `evaluate(place, trade, criteria, franchise_names, blacklist, now) -> Verdict`.
- Raisons d'exclusion (exactes) :
  - « Trop d'avis (N) » ;
  - « Pas assez d'avis (N) » ;
  - « Sans site » / « Avec site » ;
  - « Sans téléphone » / « Pas de mobile » ;
  - « Hors métier (catégorie) » ;
  - « Franchise ou chaîne » ;
  - « Liste noire » ;
  - « Fermé définitivement ».
- C20 : un établissement **sans note** n'est pas exclu pour ça.
- C31 : un nom qui *contient* le nom d'une enseigne, sans correspondre exactement à la forme normalisée de l'enseigne, est marqué « à vérifier » et non exclu. Exemple : « Boulangerie Paul Hoarau » face à l'enseigne « Paul ».
- `is_mobile(phone) -> bool` avec `phonenumbers`. Un numéro de La Réunion en 0692 ou 0693 est un mobile.
- `dedup_key(place) -> str` (= `place_id`). `merge` garde la première version et ajoute les mots-clés qui l'ont trouvé (C38).
- Reprise depuis `prospection-bot` (version `530ba12`) : `filters.py`, `services/franchises.py`, `trades.py`. Seulement les fonctions nécessaires, relues ; leurs anciens tests sont repris quand ils s'appliquent.

- [ ] **Tests :** un par critère (C19, C20, C21, C22 avec `test_C22_reunion_0692_is_mobile`, C23), plus :
  - `test_C30_franchise_from_list_and_personal_list_excluded` ;
  - `test_C31_independent_with_brand_like_name_marked_to_check` ;
  - `test_C33_blacklist_excluded` ;
  - `test_C38_same_place_two_keywords_once` ;
  - `test_closed_permanently_excluded`.
- [ ] Implémenter ; tout vert ; **commit** (sources citées).

### Task 5 : Stockage des campagnes et des prospects (migration 0004)

**Files :** create `src/prospection/storage/campaigns.py`, `src/prospection/storage/prospects.py`, `src/prospection/storage/google_usage.py`, `src/prospection/storage/exclusions.py`, `src/prospection/storage/migrations/versions/0004_campaigns.py` ; tests `tests/storage/test_campaigns.py`, etc.

**Tables :**
- `campaigns` : `id`, `name`, `request_json`, `status` (`queued` / `running` / `stopping` / `done`), `stop_reason`, `found`, `excluded`, `qualified`, `cost_cents`, `created_at`, `updated_at`, `heartbeat_at`.
- `campaign_steps` : `campaign_id`, `query`, `zone_label`, `bias` JSON, `page_token`, `page_number`, `done` boolean, `attempts`.
  - Une ligne par couple requête × zone. On avance d'une page à la fois, et la page suivante est enregistrée **avant** de traiter les résultats, dans la même transaction que les prospects (C40).
- `prospects` : `id`, `campaign_id`, `place_id` (unique par campagne), `data_json` (Place validé), `keywords` text[], `qualified`, `reasons` text[], `to_check` text[], `status` (`à appeler` par défaut pour les qualifiés), `created_at`.
- `google_usage` : `month` (AAAA-MM, fuseau de l'app), `calls`, `cost_cents`. Mis à jour en `UPDATE … RETURNING` sous le verrou consultatif « google » (C07, Review Focus 5).
- `campaign_events` : journal court (C81 partiel) : `campaign_id`, `at`, `level`, `message`.
- `franchise_names` (liste perso) et `blacklist` (`name_norm`, `place_id`, `siren`, `added_at`).
- `campaign_templates` : `name`, `request_json` (C18).

- [ ] **Tests :** migration dans les deux sens (test existant), plus :
  - `test_C40_next_page_saved_with_results_atomically` ;
  - `test_C38_unique_place_per_campaign` ;
  - `test_C07_usage_counter_is_atomic_under_lock` ;
  - `test_C18_template_saved_and_listed`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 6 : Étape de campagne (C34 à C39, C41, C79, C119)

**Files :** create `src/prospection/application/campaign_step.py`, `src/prospection/application/campaigns.py` ; tests `tests/application/test_campaign_step.py`.

**Interfaces :**
- `create_campaign(engine, request, now) -> int` : crée la campagne et ses étapes (requêtes × zones), au statut `queued`.
- `run_step(engine, box, client, campaign_id, now) -> StepOutcome(done: bool)`. Elle traite **une** page :
  1. Statut `stopping` → `done`, avec la raison « Arrêtée à votre demande ».
  2. Objectif atteint → `done`, avec la raison « Objectif atteint : N prospects qualifiés ».
  3. Plus d'étape restante → `done`, avec la raison « Plus de résultats sur Google Maps pour ces métiers et cette zone (N qualifiés sur M voulus) ».
  4. `can_call` faux → `done`, avec la raison du plafond (Global Constraints).
  5. Sinon : réserve l'appel (compteur), appelle Google, applique les critères, déduplique, enregistre la page suivante et les prospects dans **une** transaction, puis met à jour les compteurs et le coût de la campagne (C79).
- `GoogleBusy` : l'étape est retentée jusqu'à 3 fois, avec une pause croissante (5, 30 puis 120 s). Ensuite, l'étape est sautée et le journal note « Google trop sollicité : page ignorée ».
- `GoogleRefused` : arrêt, avec la raison du message.
- Erreur sur **un** établissement : journalisée, la campagne continue (C41).
- `request_stop(engine, campaign_id)` (C35) : les prospects déjà trouvés sont gardés.
- `progress(engine, campaign_id) -> Progress(status, step_label, found, excluded, qualified, target, cost_cents, exclusion_counts: list[(raison, n)], recent_events, stop_reason)`.

- [ ] **Tests** (faux Google, horloge injectée) :
  - `test_C36_continues_until_target` ;
  - `test_C37_stops_when_source_exhausted_with_reason` ;
  - `test_C37_C07_stops_at_free_quota_with_reason_and_keeps_prospects` (Review Focus 1) ;
  - `test_C35_stop_keeps_found` ;
  - `test_C38_duplicate_across_keywords_counted_once` ;
  - `test_C41_bad_place_does_not_stop` ;
  - `test_busy_retried_then_skipped` ;
  - `test_C79_cost_recorded_per_campaign` ;
  - `test_C40_rerun_after_crash_does_not_double_count_prospects` (Review Focus 2 : l'étape est rejouée après une exception simulée pendant l'appel ; les prospects ne sont pas comptés deux fois ; l'appel interrompu, qui a pu avoir lieu chez Google, reste compté : décision prudente pour le budget, donc 2 appels comptés).
- [ ] Implémenter ; tout vert ; **commit**.

### Task 7 : Tâche de fond (worker) (C40)

**Files :** create `src/prospection/worker.py` (point d'entrée), `src/prospection/application/campaign_queue.py` ; modify `Dockerfile` (la commande reste celle du web ; le worker se lance par `python -m prospection.worker`), `README.md` (2ᵉ service Railway) ; tests `tests/application/test_campaign_queue.py`, `tests/test_worker.py`.

**Interfaces :**
- `claim_next(engine, now, stale_after=timedelta(minutes=2)) -> int | None` :
  - `SELECT … FOR UPDATE SKIP LOCKED` sur les campagnes `queued`, ou `running` dont le `heartbeat_at` est périmé (reprise après redémarrage) ;
  - passe la campagne en `running` et met à jour le `heartbeat_at`.
- `worker.main(stop_event)` : boucle « réclamer puis `run_step` jusqu'à `done` », avec une pause de 2 s si rien à faire. S'arrête proprement sur SIGTERM (Railway). Les journaux ne contiennent ni clé ni URL complète.
- La campagne qui attend un nouvel essai garde son heartbeat, pour qu'aucun autre worker ne la vole.

- [ ] **Tests :**
  - `test_C40_stale_running_campaign_is_reclaimed` ;
  - `test_two_workers_never_claim_the_same_campaign` (Review Focus 5) ;
  - `test_worker_stops_on_signal`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 8 : Écran Recherche (C10 à C18, C16, C11)

**Files :** create `src/prospection/ui/routes_search.py`, `src/prospection/ui/templates/recherche.html` (remplacé), `_zone_choices.html`, `_estimate.html` ; tests `tests/ui/test_search_form.py`.

Écran conforme à la maquette 1 :
- nom ;
- métiers, avec les synonymes en puces retirables (HTMX) ;
- zone : ville avec choix de la commune si ambiguë (HTMX, `geo.api.gouv.fr`), départements, rayon ;
- nombre de qualifiés ;
- critères ;
- source : « Google Maps » seulement, avec « Entreprises récemment créées » affiché « bientôt » (lot 4) ;
- estimation « Coût estimé : 0 € (dans le quota gratuit de Google) » ou le montant ;
- option « Enregistrer comme modèle » et liste des modèles ;
- bouton « Lancer ».

Les erreurs de validation sont affichées au champ concerné (C17). « Lancer » crée la campagne et redirige vers le Suivi. Sans clé Google, « Lancer » est refusé avec le message C08.

- [ ] **Tests :**
  - `test_C17_errors_shown_per_field` ;
  - `test_C15_synonyms_listed_and_removable` ;
  - `test_C13_ambiguous_city_asks_to_choose` ;
  - `test_C16_estimate_shown_before_launch` ;
  - `test_C18_template_saved_and_reloaded` ;
  - `test_C08_launch_refused_without_google_key` ;
  - `test_launch_creates_campaign_and_redirects`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 9 : Écran Suivi en direct (C34, C35, C37, C119)

**Files :** create `src/prospection/ui/routes_campaign.py`, `src/prospection/ui/templates/suivi.html`, `_progress.html` ; tests `tests/ui/test_campaign_progress.py`.

Écran conforme à la maquette 2 :
- anneau « N sur M qualifiés » ;
- trouvés, exclus, dépensé ;
- étape en cours ;
- « Pourquoi exclus » ;
- derniers événements.

Le fragment `_progress.html` est rafraîchi toutes les 3 s (`hx-trigger="every 3s"`), seulement tant que la campagne tourne.

- Bouton « Arrêter (on garde les N) » (C35).
- Bouton « Appeler les N déjà prêts » vers `/prospects?campagne=ID` (C119 ; la liste arrive au lot 3).
- À la fin, la raison d'arrêt s'affiche en clair (C37).

- [ ] **Tests :**
  - `test_C34_progress_fragment_shows_counts` ;
  - `test_polling_stops_when_done` ;
  - `test_C35_stop_button` ;
  - `test_C37_end_reason_displayed` ;
  - `test_C119_call_ready_link`.
- [ ] Implémenter ; tout vert ; **commit**.

### Task 10 : Réglages des exclusions, parcours de bout en bout, README

**Files :** create `src/prospection/ui/templates/reglages_exclusions.html` (franchises perso et liste noire, un nom par ligne : C30, C33) ; `tests/e2e/test_parcours_campagne.py`, avec un faux Google servi par l'image de test via `GOOGLE_PLACES_BASE_URL`, réglage réservé aux tests et refusé si `BEHIND_PROXY=true` ; `README.md` (worker, quota gratuit).

- [ ] **Bout en bout :** lancer une campagne sur un faux Google. Le Suivi passe de 0 à N qualifiés, la raison d'arrêt s'affiche, et « Arrêter » fonctionne.
- [ ] CI verte ; **commit**.

### Task 11 : Pays francophones (C121 à C124), validée le 25/10/2026

**Files :** `src/prospection/data/pays.yaml` (code, nom, code région Google, indicatif) et un fichier de villes et provinces / cantons par pays (`data/zones_be.yaml`, `zones_ch.yaml`, `zones_lu.yaml`, `zones_mc.yaml`, source ouverte citée en tête de fichier) ; zones avec un champ `country` (migration 0004 encore modifiable : rien n'est en production) ; `google_search._body` (code région du pays de l'étape) ; `page_results._outside_zone` (pays, puis province / canton) ; `domain/phones.py` (BE, CH, LU, MC) ; formulaire Recherche (choix du pays, France par défaut).

- [ ] **Tests d'abord :** une zone « Liège (BE) » envoie `regionCode: BE` ; un établissement en France pour une zone belge est « Hors zone » ; « +32 470 12 34 56 » est un mobile ; le formulaire sans pays reste en France ; un modèle enregistré avant garde la France.
- [ ] Code minimal, lint, types, tests ; **commit** par comportement.

### Fin du lot

- [ ] Relecture finale (agent neuf, modèle le plus capable) et relecture sécurité ciblée : textes Google injectés, plafond, worker, réglage de test.
- [ ] Corrections (test d'abord), CI verte, pull request.
