# Lot 6 · Contact et préparation de l'appel (plan court)

Comportements : C53 à C60, C110 à C112.

Briques reprises de `prospection-bot` (version 530ba12), relues et améliorées :
- `services/email_check.py` : syntaxe, adresses « ne pas répondre » ou factices, fautes de frappe des grands fournisseurs, adresses jetables, serveur mail (MX). Listes déplacées dans un fichier de données ;
- `services/opportunity.py` : score d'opportunité expliqué ligne par ligne, adapté aux données de la v2 (rapport du site, registre, avis) ;
- `services/linkedin.py::people_search_url` : lien de **recherche** LinkedIn (aucune lecture de LinkedIn, règle 2).

## Décisions (écrites, à valider)

- **Serveur mail (MX)** : vérifié par la tâche de fond avec `dnspython` (nouvelle dépendance, pure Python, très répandue ; la bibliothèque standard ne sait pas lire un MX). Le résultat est gardé par domaine, en base, pour 30 jours. Pas de sonde SMTP (port 25 fermé sur Railway, peu fiable, risque de liste noire). Aucun tiers interrogé : le résolveur DNS du serveur.
- **Rythme des avis** (C112) : les dates des avis demandent un champ Google plus cher (palier « Atmosphere »). Non demandé (budget à 0 €) : on montre le nombre d'avis et la note ; le rythme est dit « non disponible ».
- **Confiance par information** (C60) : « sûr » = source officielle ou fiche Google ; « probable » = déduit avec une confirmation forte (site retrouvé, email avec serveur mail) ; « à vérifier » = rapprochement incertain, homonyme possible, email douteux.
- **Fiche « Pour l'appel »** (C110, C111) : règles fixes dans `data/call_rules.yaml` (schéma strict, une règle invalide fait échouer le démarrage et les tests). 1 accroche et 3 douleurs au plus, triées par priorité, toujours « indices à confirmer ».

## Architecture

| Couche | Fichier | Rôle |
|---|---|---|
| domain | `email_check.py` (+ `data/email_rules.yaml`) | Email : syntaxe, factice, jetable, faute de frappe, générique ou nominatif (C53, C54) |
| domain | `signals.py` | Signaux d'un prospect (site, avis, création, effectif, horaires…) tirés des données déjà gardées |
| domain | `opportunity.py` | Score sur 100 et détail du calcul (C57) |
| domain | `qualification.py` | Raison lisible (C58), confiance par information (C60), drapeaux (C59) |
| domain | `call_sheet.py` (+ `data/call_rules.yaml`) | Accroche et douleurs (C110, C111) |
| domain | `health.py` | Indices de santé (C112) |
| sources | `mail_domain.py` | Serveur mail d'un domaine (MX), résolveur avec délai |
| storage | migration 0008 | `mail_domains` (domaine, statut, date) |
| application | `mail_check.py` | La tâche de fond vérifie les domaines des emails pas encore vus |
| ui | fiche, liste | Score et raison dans la liste ; blocs « Pour l'appel », « Santé », contacts avec statut, mobile/fixe (C55), lien LinkedIn du dirigeant (C56) |
