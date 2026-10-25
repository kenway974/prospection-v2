# Lot 1 · Réglages et clés — plan de construction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** le propriétaire saisit une fois ses clés (Google, Notion, Sirène). Elles sont chiffrées en base, jamais réaffichées, et chacune a un bouton « Tester » avec un message clair. Il choisit son CRM (Notion ou aucun) et sa base Notion, fixe son budget Google mensuel, et l'app dit quand une clé manque.

**Architecture :**
- Les clés sont chiffrées (Fernet) par `storage/` avec la clé `ENCRYPTION_KEY`, qui vient seulement de l'environnement.
- Les tests de clé appellent les vraies API via `sources/` (Google Places, INSEE) et `crm/` (Notion), avec un client `httpx` injecté. Dans les tests, ce client est remplacé par un faux (`httpx.MockTransport`), donc aucun réseau.
- `application/` orchestre. `ui/` affiche, avec HTMX pour le bouton « Tester ».

**Tech Stack :** celle du lot 0, plus `cryptography` (Fernet) et `httpx` (dépendance de production).

**Spec :** `docs/superpowers/specs/2026-10-24-prospection-v2-design.md` (sections 4, 7, 10, base Notion « Prospects v2 »). Feuille de route : `docs/superpowers/plans/2026-10-24-feuille-de-route.md`.

## Global Constraints

Celles du lot 0 (`docs/superpowers/plans/2026-10-24-lot-0-socle.md`), plus :
- **Une clé n'apparaît jamais en clair** après sa saisie : ni dans une page, ni dans un journal, ni dans un message d'erreur, ni dans une exception. L'écran montre seulement « Enregistrée le JJ/MM/AAAA » et le résultat du dernier test.
- `ENCRYPTION_KEY` (clé Fernet) vient seulement de l'environnement, jamais de la base. Si elle manque ou est invalide, l'app refuse de démarrer avec un message qui nomme la variable.
- Les appels réseau des tests de clé ont un délai de **10 s** et ne suivent pas les redirections.
- Les tests de clé choisissent des appels **gratuits** :
  - Google : Text Search (New) avec le masque de champs `places.id` (palier « IDs Only », sans coût) ;
  - Notion : `GET /v1/users/me` ;
  - INSEE : `GET /api-sirene/3.11/informations`.
- Version d'API Notion épinglée : `2022-06-28`. Réponses externes validées (pydantic) avant usage.

## Review Focus

1. **Clé collée avec des espaces ou un retour à la ligne** (copier-coller depuis le téléphone) : elle est nettoyée avant d'être chiffrée et testée. → Task 2.
2. **Session expirée pendant un clic sur « Tester »** (requête HTMX) : l'app renvoie vers la connexion (`HX-Redirect`) au lieu d'insérer la page de connexion dans le bloc. → Task 4.
3. **API qui répond n'importe quoi** (HTML, JSON inattendu, 500) : message « réponse inattendue, réessayez plus tard », jamais une erreur 500 de l'app. → Task 3.
4. **Clé enregistrée puis `ENCRYPTION_KEY` changée** : l'écran dit « Clé illisible : saisissez-la à nouveau » au lieu de planter. → Task 1 et Task 2.
5. **Budget saisi avec une virgule (« 12,50 »), à zéro ou négatif** : la virgule est acceptée ; zéro et le négatif sont refusés avec un message. → Task 6.

---

### Task 1 : Chiffrement des clés en base (C85, C86)

**Files :** create `src/prospection/storage/secret_box.py`, `src/prospection/storage/api_keys.py`, `src/prospection/storage/migrations/versions/0003_api_keys_and_settings.py` ; modify `src/prospection/config.py`, `src/prospection/storage/db.py`, `src/prospection/cli.py`, `.env.example` ; tests `tests/storage/test_secret_box.py`, `tests/storage/test_api_keys.py`, `tests/test_config.py`, `tests/test_cli_migrate.py`.

