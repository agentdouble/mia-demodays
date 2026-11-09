# MIA Fraude — ajout isolé

Branche `feat/mia-fraude-game`, base `91208ec` de `dev`.

## Ouvrir localement

Depuis ce dossier de travail :

```sh
python3 -m app.preview
```

Ouvrir **http://localhost:8082/fraude**. Recommander est disponible au même port sous `/recommander`. Aucune dépendance supplémentaire pour cet aperçu. La prévisualisation écrit uniquement dans `data/preview/`, ignoré par Git ; elle n'utilise pas les données de production. Le serveur local écoute sur la boucle locale uniquement.

Pour refaire une partie de test, utilisez **Nouvel essai**, proposé à la fin ou après « Vous avez déjà joué ». Ce bouton ne retire que la partie de ce navigateur, permet de réutiliser son trigramme et conserve les autres joueurs. Il est disponible uniquement avec `python3 -m app.preview` sur HTTP local. La configuration normale, y compris celle déployée, ne propose pas cet endpoint.

Après une mise à jour du code, arrêtez puis relancez une fois le serveur local et rechargez la page : les modules Python et fichiers statiques sont chargés au démarrage. Les documents sont désormais référencés avec une empreinte de contenu pour éviter de revoir une ancienne image en cache.

## Parcours et contenu

Console d'arcade du jeu Recommander : mêmes polices locales, personnages, cadre, boutons, classement/podium et sons 8 bits ; palette noire, ambre et feu. Le dossier original `mia/mia-recommander` est inchangé.

| Cas | Décision attendue | Détail du bonus |
| --- | --- | --- |
| Photo d'accident générée | À vérifier | Doigt supplémentaire sur la main |
| Gros dégâts | Pas d'alerte | Compte rendu de contrôle concordant |
| Facture de réparation | À vérifier | AB-274-CD / AB-247-CD |
| Facture et virement différents | Pas d'alerte | Acompte de 400 € expliquant le solde |
| Photographies datées de dommages | À vérifier | Même rayure en Y et enfoncement sous deux angles |
| Deux assurés, même IBAN | Pas d'alerte | Attestation de compte joint |

Ordre mélangé pour chaque partie. La question est **« Cette pièce mérite-t-elle une vérification ? »**. Ce n'est pas un verdict de fraude ni une démonstration de performances de Frod. La photo impressionnante est documentée ; son rapport est une pièce fictive du scénario. Provenance et prompts : [fraud-assets.md](fraud-assets.md).

Après la décision : un essai pour toucher le détail pertinent, possibilité de passer. Les pièces ont des formats distincts (déclaration en formulaire, facture de garage, facture détaillée avec tableau et règlements en pied de page, reçu bancaire, rapport et attestation). Les pièces s'agrandissent dans un inspecteur plein écran avec zoom ×1/×2/×4 ; on peut faire défiler au doigt ou glisser avec la souris pour examiner une zone. Un défilement ne valide pas un point de bonus. Les corrections encadrent les zones et expliquent les cas. Clavier : Tab/Entrée pour les commandes, gauche/droite pour décider quand le focus n'est pas sur un bouton ; sur une image pendant le bonus, flèches pour déplacer le repère, Entrée pour choisir. Les animations respectent la réduction des mouvements.

Le rang est affiché dès le résultat, avec un accès direct au podium. Classement séparé : nombre de bonnes décisions, puis indices trouvés, puis somme des temps de décision. Le temps du bonus, de la correction et de l'écran de règles est exclu. Consultation des pièces et agrandissement pendant la décision restent chronométrés. Les interruptions réseau durant une décision peuvent allonger ce temps ; le serveur ne fait pas confiance à un chrono envoyé par le navigateur.

Une partie par navigateur et trigramme, reprise après rechargement. Une partie non terminée expire au bout de 30 minutes ; résultats conservés 30 jours, comme Recommander.

## Isolation

