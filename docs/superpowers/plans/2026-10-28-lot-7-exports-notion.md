# Lot 7 · Exports et Notion (plan court)

Comportements : C62 à C75, C89, C118, C32 (reporté du lot 2).

Briques reprises de `prospection-bot` (version 530ba12), relues et améliorées :
- `main.py::save_csv` : CSV en `utf-8-sig` (accents corrects dans Excel) ;
- `app.py` (export Excel) : `openpyxl`, en-tête coloré, largeurs, volet figé, score coloré ;
- `services/crm/notion.py` : `clean_database_id`, aides de propriétés (`_title`, `_rich_text`, `_phone`, `_email_prop`, `_url_prop`), messages d'erreur 401 / 404 qui disent quoi faire, recherche de doublon avant création, mise à jour par `PATCH /pages/{id}`.
Améliorations : textes neutralisés contre les formules (C89, absent de l'ancien code) ; ne jamais écraser une saisie manuelle (C70) ; envoi par la tâche de fond avec reprise après panne et respect des limites (C73, C75) ; doublon cherché par « ID app » puis SIREN (l'ancien cherchait par nom et téléphone).

## Décisions (écrites, à valider)

- **CSV** : séparateur « ; » (Excel en français l'attend), `utf-8-sig`. Deux fichiers : prospects et exclus (C65). Excel : un fichier, deux onglets.
- **Nouvelle dépendance** : `openpyxl` (déjà utilisée par l'ancienne app ; écrire du .xlsx à la main serait fragile).
- **Exports passés (C66)** : régénérés à la demande depuis la base (rien de stocké, toujours à jour) ; liens sur chaque campagne.
- **ID app** = identifiant Google de l'établissement (ou `siren:…` pour une entreprise hors Maps) : stable d'une campagne à l'autre, donc un même établissement n'est jamais recréé (C69).
- **Ne pas écraser (C70)** : l'app n'écrit que ses colonnes, et seulement si la cellule est vide ou porte encore la valeur que l'app y avait mise (valeurs envoyées gardées en base) ; « Notes perso » jamais ; « Statut CRM » seulement à la création (« Nouveau »).
- **Envoi** : le bouton « Exporter » met les prospects cochés en file ; la tâche de fond les envoie (≈ 3 requêtes par seconde au plus, `Retry-After` respecté) ; panne ou 429/5xx : réessai plus tard ; refus (400) : en échec avec la raison. Après succès, statut « exporté ».
- **Déjà dans le CRM (C32)** : la tâche de fond relit la base Notion toutes les heures (ID app, SIREN, nom) ; un établissement déjà présent est exclu des campagnes avec la raison « Déjà dans le CRM ».

## Architecture

| Couche | Fichier | Rôle |
|---|---|---|
| domain | `sheet_safe.py` | Cellule neutralisée (formules, caractères de contrôle) |
| domain | `export_rows.py` | Colonnes et lignes de l'export (prospects triés par score, exclus avec raison) |
| domain | `crm_record.py` | Propriétés Notion d'un prospect ; fusion sans écraser (C70) |
| crm | `notion_pages.py` | Chercher, lire, créer, mettre à jour une page ; erreurs typées |
| storage | migration 0009 | `crm_exports` (file, page, valeurs envoyées, erreur) ; `crm_index` (C32) |
| application | `file_export.py`, `crm_export.py`, `crm_index.py` | Fichiers ; file d'envoi ; relecture du CRM |
| ui | campagne, écran « Exporter », fiche | Liens de téléchargement ; relecture avant envoi ; bilan ; lien vers la fiche Notion |
