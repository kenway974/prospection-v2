# Envoi groupé du mail d'audit, accroche tirée de l'audit, ordre des points, site vérifié, SMS · spec

Demandé le 10/11/2026 par le propriétaire. Comportements C168 à C181 de `COMPORTEMENTS.md`
(ajoutés après validation de cette spec).

## Pourquoi

Envoyer le mail d'audit à toute une sélection depuis la page Prospects, comme on la supprime
aujourd'hui, avec une première phrase qui pointe le vrai problème du site et des points rangés
du plus important au moins important. Doubler chaque mail d'un SMS court. Et ne plus auditer
le site d'une plateforme ou d'un réseau à la place de celui de l'entreprise.

## Ce qui est décidé (par le propriétaire)

- **Envoi direct, sans relecture**, depuis la sélection de la page Prospects. Le script sera
  affiné au fil du temps pour limiter les erreurs. La règle de `CLAUDE.md` change en
  conséquence (« jamais d'envoi en masse » → envoi groupé possible, espacé et plafonné).
- **Délai entre deux mails** et **plafond par jour**.
- Prospects non contactables **écartés, avec leur raison** (pas d'email valide, déjà envoyé,
  désinscrit, pas d'audit). Chaque envoi fait comme l'envoi depuis la fiche (C146, C147) :
  versions qui tournent, lien de désinscription, note datée, rappel.
- **Accroche** : une phrase **courte et directe** qui pointe le problème, **sans accuser ni
  accabler** le travail déjà fait, sur un ton **B2B** : je viens apporter de la valeur.
- **Ordre des points** : 1. légal, 2. clients perdus (référencement compris), 3. suivi des
  performances, 4. le reste.
- **Site d'un tiers** : à corriger si possible, sans exemple fourni (sinon, laisser tomber).
- **Nom d'expéditeur des SMS** : « Kenny ».
- **SMS** : un compte **Brevo**, qui facture les SMS. Envoyé **avec le mail**, structure courte
  de type AIDA (attention, intérêt, désir, action), trois versions :
  1. mail envoyé → « plus de détails dans le mail que je viens de vous envoyer » ;
  2. mail refusé → « répondez pour plus de détails », et dire que son adresse ne reçoit pas
     les mails. *(10/11/2026)* Le dirigeant doit **toujours** savoir que son mail est bloqué,
     même si le refus arrive après coup ;
  3. pas d'adresse trouvée → « répondez pour plus de détails ».

## Ce qui est décidé par moi (Claude), à vérifier

### Envoi groupé (C168 à C170)

1. **Bouton « Envoyer le mail d'audit »** à côté de « Supprimer » sur la page Prospects, même
   sélection (même nombre maximum). L'écran de confirmation dit, pour chaque prospect, si le
   mail part, si le SMS part, et sinon pourquoi. Un clic sur « Envoyer » met tout **en file** :
   rien ne part depuis l'interface (travail long en tâche de fond).
2. **File d'envoi** (nouvelle table, migration numérotée et testée) traitée par la tâche de
   fond : **un envoi toutes les 60 à 120 secondes** (durée tirée au hasard, pour ne pas
   ressembler à un robot), **plafond de 30 mails par jour** par défaut, réglable dans
   Réglages → Mail. Ce qui dépasse le plafond part les jours suivants.
3. **Heures d'envoi** : du lundi au vendredi, de 9 h à 19 h (heure de Paris), pour les mails
   comme pour les SMS. Un mail de prospection reçu à 3 h du matin trahit l'automate.
4. La page Suivi montre la file : en attente, envoyé, échec (avec la raison). Une ligne en
   attente peut être annulée.
5. Au moment de l'envoi, tout est revérifié (un prospect désinscrit entre-temps n'est pas
   contacté). Un refus de Gmail marque la ligne « échec » ; trois refus de suite arrêtent la
   file et le disent (compte Gmail délié, quota atteint…).
6. Un prospect dont le site n'est pas confirmé (point C174) est **écarté** de l'envoi groupé :
   « site à vérifier ». Il reste envoyable depuis la fiche, après relecture.

### Accroche tirée de l'audit (C171)

7. L'accroche vient du **premier point du mail** (le plus important après le tri du point 9).
   Pour chaque code de problème, une ou plusieurs phrases dans `mail_rules.yaml`
   (`accroches_audit`), qui tournent comme les autres versions et sont comptées dans la page
   Stats. Faute de phrase pour ce point, l'accroche actuelle (note Google, ancienneté…) reste.
8. Style imposé *(10/11/2026)* : **phrase choc, 10 mots au plus, en MAJUSCULES** (accents
   gardés), le constat et ce qu'il coûte, jamais « votre site est mauvais ». Les textes sont
   écrits normalement dans le fichier ; l'app les met en majuscules (réglage
   `accroche_majuscules`, activé) et refuse de démarrer si une accroche dépasse 10 mots.
   Exemples :
   - `no_legal_notice` : « MENTIONS LÉGALES ABSENTES : JUSQU'À 75 000 € D'AMENDE. »
   - `no_privacy_policy` : « VOUS COLLECTEZ DES DONNÉES SANS POLITIQUE DE CONFIDENTIALITÉ. »
   - `no_form` : « LE SOIR, VOS CLIENTS NE PEUVENT PAS VOUS ÉCRIRE. »
   - `form_basic` : « VOTRE FORMULAIRE NE DIT PAS CE QUE VEUT LE CLIENT. »
   - `no_https` : « VOS VISITEURS VOIENT « NON SÉCURISÉ » EN ARRIVANT. »
   - `slow_mobile` : « SUR MOBILE, VOS VISITEURS PARTENT AVANT L'AFFICHAGE. »
   - `no_tracking` : « COMBIEN DE CLIENTS VOUS AMÈNE VOTRE SITE ? MYSTÈRE. »
   Risque connu : un texte en majuscules fait partie des signaux que regardent les filtres
   anti-spam. Une seule ligne courte limite ce risque ; la page Stats dira si le taux de
   réponse baisse, et le réglage permet de revenir en arrière en un clic.

