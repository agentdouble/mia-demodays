# MIA Recommander

Jeu d'arcade de démo : le joueur classe 6 clients, tirés au hasard parmi 20, selon qu'ils vont augmenter ou non leur versement 111bis (plafond 3 200 € → 4 500 €), contre la montre. Son temps est projeté sur l'ensemble du foyer ciblé (50 000 clients) face à MIA, puis un classement s'affiche.

- Interface sans étape de build : `index.html`, `game.css`, `game.js` et `api.js`.
- Version jouable : https://claude.ai/artifact/XjTJfUr7CtSpFKb2yz9Bi8
- Le trigramme et le classement utilisent maintenant l’API SQLite du dépôt, indépendante de Claude. Une seule partie par trigramme et session de navigateur ; aucune vérification d’identité.
- Les clients sont fictifs.

Installation et vérifications : voir le [README racine](../../README.md).
