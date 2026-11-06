# Mail d'audit, audit complet, formulaire de contact, activité Sirène · spec

Demandé le 04/11/2026 par le propriétaire (réponses données en une fois, feu vert pour coder ensuite). Comportements C137 à C150 de `COMPORTEMENTS.md`.

## Pourquoi

Sur la fiche d'un prospect, je veux un bouton qui prépare un **mail court** : les problèmes de son site, chacun relié à **son business** (clients perdus, confiance, données de ses clients, obligations légales), puis un lien vers mon portfolio et une proposition d'appel de 15 minutes. Je relis, je modifie si besoin, et j'envoie depuis mon Gmail. Pour que ce mail tienne la route, l'audit doit être **juste** (le formulaire de contact était souvent manqué) et **plus complet** (RGPD, sécurité, contact, autorité). Les entreprises trouvées dans Sirène doivent aussi être mieux décrites.

## Ce qui est décidé (par le propriétaire)

- Envoi depuis **Gmail** (`kapignolet18@gmail.com`), relié une fois à l'app.
- Bouton « Mail d'audit » → mail **pré-rédigé** (objet + texte), **modifiable**, puis bouton « Envoyer ».
- Mail **court et direct**, lien vers le **portfolio**, proposition d'un **appel de 15 minutes**, lien **Calendly** facultatif (pas encore créé : le champ reste vide tant qu'il n'existe pas).
- *(06/11/2026)* Mails **plus concis** ; l'appel à l'action devient « Pour plus d'infos, appelez-moi au … : je vous explique tout, c'est gratuit et sans engagement » (sans téléphone réglé : « répondez à ce mail »).
- Rédaction par **règles fixes** dans un fichier modifiable (`data/mail_rules.yaml`) : pour chaque problème, une phrase « problème → conséquence business → ce qu'il faudrait faire ».
- Chiffres donnés **en fourchette**, sans source citée.
- Après l'envoi : **rappel pour appeler** le prospect 1 à 3 jours plus tard (réglable).
- Lien **« ne plus recevoir de mails »** obligatoire.
- Audit complet : RGPD, sécurité, mobile et vitesse, visibilité (titre, description, **score d'autorité** via une API gratuite), contact, fraîcheur. Champ libre pour ajouter des points et pour le poids selon le métier.
- Formulaire : il doit être trouvé même sur la page Contact, et l'audit dit **où** il est (en haut de l'accueil, c'est le mieux pour un métier de service).
- Sirène : trouver **le maximum de détails** sur l'activité (champ libre).

## Ce qui est décidé par moi (Claude), à vérifier

1. **Cause du bug « pas de formulaire »** (les deux sites donnés ne sont pas joignables depuis mon environnement, diagnostic fait dans le code) :
   - seule la page d'accueil était lue : un formulaire sur `/contact` n'était jamais vu ;
   - la lecture s'arrêtait à 500 Ko : sur les pages lourdes (Elementor, Divi), le formulaire en bas de page était coupé ;
   - un champ « email » écrit en `type="text"` (Divi, vieux thèmes) ou un formulaire intégré depuis un service (Google Forms, Typeform, Jotform, HubSpot, Brevo, Tally…) n'était pas reconnu.
   → Lecture jusqu'à 1,5 Mo ; champs reconnus aussi par leur nom (`email`, `mail`, `telephone`, `message`…) ; services de formulaire reconnus ; si l'accueil n'a pas de formulaire, lecture de **2 pages au plus** du même site dont le lien parle de contact, devis, rendez-vous ou réservation, en **8 secondes au total** (un seul budget pour ces pages). Une page coupée sans formulaire visible donne « formulaire non vérifié », jamais « pas de formulaire ».
2. **Emplacement du formulaire** : « en haut de l'accueil » si moins d'un quart du texte de la page le précède, « plus bas sur l'accueil », « sur une page Contact » (petit problème : invisible depuis l'accueil), « aucun » (problème grave).
3. **Chaque problème d'audit a un code stable** (`no_https`, `no_form`…), gardé avec le texte. Les anciens audits sans code sont relus grâce à une table « début du texte → code » (lecture seulement).
4. **RGPD** : mentions légales absentes ; politique de confidentialité absente alors que le site collecte des données (formulaire ou traceurs) ; traceurs soumis au consentement (Google Analytics / Tag Manager, pixel Facebook, Hotjar, Clarity) chargés sans outil de consentement connu (tarteaucitron, Axeptio, Cookiebot, Didomi, OneTrust, Complianz, CookieYes, iubenda…, ou Consent Mode de Google). Matomo et Plausible ne sont pas comptés (exemptés possibles par la CNIL).
5. **Sécurité** : pas de HTTPS (et si un formulaire existe, ses messages circulent en clair) ; HTTPS cassé (certificat invalide : l'adresse https ne répond pas et la même en http répond) ; fichiers chargés en http sur une page https (déjà là) ; WordPress / PHP anciens (déjà là).
6. **Contact** : numéro affiché mais pas cliquable sur mobile (aucun lien `tel:`) ; pas de réservation en ligne pour les métiers où elle compte (restauration, coiffure, beauté, bien-être, santé, sport, auto-école, garage…, liste dans `site_signals.yaml`).
7. **Autorité** : Open PageRank (DomCop), gratuit avec une clé (Réglages → Clés). Note de 0 à 10, demandée seulement à l'ouverture du mail (une requête), gardée 30 jours par domaine. Sous 2/10 : « Site presque inconnu de Google ». Sans clé : le point est simplement absent.
8. **Ordre des points du mail** : les 3 problèmes au poids le plus fort, un bonus selon le métier (fichier de règles : santé, droit et chiffres → RGPD et sécurité d'abord ; restauration, beauté, bien-être → mobile et réservation d'abord ; bâtiment et dépannage → formulaire, mobile, numéro cliquable d'abord). Pas de point sans règle écrite. Aucun problème connu → pas de bouton (rien à dire).
9. **Gmail** : connexion OAuth Google (droit « envoyer des mails » seulement, plus l'adresse du compte). « Délier Gmail » retire aussi l'accès chez Google (révocation) ; si Google ne confirme pas, l'écran dit de le retirer sur myaccount.google.com/permissions. Identifiants de l'app Google dans les variables d'environnement (`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`) ; le jeton de connexion est **chiffré en base**. Envoi par l'API Gmail en HTTPS (Railway bloque l'envoi SMTP hors offre Pro). Adresse publique de l'app : `PUBLIC_URL`, sinon le domaine Railway (`RAILWAY_PUBLIC_DOMAIN`).
10. **Un seul mail d'audit par prospect** : une fois envoyé, la fiche affiche la date et le bouton disparaît. Mail en **texte simple**, accompagné de sa version HTML tirée du texte et entièrement échappée (Gmail recoupe les mails en texte simple vers 76 caractères ; seuls les liens deviennent cliquables). Destinataire : un email du prospect jugé valide ou pas encore vérifié (jamais invalide, douteux, inutile comme « noreply », ni désinscrit), au choix dans une liste.
11. **Désinscription** : ligne ajoutée en bas de chaque mail, **non modifiable**, avec un lien vers une page publique de l'app (sans connexion) ; un clic sur « Confirmer » bloque l'adresse **pour toujours**. Le blocage garde seulement l'empreinte de l'adresse (HMAC-SHA256 salée par une valeur tirée de `ENCRYPTION_KEY` : introuvable sans la clé de l'hébergeur), même après suppression du prospect (droit d'opposition). Une adresse désinscrite ne part plus non plus dans les exports CSV / Excel ni dans Notion. En-têtes `List-Unsubscribe` et `List-Unsubscribe-Post` (désinscription en un clic depuis Gmail). Cette page est la seule action acceptée hors de l'app (le jeton aléatoire de l'envoi sert de clé).
12. **Après l'envoi** : note datée « Mail d'audit envoyé à … » et action « Rappeler » dans N jours (1 à 3, 2 par défaut), qui remplace l'action prévue. Les notifications existantes (C108) font le rappel.
13. **Sirène** :
    - API Recherche d'entreprises (déjà utilisée, gratuite) : labels et compléments (RGE, Qualiopi, Bio, ESS, entreprise du patrimoine vivant, société à mission, organisme de formation, entrepreneur de spectacles, établissement de santé), nombre d'établissements ouverts, activité de l'établissement si différente.
    - Registre national des entreprises de l'INPI (gratuit, compte sur data.inpi.fr, identifiants saisis dans Réglages → Clés sous la forme `email:motdepasse`) : **objet social**, **description détaillée** de chaque activité, forme d'exercice (artisanale, commerciale, libérale…), **noms de domaine déclarés**. Fait par la tâche de fond, quelques entreprises à la fois.
14. **`CLAUDE.md`** : la règle « Aucun envoi de message » devient « un seul envoi : le mail d'audit, relu et envoyé par moi depuis la fiche ; jamais d'envoi automatique ni en masse ». Elle décrit ce que fait l'app, c'est pourquoi elle change.

## Limites connues

- Formulaires dessinés en JavaScript : reconnus à la trace exacte qu'ils laissent dans le HTML (classe du widget : Ninja Forms, Squarespace, Weebly, Jimdo, Webflow, Wix ; identifiant de l'application Wix Forms), sans lancer de navigateur. Un navigateur par site a été écarté : lourd sur Railway et risqué (il chargerait n'importe quelle adresse, y compris interne). Un formulaire sans aucune trace reste « non vérifié » si la page vient d'un constructeur connu.
- Open PageRank : service tiers gratuit, quota limité ; une panne n'empêche pas le mail.
- Gmail : tant que l'app Google est en mode « Test », Google coupe la connexion au bout de 7 jours. La passer « En production » (sans validation Google, un avertissement s'affiche à la connexion) supprime cette limite. Expliqué dans le guide de déploiement.
