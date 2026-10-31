# Menus de la maison

Site statique publié par GitHub Pages depuis le dossier `docs/`.

- `data/recettes/*.json` : une recette par fichier
- `data/menus/AAAA-Sxx.json` : le menu d'une semaine (repas + extras)
- `python3 build.py` régénère `docs/`

Chaque fiche recette et chaque liste de courses contient un bouton « Ajouter à Bring »
(lien d'import de recettes Bring) et des données schema.org Recipe que Bring lit.
