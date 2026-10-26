# Lot 3 · Suivi des appels — plan court

Comportements : C61, C102 à C107, C109, C120. C108 (notifications) reste au lot 9.

## Données (migration 0005)
- `prospects` : + `contact_name`, `contact_mobile`, `contact_email`, `updated_at`.
- `prospect_notes` : `id`, `prospect_id`, `created_at`, `text` (≤ 2 000 caractères).
- `prospect_actions` : `id`, `prospect_id`, `kind` (rappeler, devis, rendez-vous, passer), `due_date`, `due_time` (facultative), `created_at`, `done_at`. Une seule action ouverte par prospect (index unique partiel).
- `call_session` : une ligne (filtre statut + recherche, prospect courant) pour reprendre la session (C109).

## Domaine (pur)
- `domain/call_status.py` : statuts, libellés, action proposée (« à rappeler » ou « messagerie » → Rappeler demain).
- `domain/agenda.py` : `(actions, maintenant, fuseau) → en retard / aujourd'hui / demain`, triés par heure.
- `domain/contact.py` : validation du contact (mobile via phonenumbers, email simple, longueurs).

## Écrans
- **Prospects** (C61, C120) : recherche (nom, ville, métier), filtres par statut avec compteurs, « Démarrer la session d'appel ».
- **Fiche / session** (C102 à C106, C109) : précédent / suivant et position (4 / 12) dans la file filtrée ; Appeler (`tel:` nettoyé), fiche Google ; statut en un geste ; prochaine action ; notes datées ; contact modifiable. Chaque saisie part tout de suite (HTMX) ; refus serveur = message au champ, saisie gardée ; coupure réseau = message global (app.js), saisie gardée.
- **Aujourd'hui** (C107) : en retard, aujourd'hui, demain ; cocher termine l'action ; session à reprendre.

## Décisions
- File triée par date de qualification tant que le score d'opportunité n'existe pas (lot 6) ; le tri passera au score ensuite.
- Seuls les prospects qualifiés sont dans la liste ; les exclus restent visibles dans le suivi de campagne.

## Après relecture (18 constats, tous traités)
- Session : file figée au démarrage (`call_session.queue`), seule une fiche ouverte depuis la session (`?session=1`) la met à jour.
- « Rappeler demain » est proposé dans le formulaire, plus créé d'office.
- Action et contact s'enregistrent au changement ; la note au bouton, avec avertissement avant de quitter une saisie non enregistrée ; bandeau collant, message différent pour une coupure réseau et pour une erreur du serveur.
- Tri (C61) : ordre de la recherche, nom, ville ; le score s'ajoutera au lot 6.
- Reportés, écrits ici : note courte et activité de fond sur Aujourd'hui (lot 9), recherche du dirigeant (lot 6), ville et distance sur la fiche (lot 8). Une session expirée pendant une saisie renvoie à la connexion (saisie perdue) : accepté, la session dure 30 jours.
