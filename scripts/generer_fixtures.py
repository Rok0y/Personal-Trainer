"""Genere les cas de reference qui prouvent que le portage JS est fidele.

Les detections sont des fonctions **pures** d'un corps vers un jeton : les
deux implementations doivent donc s'accorder sur n'importe quelle entree,
anatomiquement plausible ou non. Des poses tirees au hasard couvrent bien
mieux les abords des seuils qu'une captation reelle, ou l'on repasse sans
cesse par les memes configurations — et elles ne demandent ni camera ni
patience.

Sortie : scripts/fixtures_detections.jsonl, une pose par ligne, avec les
jetons attendus. A rejouer avec `node scripts/comparer_detections.mjs`.

    python -m scripts.generer_fixtures [nombre_de_poses]
"""

import inspect
import json
import random
import sys
from pathlib import Path

from mouvements import exercices, positions
from vision.body import Body, LandmarkPoint
from vision.landmarks import LANDMARKS

GRAINE = 20260909
"""Fixe pour que le fichier genere soit reproductible : deux executions
produisent les memes poses, donc un diff du harnais signale un changement de
logique et jamais un changement de tirage."""

DESTINATION = Path(__file__).parent / "fixtures_detections.jsonl"


def fonctions_publiques(module):
    """Les fonctions du module qui prennent un corps et rendent un jeton.

    Recensees par introspection plutot que listees a la main : une detection
    ajoutee sans jumelle JS doit faire echouer le harnais, pas passer
    inapercue parce que personne n'a pense a l'inscrire ici.
    """
    trouvees = {}
    for nom, objet in inspect.getmembers(module, inspect.isfunction):
        if nom.startswith("_") or objet.__module__ != module.__name__:
            continue
        if list(inspect.signature(objet).parameters) == ["corps"]:
            trouvees[nom] = objet
    return trouvees


def pose_au_hasard(rng):
    points = {}
    for nom in LANDMARKS:
        points[nom] = LandmarkPoint(
            x=rng.random(), y=rng.random(), z=rng.random() * 2 - 1, visibilite=rng.random()
        )
    return Body(points)


def serialiser(corps):
    """La pose au format que lira le JS : un tableau indexe comme MediaPipe."""
    tableau = [None] * (max(LANDMARKS.values()) + 1)
    for nom, index in LANDMARKS.items():
        p = corps.points[nom]
        tableau[index] = {
            "x": p.x,
            "y": p.y,
            "z": p.z,
            "visibility": p.visibilite,
        }
    return tableau


def natif(jeton):
    """Ramene un jeton a un type Python standard.

    `calculer_angle` passe par numpy, si bien qu'une comparaison d'angle rend
    un `numpy.bool_` et non un `bool` : invisible dans un `if`, mais refuse
    par json.dumps. Les detections rendent une chaine, les fonctions d'erreur
    None, les positions un booleen.
    """
    if jeton is None or isinstance(jeton, str):
        return jeton
    return bool(jeton)


def main():
    nombre = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    rng = random.Random(GRAINE)

    fonctions = {**fonctions_publiques(exercices), **fonctions_publiques(positions)}

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for _ in range(nombre):
            corps = pose_au_hasard(rng)
            jetons = {
                nom: natif(fonction(corps)) for nom, fonction in fonctions.items()
            }
            ligne = {"landmarks": serialiser(corps), "jetons": jetons}
            fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    print(f"{nombre} poses ecrites dans {DESTINATION}")
    print(f"{len(fonctions)} fonctions couvertes :")
    for nom in sorted(fonctions):
        print(f"  {nom}")


if __name__ == "__main__":
    main()