- Dispatch de `/fraude` uniquement dans `app/portal.py`. Les autres chemins gardent l'application originale. L'initialisation de Fraude est contenue : son échec retourne 503 sur Fraude et laisse Recommander fonctionner.
- `fraude.sqlite3` voisine de `mia.sqlite3` : aucun changement de schéma dans la base du collègue. Refus d'une configuration où les deux noms désignent le même fichier.
- Cookie `/fraude`, noms et signatures HMAC distincts, classement et quotas séparés. Un même trigramme peut jouer aux deux jeux.
- Décisions, bonus et temps calculés côté serveur. Une seule pièce courante est envoyée ; correction et zones privées jusqu'au choix du bonus. Aucun envoi de dossier, appel IA ou téléchargement externe en jeu.
- Requêtes répétées identiques sans double score ni remise à zéro du chrono ; choix modifiés refusés. La reprise consulte l'état enregistré.
- Manifeste public explicite, CSP, CSRF/origine/hôte stricts, corps et schémas limités. Les 6 réponses restent dans `app/fraud_cases.json`, hors fichiers servis.

## Vérification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node --test tests/fraud-frontend.test.mjs
```

Les tests couvrent aussi la suite Recommander via le dispatch réel, l'isolation des cookies/bases/classements, les requêtes concurrentes, les reprises, les sauvegardes des deux bases et la restriction de « Nouvel essai » au mode local. Ce dernier conserve les autres joueurs et Recommander. Les tests JavaScript couvrent les coordonnées avec bandes vides, les seuils de swipe et l'API/CSRF/reprise réseau.

Le parcours de l'interface a aussi été exercé avec un DOM simulé branché sur le vrai WSGI, sans socket : six décisions, choix d'indice et bonus, correction, classement et retour d'un joueur déjà inscrit. Une réponse perdue après commit a été simulée pour vérifier le bouton « Réessayer ». Ce contrôle ne remplace pas un navigateur : le rendu, le tactile et le cadrage des indices doivent encore être validés visuellement sur téléphone. Chrome et Firefox ne peuvent pas démarrer sous les restrictions de l'environnement Codex utilisé ici.

## Préparer la mise en ligne

Aucun déploiement n'est déclenché par cette branche. Ne pas remplacer l'installation du collègue avec un nouveau projet. Le fonctionnement reste `dev` → `stg` → `prod`, releases manuelles.

Modifications préparées dans ce commit :

1. Docker embarque `mia/mia-fraude` ; le healthcheck vérifie les **deux** jeux.
2. Caddy autorise `/fraude` et `/fraude/*`, sans changer la redirection racine vers Recommander.
3. Sauvegarde quotidienne et avant release : les **deux** bases si elles existent ; snapshots distincts, contrôle de restauration et conservation inchangés.
4. Contrôleur de release : vérification HTTP des deux jeux avant validation. Les sauvegardes restent compatibles avec l'ancienne base.

**Attention opérationnelle concrète :** Caddyfile, `release.py` et `backup.py` sont copiés sur l'hôte et appartiennent à root. L'image seule ne les met pas à jour. Pour la mise en ligne, un opérateur doit copier ces trois fichiers depuis le commit sélectionné dans `/usr/local/lib/mia-demodays/` (modes habituels), après en avoir gardé une copie. Ne pas relancer `install-host.py` : cela n'est pas nécessaire pour ajouter une route.

Ordre proposé : livrer/tester l'image en staging sur `/recommander` et `/fraude`, vérifier un exemple de chaque cas et une reprise ; mettre à jour le contrôleur et le script de sauvegarde sur l'hôte ; valider le candidat et promouvoir son digest exact par la procédure existante ; installer le Caddyfile étendu et le valider, puis recréer le service Caddy de production avec `up -d --force-recreate caddy` via le Compose habituel pour prendre en compte ce fichier monté (`admin off`, donc pas de reload via l'API d'administration). Vérifier ensuite les deux liens publics et lancer une sauvegarde pour constater les deux snapshots.

Le root-owned kit complet est décrit dans [deploy/README.md](../deploy/README.md). La modification Caddy est additive ; pour revenir en arrière, restaurer les fichiers sauvegardés et le digest précédent. Garder la base Fraude séparée ; aucun restore automatique sur les données actives.

Sauvegarde manuelle locale : `python3 -m app.maintenance --game fraude backup /chemin/nouveau-snapshot.sqlite3` (avec l'environnement applicatif habituel). `check` accepte le chemin de n'importe lequel des deux snapshots ; `purge --game fraude` ne touche que Fraude.
