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
import math
import random
import sys
from pathlib import Path

from mouvements import echauffements, exercices, positions
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


NOMBRE_POSES_DE_GESTE = 500
"""Poses construites bras leves, en plus des poses au hasard.

Le hasard n'atteint presque jamais « deux bras leves » : mesure, 4 poses sur
5 000 levent les deux bras, et aucune n'a le buste debout. La condition de
buste ajoutee a `deux_bras_leves` n'etait donc comparee par rien — la retirer
d'un seul cote passait vert. Meme lecon que les scenarios ecrits du harnais de
seances : un etat etroit se vise, il ne se tire pas."""


def pose_bras_leves(rng):
    """Deux bras tendus au-dessus des epaules, buste oriente au hasard.

    Le buste tourne de -90 a +90 degres autour du milieu des epaules : debout a
    zero, allonge aux extremes, et la frontiere a 45 degres visitee au passage.
    Le reste du corps garde ses valeurs tirees au hasard, ce qui fait aussi
    tourner les detections d'exercice sur ces poses.
    """
    corps = pose_au_hasard(rng)
    points = corps.points
    milieu_x, milieu_y = 0.3 + rng.random() * 0.4, 0.3 + rng.random() * 0.4
    demi_largeur = 0.03 + rng.random() * 0.08
    for cote, signe in (("gauche", -1), ("droite", 1)):
        suffixe_bras = "gauche" if cote == "gauche" else "droit"
        ex, ey = milieu_x + signe * demi_largeur, milieu_y
        points[f"epaule_{cote}"] = LandmarkPoint(ex, ey, 0, 1)
        # Le bras est tendu vers le haut, a quelques degres pres : l'angle du
        # coude reste au-dessus de 160 la plupart du temps, pas toujours.
        derive = (rng.random() - 0.5) * 0.04
        points[f"coude_{suffixe_bras}"] = LandmarkPoint(ex + derive, ey - 0.12, 0, 1)
        points[f"poignet_{suffixe_bras}"] = LandmarkPoint(ex + 2 * derive, ey - 0.24, 0, 1)
    angle = math.radians(rng.uniform(-90, 90))
    distance = 0.15 + rng.random() * 0.2
    hx = milieu_x + distance * math.sin(angle)
    hy = milieu_y + distance * math.cos(angle)
    points["hanche_gauche"] = LandmarkPoint(hx - demi_largeur, hy, 0, 1)
    points["hanche_droite"] = LandmarkPoint(hx + demi_largeur, hy, 0, 1)
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

    # `echauffements` est dans la liste depuis qu'une detection definie la —
    # et nulle part ailleurs — a traverse tout le harnais sans etre vue.
    # `fonctions_publiques` filtre sur `objet.__module__`, donc les detections
    # que ce module **importe** d'`exercices` ne sont pas comptees deux fois :
    # seules celles qui lui sont propres s'ajoutent. C'est exactement la classe
    # d'oubli que l'introspection devait empecher, et elle ne l'empechait que
    # sur les modules qu'on avait pense a lui donner.
    fonctions = {
        **fonctions_publiques(exercices),
        **fonctions_publiques(echauffements),
        **fonctions_publiques(positions),
    }

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        # Les poses de geste viennent **apres** : les 5 000 premieres restent
        # celles d'avant, tirees de la meme graine.
        for indice in range(nombre + NOMBRE_POSES_DE_GESTE):
            corps = pose_au_hasard(rng) if indice < nombre else pose_bras_leves(rng)
            jetons = {
                nom: natif(fonction(corps)) for nom, fonction in fonctions.items()
            }
            ligne = {"landmarks": serialiser(corps), "jetons": jetons}
            fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    print(
        f"{nombre} poses au hasard et {NOMBRE_POSES_DE_GESTE} poses bras leves "
        f"ecrites dans {DESTINATION}"
    )
    print(f"{len(fonctions)} fonctions couvertes :")
    for nom in sorted(fonctions):
        print(f"  {nom}")


if __name__ == "__main__":
    main()
