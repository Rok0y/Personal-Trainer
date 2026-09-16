"""Sert `web/static` **sans cache**, pour vérifier une modification à l'écran.

`python -m http.server` n'envoie aucun en-tête de cache. Le navigateur applique
alors son heuristique de fraîcheur sur `Last-Modified` et ressert un module
depuis son cache disque, avec un statut 200 et sans rien revalider. Mesuré
pendant ce travail : un `export` ajouté à `cadrage.js` était bien servi par le
serveur (9 320 octets) et le navigateur continuait de lire l'ancienne version
(9 015 octets), échouant sur « does not provide an export named … ». *Un import
figé fait passer un code correct pour cassé*, et on cherche le défaut dans le
code qu'on vient d'écrire.

C'est le même problème que celui du déploiement, traité là-bas par
`scripts/empreinte_deploiement.py` — qui marque chaque ressource de l'empreinte
du commit. Ici il n'y a pas d'empreinte : on change de fichier toutes les deux
minutes, donc on demande simplement au navigateur de ne rien garder.

**À n'utiliser qu'en développement.** L'entrée `statique` de
`.claude/launch.json` reste le serveur nu, qui reproduit exactement la forme du
déploiement — c'est elle qu'il faut pour vérifier le comportement du cache, et
celle-ci pour vérifier le reste.

Usage : `python -m scripts.servir_statique [port]`
"""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent / "web" / "static"


class SansCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Les trois ensemble : `no-store` pour les navigateurs récents, les
        # deux autres pour ceux qui ne l'honorent pas seul.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    gestionnaire = partial(SansCache, directory=str(RACINE))
    serveur = ThreadingHTTPServer(("127.0.0.1", port), gestionnaire)
    print(f"web/static servi sans cache sur http://127.0.0.1:{port}")
    serveur.serve_forever()


if __name__ == "__main__":
    main()