**Interfaces :**
- `Settings.encryption_key: SecretStr`, validée comme une clé Fernet ; l'erreur nomme `ENCRYPTION_KEY`.
- `enum Service { GOOGLE = "google", NOTION = "notion", INSEE = "insee" }` dans `domain/services.py` (libellés : « Google Maps », « Notion », « Sirène (INSEE) »).
- `SecretBox(key: str)` avec `encrypt(plain: str) -> bytes` et `decrypt(token: bytes) -> str`, qui lève `UnreadableSecret` si le jeton est illisible.
- Table `api_keys(service text pk, ciphertext bytea not null, saved_at timestamptz not null, tested_at timestamptz null, test_ok boolean null, test_message text null)`.
- Table `app_settings(id smallint pk check (id = 1), crm text not null default 'none', notion_database_id text null, notion_database_title text null, google_budget_cents integer null)`, avec sa ligne unique insérée par la migration.
- Fonctions :
  - `save_key(conn, service, ciphertext, now) -> None` (remet le dernier test à zéro) ;
  - `load_key(conn, service) -> StoredKey | None`, où `StoredKey(service, ciphertext, saved_at, tested_at, test_ok, test_message)` ;
  - `record_test(conn, service, now, ok, message) -> None` ;
  - `delete_key(conn, service) -> None`.
- Commande CLI `generate-encryption-key` : affiche une clé Fernet neuve, à coller dans `ENCRYPTION_KEY`.

- [ ] **Tests qui échouent :**
  - `test_C85_ciphertext_does_not_contain_the_key` : chiffrer `"AIza-secret-123"` donne des octets qui ne le contiennent pas, et le déchiffrement redonne la valeur.
  - `test_C85_wrong_key_raises_unreadable` : chiffré avec la clé A, déchiffré avec la clé B → `UnreadableSecret`.
  - `test_C86_encryption_key_comes_from_environment_only` : sans `ENCRYPTION_KEY`, `load_settings` lève une erreur qui la nomme ; une valeur qui n'est pas une clé Fernet est refusée.
  - `test_C85_stored_key_is_encrypted_in_database` : après `save_key`, la colonne `ciphertext` lue en SQL brut ne contient pas la clé en clair.
  - `test_record_and_reset_test_result`.
  - `test_cli_generates_a_valid_fernet_key`.
  - Mettre à jour les tests existants qui construisent `Settings`.
- [ ] Lancer → échec. Implémenter. Migration testée dans les deux sens (le test existant couvre `head`). Lint, types, couches, tests verts.
- [ ] **Commit** `feat(stockage): clés API chiffrées en base, clé de chiffrement dans l'environnement (C85, C86)`.

### Task 2 : Saisie des clés, jamais réaffichées (C02, C04)

