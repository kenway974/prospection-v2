# Comportements à développer

Liste validée par le propriétaire (issue #26 de `prospection-bot`, cases cochées). C'est **la référence** : chaque ligne = un test qui échoue d'abord, puis le code. Le numéro sert à relier le test, le commit et la ligne.
Ajouter ou retirer un comportement = modifier ce fichier (avec l'accord du propriétaire).

**Priorité transversale : interface développée d'abord pour le mobile.**

---

## 1. Configuration de l'app
- C01 Accès protégé par mot de passe (un seul utilisateur)
- C02 Je saisis mes clés une fois : Google, CRM (Notion ou HubSpot), Sirène (INSEE)
- C03 Chaque clé est testée avec un bouton « Tester », avec un message clair si elle est refusée
- C04 Les clés ne s'affichent plus jamais en clair après la saisie
- C05 Je choisis mon CRM : Notion, HubSpot ou aucun
- C06 Je choisis la base Notion / le pipeline HubSpot de destination
- C07 Je fixe un budget Google maximum par mois ; l'app refuse de le dépasser
- C08 Sans clé Google, l'app le dit et bloque seulement les recherches Google Maps
- C09 Sans CRM configuré, l'app fonctionne quand même (export fichier seulement)

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
- C33 Exclure ma liste noire (entreprises qui ont dit non)

## 4. Lancement
- C34 Je vois la progression en direct (étape, trouvés, exclus, qualifiés)
- C35 Je peux arrêter la campagne ; ce qui est déjà trouvé est gardé
- C36 L'app continue à chercher tant qu'elle n'a pas le nombre de qualifiés demandé…
- C37 … et s'arrête quand la source est épuisée ou le budget atteint, en disant combien elle a trouvé et pourquoi pas plus
- C38 Un même établissement trouvé par deux mots-clés ou deux sources n'est traité qu'une fois
- C39 Les critères gratuits sont appliqués avant les appels payants
- C40 Une campagne coupée (réseau, redémarrage) peut reprendre là où elle s'était arrêtée
- C41 Une erreur sur un prospect n'arrête pas la campagne

## 5. Enrichissement
**Google Maps**
- C42 Récupérer nom, adresse, téléphone, site, note, nombre d'avis, catégories, horaires, lien de la fiche
- C43 Photos de la fiche : nombre, ajoutées par le propriétaire ou seulement par des clients

**Registre officiel**
- C44 Récupérer SIREN / SIRET, date de création, code et libellé d'activité, forme juridique, effectif, dirigeants
- C45 Rapprocher la fiche Google de la bonne entreprise seulement si la correspondance est sûre ; sinon « à vérifier »

**Site web**
- C46 Retrouver le site quand il manque sur la fiche Google (domaine deviné + confirmation sur la page)
- C47 Ne jamais adopter le site d'un homonyme
- C48 Récupérer emails, téléphones, liens réseaux sociaux (Facebook, Instagram, LinkedIn de l'entreprise)
- C49 Détecter la technologie du site (WordPress, Wix, Shopify…)
- C50 Audit rapide : HTTPS, mobile, vitesse, titre, formulaire, outil de suivi, copyright ancien
- C51 Analyse SEO locale : le métier et la ville apparaissent-ils dans le titre, le H1, le texte, les balises des images
- C52 Score de qualité du site avec la liste des problèmes

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

## 7. Envoi au CRM
- C67 Relecture avant l'envoi : je retire un prospect d'un clic (sinon envoi automatique)
- C68 Chaque prospect qualifié est créé dans Notion ou HubSpot (entreprise + contact dirigeant)
- C69 Pas de doublon : un prospect déjà dans le CRM est mis à jour, pas recréé
- C70 Une info déjà saisie à la main dans le CRM n'est jamais écrasée
- C71 Le nom de la campagne et la date sont enregistrés sur la fiche
- C72 Lien direct vers la fiche créée dans le CRM
- C73 Si le CRM est en panne : rien n'est perdu, l'envoi est réessayé plus tard, l'export fichier marche quand même
- C74 Bilan : créés, mis à jour, en échec (avec la raison)
- C75 Respect des limites d'appels de Notion / HubSpot

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
- C94 Suppression automatique des prospects non retenus au-delà de N mois (RGPD)
- C95 Supprimer toutes les données d'une entreprise sur demande

## 12. Maintenance
- C96 Tests automatiques à chaque modification (sans réseau)
- C97 Déploiement automatique quand les tests passent
- C98 Alerte (email) si une campagne programmée échoue
- C99 Vérification hebdomadaire des vraies API (Google, Sirène, Notion, HubSpot) : alerte si l'une change de format
- C100 Erreurs remontées automatiquement (service gratuit type Sentry)
- C101 README + guide de déploiement à jour
