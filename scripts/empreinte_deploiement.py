"""Ajoute une empreinte de version à chaque ressource locale du site publié.

Un déploiement ne doit jamais être servi à moitié. Sans ça, un navigateur qui
tient encore l'ancien `camera.js` en cache le combine avec le nouveau
`index.html` — et l'application échoue sur une fonction disparue, en ne
laissant pour indice qu'un message qui accuse un code déjà corrigé. C'est
arrivé, sur un iPad, au démarrage d'une séance.

**Le cache n'est pas en cause, sa granularité l'est.** GitHub Pages sert
`Cache-Control: max-age=600`, mais chaque fichier expire pour son compte : le
document HTML peut être frais pendant que le module qu'il importe est vieux de
dix minutes. Sur iOS, un site ajouté à l'écran d'accueil les garde plus
longtemps encore, et il n'y a pas de « recharger en ignorant le cache ».

La réponse est de **changer l'adresse plutôt que d'espérer l'expiration** :
`camera.js?v=<empreinte>` est une ressource que le navigateur n'a jamais vue,
donc qu'il ne peut pas servir de travers. L'empreinte vient du commit déployé,
donc elle change exactement quand le contenu change.

Trois précisions qui font la différence entre « ça marche » et « ça marche
toujours ».

- **Les modules s'importent entre eux.** Marquer seulement les imports de la
  page laisserait `camera.js?v=neuf` charger `./landmarks.js` sans empreinte,
  c'est-à-dire depuis le cache. On réécrit donc aussi les imports des `.js`.
- **Les données comptent** : `donnees/seances.json` est relu à chaque
  ouverture, et un catalogue périmé se voit moins vite qu'un module cassé,
  mais se voit.
- **Les adresses absolues ne sont jamais touchées.** Un CDN gère son propre
  cache, et lui ajouter une requête inconnue fait rater le sien.

N'agit que sur la copie publiée (`_site`) : en développement, l'empreinte
gênerait plus qu'elle n'aiderait, le serveur local ne cachant rien.

Usage : `python -m scripts.empreinte_deploiement _site <empreinte>`
"""

import re
import sys
from pathlib import Path

#: Ce qu'on réécrit. Chaque motif capture l'adresse dans son groupe 1.
MOTIFS = (
    # import ... from "./x.js"  /  import("./x.js")
    re.compile(r"""(?<=from )(["'])(\.{1,2}/[^"']+\.js)\1"""),
    re.compile(r"""(?<=import\()(["'])(\.{1,2}/[^"']+\.js)\1"""),
    # <link rel="stylesheet" href="../x.css">  /  <script src="…">
    re.compile(r"""(?<=href=)(["'])(\.{0,2}/?[\w./-]+\.css)\1"""),
    re.compile(r"""(?<=src=)(["'])(\.{0,2}/?[\w./-]+\.js)\1"""),
    # fetch("../donnees/x.json")
    re.compile(r"""(?<=fetch\()(["'])(\.{1,2}/[^"']+\.json)\1"""),
)

EXTENSIONS = (".html", ".js")


def marquer(texte, empreinte):
    """Ajoute `?v=<empreinte>` aux adresses locales, et à elles seules."""
    marques = 0

    def remplacer(trouve):
        nonlocal marques
        guillemet, adresse = trouve.group(1), trouve.group(2)
        # Une adresse absolue a son propre cache : y toucher ferait rater le
        # sien sans rien nous apporter.
        if adresse.startswith(("http://", "https://", "//")) or "?" in adresse:
            return trouve.group(0)
        marques += 1
        return f"{guillemet}{adresse}?v={empreinte}{guillemet}"

    for motif in MOTIFS:
        texte = motif.sub(remplacer, texte)
    return texte, marques


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2

    racine = Path(sys.argv[1])
    empreinte = sys.argv[2][:12]
    if not racine.is_dir():
        print(f"Dossier introuvable : {racine}", file=sys.stderr)
        return 1

    total = 0
    fichiers = 0
    for chemin in racine.rglob("*"):
        if not chemin.is_file() or chemin.suffix not in EXTENSIONS:
            continue
        texte = chemin.read_text(encoding="utf-8")
        marque, combien = marquer(texte, empreinte)
        if combien:
            chemin.write_text(marque, encoding="utf-8")
            total += combien
            fichiers += 1

    print(f"Empreinte {empreinte} : {total} adresses marquees dans {fichiers} fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