### Ordre des points (C172)

9. Chaque point de `mail_rules.yaml` reçoit une **catégorie** : `legal`, `clients`, `suivi`,
   `autre`. Le mail prend les points dans cet ordre de catégories, puis du plus lourd au plus
   léger dans une même catégorie (poids + bonus du métier). Trois points au plus, comme
   aujourd'hui.
10. Rangement : **légal** = mentions légales, confidentialité, cookies, formulaire sans accord
    RGPD ; **clients** = pas de formulaire, demande de devis incomplète, formulaire enterré,
    HTTPS absent ou cassé (fait fuir les visiteurs), mobile, lenteur, réservation, numéro non
    cliquable, référencement (peu de texte, titre, description, page invisible pour Google,
    autorité faible), contenu JavaScript, simulateur ; **suivi** = aucun outil de mesure,
    ancien Google Analytics ; **autre** = réseaux sociaux, site pas mis à jour, technologie
    vieillissante.

### Site vraiment celui de l'entreprise (C173, C174)

11. Le site donné par la fiche Google est aussi **vérifié**, comme un site deviné : il doit
    citer le nom, le téléphone ou l'adresse de l'entreprise (page d'accueil, page lue par le
    navigateur pour un site JavaScript, ou page Contact). Sinon, la fiche dit « Site à
    vérifier : il ne parle pas de cette entreprise (plateforme, réseau ou hébergeur ?) ». Le
    rapport est gardé, mais le prospect est écarté de l'envoi groupé (point 6).
12. **Domaine partagé** : un même nom de domaine trouvé chez **3 entreprises différentes ou
    plus** (noms différents) dans les prospects est une plateforme ou un réseau. Il est traité
    comme un réseau social (C154) : prospect « sans site », pas d'audit de ce site.
