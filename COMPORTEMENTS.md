# Comportements à développer

Liste validée par le propriétaire (issue #26 de `prospection-bot`, cases cochées ; C102 à C120 et ajustements validés le 24/10/2026 avec la spec `docs/superpowers/specs/2026-10-24-prospection-v2-design.md`). C'est **la référence** : chaque ligne = un test qui échoue d'abord, puis le code. Le numéro sert à relier le test, le commit et la ligne.
Ajouter ou retirer un comportement = modifier ce fichier (avec l'accord du propriétaire).

**Priorité transversale : interface développée d'abord pour le mobile.**

---

## 1. Configuration de l'app
- C01 Accès protégé par mot de passe (un seul utilisateur)
- C02 Je saisis mes clés une fois : Google, Notion, Sirène (INSEE)
- C03 Chaque clé est testée avec un bouton « Tester », avec un message clair si elle est refusée
- C04 Les clés ne s'affichent plus jamais en clair après la saisie
- C05 Je choisis mon CRM : Notion ou aucun (HubSpot reporté)
- C06 Je choisis la base Notion de destination (par défaut « Prospects v2 », page DEV)
- C07 Je fixe un plafond de dépense Google par mois ; l'app refuse de le dépasser. Par défaut 0 € : l'app reste dans le quota gratuit de Google
- C08 Sans clé Google, l'app le dit et bloque seulement les recherches Google Maps
- C09 Sans CRM configuré, l'app fonctionne quand même (export fichier, y compris des intéressés)

## 2. Configuration d'une campagne
- C10 Je donne un nom à la campagne
- C11 Je choisis la source : Google Maps, entreprises récemment créées, ou les deux
- C12 Je saisis un ou plusieurs métiers (mots-clés)
- C13 Je saisis une ou plusieurs villes, ou des départements, ou un rayon autour d'une ville
- C14 Je fixe le nombre de prospects qualifiés voulus (ex. 20)
- C15 L'app lance aussi les synonymes du métier (« cuisiniste » → « cuisine sur mesure »)
- C16 L'app m'affiche une estimation du coût avant de lancer
- C17 L'app refuse de lancer sans métier ou sans zone, et dit pourquoi
- C18 Je peux enregistrer une campagne comme modèle et la relancer
- C121 Je choisis le pays de la zone : France (par défaut), Belgique, Suisse, Luxembourg ou Monaco ; Google ne cherche que dans ce pays *(validé le 25/10/2026)*
- C122 Hors de France, je saisis une ville, une province (Belgique) ou un canton (Suisse, Luxembourg), ou un rayon autour d'une ville *(validé le 25/10/2026)*
- C123 Un établissement situé hors du pays ou de la province / du canton choisi est exclu « Hors zone » *(validé le 25/10/2026)*
- C124 Les numéros belges, suisses, luxembourgeois et monégasques sont reconnus (mobile ou fixe) *(validé le 25/10/2026)*
- C126 Vitesse du site sur mobile mesurée par Google PageSpeed Insights (note, temps d'affichage, problèmes principaux) ; un site lent compte dans le score et donne une accroche *(validé le 29/10/2026)*
- C131 Une page « en construction » de l'hébergeur compte comme « sans site » : gardée avec « Sans site seulement » (la fiche Google indique un site, il est lu pour le savoir), écartée avec « Avec site seulement », et mentionnée telle quelle (« page en construction ») *(validé le 29/10/2026)*
- C132 Je choisis un secteur (artisans du bâtiment, mode, esthétique, sport…) : le champ « Métiers » se remplit avec tous ses mots-clés (plombier, électricien… ; boutiques de vêtements, bijouteries… ; coiffure, onglerie, maquillage… ; salles de sport, coachs, pilates, yoga…), que je peux retirer avant de lancer ; aussi sur le Terrain *(demandé le 29/10/2026, repris de la V1)*
- C125 Entreprises récemment créées hors de France : registre officiel du pays quand il est ouvert (Belgique : BCE ; Suisse : Zefix) ; sinon l'app dit que cette source n'existe pas pour ce pays *(validé le 25/10/2026)*

## 3. Critères de qualification
**Fiche Google Maps**
- C19 Nombre d'avis minimum / maximum
- C20 Un établissement sans note n'est pas exclu
- C21 Avec site / sans site / peu importe
- C22 Avec téléphone / mobile seulement / peu importe
- C23 Exclure les catégories Google hors métier (restaurant pour « cuisiniste »…)

**Entreprise (registre officiel)**
- C24 Créée depuis moins de N jours / mois
- C25 Code d'activité (NAF) parmi une liste
- C26 Tranche d'effectif
- C27 Entreprise active uniquement (pas radiée)

**Site web**
- C28 Score de qualité du site maximum (ne garder que les sites faibles)
- C29 Site sans formulaire de contact, sans HTTPS, non adapté au mobile : garder / exclure

**Exclusions générales**
- C30 Exclure les franchises et les chaînes (liste fournie + ma liste)
- C31 Ne pas exclure un indépendant dont le nom ressemble à une enseigne
- C32 Exclure les prospects déjà présents dans le CRM
- C33 Exclure ma liste noire (entreprises qui ont dit non) ; marquer « pas intéressé » propose l'ajout, sans l'imposer

## 4. Lancement
- C34 Je vois la progression en direct (étape, trouvés, exclus, qualifiés)
- C35 Je peux arrêter la campagne ; ce qui est déjà trouvé est gardé
- C36 L'app continue à chercher tant qu'elle n'a pas le nombre de qualifiés demandé…
- C37 … et s'arrête quand la source est épuisée ou le budget atteint, en disant combien elle a trouvé et pourquoi pas plus
- C38 Un même établissement trouvé par deux mots-clés ou deux sources n'est traité qu'une fois
- C39 Les critères gratuits sont appliqués avant les appels payants
- C40 Une campagne coupée (réseau, redémarrage) peut reprendre là où elle s'était arrêtée
- C41 Une erreur sur un prospect n'arrête pas la campagne
- C119 Pendant que la recherche continue, je peux déjà appeler les prospects qualifiés

## 5. Enrichissement
**Google Maps**
- C42 Récupérer nom, adresse, téléphone, site, note, nombre d'avis, catégories, horaires, lien de la fiche
- C43 Photos de la fiche : nombre, et estimation « probable » de qui les a ajoutées (propriétaire ou clients)

**Registre officiel**
- C44 Récupérer SIREN / SIRET, date de création, code et libellé d'activité, forme juridique, effectif, dirigeants
- C45 Rapprocher la fiche Google de la bonne entreprise seulement si la correspondance est sûre ; sinon « à vérifier »
- C149 La fiche dit tout ce que le registre gratuit sait de l'activité : labels (RGE, Qualiopi, Bio, ESS, patrimoine vivant…), nombre d'établissements ouverts, activité de l'établissement si elle diffère *(demandé le 04/11/2026)*
- C150 Avec mes identifiants INPI, la fiche montre l'objet social, la description détaillée de chaque activité, sa forme d'exercice et les noms de domaine déclarés au registre national des entreprises *(demandé le 04/11/2026)*

**Site web**
- C46 Retrouver le site quand il manque sur la fiche Google (domaine deviné + confirmation sur la page)
- C47 Ne jamais adopter le site d'un homonyme
- C48 Récupérer emails, téléphones, liens réseaux sociaux (Facebook, Instagram, LinkedIn de l'entreprise)
- C49 Détecter la technologie du site (WordPress, Wix, Shopify…)
- C50 Audit rapide : HTTPS, mobile, vitesse, titre, formulaire, outil de suivi, copyright ancien
- C51 Analyse SEO locale : le métier et la ville apparaissent-ils dans le titre, le H1, le texte, les balises des images
- C52 Score de qualité du site avec la liste des problèmes
- C137 Un formulaire de contact est reconnu même quand son champ email n'est pas typé « email », quand il est bas dans une page lourde, quand il vient d'un service de formulaires (Google Forms, Typeform, HubSpot…), ou quand il est dessiné en JavaScript (widget Ninja Forms, Wix, Squarespace, Weebly, Jimdo, Webflow) *(demandé le 04/11/2026)*
- C138 Si l'accueil n'a pas de formulaire, l'app lit jusqu'à 2 pages du site dont le lien parle de contact, devis, rendez-vous ou réservation (formulaire, emails, téléphones) ; sans certitude, elle dit « formulaire non vérifié », jamais « pas de formulaire » *(demandé le 04/11/2026)*
- C139 L'audit dit où est le formulaire : en haut de l'accueil, plus bas sur l'accueil, seulement sur une page Contact (petit problème) ou aucun *(demandé le 04/11/2026)*
- C140 Audit RGPD : mentions légales, politique de confidentialité quand le site collecte des données, traceurs chargés sans bandeau de consentement *(demandé le 04/11/2026)*
- C141 Audit sécurité : HTTPS absent ou cassé (certificat invalide), messages du formulaire envoyés en clair *(demandé le 04/11/2026)*
- C142 Audit contact : numéro affiché mais pas cliquable sur mobile ; pas de réservation en ligne pour les métiers où elle compte *(demandé le 04/11/2026)*
- C143 Score d'autorité du domaine (Open PageRank, gratuit avec une clé), gardé 30 jours ; un site presque inconnu de Google est signalé *(demandé le 04/11/2026)*

**Contact**
- C53 Vérifier chaque email (syntaxe, domaine qui reçoit des mails, adresse jetable)
- C54 Distinguer email nominatif et générique (contact@)
- C55 Distinguer mobile et fixe
- C56 Lien de recherche LinkedIn du dirigeant (sans scraper LinkedIn)

**Synthèse**
- C57 Score d'opportunité sur 100, avec le détail du calcul
- C58 Raison de qualification lisible (« sans site, créée il y a 2 mois, 4 avis »)
- C59 Drapeaux « à vérifier » quand une info est douteuse
- C60 Note de confiance par info (sûr / probable / à vérifier)

## 6. Résultats et export
- C61 Trier / filtrer les résultats dans l'app avant l'export
- C62 Export CSV lisible par Excel (accents corrects)
- C63 Export Excel (.xlsx)
- C64 Une ligne par prospect, toutes les infos en colonnes, triées par score d'opportunité
- C65 Un onglet / fichier séparé avec les exclus et la raison
- C66 Je retrouve les exports des campagnes passées
- C118 L'export fichier d'une campagne ne change aucun statut de prospect
- C120 La liste des prospects se cherche (nom, ville, métier) et se filtre par statut, avec le nombre de prospects par statut
- C127 Les prospects trouvés sur le terrain sont séparés des prospects à appeler (recherche sur Internet) : deux onglets, chacun avec sa liste, ses compteurs et sa session d'appel *(demandé le 29/10/2026)*
- C128 La liste des prospects se filtre par campagne (chaque campagne avec son nombre de prospects, la plus récente d'abord) *(demandé le 29/10/2026)*
- C129 Je coche plusieurs prospects dans la liste (ou tous) et je les supprime en une fois, après une page de confirmation ; je peux demander qu'ils ne soient plus jamais repris *(demandé le 29/10/2026)*
- C130 Lancer une campagne (ou envoyer un formulaire) n'affiche jamais « Quitter le site ? » ; seule une note ou une saisie de fiche pas encore enregistrée prévient *(demandé le 29/10/2026)*
- C133 Dans chaque onglet, la liste est rangée par campagne (un titre par campagne, la plus récente d'abord) ; la session d'appel suit le même ordre *(demandé le 29/10/2026)*
- C134 Le choix de la ville propose les communes pendant la frappe (« Recherche des villes… » pendant l'attente) ; la commune choisie reste seule à l'écran *(demandé le 29/10/2026)*
- C135 Pendant une action longue (lancer une campagne, chercher sur le terrain, ouvrir la session, exporter, supprimer), le bouton affiche un petit cercle qui tourne et dit ce qui se passe ; un deuxième appui n'envoie rien *(demandé le 29/10/2026)*
- C136 Chaque prospect affiche un résumé de l'audit de son site en une ligne (principaux problèmes, lenteur sur mobile), dans la liste et en haut de la fiche *(demandé le 29/10/2026)*

## 7. Envoi au CRM
- C67 Relecture avant l'envoi : je retire un prospect d'un clic (les « à vérifier » sont décochés par défaut) ; l'envoi se fait seulement quand j'appuie sur Exporter
- C68 Chaque prospect intéressé exporté est créé dans la base Notion (entreprise + dirigeant), avec ses notes et sa prochaine action ; il passe alors au statut « exporté »
- C69 Pas de doublon : un prospect déjà dans le CRM est mis à jour, pas recréé
- C70 Une info déjà saisie à la main dans le CRM n'est jamais écrasée
- C71 Le nom de la campagne et la date sont enregistrés sur la fiche
- C72 Lien direct vers la fiche créée dans le CRM
- C73 Si Notion est en panne : rien n'est perdu, l'envoi est réessayé plus tard, l'export fichier marche quand même
- C74 Bilan : créés, mis à jour, en échec (avec la raison)
- C75 Respect des limites d'appels de Notion

## 8. Suivi dans le temps
- C76 Mettre à jour une campagne passée (fermés, changements de site…)
- C77 Campagne récurrente programmée (ex. chaque lundi : les créations de la semaine)
- C78 Alerte quand de nouvelles entreprises correspondent à une campagne enregistrée

## 9. Pilotage
- C79 Coût réel de chaque campagne (Google, autres API)
- C80 Tableau de bord : campagnes, prospects trouvés, taux de qualification, coût par prospect qualifié
- C81 Journal de chaque campagne consultable (ce qui a été fait, erreurs)

## 10. Sécurité
- C82 Mot de passe haché, limite d'essais de connexion
- C83 Journal des connexions (date, IP, réussie ou non)
- C84 HTTPS uniquement
- C85 Clés API chiffrées en base, jamais dans les journaux ni les exports
- C86 Clé de chiffrement uniquement dans les variables d'environnement de l'hébergeur, jamais en base
- C87 Aucune visite d'adresse interne pendant l'analyse des sites (protection SSRF)
- C88 Taille et durée de lecture des pages limitées
- C89 Textes venant des sites neutralisés : pas d'injection dans l'interface ni de formule piégée dans le CSV / Excel
- C90 Dépendances à jour et vérifiées automatiquement
- C91 Sauvegarde automatique quotidienne de la base

## 11. Conformité
- C92 Respect des conditions Google (API officielle seulement, pas de scraping de Google ni de LinkedIn)
- C93 Respect des entrepreneurs qui ont refusé la diffusion de leurs données dans Sirène
- C94 Suppression automatique des prospects non retenus après 6 mois sans activité, réglable (RGPD) ; jamais les intéressés, exportés ou à rappeler
- C95 Supprimer toutes les données d'une entreprise sur demande

## 12. Maintenance
- C96 Tests automatiques à chaque modification (sans réseau)
- C97 Déploiement automatique quand les tests passent
- C98 Alerte (notification sur le téléphone) si une campagne programmée échoue
- C99 Vérification hebdomadaire des vraies API (Google, Sirène, Notion) : alerte (notification) si l'une change de format
- C100 Erreurs remontées automatiquement (service gratuit type Sentry)
- C101 README + guide de déploiement à jour

## 13. Suivi des appels
- C102 Après un appel, je classe le prospect en un geste : intéressé, à rappeler, pas intéressé, messagerie, pas joint, faux numéro
- C103 Je planifie une prochaine action (rappeler, envoyer un devis, rendez-vous, passer) avec une date et une heure facultative
- C104 J'écris des notes datées sur chaque prospect
- C105 Je complète ou corrige le contact (dirigeant, mobile, email) directement sur la fiche
- C106 Chaque saisie est enregistrée immédiatement ; en cas d'échec, l'app le dit et garde ma saisie
- C107 L'écran Aujourd'hui liste les actions en retard, du jour et de demain, recalculées chaque jour dans mon fuseau horaire (Paris par défaut) ; je coche une action pour la terminer
- C108 Je reçois une notification avant chaque relance (15 min avant une action avec heure, 8 h pour celles du jour sans heure ; réglable)
- C109 Je reprends une session d'appel là où je l'avais laissée (précédent / suivant, position dans la file triée par score)

## 14. Préparation de l'appel
- C110 Chaque prospect a une fiche « Pour l'appel » (accroche + douleurs probables) produite par des règles fixes, sans IA, rangées dans un fichier que je peux compléter
- C111 La fiche « Pour l'appel » présente les douleurs comme des indices à confirmer, jamais comme des certitudes
- C112 Je vois les indices de santé de l'entreprise (CA et résultat si publiés, effectif, horaires, activité des avis) ; « non publié » quand l'info manque, « probable » quand c'est une estimation

## 15. Prospection terrain
- C113 Mode Terrain : je cherche les petits commerces autour de ma position ou d'une adresse, avec des filtres (moins de N avis, sans site, ouvert maintenant)
- C114 Mode Terrain : les arrêts sont ordonnés pour une tournée et j'ouvre l'itinéraire dans Google Maps
- C115 Mode Terrain : je pose un statut en un geste devant la boutique (intéressé, repasser, non)

## 16. App sur le téléphone
- C116 L'app s'installe sur Android (icône, plein écran) et reste connectée 30 jours
- C117 La barre de navigation flottante donne accès en un geste à Aujourd'hui, Prospects, Terrain, Recherche, Réglages *(Réglages ajouté le 29/10/2026)*

## 17. Mail d'audit
- C144 Je relie mon Gmail une fois dans Réglages et je règle le mail : nom, téléphone, lien du portfolio, lien Calendly (facultatif), délai du rappel (1 à 3 jours) *(demandé le 04/11/2026)*
- C145 Sur la fiche, « Mail d'audit » prépare un mail court : au plus 3 problèmes du site, chacun relié à son effet sur le business du prospect (règles fixes dans un fichier, adaptées au métier, chiffres en fourchette), puis portfolio et appel de 15 minutes ; je peux tout modifier *(demandé le 04/11/2026)*
- C146 « Envoyer » part de mon Gmail vers un email valide du prospect, une seule fois par prospect ; le lien « ne plus recevoir de mails » est toujours ajouté *(demandé le 04/11/2026)*
- C147 Après l'envoi, une note datée est ajoutée et un rappel « Rappeler » est planifié dans le délai réglé *(demandé le 04/11/2026)*
- C148 Le lien de désinscription ouvre une page publique ; après confirmation, plus aucun mail n'est envoyé à cette adresse, même si le prospect est supprimé *(demandé le 04/11/2026)*
- C151 Une page publique (sans connexion) décrit l'app et sa politique de confidentialité : elle sert de page d'accueil et de règles de confidentialité pour l'écran de consentement Google *(demandé le 05/11/2026)*
- C152 Un site affiché seulement par JavaScript (Base44, Lovable, Bolt…) n'est jamais jugé « sans texte » ni « sans formulaire » : l'audit dit que son contenu est à vérifier à la main *(demandé le 06/11/2026)*
- C153 L'audit distingue un formulaire basique (nom, email, message) d'un formulaire de devis détaillé (champs du métier : type de travaux, surface, photos, date…) *(demandé le 06/11/2026)*
- C154 Une fiche Google qui renvoie vers un réseau social ou un annuaire (Instagram, Facebook, Linktree, PagesJaunes…) compte comme « sans site » *(demandé le 06/11/2026)*
- C155 Les mails d'audit sont plus concis et finissent par « appelez-moi pour plus d'infos, c'est gratuit et sans engagement » *(demandé le 06/11/2026)*
- C156 Sur la fiche, « Refaire l'audit » demande un nouvel audit du site à la tâche de fond (gratuit) ; la fiche dit qu'il est en cours, la vitesse déjà mesurée est gardée *(demandé le 06/11/2026)*
- C157 Sur la fiche, « Mail refusé » note le refus, permet un nouvel envoi vers une autre adresse (jamais la même) et donne l'accroche d'appel ; un refus signalé par Gmail dans le fil du mail est repéré automatiquement *(demandé le 06/11/2026)*
- C158 L'audit dit si le formulaire est tout en bas de la page Contact et s'il manque un bouton « Devis » (ou réservation) visible en haut de l'accueil *(demandé le 06/11/2026)*
- C159 L'audit juge la qualité du formulaire : trop de champs obligatoires, pas de mention RGPD, questions utiles au métier qui manquent (surface, photos, date…, selon le corps de métier) *(demandé le 06/11/2026)*