**Files :** create `src/prospection/application/api_keys.py`, `src/prospection/ui/routes_settings.py`, `src/prospection/ui/templates/reglages.html`, `src/prospection/ui/templates/reglages_cles.html`, `src/prospection/ui/templates/_cle.html` ; modify `src/prospection/ui/app.py`, `src/prospection/ui/templates/aujourdhui.html` (l'icône Réglages mène à `/reglages`) ; tests `tests/application/test_api_keys.py`, `tests/ui/test_settings_keys.py`.

**Interfaces :**
- `KeyStatus(service: Service, saved_at: datetime | None, readable: bool, tested_at: datetime | None, test_ok: bool | None, test_message: str | None)`.
- `key_statuses(engine, box) -> list[KeyStatus]`, toujours dans l'ordre GOOGLE, NOTION, INSEE.
- `store_key(engine, box, service, raw: str, now) -> None` : enlève les espaces et les retours à la ligne ; une valeur vide lève `EmptyKey`.
- `read_key(engine, box, service) -> str | None` (usage interne seulement).
- `remove_key(engine, service) -> None`.
- Routes protégées :
  - `GET /reglages` : liste « Clés API », « CRM », « Budget Google », « Connexions » ;
  - `GET /reglages/cles` ;
  - `POST /reglages/cles/{service}` (champ `cle`, `type="password"`, `autocomplete="off"`), qui redirige en 303 vers `/reglages/cles` ;
  - `POST /reglages/cles/{service}/supprimer`.
  - Un service inconnu donne 404.
- Chaque clé est affichée dans un bloc qui contient, au choix :
  - « Pas encore saisie » ;
  - « Enregistrée le 25/10/2026 » ;
  - « Clé illisible : saisissez-la à nouveau ».

  Le bloc contient aussi le champ « Nouvelle clé », le bouton « Enregistrer » et, si une clé est enregistrée, « Tester » et « Supprimer ».

- [ ] **Tests qui échouent :**
  - `test_C02_key_is_saved_once_and_status_shown` : POST de la clé, puis GET : « Enregistrée le » est présent et la clé n'apparaît **nulle part** dans le HTML.
  - `test_C04_key_never_in_page_logs_or_redirect` : avec `caplog` en niveau DEBUG, la clé n'apparaît ni dans les journaux, ni dans l'en-tête `Location`, ni dans le corps.
  - `test_C02_pasted_key_is_trimmed` (Review Focus 1) : `"  AIza-123\n"` est enregistrée comme `"AIza-123"`.
  - `test_C02_empty_key_is_refused` : message « Collez la clé avant d'enregistrer. »
  - `test_unreadable_key_asks_to_retype` (Review Focus 4).
  - `test_remove_key`.
  - `test_unknown_service_is_404`.
- [ ] Lancer → échec. Implémenter. Tout vert.
- [ ] **Commit** `feat(réglages): saisie des clés, jamais réaffichées (C02, C04)`.

### Task 3 : Vérification des clés auprès des vraies API (C03)

**Files :** create `src/prospection/sources/http.py`, `src/prospection/sources/google_places.py`, `src/prospection/sources/insee.py`, `src/prospection/crm/notion.py`, `src/prospection/domain/key_check.py` ; tests `tests/sources/test_google_key_check.py`, `tests/sources/test_insee_key_check.py`, `tests/crm/test_notion_key_check.py`.

**Interfaces :**
- `KeyCheck(ok: bool, message: str)` dans `domain/key_check.py` (contrat commun aux trois couches).
- `make_client() -> httpx.Client` : délai de 10 s, `follow_redirects=False`.
- `check_google_key(client, key) -> KeyCheck` : `POST https://places.googleapis.com/v1/places:searchText`, en-têtes `X-Goog-Api-Key` et `X-Goog-FieldMask: places.id`, corps `{"textQuery": "mairie Paris"}`.
- `check_insee_key(client, key) -> KeyCheck` : `GET https://api.insee.fr/api-sirene/3.11/informations`, en-tête `X-INSEE-Api-Key-Integration`.
- `check_notion_token(client, token) -> KeyCheck` : `GET https://api.notion.com/v1/users/me`, en-têtes `Authorization: Bearer …` et `Notion-Version: 2022-06-28`.
- Messages (exacts) :

| Cas | Message |
|---|---|
| Google, 200 | « Clé Google valide. » |
| Google, 400 avec `API_KEY_INVALID` | « Clé refusée par Google : vérifiez qu'elle est copiée en entier. » |
| Google, 403 | « Google refuse l'accès : activez « Places API (New) » et la facturation dans Google Cloud. » |
| INSEE, 200 | « Clé Sirène valide. » |
| INSEE, 401 ou 403 | « Clé refusée par l'INSEE : vérifiez-la sur portail-api.insee.fr et que l'application est abonnée à l'API Sirene. » |
| Notion, 200 | « Jeton Notion valide. » |
| Notion, 401 | « Jeton refusé par Notion : copiez le « secret » de votre intégration. » |
| Délai dépassé ou réseau | « {Service} ne répond pas. Réessayez dans un instant. » |
| Tout autre statut, ou réponse illisible | « Réponse inattendue de {Service}. Réessayez plus tard. » |

- **Jamais** la clé, la réponse brute ni l'URL complète dans un message ou un journal.

- [ ] **Tests qui échouent** (faux transport `httpx.MockTransport`), pour chaque service :
  - `test_C03_valid` ;
  - `test_C03_refused` ;
  - `test_C03_timeout` (le transport lève `httpx.ConnectTimeout`) ;
  - `test_C03_unexpected_html` (Review Focus 3).

  Plus, pour chaque service, un test qui vérifie les en-têtes et le corps exacts envoyés, et `test_C03_google_403_explains_api_activation`.
- [ ] Lancer → échec. Implémenter. Couches : `sources` et `crm` importent seulement `domain`. Tout vert.
- [ ] **Commit** `feat(sources): vérification des clés Google, INSEE et Notion (C03)`.

### Task 4 : Bouton « Tester » avec HTMX, session expirée gérée (C03)

**Files :** create `src/prospection/application/key_tests.py` ; modify `src/prospection/ui/routes_settings.py`, `src/prospection/ui/errors.py`, `src/prospection/ui/deps.py` ; tests `tests/application/test_key_tests.py`, `tests/ui/test_settings_test_button.py`, `tests/ui/test_htmx_session.py`.

**Interfaces :**
- `run_key_test(engine, box, service, client, now) -> KeyCheck` : lit la clé, appelle le vérificateur du service, enregistre le résultat. Sans clé : `KeyCheck(False, "Aucune clé enregistrée.")`. Clé illisible : `KeyCheck(False, "Clé illisible : saisissez-la à nouveau.")`.
- Dépendance `get_http_client() -> httpx.Client`, remplacée dans les tests.
- `POST /reglages/cles/{service}/tester`, avec `hx-post`, `hx-target` sur le bloc de la clé et `hx-swap="outerHTML"`. La route renvoie le fragment `_cle.html` mis à jour, avec le message dans `role="status"`, et « Test en cours… » affiché pendant la requête (indicateur HTMX).
- Le gestionnaire `LoginRequired` renvoie un `200` vide avec l'en-tête `HX-Redirect: /connexion?suite=…` quand la requête porte `HX-Request: true`, et un 303 sinon.

- [ ] **Tests qui échouent :**
  - `test_C03_test_button_shows_result_and_records_it` ;
  - `test_C03_test_without_key` ;
  - `test_C04_test_result_never_contains_key` ;
  - `test_htmx_request_with_expired_session_gets_hx_redirect` (Review Focus 2) ;
  - `test_plain_request_with_expired_session_still_303`.
- [ ] Lancer → échec. Implémenter. Tout vert.
- [ ] **Commit** `feat(réglages): bouton Tester pour chaque clé (C03)`.

### Task 5 : Choix du CRM et de la base Notion (C05, C06, C09)

**Files :** create `src/prospection/storage/app_settings.py`, `src/prospection/application/crm_settings.py`, `src/prospection/ui/templates/reglages_crm.html` ; modify `src/prospection/crm/notion.py`, `src/prospection/ui/routes_settings.py` ; tests `tests/storage/test_app_settings.py`, `tests/crm/test_notion_databases.py`, `tests/application/test_crm_settings.py`, `tests/ui/test_settings_crm.py`.

**Interfaces :**
- `AppSettings(crm: Crm, notion_database_id: str | None, notion_database_title: str | None, google_budget_cents: int | None)`, avec `enum Crm { NONE = "none", NOTION = "notion" }`.
- `load_app_settings(conn) -> AppSettings` et `save_crm(conn, crm, database_id, database_title) -> None`.
- `list_notion_databases(client, token) -> list[NotionDatabase(id: str, title: str)]` : `POST https://api.notion.com/v1/search`, corps `{"filter": {"property": "object", "value": "database"}}`, réponse validée par pydantic, titres en texte brut, triés.
- Écran `GET /reglages/crm` : choix « Notion » ou « Aucun (export fichier seulement) ».
  - Si Notion est choisi et le jeton enregistré : liste des bases partagées avec l'intégration. « Prospects v2 » est présélectionnée si elle existe.
  - Si la liste est vide : « Aucune base visible : dans Notion, ouvrez « Prospects v2 », menu ••• → Connexions → ajoutez votre intégration. »
- `POST /reglages/crm` : refuse Notion sans base choisie, avec le message « Choisissez la base Notion de destination. »
- C09 : choisir « Aucun » est enregistré et l'app reste utilisable.

- [ ] **Tests qui échouent :**
  - `test_C05_choose_notion_or_none` ;
  - `test_C06_databases_listed_and_prospects_v2_preselected` ;
  - `test_C06_no_database_explains_sharing` ;
  - `test_C06_notion_without_database_refused` ;
  - `test_C09_none_is_saved_and_pages_still_work` ;
  - `test_notion_search_response_validated` (JSON inattendu donne « Réponse inattendue de Notion »).
- [ ] Lancer → échec. Implémenter. Tout vert.
- [ ] **Commit** `feat(réglages): choix du CRM et de la base Notion (C05, C06, C09)`.

### Task 6 : Budget Google mensuel et clé Google manquante (C07, C08)

**Files :** create `src/prospection/domain/budget.py`, `src/prospection/ui/templates/reglages_budget.html` ; modify `src/prospection/storage/app_settings.py`, `src/prospection/ui/routes_settings.py`, `src/prospection/ui/routes_pages.py`, `src/prospection/ui/templates/recherche.html` ; tests `tests/domain/test_budget.py`, `tests/ui/test_settings_budget.py`, `tests/ui/test_missing_google_key.py`.

**Interfaces :**
- `parse_budget(text: str) -> int`, en centimes. Accepte « 25 », « 12,50 » et « 12.50 ».
  - Une valeur nulle ou négative lève `InvalidBudget("Indiquez un montant supérieur à 0 €.")`.
  - Plus de 1 000 € lève `InvalidBudget("Le budget mensuel est limité à 1 000 €.")`.
  - Un texte illisible lève `InvalidBudget("Indiquez un montant en euros, par exemple 25 ou 12,50.")`.
- `remaining_cents(budget_cents: int, spent_cents: int) -> int` (jamais négatif). Il sera utilisé au lot 2 pour refuser tout appel payant au-delà du budget.
- `save_budget(conn, cents) -> None`.
- `GET` et `POST /reglages/budget`, avec le montant affiché « 25,00 € ».
- C08 : l'écran Recherche affiche, sans clé Google : « Ajoutez votre clé Google dans Réglages pour chercher sur Google Maps. Les entreprises récemment créées restent disponibles. », avec un lien vers `/reglages/cles`. Sans budget défini : « Fixez un budget Google mensuel avant de lancer une recherche Google Maps. »

- [ ] **Tests qui échouent :**
  - `test_C07_budget_parsing` (paramétré, Review Focus 5) ;
  - `test_C07_remaining_never_negative` ;
  - `test_C07_budget_saved_and_displayed` ;
  - `test_C08_search_screen_says_google_key_missing` ;
  - `test_C08_message_disappears_when_key_saved`.
- [ ] Lancer → échec. Implémenter. Tout vert.
- [ ] **Commit** `feat(réglages): budget Google mensuel et clé Google manquante signalée (C07, C08)`.

### Task 7 : Documentation et parcours de bout en bout

**Files :** modify `README.md` (variables `ENCRYPTION_KEY`, où trouver chaque clé : Google Cloud Console → API Places (New) ; Notion → Intégrations → secret, et partage de « Prospects v2 » ; portail-api.insee.fr → application abonnée à Sirene), `.github/workflows/ci.yml` (`ENCRYPTION_KEY` pour l'étape 7) ; create `tests/e2e/test_parcours_reglages.py`.

- [ ] **Test de bout en bout qui échoue** `test_C02_C04_save_key_then_never_shown` : connexion, Réglages → Clés API, coller une fausse clé Google, Enregistrer ; « Enregistrée le » est visible et la valeur n'apparaît pas dans la page.
- [ ] Construire l'image, lancer les tests de bout en bout. Tout vert, CI verte.
- [ ] **Commit** `docs: réglages et clés dans le README ; parcours de bout en bout (C02, C04)`.

### Fin du lot

- [ ] Une relecture finale (agent neuf, modèle le plus capable), plus une relecture de sécurité ciblée sur les Tasks 1 à 4 (secrets).
- [ ] Corrections (test d'abord) ; CI verte ; pull request ; validation du propriétaire.