13. La liste des plateformes connues (`not_sites`) s'allonge : annuaires et places de marché
    des artisans et commerçants (Travaux.com, Hellopro, Mappy, 118712, Kompass, Societe.com,
    Justacoté, Yelp, TripAdvisor, TheFork, Booksy, Kiute, Allovoisins, Leboncoin, Ooreka…), à
    relire par le propriétaire.

### SMS (C175 à C180)

14. **Brevo** : compte créé par le propriétaire, **SMS prépayés facturés par Brevo** (quelques
    centimes par SMS en France, tarif à vérifier sur leur site au moment de l'achat). La clé
    API va dans Réglages → Clés, chiffrée en base comme les autres. Réglages → SMS : nom
    d'expéditeur (11 caractères au plus, « Kenny » par défaut), plafond par jour (30 par
    défaut), activé ou non.
15. **Mobiles français seulement** (06, 07 et +33 6, +33 7), reconnus avec `phonenumbers`, déjà
    dans le projet. Jamais vers un entrepreneur non diffusible (Sirène), jamais après un STOP,
    une seule fois par prospect.
16. **Moment** : la plupart des serveurs renvoient un refus en quelques minutes. Le SMS part donc
    **20 minutes après le mail** (dans les heures d'envoi). Juste avant, l'app relit la
    conversation Gmail de ce mail (en-têtes seulement, comme C163) pour y chercher un refus.
    La version dépend du résultat : mail parti et non refusé (1), mail refusé, par Gmail tout de
    suite ou par le serveur du destinataire ensuite, ou adresse déjà marquée « mail refusé »
    C157 (2), pas d'adresse (3). Sans mail (pas d'adresse), le SMS part dans la file sans
    attendre.
16 bis. **Refus tardif** : si un refus est repéré **après** un SMS de version 1 (la relecture
    des réponses C163 tourne toutes les 30 minutes), un **second SMS**, une seule fois, prévient
    le dirigeant : « Mon mail n'a pas pu vous être remis : votre adresse ne reçoit pas les
    mails, vos clients ont sans doute le même problème. Écrivez-moi au {telephone}. Kenny ».
    Il respecte les heures d'envoi et compte dans le plafond du jour.
17. **Textes** dans un fichier modifiable (`sms_rules.yaml`), avec les variables {entreprise},
    {probleme} (titre court du premier point), {telephone}. Chaque texte, une fois rempli, tient
    en **un seul SMS** (160 caractères, alphabet SMS de base, mention STOP comprise) : l'app
    refuse de démarrer sinon, avec un message qui dit quoi raccourcir. Exemples :
    1. « Bonjour, {entreprise} : {probleme} sur votre site. 3 points simples à corriger, détails
       dans le mail envoyé à l'instant. Kenny, dév web »
    2. « Bonjour, {entreprise} : {probleme} sur votre site. Mon mail n'a pas pu vous être remis :
       écrivez-moi au {telephone} pour les détails. Kenny »
    3. « Bonjour, {entreprise} : {probleme} sur votre site. 3 points simples à corriger :
       écrivez-moi au {telephone} pour les détails. Kenny, dév web »
18. **Réponses** : un SMS envoyé sous un nom (« Kenny ») **ne peut pas recevoir de réponse**.
    Les textes invitent donc à **écrire au numéro réglé dans Réglages → Mail** (ton mobile).
19. **STOP** : Brevo ajoute la mention « STOP au 36111 » aux SMS marketing et bloque lui-même
    les numéros qui ont répondu STOP. L'app relit chaque jour la liste des numéros bloqués chez
    Brevo et les ajoute à sa propre liste de refus (comme les désinscriptions des mails). À
    vérifier sur le vrai compte, hors CI.
20. Aucun appel réseau dans les tests : un faux Brevo, comme pour Google et Gmail. Une
    vérification sur le vrai Brevo tourne à part (C99).

## Ce qui ne change pas

- Envoi depuis la fiche, avec relecture : inchangé.
- Le mail garde au plus 3 points, le lien de désinscription, la signature et l'appel à l'action.

## Hors champ

- Page d'audit publique liée depuis le SMS.
- SMS hors de France.
