# Lot 5 · Site web (plan court)

Comportements : C28, C29, C46 à C52, C87, C88, C39 (test reporté du lot 2).

Briques reprises de `prospection-bot` (`services/site_finder.py`, `services/analyzer.py`, version 530ba12), relues et améliorées :
- garde SSRF : l'ancien code vérifiait l'adresse puis laissait `requests` la résoudre une seconde fois (faille « DNS rebinding ») ; ici l'adresse vérifiée est celle utilisée pour la connexion ;
- lecture HTML avec la bibliothèque standard (`html.parser`) au lieu de BeautifulSoup (dépendance en moins) ;
- règles d'audit pures (domaine), l'année courante passée en paramètre (l'ancien code lisait l'horloge) ;
- site deviné adopté seulement sur confirmation forte (même téléphone, ou nom complet + code postal) ; un homonyme n'est jamais adopté (C47).

Écarté (YAGNI) : PageSpeed (API externe en plus ; la vitesse est mesurée au chargement), vidéo, galerie, blog, livraison.

## Architecture

| Couche | Fichier | Rôle |
|---|---|---|
| sources | `web_reader.py` | Lecture sûre d'une page : http(s), ports 80/443, adresse publique vérifiée et utilisée pour la connexion, 3 redirections au plus (chacune vérifiée), 500 Ko, 8 s, HTML seulement (C87, C88) |
| domain | `html_page.py` | Page lue → `Page` (titre, balises meta, H1, formulaires, liens, textes alternatifs des images, texte), bornée |
| domain | `site_audit.py` | Technologie (C49), problèmes et score sur 100 (C50, C52) |
| domain | `site_seo.py` | Métier et ville dans le titre, le H1, le texte, les images (C51) |
| domain | `site_contacts.py` | Emails, téléphones, réseaux sociaux de l'entreprise (C48) |
| domain | `site_guess.py` | Domaines devinés et confirmation sur la page (C46, C47) |
| application | `site_check.py` | Un établissement → rapport du site (lu, deviné, ou absent) |
| storage | migration 0007 | `prospects.site_json` ; `campaign_steps.pending_page_json` (page payée gardée avant traitement, C40) |
| ui | fiche | Bloc « Le site » : score, problèmes, technologie, SEO, contacts trouvés |

## Ordre (C39)

Critères gratuits sur la fiche Google (déjà payée) → lecture du site, gratuite mais lente, seulement pour les établissements encore qualifiés → critères « site » (C28, C29). Les recherches Google payées du registre restent après les critères gratuits du registre (lot 4).

## Bout en bout

En mode test, le lecteur de sites passe par le faux local (aucune visite réelle).
