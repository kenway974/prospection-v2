# Bonnes pratiques de développement

Fichier générique, valable pour tous les projets (repris du projet Oser, exemples adaptés à Python). Chaque projet l'importe depuis son `CLAUDE.md` (`@.claude/bonnes-pratiques.md`) et n'y ajoute que ses règles propres.

Ces règles s'appliquent **dès la première ligne de code**, sans attendre qu'un problème apparaisse ni qu'on les rappelle. Toute règle vérifiable par un outil est vérifiée par le lint ou la CI ; les autres se vérifient en relisant son propre diff avant de livrer.

## 1. Avant de coder

- Comprendre le besoin réel et le reformuler. Poser les questions qui changent la solution, une à la fois.
- Une fonctionnalité qui change une structure (données, contenu, architecture) passe par une spec courte validée avant le code.
- Choisir la solution la plus simple qui répond au besoin (YAGNI). Pas de fonctionnalité « au cas où ».
- Les décisions se prennent avec le propriétaire du projet. Une décision technique prise seule est notée et expliquée dans le compte rendu.

## 2. Architecture et découpage

- **Une responsabilité par fichier, par fonction, par composant.** Un fichier qui dépasse ~150 lignes ou qui fait plusieurs choses est découpé.
- **Couches séparées** : logique métier pure (testable sans interface ni stockage ni réseau), accès aux données, interface. L'interface affiche et délègue ; elle ne contient pas de règle métier.
- **Pas de duplication** : on extrait dès la deuxième occurrence.
- **Pas de cycle d'imports.** Les dépendances vont dans un seul sens (interface → logique → types).
- Le contenu et la configuration vivent dans des fichiers de données validés, pas dans le code.
- Noms explicites, en cohérence avec le vocabulaire du métier. Pas de code mort, pas d'export inutilisé, pas de dépendance inutilisée.

## 3. Interface

- Composants petits et réutilisables ; une page assemble, elle ne contient pas de logique.
- Le style est centralisé (thème, feuille de style), pas éparpillé dans chaque écran.
- Accessibilité dès le départ : libellés corrects, contrastes suffisants, cibles tactiles ≥ 44 px.

## 4. Performance (dès la conception)

- Charger et calculer seulement ce qui sert à l'écran affiché ; le travail long tourne en tâche de fond.
- Mettre en cache ce qui peut l'être (réponses d'API coûteuses, données déjà chargées).
- Pas de calcul coûteux répété ; optimiser seulement quand c'est mesuré utile.
- Dépendances légères : vérifier avant d'en ajouter une, préférer la bibliothèque standard quand elle suffit.

## 5. Qualité et tests

- **Tests d'abord (TDD)** : écrire le test, le voir échouer pour la bonne raison, écrire le code minimal, le voir passer.
- Une correction de bug commence par un test qui reproduit le bug.
- Tester le comportement, pas l'implémentation. Pas de test qui passe sans jamais avoir échoué.
- Trois niveaux : unitaires (logique pure), intégration (couches assemblées, services externes simulés), bout en bout sur les parcours principaux.
- Typage strict. Aucune erreur ni avertissement de lint toléré.

## 6. Données et sécurité

- Valider strictement tout ce qui entre : saisie, stockage, import, réponses d'API, pages web lues.
- Format de données versionné, migrations numérotées et testées. Jamais d'écrasement silencieux de données.
- Aucun secret dans le dépôt (`.env*` ignoré). Aucune requête vers un tiers sans raison et sans accord.
- Aucun texte externe injecté brut dans l'interface ou dans un export. En-têtes de sécurité (CSP, `frame-ancestors`, `nosniff`, `Referrer-Policy`, HSTS).
- Dépendances surveillées (Dependabot ou équivalent) ; aucune faille connue « high » en production.

## 7. CI (intégration continue)

Chaque push et chaque Pull Request lancent, dans cet ordre, et **la CI bloque si une étape échoue** :

1. Installation reproductible (dépendances verrouillées, fichier de verrouillage commité).
2. Audit des dépendances : aucune faille « high » en production.
3. Lint (dont taille maximale des fichiers et absence de cycle d'imports).
4. Vérification des types.
5. Tests unitaires et d'intégration (rejoués dans un fuseau horaire éloigné d'UTC si des dates sont en jeu), avec seuil de couverture.
6. Build de production (image de déploiement).
7. Tests de bout en bout sur le build.

Rien n'est fusionné dans la branche principale si la CI n'est pas verte.

## 8. Git et livraison

- Ne jamais travailler directement sur la branche principale : une branche par travail, fusion après validation.
- Commits petits et cohérents, messages clairs qui disent ce qui change et pourquoi.
- Avant de livrer : relire son diff, lancer lint, types, tests, build. Annoncer les résultats réels, pas supposés.
- Compte rendu honnête : ce qui est fait, ce qui ne l'est pas, les décisions prises, les limites connues.
